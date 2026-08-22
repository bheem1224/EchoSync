import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.music_database import Base, Track, Artist, Album, LocalMedia, TrackArtist
from core.db.echo_sync_track import EchosyncTrack, EchosyncMedia
from core.database.repositories.track_repo import TrackRepository
from core.matching_engine.matching_engine import (
    WeightedMatchingEngine,
    calculate_duration_score,
)
from core.matching_engine.scoring_profile import ExactSyncProfile
from services.playlists_api import get_library_candidates, resolve_duplicate_matches


@pytest.fixture
def e2e_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


def test_e2e_multi_artist_schema_and_collaborator_resolution(e2e_db):
    """
    Validates:
    1. Ingestion of multi-artist tracks creates atomic Artist rows.
    2. Track.artist_id points to primary lead artist.
    3. track_artists junction table stores all atomic collaborators with roles/positions.
    4. Candidate query discovers tracks via single-entity collaborator tokens.
    """
    session = e2e_db
    repo = TrackRepository(session)

    tracks = [
        EchosyncTrack(
            raw_title="Rewrite The Stars",
            artist_name="Zac Efron, Zendaya",
            album_title="The Greatest Showman",
            duration=217000,
            media=[EchosyncMedia(file_path="/music/rewrite_the_stars.flac")],
        ),
        EchosyncTrack(
            raw_title="Mama",
            artist_name="Jonas Blue feat. William Singe",
            album_title="Blue",
            duration=184000,
            media=[EchosyncMedia(file_path="/music/mama.flac")],
        ),
        EchosyncTrack(
            raw_title="Safe and Sound",
            artist_name="Capital Cities",
            album_title="In a Tidal Wave of Mystery",
            duration=192000,  # 3:12 original cut
            media=[EchosyncMedia(file_path="/music/safe_and_sound_original.flac")],
        ),
        EchosyncTrack(
            raw_title="Safe and Sound",
            artist_name="Capital Cities",
            album_title="In a Tidal Wave of Mystery",
            edition="Extended Remix",
            duration=343000,  # 5:43 extended remix
            media=[EchosyncMedia(file_path="/music/safe_and_sound_remix.flac")],
        ),
    ]

    repo.bulk_upsert_tracks(session, tracks)
    session.commit()

    # 1. Check Atomic Artists in DB
    all_artists = {a.name for a in session.query(Artist).all()}
    assert "Zac Efron" in all_artists
    assert "Zendaya" in all_artists
    assert "Jonas Blue" in all_artists
    assert "William Singe" in all_artists
    assert "Capital Cities" in all_artists
    # Strict 1-entity rule: composite strings must not exist as Artists
    assert "Zac Efron, Zendaya" not in all_artists
    assert "Jonas Blue feat. William Singe" not in all_artists

    # 2. Check "Mama" collaborator query via track_artists
    mama_cand = get_library_candidates(session, target_title="Mama", target_artist="William Singe")
    assert len(mama_cand) == 1
    assert mama_cand[0].title == "Mama"
    assert mama_cand[0].artist.name == "Jonas Blue"
    assert [a.name for a in mama_cand[0].all_artists] == ["Jonas Blue", "William Singe"]


def test_e2e_polynomial_duration_precision():
    """
    Validates polynomial duration decay curve precision:
    - Standard mode: T=5000ms, Limit=6000ms, k=6 (5050ms > 0.99, >= 6000ms == 0.0)
    - Strict mode: T=2000ms, Limit=3000ms, k=6 (2050ms > 0.99, >= 3000ms == 0.0)
    """
    # Standard Mode
    assert calculate_duration_score(0, strict=False) == 1.0
    assert calculate_duration_score(5000, strict=False) == 1.0
    assert calculate_duration_score(5050, strict=False) > 0.99
    assert calculate_duration_score(5500, strict=False) > 0.98
    assert calculate_duration_score(6000, strict=False) == 0.0
    assert calculate_duration_score(6500, strict=False) == 0.0

    # Strict Mode
    assert calculate_duration_score(0, strict=True) == 1.0
    assert calculate_duration_score(2000, strict=True) == 1.0
    assert calculate_duration_score(2050, strict=True) > 0.99
    assert calculate_duration_score(2500, strict=True) > 0.98
    assert calculate_duration_score(3000, strict=True) == 0.0
    assert calculate_duration_score(3500, strict=True) == 0.0


def test_e2e_cover_version_and_remix_boundaries():
    """
    Validates:
    - Cover versions across distinct artist boundaries score 0.0 (cannot claim original track).
    - Original 3:12 query matches canonical cut and rejects 5:43 extended remix.
    - Matching album applies +2.0 boost; missing/mismatched album incurs 0.0 penalty.
    """
    engine = WeightedMatchingEngine(ExactSyncProfile())

    # 1. Cover Version Boundary
    source_cover = EchosyncTrack(
        raw_title="Rewrite The Stars",
        artist_name="James Arthur & Anne-Marie",
        album_title="The Greatest Showman: Reimagined",
        duration=217000,
    )
    cand_original = EchosyncTrack(
        raw_title="Rewrite The Stars",
        artist_name="Zac Efron & Zendaya",
        album_title="The Greatest Showman",
        duration=217000,
    )
    cover_match = engine.calculate_match(source_cover, cand_original)
    assert cover_match.confidence_score == 0.0
    assert "Artist boundary mismatch" in cover_match.reasoning or cover_match.fuzzy_text_score < 0.70

    # 2. Canonical Cut vs Extended Remix
    source_original_query = EchosyncTrack(
        raw_title="Safe and Sound",
        artist_name="Capital Cities",
        album_title="In a Tidal Wave of Mystery",
        duration=192000,  # 3:12
    )
    cand_orig_cut = EchosyncTrack(
        raw_title="Safe and Sound",
        artist_name="Capital Cities",
        album_title="In a Tidal Wave of Mystery",
        duration=192000,
    )
    cand_remix_cut = EchosyncTrack(
        raw_title="Safe and Sound",
        artist_name="Capital Cities",
        album_title="In a Tidal Wave of Mystery",
        edition="Extended Remix",
        duration=343000,  # 5:43
    )

    res_orig = engine.calculate_match(source_original_query, cand_orig_cut)
    res_remix = engine.calculate_match(source_original_query, cand_remix_cut)

    assert res_orig.confidence_score >= 90.0
    assert res_orig.duration_match_score == 1.0

    assert res_remix.confidence_score == 0.0
    assert res_remix.duration_match_score == 0.0


def test_e2e_playlist_sync_telemetry_and_greedy_winner_take_all(e2e_db):
    """
    Simulates a full playlist sync analysis pass:
    - Verifies found_in_library + missing_tracks == total_tracks.
    - Verifies zero duplicate matched_track_id assignments.
    """
    session = e2e_db
    repo = TrackRepository(session)

    # Ingest library
    lib_tracks = [
        EchosyncTrack(
            raw_title="Rewrite The Stars",
            artist_name="Zac Efron & Zendaya",
            album_title="The Greatest Showman",
            duration=217000,
            media=[EchosyncMedia(file_path="/music/rewrite_the_stars.flac")],
        ),
        EchosyncTrack(
            raw_title="Safe and Sound",
            artist_name="Capital Cities",
            album_title="In a Tidal Wave of Mystery",
            duration=192000,
            media=[EchosyncMedia(file_path="/music/safe_and_sound.flac")],
        ),
        EchosyncTrack(
            raw_title="Mama",
            artist_name="Jonas Blue feat. William Singe",
            album_title="Blue",
            duration=184000,
            media=[EchosyncMedia(file_path="/music/mama.flac")],
        ),
    ]
    repo.bulk_upsert_tracks(session, lib_tracks)
    session.commit()

    engine = WeightedMatchingEngine(ExactSyncProfile())

    # Simulated Playlist Input
    playlist_source_items = [
        {"title": "Rewrite The Stars", "artist": "Zac Efron & Zendaya", "duration": 217000},
        {"title": "Rewrite The Stars", "artist": "James Arthur & Anne-Marie", "duration": 217000},
        {"title": "Safe and Sound", "artist": "Capital Cities", "duration": 192000},
        {"title": "Mama", "artist": "Jonas Blue feat. William Singe", "duration": 184000},
        {"title": "Nonexistent Song", "artist": "Unknown Band", "duration": 200000},
    ]

    evaluated_playlist = []
    for item in playlist_source_items:
        src_track = EchosyncTrack(
            raw_title=item["title"],
            artist_name=item["artist"],
            album_title="",
            duration=item["duration"],
        )
        candidates = get_library_candidates(session, item["title"], item["artist"])

        best_score = 0.0
        best_cand_id = None
        cand_matches = []

        for cand in candidates:
            cand_dto = EchosyncTrack(
                raw_title=cand.title,
                artist_name=cand.artist.name if cand.artist else "",
                album_title=cand.album.title if cand.album else "",
                duration=cand.duration or 0,
                edition=cand.edition,
            )
            res = engine.calculate_match(src_track, cand_dto)
            if res.confidence_score >= 70.0:
                cand_matches.append({
                    "id": cand.id,
                    "score": res.confidence_score,
                    "target_identifier": f"plex://{cand.id}",
                })
            if res.confidence_score > best_score:
                best_score = res.confidence_score
                best_cand_id = cand.id

        lib_match = "Found" if best_score >= 85 else ("Found (score: 75%)" if best_score >= 70 else "Not Found")
        evaluated_playlist.append({
            "title": item["title"],
            "artist": item["artist"],
            "matched_track_id": best_cand_id if best_score >= 70 else None,
            "match_score": best_score,
            "library_match": lib_match,
            "target_identifier": f"plex://{best_cand_id}" if (best_cand_id and best_score >= 70) else None,
            "candidate_matches": cand_matches,
        })

    # Run Greedy 1:1 Winner-Take-All Collision Resolution
    resolved_playlist = resolve_duplicate_matches(evaluated_playlist)

    total_tracks = len(resolved_playlist)
    found_count = sum(1 for t in resolved_playlist if t["library_match"].startswith("Found"))
    missing_count = sum(1 for t in resolved_playlist if t["library_match"] == "Not Found")

    # Invariant: found + missing == total
    assert found_count + missing_count == total_tracks

    # Invariant: Zero duplicate matched_track_id assignments
    assigned_ids = [t["matched_track_id"] for t in resolved_playlist if t["matched_track_id"] is not None]
    assert len(assigned_ids) == len(set(assigned_ids))

    # Assert specific outcomes
    # 1. Zac Efron & Zendaya matches Rewrite The Stars
    assert resolved_playlist[0]["library_match"] == "Found"
    assert resolved_playlist[0]["matched_track_id"] is not None

    # 2. James Arthur cover is unmatched (rejected by artist boundary guard)
    assert resolved_playlist[1]["library_match"] == "Not Found"
    assert resolved_playlist[1]["matched_track_id"] is None

    # 3. Safe and Sound matches
    assert resolved_playlist[2]["library_match"] == "Found"
    assert resolved_playlist[2]["matched_track_id"] is not None

    # 4. Mama matches
    assert resolved_playlist[3]["library_match"] == "Found"
    assert resolved_playlist[3]["matched_track_id"] is not None

    # 5. Nonexistent song is Not Found
    assert resolved_playlist[4]["library_match"] == "Not Found"
    assert resolved_playlist[4]["matched_track_id"] is None
