from database.music_database import Album, Artist, Base, LocalMedia, MusicDatabase, Track
from core.database.repositories.track_repo import TrackRepository


def test_placeholder_tracks_are_selected_when_metadata_is_populated(tmp_path):
    music_db = MusicDatabase(tmp_path / "music.db")
    Base.metadata.create_all(music_db.engine)

    with music_db.session_scope() as session:
        artist = Artist(name="Unknown Artist", normalized_name="unknown artist")
        album = Album(title="Unknown Album", normalized_title="unknown album", artist=artist)
        session.add_all([artist, album])
        session.flush()

        for index in range(10):
            track = Track(
                title=f"Populated title {index}",
                normalized_title=f"populated title {index}",
                sync_id=f"placeholder-{index}",
                artist_id=artist.id,
                album_id=album.id,
                metadata_enhanced=True,
            )
            session.add(track)
            session.flush()
            session.add(
                LocalMedia(
                    track_id=track.id,
                    media_id=f"placeholder-media-{index}",
                    file_path=f"/music/placeholder-{index}.flac",
                    file_format="flac",
                )
            )

        session.flush()
        candidates = TrackRepository.get_tracks_for_enhancement(
            session,
            batch_size=50,
            check_all_files=False,
        )

    assert {track.sync_id for track in candidates} == {f"placeholder-{index}" for index in range(10)}
