import pytest
from database.music_database import get_database, Track, LocalMedia, Base
from core.db.echo_sync_track import EchosyncTrack, EchosyncMedia
from core.database.repositories.track_repo import TrackRepository, bulk_upsert_tracks


def test_echosync_track_nanoid_generation():
    """Verify EchosyncTrack defaults to an 8-char NanoID, never legacy ss:track:meta:."""
    t1 = EchosyncTrack(
        raw_title="Safe and Sound",
        artist_name="Capital Cities",
        album_title="In a Tidal Wave of Mystery",
    )
    assert t1.sync_id is not None
    assert len(t1.sync_id) == 8
    assert not t1.sync_id.startswith("ss:")

    # Explicit non-legacy sync_id is preserved
    t2 = EchosyncTrack(
        sync_id="custom_sync_123",
        raw_title="Safe and Sound",
        artist_name="Capital Cities",
        album_title="In a Tidal Wave of Mystery",
    )
    assert t2.sync_id == "custom_sync_123"


def test_track_version_separation_and_no_collapsing():
    """Verify original track and remix with differing editions/durations create separate Track records."""
    db = get_database()
    Base.metadata.drop_all(db.engine)
    Base.metadata.create_all(db.engine)

    session = db.get_session()
    try:
        # Original Radio Edit
        original = EchosyncTrack(
            raw_title="Safe and Sound",
            artist_name="Capital Cities",
            album_title="In a Tidal Wave of Mystery",
            duration=193000,
            edition=None,
            media=[
                EchosyncMedia(
                    file_path="/music/Capital Cities/Safe and Sound.flac",
                    file_format="FLAC",
                )
            ]
        )
        # Extended Remix
        remix = EchosyncTrack(
            raw_title="Safe and Sound (Remix)",
            artist_name="Capital Cities",
            album_title="In a Tidal Wave of Mystery",
            duration=343000,
            edition="Remix",
            media=[
                EchosyncMedia(
                    file_path="/music/Capital Cities/Safe and Sound (Remix).flac",
                    file_format="FLAC",
                )
            ]
        )

        bulk_upsert_tracks(session, [original, remix])
        session.commit()

        # Both tracks should exist in DB separately with their respective durations
        tracks = session.query(Track).order_by(Track.duration).all()
        assert len(tracks) == 2

        track_orig = tracks[0]
        track_remix = tracks[1]

        assert track_orig.duration == 193000
        assert track_orig.edition is None or track_orig.edition == ""
        assert not track_orig.sync_id.startswith("ss:")
        assert len(track_orig.sync_id) == 8

        assert track_remix.duration == 343000
        assert track_remix.edition == "Remix"
        assert not track_remix.sync_id.startswith("ss:")
        assert len(track_remix.sync_id) == 8

        assert track_orig.sync_id != track_remix.sync_id
        assert track_orig.id != track_remix.id

        # Rescan test: Updating original track should not affect remix or change sync_id
        orig_sync_id = track_orig.sync_id
        original_rescan = EchosyncTrack(
            raw_title="Safe and Sound",
            artist_name="Capital Cities",
            album_title="In a Tidal Wave of Mystery",
            duration=193500,
            edition=None,
            media=[
                EchosyncMedia(
                    file_path="/music/Capital Cities/Safe and Sound.flac",
                    file_format="FLAC",
                )
            ]
        )
        bulk_upsert_tracks(session, [original_rescan])
        session.commit()
        session.expire_all()

        re_tracks = session.query(Track).order_by(Track.duration).all()
        assert len(re_tracks) == 2
        assert re_tracks[0].sync_id == orig_sync_id
        assert re_tracks[0].duration == 193500
        assert re_tracks[1].duration == 343000
    finally:
        session.close()


def test_legacy_sync_id_in_batch_is_remediated_to_nanoid():
    """Verify incoming tracks with legacy 'ss:track:meta:...' are assigned fresh NanoIDs."""
    db = get_database()
    Base.metadata.drop_all(db.engine)
    Base.metadata.create_all(db.engine)

    session = db.get_session()
    try:
        legacy_track = EchosyncTrack(
            sync_id="ss:track:meta:test:artist",
            raw_title="Test Title",
            artist_name="Test Artist",
            album_title="Test Album",
            duration=200000,
            media=[
                EchosyncMedia(
                    file_path="/music/test.flac",
                    file_format="FLAC",
                )
            ]
        )

        bulk_upsert_tracks(session, [legacy_track])
        session.commit()

        db_track = session.query(Track).first()
        assert db_track is not None
        assert not db_track.sync_id.startswith("ss:")
        assert len(db_track.sync_id) == 8
    finally:
        session.close()


def test_alembic_data_migration_sync_id_backfill():
    """Verify that Alembic migration f1e2d3c4b5a6 updates legacy ss: URIs to NanoIDs in both music.db and working.db."""
    from database.music_database import get_database as get_music_db, Artist, Album, Track, Base as MusicBase
    from database.working_database import get_working_database, UserRating, UserTrackState, Account, WorkingBase
    from database.migrations.music.versions.f1e2d3c4b5a6_backfill_nanoid_sync_ids import upgrade as run_migration
    import sqlalchemy as sa

    music_db = get_music_db()
    working_db = get_working_database()

    MusicBase.metadata.drop_all(music_db.engine)
    MusicBase.metadata.create_all(music_db.engine)
    WorkingBase.metadata.drop_all(working_db.engine)
    WorkingBase.metadata.create_all(working_db.engine)

    legacy_sync_id = "ss:track:meta:safe and sound:capital cities"

    with music_db.get_session() as m_sess:
        artist = Artist(name="Capital Cities")
        m_sess.add(artist)
        m_sess.flush()
        # Seed track with legacy URI
        track = Track(
            id=9819,
            sync_id=legacy_sync_id,
            title="Safe and Sound",
            artist_id=artist.id,
            duration=193000,
        )
        m_sess.add(track)
        m_sess.commit()

    with working_db.session_scope() as w_sess:
        account = Account(plugin_id=1, remote_account_id="user_1", username="testuser")
        w_sess.add(account)
        w_sess.flush()
        rating = UserRating(
            account_id=account.id,
            sync_id=legacy_sync_id,
            rating=5.0,
            play_count=12,
        )
        state = UserTrackState(
            account_id=account.id,
            sync_id=legacy_sync_id,
            is_unlinked=False,
            is_hard_deleted=False,
        )
        w_sess.add_all([rating, state])

    # Execute Alembic migration upgrade on the database connection
    class MockOpContext:
        @staticmethod
        def get_bind():
            return music_db.engine.connect()

    import alembic.op as alembic_op
    orig_get_bind = getattr(alembic_op, "get_bind", None)
    try:
        alembic_op.get_bind = MockOpContext.get_bind
        run_migration()
    finally:
        if orig_get_bind:
            alembic_op.get_bind = orig_get_bind

    # Verify music_library.db tracks table
    with music_db.get_session() as m_sess:
        migrated_track = m_sess.query(Track).filter_by(id=9819).first()
        assert migrated_track is not None
        assert not migrated_track.sync_id.startswith("ss:")
        assert len(migrated_track.sync_id) == 8
        new_sync_id = migrated_track.sync_id

    # Verify working.db tables were mapped to the new NanoID
    with working_db.session_scope() as w_sess:
        migrated_rating = w_sess.query(UserRating).filter_by(sync_id=new_sync_id).first()
        assert migrated_rating is not None
        assert migrated_rating.rating == 5.0
        assert migrated_rating.play_count == 12

        migrated_state = w_sess.query(UserTrackState).filter_by(sync_id=new_sync_id).first()
        assert migrated_state is not None


def test_decouple_collapsed_media_files_and_rescan():
    """Verify track 9819 containing collapsed media files is cleanly dissociated into 2 distinct Track records."""
    db = get_database()
    Base.metadata.drop_all(db.engine)
    Base.metadata.create_all(db.engine)

    session = db.get_session()
    try:
        # Create artist and collapsed track 9819 with 2 LocalMedia files
        from database.music_database import Artist
        artist = Artist(name="Capital Cities")
        session.add(artist)
        session.flush()

        collapsed_track = Track(
            id=9819,
            sync_id="g8a9b1c2",
            title="Safe and Sound",
            artist_id=artist.id,
            duration=343000,  # Erroneously overwritten by remix
        )
        session.add(collapsed_track)
        session.flush()

        from database import _canonicalize_path
        m1 = LocalMedia(
            media_id="med_0001",
            track_id=9819,
            file_path=_canonicalize_path("/music/Capital Cities/Safe and Sound.flac"),
            file_format="FLAC",
        )
        m2 = LocalMedia(
            media_id="med_0002",
            track_id=9819,
            file_path=_canonicalize_path("/music/Capital Cities/Safe and Sound (Remix).flac"),
            file_format="FLAC",
        )
        session.add_all([m1, m2])
        session.commit()

        # Execute decoupling / rescan
        decoupled_count = TrackRepository.decouple_collapsed_media(session)
        session.commit()
        session.expire_all()

        assert decoupled_count == 1

        # Verify there are now 2 distinct Track records
        tracks = session.query(Track).all()
        assert len(tracks) == 2

        track_ids = {t.id for t in tracks}
        assert 9819 in track_ids

        # Verify media files are now attached to separate tracks
        m1_refreshed = session.query(LocalMedia).filter_by(media_id="med_0001").first()
        m2_refreshed = session.query(LocalMedia).filter_by(media_id="med_0002").first()

        assert m1_refreshed.track_id != m2_refreshed.track_id
        assert m1_refreshed.track_id == 9819
        assert m2_refreshed.track_id != 9819

        # Rescan with accurate durations updates both tracks accurately
        t1_scan = EchosyncTrack(
            raw_title="Safe and Sound",
            artist_name="Capital Cities",
            album_title="In a Tidal Wave of Mystery",
            duration=193000,
            edition=None,
            media=[
                EchosyncMedia(
                    file_path="/music/Capital Cities/Safe and Sound.flac",
                    file_format="FLAC",
                )
            ]
        )
        t2_scan = EchosyncTrack(
            raw_title="Safe and Sound (Remix)",
            artist_name="Capital Cities",
            album_title="In a Tidal Wave of Mystery",
            duration=343000,
            edition="Remix",
            media=[
                EchosyncMedia(
                    file_path="/music/Capital Cities/Safe and Sound (Remix).flac",
                    file_format="FLAC",
                )
            ]
        )
        bulk_upsert_tracks(session, [t1_scan, t2_scan])
        session.commit()
        session.expire_all()

        t_orig = session.query(Track).filter_by(id=9819).first()
        assert t_orig.duration == 193000

        t_remix = session.query(Track).filter(Track.id != 9819).first()
        assert t_remix.duration == 343000
        assert t_remix.edition == "Remix"
    finally:
        session.close()
