"""Tests for AcoustID candidate arbitration (global release count canonical weighting)
and Stage 0 signature gate bypass under force mode.
"""

from unittest.mock import MagicMock

import echosync_core
from core.matching_engine.fingerprinting import FingerprintGenerator
from core.metadata.engine import MetadataResolutionEngine
from core.metadata.schemas import ResolutionRequest


def test_acoustid_candidate_arbitration_canonical_release_count(monkeypatch, tmp_path):
    """Verify Stage 3 scores all candidates without early termination, and canonical weighting
    (release_count >= 20 -> +10.0 bonus) allows the original canonical artist (Evanescence)
    to outrank remixers/covers (Da Tweekaz).
    """
    audio_file = tmp_path / "bring_me_to_life.mp3"
    audio_file.write_bytes(b"dummy audio data for testing")

    file_dur_ms = 237000

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Bring Me To Life",
            "artist": "Evanescence",
            "duration_ms": file_dur_ms,
            "channels": 2,
        },
    )

    dummy_chromaprint = "A" * 60
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_chromaprint, file_dur_ms / 1000.0),
    )

    cand_da_tweekaz = {
        "title": "Bring Me To Life",
        "artist": "Da Tweekaz",
        "album": "Da Tweekaz Bootleg",
        "duration_ms": file_dur_ms,
        "release_id": "rel-tweekaz-1",
        "releases": [
            {"id": "rel-tweekaz-1", "release_group": {"id": "rg-tweekaz-1", "primary_type": "Single"}}
        ],
        "release_group": {"id": "rg-tweekaz-1", "title": "Da Tweekaz Bootleg", "primary_type": "Single"},
    }

    cand_evanescence = {
        "title": "Bring Me To Life",
        "artist": "Evanescence",
        "album": "Fallen",
        "duration_ms": file_dur_ms,
        "release_id": "rel-fallen-1",
        "releases": [
            {"id": f"rel-ev-{i}", "release_group": {"id": f"rg-ev-{i % 3}", "primary_type": "Album"}}
            for i in range(25)
        ],
        "release_group": {"id": "rg-ev-0", "title": "Fallen", "primary_type": "Album"},
    }

    mock_mb = MagicMock()
    mock_mb.get_metadata.side_effect = lambda mbid: (
        cand_da_tweekaz if mbid == "mbid-da-tweekaz"
        else cand_evanescence if mbid == "mbid-evanescence"
        else None
    )

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "aid-bring-me-to-life",
        "mbids": ["mbid-da-tweekaz", "mbid-evanescence"],
        "recordings": [
            {
                "id": "mbid-da-tweekaz",
                "title": "Bring Me To Life",
                "artist": "Da Tweekaz",
                "score": 96,
                "duration": file_dur_ms / 1000.0,
            },
            {
                "id": "mbid-evanescence",
                "title": "Bring Me To Life",
                "artist": "Evanescence",
                "score": 95,
                "duration": file_dur_ms / 1000.0,
            },
        ],
    }

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="media_test_arbitration",
        file_path=audio_file,
        baseline_title="Bring Me To Life",
        baseline_artist="Evanescence",
    )

    result = engine.resolve_track(req)

    # Evanescence must win over Da Tweekaz
    assert result.musicbrainz_track_id == "mbid-evanescence"
    assert result.artist == "Evanescence"
    assert result.title == "Bring Me To Life"
    assert result.resolution_method == "acoustid"

    # Total confidence score must be strictly bounded in [0.0, 1.0]
    assert 0.0 <= result.confidence_score <= 1.0

    # Verify both candidates were scored and logged in diagnostics
    diagnostics = result.diagnostics or req._diagnostics
    stage3_diag = next((d for d in diagnostics if d.get("stage") == "Stage 3: AcoustID"), None)
    assert stage3_diag is not None
    candidates = stage3_diag.get("candidates") or []
    assert len(candidates) == 2

    ev_diag = next(c for c in candidates if c.get("mbid") == "mbid-evanescence")
    tweekaz_diag = next(c for c in candidates if c.get("mbid") == "mbid-da-tweekaz")

    assert ev_diag.get("status") == "WINNER"
    assert ev_diag.get("canonical_weight") == 10.0
    assert ev_diag.get("release_count") >= 20
    assert 0.0 <= ev_diag.get("total_score") <= 100.0

    assert tweekaz_diag.get("status") == "RUNNER_UP"
    assert tweekaz_diag.get("canonical_weight") == 0.0
    assert tweekaz_diag.get("release_count") < 5
    assert 0.0 <= tweekaz_diag.get("total_score") <= 100.0


def test_stage0_signature_bypass_on_force_recheck(monkeypatch, tmp_path):
    """Verify Stage 0 Zero-Trust Signature Gate is bypassed when force_recheck or force_mode is active."""
    audio_file = tmp_path / "signature_test.mp3"
    audio_file.write_bytes(b"dummy audio for signature test")

    file_dur_ms = 180000

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "My Track",
            "artist": "Original Artist",
            "echosync_signature": "valid_mock_signature_123",
            "musicbrainz_id": "mbid-existing-111",
            "duration_ms": file_dur_ms,
            "channels": 2,
        },
    )

    if hasattr(echosync_core, "verify_audio_signature"):
        monkeypatch.setattr(echosync_core, "verify_audio_signature", lambda *args, **kwargs: True)

    dummy_chromaprint = "B" * 60
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_chromaprint, file_dur_ms / 1000.0),
    )

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "aid-force-test",
        "mbids": ["mbid-new-222"],
        "recordings": [
            {
                "id": "mbid-new-222",
                "title": "My Track (Remastered)",
                "artist": "Original Artist",
                "score": 98,
                "duration": file_dur_ms / 1000.0,
            }
        ],
    }

    mock_mb = MagicMock()
    mock_mb.get_metadata.return_value = {
        "title": "My Track (Remastered)",
        "artist": "Original Artist",
        "album": "Greatest Hits",
        "duration_ms": file_dur_ms,
        "release_id": "rel-hits-1",
        "release_group": {"id": "rg-hits-1", "primary_type": "Album"},
    }

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    # 1. Unforced: Stage 0 short-circuits with signature_verified
    req_unforced = ResolutionRequest(
        media_id="media_unforced",
        file_path=audio_file,
        baseline_title="My Track",
        baseline_artist="Original Artist",
        force_mode=False,
        force_recheck=False,
    )
    result_unforced = engine.resolve_track(req_unforced)
    assert result_unforced.resolution_method.startswith("signature_verified")
    mock_acoustid.resolve_fingerprint_details.assert_not_called()

    diagnostics_unforced = result_unforced.diagnostics or req_unforced._diagnostics
    stage0_unforced = next((d for d in diagnostics_unforced if d.get("stage") == "Stage 0: Signature Gate"), None)
    assert stage0_unforced is not None
    assert stage0_unforced.get("status") == "hit"

    # 2. Forced: Stage 0 signature gate is bypassed and waterfall continues to AcoustID
    req_forced = ResolutionRequest(
        media_id="media_forced",
        file_path=audio_file,
        baseline_title="My Track",
        baseline_artist="Original Artist",
        force_recheck=True,
    )
    result_forced = engine.resolve_track(req_forced)

    # Remote lookup must be executed
    assert mock_acoustid.resolve_fingerprint_details.called
    assert result_forced.resolution_method == "acoustid"
    assert result_forced.musicbrainz_track_id == "mbid-new-222"

    diagnostics_forced = result_forced.diagnostics or req_forced._diagnostics
    stage0_forced = next((d for d in diagnostics_forced if d.get("stage") == "Stage 0: Signature Gate"), None)
    assert stage0_forced is not None
    assert stage0_forced.get("status") == "bypassed"
