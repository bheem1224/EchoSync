"""Unit tests for TrackArtist deduplication and safe junction table lifecycles."""

from database.music_database import Base, MusicDatabase, Track, Artist, TrackArtist, LocalMedia
from core.metadata.adapter import ResolutionAdapter, reconcile_media_assignment
from core.db.echo_sync_track import EchosyncTrack


def test_hydrate_track_deduplicates_redundant_artists(tmp_path):
    """Verify that hydrate_track avoids duplicate (artist_id, role) TrackArtist insertions."""
    music_db = MusicDatabase(tmp_path / "test.db")
    Base.metadata.create_all(music_db.engine)

    with music_db.session_scope() as session:
        adapter = ResolutionAdapter()

        # Artist "W&W" created in database
        artist = Artist(name="W&W", normalized_name="w&w")
        session.add(artist)
        session.flush()

        track = Track(
            title="God Is a Girl",
            sync_id="test-sync-1",
            artist_id=artist.id,
        )
        session.add(track)
        session.flush()

        # Redundant artist references in DTO (e.g. "W&W & W&W" or same artist repeated in primary)
        dto = EchosyncTrack()
        dto.title = "God Is a Girl"
        dto.primary_artists = ["W&W", "w&w", "W&W"]
        dto.featured_artists = ["AXMO", "AXMO"]
        dto.remixers = ["Steve Aoki", "Steve Aoki"]

        hydrated = adapter.hydrate_track(dto, session, track)
        session.flush()

        # Check that artist_associations contains only distinct (artist_id, role) pairs
        pairs = [(assoc.artist_id, assoc.role) for assoc in hydrated.artist_associations]
        assert len(pairs) == len(set(pairs)), f"Duplicate associations found: {pairs}"

        # Should have 1 primary (W&W), 1 featured (AXMO), 1 remixer (Steve Aoki)
        assert len(hydrated.artist_associations) == 3
        roles = [assoc.role for assoc in hydrated.artist_associations]
        assert roles == ["primary", "featured", "remixer"]


def test_reconcile_media_assignment_flushes_deduplicated_track_artists(tmp_path):
    """
    Verify that reconcile_media_assignment succeeds without SQLite IntegrityError
    when an audio file has redundant artists decomposing to the same artist entity.
    """
    music_db = MusicDatabase(tmp_path / "test.db")
    Base.metadata.create_all(music_db.engine)

    with music_db.session_scope() as session:
        # Pre-populate primary artist
        artist = Artist(name="Armin van Buuren", normalized_name="armin van buuren")
        session.add(artist)
        session.flush()

        # Initial track and local media
        track = Track(
            title="Repeat After Me",
            sync_id="sync-ram-1",
            artist_id=artist.id,
        )
        session.add(track)
        session.flush()

        media = LocalMedia(
            media_id="media_ram_1",
            track_id=track.id,
            file_path=str(tmp_path / "repeat_after_me.flac"),
            file_format="flac",
        )
        session.add(media)
        session.flush()

        # Incoming metadata with redundant artist credits decomposing to duplicate primary artists
        dto = EchosyncTrack()
        dto.title = "Repeat After Me"
        # Decomposes with "Armin van Buuren" listed redundantly
        dto.artist_name = "Armin van Buuren, Armin van Buuren & Dimitri Vegas & Like Mike"
        dto.edition = "Club Mix"

        # Reconcile media assignment (triggers decoupling or hydration)
        reconciled = reconcile_media_assignment(session, media, dto)
        session.flush()

        assert reconciled is not None
        # Assert no duplicate (artist_id, role) tuples in database
        db_assocs = (
            session.query(TrackArtist)
            .filter(TrackArtist.track_id == reconciled.id)
            .all()
        )
        pairs = [(a.artist_id, a.role) for a in db_assocs]
        assert len(pairs) == len(set(pairs)), f"Duplicates in database: {pairs}"


def test_rehydrate_existing_track_explicit_flush_ordering(tmp_path):
    """
    Verify that updating/re-hydrating an existing Track that already has TrackArtist
    rows in the database deletes the old associations before inserting new ones,
    preventing SQLite UNIQUE constraint failures.
    """
    music_db = MusicDatabase(tmp_path / "test.db")
    Base.metadata.create_all(music_db.engine)

    with music_db.session_scope() as session:
        adapter = ResolutionAdapter()

        artist = Artist(name="Hardwell", normalized_name="hardwell")
        session.add(artist)
        session.flush()

        track = Track(
            title="Spaceman",
            sync_id="sync-spaceman-1",
            artist_id=artist.id,
        )
        session.add(track)
        session.flush()

        # Pre-existing association in DB
        existing_ta = TrackArtist(track_id=track.id, artist_id=artist.id, role="primary", position=0)
        session.add(existing_ta)
        session.flush()

        # Re-hydrate the same track with the same artist
        dto = EchosyncTrack()
        dto.title = "Spaceman"
        dto.primary_artists = ["Hardwell"]

        hydrated = adapter.hydrate_track(dto, session, track)
        # Without explicit delete flush ordering, this would raise IntegrityError
        session.flush()

        assert hydrated.id == track.id
        db_assocs = session.query(TrackArtist).filter_by(track_id=track.id).all()
        assert len(db_assocs) == 1
        assert db_assocs[0].artist_id == artist.id
        assert db_assocs[0].role == "primary"
