"""Tests for Native Content-Addressed Acoustic Proof (ECHOSYNC_SIGNATURE).

Validates pure PCM stream hashing, deterministic BLAKE3 signature derivation,
tag tampering rejection, container jitter immunity, and Stage 0 zero-trust verification.
"""

from __future__ import annotations

import wave
from pathlib import Path
from unittest.mock import MagicMock

import echosync_core

from core.metadata.engine import MetadataResolutionEngine
from core.metadata.schemas import ResolutionRequest
from core.nexus_framework.sdk import verify_file_signature


def _create_synthetic_audio(path: Path, duration_sec: float = 1.0, channels: int = 2) -> None:
    """Generate a clean uncompressed PCM WAV file."""
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        # Generate predictable non-silent interleaved PCM samples
        sample_bytes = b"\x01\x00\x02\x00" if channels == 2 else b"\x01\x00"
        wf.writeframes(sample_bytes * int(44100 * duration_sec))


def test_hash_pcm_stream_and_signature_derivation(tmp_path: Path):
    """Verify native PCM stream hashing and deterministic signature derivation."""
    audio_path = tmp_path / "stream_test.wav"
    _create_synthetic_audio(audio_path, duration_sec=0.5)

    pcm_hash = echosync_core.hash_pcm_stream(str(audio_path))
    assert isinstance(pcm_hash, str) and len(pcm_hash) == 64
    assert all(c in "0123456789abcdef" for c in pcm_hash)

    title = "Bohemian Rhapsody"
    artist = "Queen"
    signature = echosync_core.generate_audio_signature(str(audio_path), title, artist)
    assert isinstance(signature, str) and len(signature) == 64
    assert all(c in "0123456789abcdef" for c in signature)

    # Determinism check: repeated generation yields identical signature
    sig2 = echosync_core.generate_audio_signature(str(audio_path), title, artist)
    assert signature == sig2
    assert echosync_core.verify_audio_signature(str(audio_path), title, artist, signature) is True


def test_verify_audio_signature_tamper_detection(tmp_path: Path):
    """Verify that tampering with title or artist by even 1 character rejects verification."""
    audio_path = tmp_path / "tamper_test.wav"
    _create_synthetic_audio(audio_path, duration_sec=0.5)

    title = "Starboy"
    artist = "The Weeknd"
    valid_sig = echosync_core.generate_audio_signature(str(audio_path), title, artist)

    # 1. Exact match passes
    assert echosync_core.verify_audio_signature(str(audio_path), title, artist, valid_sig) is True

    # 2. Tampered title by 1 char fails
    assert (
        echosync_core.verify_audio_signature(str(audio_path), "Starboy ", artist, valid_sig)
        is True  # Trimmed whitespace passes
    )
    assert (
        echosync_core.verify_audio_signature(str(audio_path), "Starboy!", artist, valid_sig)
        is False
    )
    assert (
        echosync_core.verify_audio_signature(str(audio_path), "starboy", artist, valid_sig)
        is True  # Case-insensitive canonical form
    )
    assert (
        echosync_core.verify_audio_signature(str(audio_path), "Starboz", artist, valid_sig)
        is False
    )

    # 3. Tampered artist fails
    assert (
        echosync_core.verify_audio_signature(str(audio_path), title, "The Weekndd", valid_sig)
        is False
    )


def test_container_jitter_immunity(tmp_path: Path):
    """Verify container metadata jitter immunity: changing tags does NOT alter PCM hash."""
    audio_path = tmp_path / "jitter_test.wav"
    _create_synthetic_audio(audio_path, duration_sec=0.5)

    initial_pcm_hash = echosync_core.hash_pcm_stream(str(audio_path))

    # Write initial metadata
    echosync_core.write_metadata(
        str(audio_path),
        {
            "title": "Initial Title",
            "artist": "Initial Artist",
            "album": "Initial Album",
        },
    )
    hash_after_tags = echosync_core.hash_pcm_stream(str(audio_path))
    assert hash_after_tags == initial_pcm_hash, "Adding tags mutated the decoded PCM hash!"

    # Overwrite with different metadata and comments
    echosync_core.write_metadata(
        str(audio_path),
        {
            "title": "Completely Different Title",
            "artist": "New Artist",
            "album": "Deluxe Remastered Edition",
            "comment": "Arbitrary container padding data " * 20,
        },
    )
    hash_after_tag_rewrite = echosync_core.hash_pcm_stream(str(audio_path))
    assert hash_after_tag_rewrite == initial_pcm_hash, (
        "Rewriting tags mutated the decoded PCM hash!"
    )


def test_stage0_signature_gate_short_circuit(tmp_path: Path):
    """Verify Stage 0 Zero-Trust Signature Gate verifies physical signature and bypasses remote calls."""
    audio_path = tmp_path / "stage0_test.wav"
    _create_synthetic_audio(audio_path, duration_sec=1.0)

    title = "Authoritative Track"
    artist = "Verified Artist"
    album = "Verified Album"

    sig = echosync_core.generate_audio_signature(str(audio_path), title, artist)

    # Embed ECHOSYNC_SIGNATURE along with baseline tags
    echosync_core.write_metadata(
        str(audio_path),
        {
            "title": title,
            "artist": artist,
            "album": album,
            "ECHOSYNC_SIGNATURE": sig,
            "musicbrainz_id": "11111111-2222-3333-4444-555555555555",
        },
    )

    # Mock providers to ensure NO remote network egress occurs
    mock_acoustid = MagicMock()
    mock_mb = MagicMock()

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id=1,
        sync_id="test_sync",
        file_path=audio_path,
        baseline_title=title,
        baseline_artist=artist,
        baseline_album=album,
    )

    result = engine.resolve_track(req)

    assert result.confidence_score == 1.0
    assert result.resolution_method.startswith("signature_verified")
    assert result.title == title
    assert result.artist == artist
    assert result.musicbrainz_track_id == "11111111-2222-3333-4444-555555555555"

    # Confirm AcoustID and MusicBrainz were NEVER called
    mock_acoustid.resolve_fingerprint_details.assert_not_called()
    mock_mb.get_metadata.assert_not_called()


def test_nexus_sdk_verify_file_signature(tmp_path: Path):
    """Verify Nexus Framework SDK helper verify_file_signature."""
    audio_path = tmp_path / "sdk_test.wav"
    _create_synthetic_audio(audio_path, duration_sec=0.5)

    title = "SDK Anthem"
    artist = "Nexus Project"

    # Before signature tag is written, returns False
    assert verify_file_signature(audio_path, title, artist) is False

    # Write valid signature tag
    sig = echosync_core.generate_audio_signature(str(audio_path), title, artist)
    echosync_core.write_metadata(
        str(audio_path),
        {
            "title": title,
            "artist": artist,
            "ECHOSYNC_SIGNATURE": sig,
        },
    )

    assert verify_file_signature(audio_path, title, artist) is True
    assert verify_file_signature(audio_path, "Tampered Title", artist) is False
