"""Audit and synthetic gap verification for Acoustic-First Zero-Trust Metadata Pipeline
and ECHOSYNC_SIGNATURE verification system.
"""

import hashlib
from pathlib import Path
from unittest.mock import MagicMock

import echosync_core

from core.matching_engine.fingerprinting import FingerprintGenerator
from core.metadata.engine import MetadataResolutionEngine
from core.metadata.schemas import ResolutionRequest, ResolutionResult


def compute_prototype_signature(audio_stream_hash: str, title: str, artist: str) -> str:
    """Canonical prototype signature generator: HASH(audio_stream_hash + ":" + title + ":" + artist).

    In production: Computed via native Rust DSP (symphonia raw PCM frame stream + BLAKE3).
    """
    payload = f"{audio_stream_hash}:{title.strip().lower()}:{artist.strip().lower()}".encode()
    return hashlib.sha256(payload).hexdigest()


class SignatureAwareResolutionEngine(MetadataResolutionEngine):
    """Reference prototype implementing the proposed Stage 0 Zero-Trust Signature Verification."""

    def _execute_waterfall(self, request: ResolutionRequest) -> ResolutionResult:
        file_path = Path(request.file_path)
        raw_tags = echosync_core.extract_metadata(str(file_path)) or {}

        embedded_sig = raw_tags.get("echosync_signature")
        tag_title = raw_tags.get("title")
        tag_artist = raw_tags.get("artist")

        # Simulated raw stream hash (in production: computed via native symphonia Rust DSP)
        audio_stream_hash = raw_tags.get("audio_stream_hash", "pcm_raw_stream_hash_shawn123")

        # Stage 0: Zero-Trust Signature Verification
        if embedded_sig and tag_title and tag_artist and not request.ignore_cache:
            expected_sig = compute_prototype_signature(audio_stream_hash, tag_title, tag_artist)
            if embedded_sig == expected_sig:
                # Valid portable signature: accept canonical tags and bypass all remote egress
                return ResolutionResult(
                    media_id=request.media_id,
                    sync_id=request.sync_id,
                    title=tag_title,
                    artist=tag_artist,
                    album=raw_tags.get("album"),
                    year=raw_tags.get("year"),
                    track_number=raw_tags.get("track_number"),
                    disc_number=raw_tags.get("disc_number"),
                    musicbrainz_track_id=raw_tags.get("musicbrainz_track_id"),
                    confidence_score=1.0,
                    resolution_method="signature_verified",
                )
            # Signature mismatch: tampered tags! Disregard and fall through to standard waterfall

        return super()._execute_waterfall(request)


def test_corrupted_embedded_mbid_with_valid_signature_bypasses_remote_egress(monkeypatch, tmp_path):
    """Verify that a valid ECHOSYNC_SIGNATURE prevents remote API egress even if a stale/corrupted

    embedded MBID tag is present.
    """
    audio_file = tmp_path / "01 - There's Nothing Holdin' Me Back.flac"
    audio_file.write_bytes(b"dummy audio flac content")

    file_dur_ms = 199000
    audio_stream_hash = "pcm_stream_shawn_verified"
    true_title = "There's Nothing Holdin' Me Back"
    true_artist = "Shawn Mendes"
    canonical_mbid = "mbid-canonical-shawn-mendes"

    valid_sig = compute_prototype_signature(audio_stream_hash, true_title, true_artist)

    # File has corrupted embedded MBID (pointing to wrong song) but valid signature
    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": true_title,
            "artist": true_artist,
            "album": "Illuminate",
            "duration_ms": file_dur_ms,
            "channels": 2,
            "musicbrainz_id": "corrupted-mbid-wrong-track",
            "musicbrainz_track_id": canonical_mbid,
            "audio_stream_hash": audio_stream_hash,
            "echosync_signature": valid_sig,
        },
    )

    dummy_cp = "S" * 60
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_cp, file_dur_ms / 1000.0),
    )

    mock_acoustid = MagicMock()
    mock_mb = MagicMock()

    engine = SignatureAwareResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="track_sig_1",
        file_path=audio_file,
        baseline_title=true_title,
        baseline_artist=true_artist,
    )

    result = engine.resolve_track(req)

    # 1. Signature verification succeeds with 1.0 confidence
    assert result.resolution_method == "signature_verified"
    assert result.title == true_title
    assert result.artist == true_artist
    assert result.musicbrainz_track_id == canonical_mbid
    assert result.confidence_score == 1.0

    # 2. Remote AcoustID and MusicBrainz APIs MUST NOT be called (zero network egress)
    assert not mock_acoustid.resolve_fingerprint_details.called
    assert not mock_mb.get_metadata.called


def test_mismatched_signature_tampered_metadata_falls_back_to_acoustic_resolution(
    monkeypatch, tmp_path
):
    """Verify that when metadata has been tampered with after signing (signature mismatch),

    the engine refuses the untrusted metadata and falls back to full acoustic resolution.
    """
    audio_file = tmp_path / "01 - There's Nothing Holdin' Me Back.flac"
    audio_file.write_bytes(b"dummy audio flac content")

    file_dur_ms = 199000
    audio_stream_hash = "pcm_stream_shawn_verified"
    true_title = "There's Nothing Holdin' Me Back"
    true_artist = "Shawn Mendes"
    recovered_mbid = "mbid-acoustid-recovered-correct"

    # Signature was generated for the original true track
    original_sig = compute_prototype_signature(audio_stream_hash, true_title, true_artist)

    # Attacker or bad tagger modified embedded title to "Tampered Title"
    tampered_title = "Tampered Fake Title"
    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": tampered_title,
            "artist": true_artist,
            "album": "Fake Album",
            "duration_ms": file_dur_ms,
            "channels": 2,
            "audio_stream_hash": audio_stream_hash,
            "echosync_signature": original_sig,  # Signature now mismatches the title!
        },
    )

    dummy_cp = "T" * 60
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_cp, file_dur_ms / 1000.0),
    )

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid-recovered-999",
        "mbids": [recovered_mbid],
    }

    mock_mb = MagicMock()
    mock_mb.get_metadata.return_value = {
        "title": true_title,
        "artist": true_artist,
        "album": "Illuminate",
        "recording_id": recovered_mbid,
        "duration_ms": file_dur_ms,
        "release_group": {"primary_type": "Album"},
    }

    engine = SignatureAwareResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="track_tampered_1",
        file_path=audio_file,
        baseline_title=None,
        baseline_artist=None,
    )

    result = engine.resolve_track(req)

    # 1. Signature mismatch falls through and resolves via AcoustID
    assert result.resolution_method == "acoustid"
    assert result.title == true_title
    assert result.artist == true_artist
    assert result.musicbrainz_track_id == recovered_mbid
    assert result.acoustid_id == "acoustid-recovered-999"

    # 2. Remote AcoustID and MusicBrainz APIs WERE called to recover truth
    assert mock_acoustid.resolve_fingerprint_details.called
    assert mock_mb.get_metadata.called
