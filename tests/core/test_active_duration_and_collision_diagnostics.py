"""Tests for silence-trimmed active_duration_ms (Rust + MatchingEngine) and collision diagnostics."""

import math
import struct
import wave
from pathlib import Path

import echosync_core

from core.db.echo_sync_track import EchosyncTrack
from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.matching_engine.scoring_profile import ExactSyncProfile
from services.playlists_api import resolve_duplicate_matches


def _write_wav_with_trailing_silence(path: Path, tone_sec: float, silence_sec: float, sample_rate: int = 44100) -> None:
    n_tone = int(tone_sec * sample_rate)
    n_silence = int(silence_sec * sample_rate)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        for i in range(n_tone):
            sample = int(0.4 * 32767 * math.sin(2.0 * math.pi * 440.0 * i / sample_rate))
            frames.extend(struct.pack("<h", sample))
        frames.extend(b"\x00\x00" * n_silence)
        wf.writeframes(bytes(frames))


def test_rust_measure_active_duration_strips_trailing_silence(tmp_path: Path):
    wav_path = tmp_path / "padded.wav"
    # 2.0s of 440Hz tone + 5.5s of dead silence = 7.5s total, ~2.0s active
    _write_wav_with_trailing_silence(wav_path, tone_sec=2.0, silence_sec=5.5)

    fp, dur_sec, pcm_hash, active_ms = echosync_core.fingerprint_hash_and_active_duration(str(wav_path), True)
    assert fp
    assert pcm_hash
    assert 7400 <= round(dur_sec * 1000) <= 7600
    assert 1900 <= active_ms <= 2100

    assert 1900 <= echosync_core.measure_active_duration(str(wav_path)) <= 2100


def test_matching_engine_accepts_silence_padded_track_and_rejects_true_edit():
    engine = WeightedMatchingEngine(ExactSyncProfile())
    spotify_track = EchosyncTrack(
        raw_title="Dream On",
        title="Dream On",
        artist_name="Aerosmith",
        album_title="Aerosmith",
        duration_ms=267000,
    )

    # 1. Local track with +12.0s of trailing silence -> active_duration_ms matches Spotify
    padded_local = EchosyncTrack(
        raw_title="Dream On",
        title="Dream On",
        artist_name="Aerosmith",
        album_title="Aerosmith",
        duration_ms=279000,
        extra_metadata={"active_duration_ms": 267100},
    )
    padded_res = engine.calculate_match(spotify_track, padded_local)
    assert padded_res.confidence_score >= 85.0

    # 2. Local track with +12.0s of actual music (true alternate cut) -> active_duration_ms is still +12s off -> rejected
    true_edit_local = EchosyncTrack(
        raw_title="Dream On",
        title="Dream On",
        artist_name="Aerosmith",
        album_title="Aerosmith",
        duration_ms=279000,
        extra_metadata={"active_duration_ms": 278900},
    )
    edit_res = engine.calculate_match(spotify_track, true_edit_local)
    assert edit_res.confidence_score < 85.0


def test_resolve_duplicate_matches_updates_status_and_diagnostics():
    tracks = [
        {
            "title": "Just so You Know",
            "artist": "Blacklite District",
            "status": "found",
            "library_match": "Found",
            "matched_track_id": 42,
            "match_score": 100.0,
            "candidate_matches": [{"id": 42, "score": 100.0}],
            "match_diagnostics": {
                "best_match": {"track_id": 42, "composite_score": 100.0},
                "candidates": [{"track_id": 42, "accepted": True, "rejection_reason": None}],
            },
        },
        {
            "title": "Just so You Know",
            "artist": "Cover Band",
            "status": "found",
            "library_match": "Found",
            "matched_track_id": 42,
            "match_score": 97.0,
            "candidate_matches": [{"id": 42, "score": 97.0}],
            "match_diagnostics": {
                "best_match": {"track_id": 42, "composite_score": 97.0},
                "candidates": [{"track_id": 42, "accepted": True, "rejection_reason": None}],
            },
        },
    ]

    resolved = resolve_duplicate_matches(tracks)
    assert resolved[0]["status"] == "found"
    assert resolved[0]["matched_track_id"] == 42

    loser = resolved[1]
    assert loser["matched_track_id"] is None
    assert loser["status"] == "not_found"
    assert loser["library_match"] == "Not Found"
    assert loser["match_diagnostics"]["best_match"] is None
    assert loser["match_diagnostics"]["candidates"][0]["accepted"] is False
    assert "Collision:" in loser["match_diagnostics"]["candidates"][0]["rejection_reason"]


def test_evaluate_single_track_diagnostics_uses_active_duration(tmp_path: Path):
    from database.music_database import Album, Artist, Base, LocalMedia, MusicDatabase, Track
    from services.playlist_sync import evaluate_single_track_diagnostics

    db = MusicDatabase(str(tmp_path / "music.db"))
    Base.metadata.create_all(db.engine)
    with db.session_scope() as session:
        artist = Artist(name="Aerosmith")
        session.add(artist)
        session.flush()
        album = Album(artist_id=artist.id, title="Aerosmith")
        session.add(album)
        session.flush()
        track = Track(
            sync_id="tr_aero",
            artist_id=artist.id,
            album_id=album.id,
            title="Dream On",
            duration=272470,
        )
        session.add(track)
        session.flush()
        session.add(
            LocalMedia(
                media_id="lm_aero",
                track_id=track.id,
                file_path="/music/dream_on.flac",
                duration_ms=272470,
                active_duration_ms=267100,
            )
        )

    trace = evaluate_single_track_diagnostics(
        title="Dream On",
        artist="Aerosmith",
        duration_ms=267000,
        album="Aerosmith",
        db=db,
    )
    assert trace["best_match"] is not None
    assert trace["best_match"]["accepted"] is True
    assert trace["best_match"]["composite_score"] >= 85.0


def test_matching_engine_accepts_remixer_in_source_title_without_remix_word():
    """Source titles like 'I Took A Pill In Ibiza - Seeb' should match 'SeeB Remix' when duration aligns."""
    engine = WeightedMatchingEngine(ExactSyncProfile())

    source_ibiza = EchosyncTrack(
        raw_title="I Took A Pill In Ibiza - Seeb",
        artist_name="Mike Posner",
        duration_ms=199000,
    )
    cand_ibiza = EchosyncTrack(
        raw_title="I Took a Pill in Ibiza (SeeB Remix)",
        title="I Took a Pill in Ibiza",
        edition="SeeB Remix",
        artist_name="Mike Posner",
        duration_ms=199000,
    )
    res_ibiza = engine.calculate_match(source_ibiza, cand_ibiza, context="sync")
    assert res_ibiza.passed_version_check is True
    assert res_ibiza.confidence_score >= 85.0

    source_monster = EchosyncTrack(
        raw_title="Monster (Dotexe )",
        artist_name="Meg & Dia",
        duration_ms=223000,
    )
    cand_monster = EchosyncTrack(
        raw_title="Monster (dotEXE remix)",
        title="Monster",
        edition="dotEXE remix",
        artist_name="Meg & Dia",
        duration_ms=223020,
    )
    res_monster = engine.calculate_match(source_monster, cand_monster, context="sync")
    assert res_monster.passed_version_check is True
    assert res_monster.confidence_score >= 85.0

    # Negative check: original source without remixer name must still reject the remix
    source_orig = EchosyncTrack(
        raw_title="I Took A Pill In Ibiza",
        artist_name="Mike Posner",
        duration_ms=199000,
    )
    res_orig = engine.calculate_match(source_orig, cand_ibiza, context="sync")
    assert res_orig.passed_version_check is False
    assert res_orig.confidence_score == 0.0

    # Generic candidate edition='Remix' with remixer in remixers or file_path
    cand_generic_remix = EchosyncTrack(
        raw_title="I Took A Pill In Ibiza",
        title="I Took A Pill In Ibiza",
        edition="Remix",
        artist_name="Mike Posner",
        remixers=["SeeB"],
        duration_ms=197000,
    )
    res_generic = engine.calculate_match(source_ibiza, cand_generic_remix, context="sync")
    assert res_generic.passed_version_check is True
    assert res_generic.confidence_score >= 85.0


def test_acoustid_penalizes_unrequested_instrumental_candidate():
    """Stage 3 AcoustID must penalize '(instrumental)' when baseline title/filename is the normal vocal track."""
    from unittest.mock import MagicMock

    from core.metadata.engine import MetadataResolutionEngine
    from core.metadata.schemas import ResolutionRequest

    acoustid_mock = MagicMock()
    acoustid_mock.resolve_fingerprint_details.return_value = {
        "acoustid_id": "c926e139-5fec-45e0-0000-000000000000",
        "score": 0.99,
        "recordings": [
            {
                "id": "0c1d99da-5311-40b8-9f99-7989859c9650",
                "title": "Hymn for the Weekend (instrumental)",
                "artist": "Coldplay",
                "duration": 262.0,
                "score": 0.99,
            },
            {
                "id": "7ba475be-0cdc-4fb2-b508-212d2166e2d0",
                "title": "Hymn for the Weekend",
                "artist": "Coldplay",
                "duration": 259.0,
                "score": 0.98,
            },
        ],
        "mbids": [
            "0c1d99da-5311-40b8-9f99-7989859c9650",
            "7ba475be-0cdc-4fb2-b508-212d2166e2d0",
        ],
    }

    mb_mock = MagicMock()
    mb_mock.get_metadata.side_effect = lambda mbid: {
        "0c1d99da-5311-40b8-9f99-7989859c9650": {
            "id": "0c1d99da-5311-40b8-9f99-7989859c9650",
            "title": "Hymn for the Weekend (instrumental)",
            "artist": "Coldplay",
            "album": "A Head Full of Dreams (listening instrumental version)",
            "length": 262000,
            "release_group": {"primary_type": "Album"},
            "release_group_count": 10,
        },
        "7ba475be-0cdc-4fb2-b508-212d2166e2d0": {
            "id": "7ba475be-0cdc-4fb2-b508-212d2166e2d0",
            "title": "Hymn for the Weekend",
            "artist": "Coldplay",
            "album": "A Head Full of Dreams",
            "length": 259000,
            "release_group": {"primary_type": "Album"},
            "release_group_count": 10,
        },
    }[mbid]

    engine = MetadataResolutionEngine(acoustid_provider=acoustid_mock, metadata_provider=mb_mock)
    req = ResolutionRequest(
        media_id="1048",
        file_path=Path("Hymn for the Weekend.flac"),
        baseline_title="Hymn for the Weekend",
        baseline_artist="Coldplay",
        baseline_album="A Head Full of Dreams",
        chromaprint="AQADtMmyJJGSJ",
        duration=262.377,
        duration_ms=262377,
        ignore_embedded_mbid=True,
        ignore_cache=True,
        force_mode=True,
    )
    res = engine.resolve_track(req, enabled_stages=["acoustid"])
    assert res is not None
    assert res.musicbrainz_track_id == "7ba475be-0cdc-4fb2-b508-212d2166e2d0"
    assert res.title == "Hymn for the Weekend"
    assert res.acoustid_id == "c926e139-5fec-45e0-0000-000000000000"


def test_text_conditioned_duration_tolerance_and_deluxe_compilation_bonus():
    """Verify text-conditioned duration bounds and Deluxe/Compilation padding bonus after version check."""
    engine = WeightedMatchingEngine(ExactSyncProfile())

    # 1. Exact Title + Exact Artist + Compilation ('Greatest Songs') with +4.11s delta -> Hymn for the Weekend
    src_hymn = EchosyncTrack(
        raw_title="Hymn for the Weekend",
        artist_name="Coldplay",
        album_title="A Head Full of Dreams",
        duration_ms=258000,
    )
    cand_hymn = EchosyncTrack(
        raw_title="Hymn for the Weekend",
        artist_name="Coldplay",
        album_title="Greatest Songs",
        duration_ms=262110,  # +4.11s
    )
    res_hymn = engine.calculate_match(src_hymn, cand_hymn, context="sync")
    assert res_hymn.confidence_score >= 85.0

    # 2. Exact Title + Exact Artist + Exact Album with +5.47s delta -> Dream On
    src_dream = EchosyncTrack(
        raw_title="Dream On",
        artist_name="Aerosmith",
        album_title="Aerosmith",
        duration_ms=267000,
    )
    cand_dream = EchosyncTrack(
        raw_title="Dream On",
        artist_name="Aerosmith",
        album_title="Aerosmith",
        duration_ms=272470,  # +5.47s
    )
    res_dream = engine.calculate_match(src_dream, cand_dream, context="sync")
    assert res_dream.confidence_score >= 85.0

    # 3. True alternate cut (+9.5s) MUST still hard-fail with 0.0%
    cand_radio = EchosyncTrack(
        raw_title="Dream On",
        artist_name="Aerosmith",
        album_title="Aerosmith",
        duration_ms=276500,  # +9.5s > 7.0s limit
    )
    res_radio = engine.calculate_match(src_dream, cand_radio, context="sync")
    assert res_radio.confidence_score == 0.0

    # 4. Version mismatch (Remix) MUST still be rejected even with exact title/artist and +4.1s delta
    cand_remix = EchosyncTrack(
        raw_title="Hymn for the Weekend (Seeb Remix)",
        title="Hymn for the Weekend",
        edition="Seeb Remix",
        artist_name="Coldplay",
        album_title="A Head Full of Dreams",
        duration_ms=262110,
    )
    res_remix = engine.calculate_match(src_hymn, cand_remix, context="sync")
    assert res_remix.passed_version_check is False
    assert res_remix.confidence_score == 0.0
