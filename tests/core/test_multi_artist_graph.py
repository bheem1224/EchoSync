import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.database.repositories.track_repo import TrackRepository
from core.db.echo_sync_track import EchosyncMedia, EchosyncTrack
from database.music_database import Artist, Base, Track, TrackArtist
from services.playlists_api import get_library_candidates


@pytest.fixture
def in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


def test_atomic_artist_splitting_and_track_artists_persistence(in_memory_db):
    """
    Verify that composite artist strings during ingestion split into atomic Artist rows,
    setting Track.artist_id to the primary artist and creating track_artists junction records.
    """
    session = in_memory_db
    repo = TrackRepository(session)

    # Ingest a track with composite artist: "Zac Efron, Zendaya"
    track_dto = EchosyncTrack(
        raw_title="Rewrite The Stars",
        artist_name="Zac Efron, Zendaya",
        album_title="The Greatest Showman",
        duration=217000,
        media=[
            EchosyncMedia(
                file_path="/music/greatest_showman/rewrite_the_stars.flac",
                file_format="flac",
            )
        ],
    )

    repo.bulk_upsert_tracks(session, [track_dto])
    session.commit()

    # 1. Verify atomic artists created in database
    all_artists = session.query(Artist).order_by(Artist.id).all()
    artist_names = {a.name for a in all_artists}
    assert "Zac Efron" in artist_names
    assert "Zendaya" in artist_names
    # Strict 1-entity rule: composite string "Zac Efron, Zendaya" must NOT exist as an Artist entity
    assert "Zac Efron, Zendaya" not in artist_names

    # 2. Verify Track fields
    db_track = session.query(Track).filter_by(title="Rewrite The Stars").first()
    assert db_track is not None
    assert db_track.artist.name == "Zac Efron"  # Primary artist

    # 3. Verify track_artists associations
    associations = (
        session.query(TrackArtist)
        .filter_by(track_id=db_track.id)
        .order_by(TrackArtist.position)
        .all()
    )
    assert len(associations) == 2

    # Primary artist
    assert associations[0].artist.name == "Zac Efron"
    assert associations[0].role == "primary"
    assert associations[0].position == 0

    # Featured collaborator
    assert associations[1].artist.name == "Zendaya"
    assert associations[1].role == "featured"
    assert associations[1].position == 1

    # 4. Verify Track.all_artists relationship
    assert len(db_track.all_artists) == 2
    assert [a.name for a in db_track.all_artists] == ["Zac Efron", "Zendaya"]


def test_multi_artist_candidate_retrieval(in_memory_db):
    """
    Verify get_library_candidates retrieves the track when queried by either
    primary artist or collaborating/featured artist tokens.
    """
    session = in_memory_db
    repo = TrackRepository(session)

    # Ingest collaborative track: "Calvin Harris feat. Dua Lipa"
    track_dto = EchosyncTrack(
        raw_title="One Kiss",
        artist_name="Calvin Harris feat. Dua Lipa",
        album_title="One Kiss",
        duration=214000,
        media=[
            EchosyncMedia(
                file_path="/music/calvin_harris/one_kiss.flac",
                file_format="flac",
            )
        ],
    )

    repo.bulk_upsert_tracks(session, [track_dto])
    session.commit()

    # Query 1: by full collaborative query string
    candidates_full = get_library_candidates(
        session, target_title="One Kiss", target_artist="Calvin Harris feat. Dua Lipa"
    )
    assert len(candidates_full) == 1
    assert candidates_full[0].title == "One Kiss"

    # Query 2: by primary artist token ("Calvin Harris")
    candidates_primary = get_library_candidates(
        session, target_title="One Kiss", target_artist="Calvin Harris"
    )
    assert len(candidates_primary) == 1
    assert candidates_primary[0].title == "One Kiss"

    # Query 3: by featured artist token ("Dua Lipa")
    candidates_featured = get_library_candidates(
        session, target_title="One Kiss", target_artist="Dua Lipa"
    )
    assert len(candidates_featured) == 1
    assert candidates_featured[0].title == "One Kiss"


def test_complex_multi_artist_delimiters(in_memory_db):
    """
    Verify splitting across various delimiters (&, /, vs., with, feat., ft.).
    """
    session = in_memory_db
    repo = TrackRepository(session)

    tracks = [
        EchosyncTrack(
            raw_title="Song A",
            artist_name="Armin van Buuren & Brennan Heart ft. Andreas Moe",
            album_title="Album A",
            duration=180000,
            media=[EchosyncMedia(file_path="/music/a.flac")],
        ),
        EchosyncTrack(
            raw_title="Song B",
            artist_name="Marshmello vs. Svdden Death",
            album_title="Album B",
            duration=190000,
            media=[EchosyncMedia(file_path="/music/b.flac")],
        ),
        EchosyncTrack(
            raw_title="Song C",
            artist_name="Artist One / Artist Two / Artist Three",
            album_title="Album C",
            duration=200000,
            media=[EchosyncMedia(file_path="/music/c.flac")],
        ),
    ]

    repo.bulk_upsert_tracks(session, tracks)
    session.commit()

    track_a = session.query(Track).filter_by(title="Song A").first()
    assert track_a is not None
    assert [a.name for a in track_a.all_artists] == [
        "Armin van Buuren",
        "Brennan Heart",
        "Andreas Moe",
    ]

    track_b = session.query(Track).filter_by(title="Song B").first()
    assert track_b is not None
    assert [a.name for a in track_b.all_artists] == ["Marshmello", "Svdden Death"]

    track_c = session.query(Track).filter_by(title="Song C").first()
    assert track_c is not None
    assert [a.name for a in track_c.all_artists] == [
        "Artist One",
        "Artist Two",
        "Artist Three",
    ]
