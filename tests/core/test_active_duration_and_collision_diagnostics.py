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

    # 1. Local track with +5.47s of trailing silence -> active_duration_ms matches Spotify
    padded_local = EchosyncTrack(
        raw_title="Dream On",
        title="Dream On",
        artist_name="Aerosmith",
        album_title="Aerosmith",
        duration_ms=272470,
        extra_metadata={"active_duration_ms": 267100},
    )
    padded_res = engine.calculate_match(spotify_track, padded_local)
    assert padded_res.confidence_score >= 85.0

    # 2. Local track with +5.47s of actual music (not silence) -> active_duration_ms is still +5.47s off -> rejected
    true_edit_local = EchosyncTrack(
        raw_title="Dream On",
        title="Dream On",
        artist_name="Aerosmith",
        album_title="Aerosmith",
        duration_ms=272470,
        extra_metadata={"active_duration_ms": 272400},
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
            "artist": "Blacklite District",
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
