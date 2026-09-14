"""Integration and unit tests for the Proportional AcoustID Veto and Resolution Hierarchy patch.

Verifies:
1. should_bypass_filename_trust_gate unit rules.
2. Unsigned files with indisputable AcoustID match (score >= 0.92, delta <= 1.0s) override
   conflicting or generic filenames without routing to the Review Queue.
3. Signed files carrying ECHOSYNC_SIGNATURE preserve user-curated metadata on acoustic divergence
   and route a ReviewTask to working.db without mutating physical tags.
4. Untagged files with embedded MBID skip Stage 1 fast-path directly to Chromaprint/AcoustID.
5. tag_file_verified strips placeholder 'Unknown' strings from physical tag writes.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import echosync_core

from core.matching_engine.fingerprinting import FingerprintGenerator
from core.matching_engine.trust_gate import (
    should_bypass_filename_trust_gate,
    verify_title_trust_gate,
)
from core.metadata.engine import MetadataResolutionEngine
from core.metadata.schemas import ResolutionRequest
from database.repositories.task_repository import TaskRepository
from services.metadata_enhancer import RetroactiveEnhancer


def test_should_bypass_filename_trust_gate_unit():
    """Verify trust gate bypass matrix for AcoustID veto."""
    # Indisputable match without signature -> Bypass
    assert (
        should_bypass_filename_trust_gate(
            acoustid_score=0.95,
            duration_delta_sec=0.4,
            has_signature=False,
            has_identifiable_tags=False,
        )
        is True
    )

    # Boundary: exactly 0.92 and 1.0s delta -> Bypass
    assert (
        should_bypass_filename_trust_gate(
            acoustid_score=0.92,
            duration_delta_sec=1.0,
            has_signature=False,
        )
        is True
    )

    # Signed file carries human curation -> Never bypass
    assert (
        should_bypass_filename_trust_gate(
            acoustid_score=0.99,
            duration_delta_sec=0.1,
            has_signature=True,
        )
        is False
    )

    # Score below threshold -> No bypass
    assert (
        should_bypass_filename_trust_gate(
            acoustid_score=0.91,
            duration_delta_sec=0.5,
            has_signature=False,
        )
        is False
    )

    # Duration delta too wide -> No bypass
    assert (
        should_bypass_filename_trust_gate(
            acoustid_score=0.98,
            duration_delta_sec=1.2,
            has_signature=False,
        )
        is False
    )


def test_verify_title_trust_gate_with_bypass():
    """Verify verify_title_trust_gate respects bypass_filename_check."""
    # Without bypass: conflicting filename fails trust gate
    passed = verify_title_trust_gate(
        candidate_title="Bohemian Rhapsody",
        baseline_title="Track 01",
        filename="01 - completely wrong.mp3",
        bypass_filename_check=False,
    )
    assert passed is False

    # With bypass: passes immediately
    passed_bypass = verify_title_trust_gate(
        candidate_title="Bohemian Rhapsody",
        baseline_title="Track 01",
        filename="01 - completely wrong.mp3",
        bypass_filename_check=True,
    )
    assert passed_bypass is True


def test_unsigned_acoustid_veto_overrides_conflicting_filename(monkeypatch, tmp_path):
    """Unsigned file with conflicting filename auto-applies AcoustID match (score >= 0.92, delta <= 1.0s)."""
    audio_file = tmp_path / "01 - Completely Wrong Song.mp3"
    audio_file.write_bytes(b"dummy audio content")

    file_dur_ms = 210000  # 210.0s

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "",
            "artist": "",
            "duration_ms": file_dur_ms,
            "channels": 2,
        },
    )

    dummy_chromaprint = "C" * 60
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_chromaprint, file_dur_ms / 1000.0),
    )

    cand_meta = {
        "title": "Acoustic Ground Truth",
        "artist": "Verified Artist",
        "album": "Greatest Hits",
        "duration_ms": file_dur_ms + 300,  # 0.3s delta
        "release_id": "rel-123",
        "release_group": {"primary_type": "Album"},
    }

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid-veto-test",
        "score": 0.96,
        "recordings": [
            {
                "id": "mbid-winner-veto",
                "title": "Acoustic Ground Truth",
                "artist": "Verified Artist",
                "duration": (file_dur_ms + 300) / 1000.0,
                "score": 0.96,
            }
        ],
        "mbids": ["mbid-winner-veto"],
    }

    mock_mb = MagicMock()
    mock_mb.get_metadata.return_value = cand_meta

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="media_veto_1",
        file_path=audio_file,
        baseline_title="Completely Wrong Song",
        baseline_artist="Wrong Artist",
    )

    result = engine.resolve_track(req)

    assert result is not None
    assert result.resolution_method == "acoustid"
    assert result.title == "Acoustic Ground Truth"
    assert result.artist == "Verified Artist"
    assert result.musicbrainz_track_id == "mbid-winner-veto"
    assert result.confidence_score == 0.95


def test_signed_file_divergence_routes_to_review_queue(monkeypatch, tmp_path):
    """Signed files with ECHOSYNC_SIGNATURE preserve tags and stage ReviewTask on divergence."""
    audio_file = tmp_path / "song_curated.mp3"
    audio_file.write_bytes(b"dummy audio content")

    file_dur_ms = 180000

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "User Curated Title",
            "artist": "User Curated Artist",
            "echosync_signature": "SIG_VALID_12345",
            "duration_ms": file_dur_ms,
            "channels": 2,
        },
    )
    monkeypatch.setattr(
        echosync_core,
        "verify_audio_signature",
        lambda path, title, artist, sig: True,
    )

    dummy_chromaprint = "D" * 60
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_chromaprint, file_dur_ms / 1000.0),
    )

    cand_meta = {
        "title": "Radically Different Title",
        "artist": "Different Artist",
        "album": "Different Album",
        "duration_ms": file_dur_ms,
        "release_id": "rel-diff",
        "release_group": {"primary_type": "Album"},
    }

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid-diff-test",
        "score": 0.98,
        "recordings": [
            {
                "id": "mbid-diff-1",
                "title": "Radically Different Title",
                "artist": "Different Artist",
                "duration": file_dur_ms / 1000.0,
                "score": 0.98,
            }
        ],
        "mbids": ["mbid-diff-1"],
    }

    mock_mb = MagicMock()
    mock_mb.get_metadata.return_value = cand_meta

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    staged_tasks = []

    def mock_create_review_task(**kwargs):
        staged_tasks.append(kwargs)
        return MagicMock()

    monkeypatch.setattr(TaskRepository, "create_review_task", mock_create_review_task)

    req = ResolutionRequest(
        media_id="media_signed_1",
        file_path=audio_file,
        baseline_title="User Curated Title",
        baseline_artist="User Curated Artist",
        ignore_cache=True,  # Force past Stage 0 cache to evaluate AcoustID divergence
    )

    result = engine.resolve_track(req)

    # Invariant: Signed file metadata preserved
    assert result.resolution_method == "signature_verified"
    assert result.title == "User Curated Title"
    assert result.artist == "User Curated Artist"
    assert result.confidence_score == 1.0

    # Invariant: Divergence staged to ReviewTask
    assert len(staged_tasks) == 1
    task_kwargs = staged_tasks[0]
    assert task_kwargs["action"] == "RESOLVE_METADATA_CONFLICT"
    assert task_kwargs["track_data"]["reason"] == "SIGNED_METADATA_DIVERGENCE"
    assert task_kwargs["track_data"]["current_title"] == "User Curated Title"
    assert task_kwargs["track_data"]["proposed_title"] == "Radically Different Title"


def test_tampered_signature_with_high_acoustid_score_auto_applies(monkeypatch, tmp_path):
    """Corrupted/tampered ECHOSYNC_SIGNATURE fails verification and auto-applies AcoustID match without ReviewTask."""
    audio_file = tmp_path / "07 - My First Guitar (13).flac"
    audio_file.write_bytes(b"dummy audio content")

    file_dur_ms = 220000

    # Tag header contains stale/tampered ECHOSYNC_SIGNATURE
    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "My First Guitar (5)",
            "artist": "Bon Jovi",
            "album": "Forever",
            "echosync_signature": "STALE_TAMPERED_SIG_HEX",
            "duration_ms": file_dur_ms,
            "channels": 2,
        },
    )

    # Cryptographic verification fails
    monkeypatch.setattr(
        echosync_core,
        "verify_audio_signature",
        lambda path, title, artist, sig: False,
    )

    dummy_chromaprint = "T" * 60
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_chromaprint, file_dur_ms / 1000.0),
    )

    cand_meta = {
        "title": "Living Proof",
        "artist": "Bon Jovi",
        "album": "Forever",
        "duration_ms": file_dur_ms + 200,
        "release_id": "rel-bonjovi-living-proof",
        "release_group": {"primary_type": "Album"},
    }

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid-bonjovi-lp",
        "score": 0.97,
        "recordings": [
            {
                "id": "mbid-living-proof",
                "title": "Living Proof",
                "artist": "Bon Jovi",
                "duration": (file_dur_ms + 200) / 1000.0,
                "score": 0.97,
            }
        ],
        "mbids": ["mbid-living-proof"],
    }

    mock_mb = MagicMock()
    mock_mb.get_metadata.return_value = cand_meta

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    staged_tasks = []

    def mock_create_review_task(**kwargs):
        staged_tasks.append(kwargs)
        return MagicMock()

    monkeypatch.setattr(TaskRepository, "create_review_task", mock_create_review_task)

    req = ResolutionRequest(
        media_id="media_tampered_1",
        file_path=audio_file,
        baseline_title="My First Guitar (5)",
        baseline_artist="Bon Jovi",
        baseline_album="Forever",
    )

    result = engine.resolve_track(req)

    # Invariant: Invalid signature is voided; AcoustID ground truth auto-applies
    assert result is not None
    assert result.resolution_method == "acoustid"
    assert result.title == "Living Proof"
    assert result.artist == "Bon Jovi"
    assert result.musicbrainz_track_id == "mbid-living-proof"
    assert result.confidence_score == 0.95

    # Invariant: NO ReviewTask staged because the signature was corrupted/void
    assert len(staged_tasks) == 0


def test_untagged_file_embedded_mbid_skipped_to_chromaprint(monkeypatch, tmp_path):
    """Untagged/unknown tracks bypass Stage 1 embedded MBID straight to Chromaprint/AcoustID."""
    audio_file = tmp_path / "track01.mp3"
    audio_file.write_bytes(b"dummy audio content")

    file_dur_ms = 195000

    # File has stale embedded MBID, but missing / unknown artist & generic title
    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Track 01",  # Generic title
            "artist": "Unknown Artist",  # Unknown artist
            "musicbrainz_trackid": "mbid-poisoned-disc-rip",
            "duration_ms": file_dur_ms,
            "channels": 2,
        },
    )

    dummy_chromaprint = "E" * 60
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_chromaprint, file_dur_ms / 1000.0),
    )

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid-clean-test",
        "score": 0.95,
        "recordings": [
            {
                "id": "mbid-acoustic-true",
                "title": "True Song Title",
                "artist": "True Artist",
                "duration": file_dur_ms / 1000.0,
                "score": 0.95,
            }
        ],
        "mbids": ["mbid-acoustic-true"],
    }

    mock_mb = MagicMock()

    def mock_mb_get(mbid):
        if mbid == "mbid-poisoned-disc-rip":
            pytest.fail("Stage 1 embedded MBID should have been bypassed for untagged track!")
        if mbid == "mbid-acoustic-true":
            return {
                "title": "True Song Title",
                "artist": "True Artist",
                "album": "True Album",
                "duration_ms": file_dur_ms,
                "release_id": "rel-true",
                "release_group": {"primary_type": "Album"},
            }
        return None

    mock_mb.get_metadata.side_effect = mock_mb_get

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="media_untagged_1",
        file_path=audio_file,
    )

    result = engine.resolve_track(req)

    assert result is not None
    assert result.resolution_method == "acoustid"
    assert result.title == "True Song Title"
    assert result.artist == "True Artist"
    assert result.musicbrainz_track_id == "mbid-acoustic-true"


def test_tag_file_verified_strips_unknown_placeholders(tmp_path, monkeypatch):
    """tag_file_verified must never write 'Unknown' placeholder strings to physical file tags."""
    audio_file = tmp_path / "test_write.mp3"
    audio_file.write_bytes(b"dummy audio content")

    written_tags = {}

    def mock_write(path, tags):
        written_tags.update(tags)

    def mock_read(path):
        return dict(written_tags)

    monkeypatch.setattr(echosync_core, "write_metadata", mock_write)
    monkeypatch.setattr(echosync_core, "read_metadata", mock_read)

    enhancer = RetroactiveEnhancer()

    # Metadata with genuine title and placeholder artist/album
    enhancer.tag_file_verified(
        audio_file,
        {
            "title": "Valid Title",
            "artist": "Unknown Artist",
            "album": "Unknown Album",
            "isrc": "US1234567890",
        },
    )

    # Assert 'Unknown Artist' and 'Unknown Album' were stripped before writing
    assert "artist" not in written_tags
    assert "album" not in written_tags
    assert written_tags["title"] == "Valid Title"
    assert written_tags["isrc"] == "US1234567890"

    # All placeholders -> write skipped
    written_tags.clear()
    res = enhancer.tag_file_verified(
        audio_file,
        {
            "title": "Unknown Title",
            "artist": "Unknown",
            "album": "Unknown",
        },
    )
    assert res == {}
    assert len(written_tags) == 0
