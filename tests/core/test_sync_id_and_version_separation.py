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
