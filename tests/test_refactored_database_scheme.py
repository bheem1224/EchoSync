"""
Test suite for the refactored split-database schema.

Covers:
- SoulSyncTrack.sync_id @property (MBID path and base64 fallback path)
- ProviderStorageBox table-name sandboxing (prv_{name}_ prefix enforcement)
- Operational tables (user_ratings) accepting and returning URN strings for sync_id
"""
from __future__ import annotations

import base64
from datetime import UTC

import pytest
from sqlalchemy import Column, Integer, MetaData, String, create_engine, inspect
from sqlalchemy.orm import sessionmaker

from core.models import SoulSyncTrack
from database.working_database import ProviderStorageBox, UserRating, WorkingBase


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def memory_working_engine():
    """
    Isolated in-memory SQLite engine with the full WorkingDatabase schema.
    Uses WorkingBase.metadata so all ORM models are available, but keeps
    each test completely independent by using a separate :memory: connection.
    """
    engine = create_engine("sqlite:///:memory:", future=True)
    WorkingBase.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def memory_working_session(memory_working_engine):
    """Sessionmaker bound to the in-memory working engine."""
    Session = sessionmaker(bind=memory_working_engine, expire_on_commit=False, future=True)
    return Session


# ---------------------------------------------------------------------------
# SoulSyncTrack.sync_id – MBID path
# ---------------------------------------------------------------------------


class TestSoulSyncTrackSyncId:
    """Unit tests for the SoulSyncTrack.sync_id computed property."""

    def test_soulsync_track_sync_id_mbid(self):
        """
        When musicbrainz_recording_id is present, sync_id must return a URN
        in the form  ss:track:mbid:{musicbrainz_recording_id}.
        """
        mbid = "b10bbbfc-cf9e-42e0-be17-e2c3e1d2600d"
        track = SoulSyncTrack(
            title="Bohemian Rhapsody",
            artists=["Queen"],
            musicbrainz_recording_id=mbid,
        )

        assert track.sync_id == f"ss:track:mbid:{mbid}"

    def test_soulsync_track_sync_id_mbid_takes_priority_over_metadata(self):
        """
        MBID branch must win even when a valid title + artist are also present.
        Ensures the fallback is never reached when an MBID is available.
        """
        mbid = "3d9a8f4e-b12c-4567-a890-fedcba098765"
        track = SoulSyncTrack(
            title="Some Other Song",
            artists=["Some Artist"],
            musicbrainz_recording_id=mbid,
        )

        assert track.sync_id.startswith("ss:track:mbid:")
        assert not track.sync_id.startswith("ss:track:meta:")

    # ---------------------------------------------------------------------------
    # SoulSyncTrack.sync_id – base64 fallback path
    # ---------------------------------------------------------------------------

    def test_soulsync_track_sync_id_fallback(self):
        """
        When musicbrainz_recording_id is absent, sync_id must return a URN
        in the form  ss:track:meta:{base64(lowercase_artist|lowercase_title)}.

        The base64 payload is: f"{artists[0].lower()}|{title.lower()}"
        encoded as UTF-8 and returned as a standard (padded) base64 string.
        """
        track = SoulSyncTrack(
            title="Bohemian Rhapsody",
            artists=["Queen"],
            musicbrainz_recording_id=None,
        )

        expected_payload = "queen|bohemian rhapsody"
        expected_b64 = base64.b64encode(expected_payload.encode("utf-8")).decode("ascii")

        assert track.sync_id == f"ss:track:meta:{expected_b64}"

    def test_soulsync_track_sync_id_fallback_lowercases_input(self):
        """
        Mixed-case artist and title must be normalised to lowercase before
        encoding so that the same track always produces the same sync_id
        regardless of how the caller supplied the metadata.
        """
        track_upper = SoulSyncTrack(
            title="STAIRWAY TO HEAVEN",
            artists=["LED ZEPPELIN"],
            musicbrainz_recording_id=None,
        )
        track_lower = SoulSyncTrack(
            title="stairway to heaven",
            artists=["led zeppelin"],
            musicbrainz_recording_id=None,
        )

        assert track_upper.sync_id == track_lower.sync_id

    def test_soulsync_track_sync_id_fallback_is_valid_base64(self):
        """
        The embedded segment of a meta sync_id must be decodable as base64
        and must reconstruct the expected  artist|title  payload.
        """
        artist, title = "radiohead", "creep"
        track = SoulSyncTrack(
            title=title.title(),   # "Creep"  — to confirm lowercasing
            artists=[artist.title()],  # "Radiohead"
            musicbrainz_recording_id=None,
        )

        prefix = "ss:track:meta:"
        assert track.sync_id.startswith(prefix)

        encoded_segment = track.sync_id[len(prefix):]
        decoded = base64.b64decode(encoded_segment.encode("ascii")).decode("utf-8")
        assert decoded == f"{artist}|{title}"


# ---------------------------------------------------------------------------
# ProviderStorageBox – prefix enforcement
# ---------------------------------------------------------------------------


class TestProviderStorageBox:
    """Verify that ProviderStorageBox unconditionally prefixes table names."""

    def test_provider_storage_box_prefixing(self):
        """
        ProviderStorageBox("spotify") must create a table named
        prv_spotify_playlists (not just 'playlists') when asked to create
        a table with the suffix 'playlists'.

        Uses an isolated MetaData so this test never contaminates the global
        WorkingBase.metadata registry.
        """
        engine = create_engine("sqlite:///:memory:", future=True)
        isolated_metadata = MetaData()

        box = ProviderStorageBox("spotify", engine, isolated_metadata)
        table = box.create_table(
            "playlists",
            Column("id", Integer, primary_key=True),
            Column("name", String, nullable=False),
        )
        box.execute()

        # 1. The returned Table object must carry the prefixed name.
        assert table.name == "prv_spotify_playlists", (
            f"Expected table name 'prv_spotify_playlists', got '{table.name}'"
        )

        # 2. The unprefixed name must NOT appear in metadata.
        assert "playlists" not in isolated_metadata.tables, (
            "Bare 'playlists' table must not be registered in metadata."
        )

        # 3. The prefixed name must appear in metadata.
        assert "prv_spotify_playlists" in isolated_metadata.tables

        # 4. The physical table must actually exist in the SQLite database.
        inspector = inspect(engine)
        db_tables = inspector.get_table_names()
        assert "prv_spotify_playlists" in db_tables, (
            f"Table not found in SQLite. Tables present: {db_tables}"
        )
        assert "playlists" not in db_tables

        engine.dispose()

    def test_provider_storage_box_different_providers_are_isolated(self):
        """
        Two ProviderStorageBox instances with different provider names must
        produce two distinct, non-overlapping table names even when given the
        same suffix.  Neither table name should be ambiguous.
        """
        engine = create_engine("sqlite:///:memory:", future=True)
        isolated_metadata = MetaData()

        spotify_box = ProviderStorageBox("spotify", engine, isolated_metadata)
        tidal_box = ProviderStorageBox("tidal", engine, isolated_metadata)

        spotify_table = spotify_box.create_table(
            "playlists",
            Column("id", Integer, primary_key=True),
            Column("name", String),
        )
        tidal_table = tidal_box.create_table(
            "playlists",
            Column("id", Integer, primary_key=True),
            Column("name", String),
        )
        spotify_box.execute()

        assert spotify_table.name == "prv_spotify_playlists"
        assert tidal_table.name == "prv_tidal_playlists"
        assert spotify_table.name != tidal_table.name

        engine.dispose()

    def test_provider_storage_box_idempotent_create(self):
        """
        Calling create_table() twice with the same suffix must NOT raise and
        must return the same logical table (idempotency guard).
        """
        engine = create_engine("sqlite:///:memory:", future=True)
        isolated_metadata = MetaData()

        box = ProviderStorageBox("spotify", engine, isolated_metadata)
        table_first = box.create_table(
            "cache",
            Column("id", Integer, primary_key=True),
        )
        table_second = box.create_table(
            "cache",
            Column("id", Integer, primary_key=True),
        )

        # Both calls must resolve to the same table object.
        assert table_first.name == table_second.name == "prv_spotify_cache"

        engine.dispose()


# ---------------------------------------------------------------------------
# Operational tables – string sync_id round-trip
# ---------------------------------------------------------------------------


class TestOperationalTablesStringSyncId:
    """Verify that sync_id columns in working.db accept and return URN strings."""

    def test_operational_tables_use_string_sync_id(
        self, memory_working_engine, memory_working_session
    ):
        """
        Insert a UserRating row using a full URN string for sync_id, then query
        it back and confirm:
          - The persisted value is identical to what was written (no int cast).
          - The Python type of the returned value is str, not int.
        """
        urn = "ss:track:mbid:b10bbbfc-cf9e-42e0-be17-e2c3e1d2600d"
        Session = memory_working_session

        with Session() as session:
            rating = UserRating(user_id=1, sync_id=urn, rating=4.5)
            session.add(rating)
            session.commit()

        with Session() as session:
            queried = session.query(UserRating).filter_by(sync_id=urn).one()

            assert queried.sync_id == urn, (
                f"Expected '{urn}', got '{queried.sync_id}'"
            )
            assert isinstance(queried.sync_id, str), (
                f"sync_id must be str, got {type(queried.sync_id)}"
            )

    def test_operational_tables_accept_meta_urn_sync_id(
        self, memory_working_engine, memory_working_session
    ):
        """
        The fallback (base64-meta) URN format must also round-trip correctly,
        confirming the column has no length constraint that would truncate it.
        """
        # Construct the same URN a SoulSyncTrack would produce for the
        # meta fallback path, and verify it survives a database round-trip.
        payload = "the beatles|hey jude"
        b64 = base64.b64encode(payload.encode("utf-8")).decode("ascii")
        urn = f"ss:track:meta:{b64}"

        Session = memory_working_session

        with Session() as session:
            rating = UserRating(user_id=2, sync_id=urn, rating=5.0)
            session.add(rating)
            session.commit()

        with Session() as session:
            queried = session.query(UserRating).filter_by(user_id=2).one()

            assert queried.sync_id == urn
            assert isinstance(queried.sync_id, str)

    def test_operational_timestamps_round_trip_as_utc_aware(
        self, memory_working_engine, memory_working_session
    ):
        """Operational timestamp columns should return timezone-aware UTC datetimes."""
        Session = memory_working_session

        with Session() as session:
            rating = UserRating(user_id=3, sync_id="ss:track:mbid:utc-check", rating=4.0)
            session.add(rating)
            session.commit()

        with Session() as session:
            queried = session.query(UserRating).filter_by(user_id=3).one()

            assert queried.timestamp is not None
            assert queried.timestamp.tzinfo is not None
            assert queried.timestamp.utcoffset() == UTC.utcoffset(queried.timestamp)

    def test_unique_constraint_on_user_id_and_sync_id(
        self, memory_working_engine, memory_working_session
    ):
        """
        The (user_id, sync_id) unique constraint on user_ratings must prevent
        a second rating for the same user+track combination.
        """
        from sqlalchemy.exc import IntegrityError

        urn = "ss:track:mbid:aaaabbbb-cccc-dddd-eeee-ffffffffffff"
        Session = memory_working_session

        with Session() as session:
            session.add(UserRating(user_id=1, sync_id=urn, rating=3.0))
            session.commit()

        with pytest.raises(IntegrityError):
            with Session() as session:
                session.add(UserRating(user_id=1, sync_id=urn, rating=5.0))
                session.commit()
