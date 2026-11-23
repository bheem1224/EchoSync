from unittest.mock import MagicMock

from core.database.repositories.track_repo import TrackRepository
from core.db.echo_sync_track import EchosyncMedia, EchosyncTrack
from database.music_database import (
    Artist,
    Base,
    ExternalIdentifier,
    LocalMedia,
    MusicDatabase,
    Track,
)
from plugins.EchoSync.plex.client import (
    PlexClient,
    verify_playlist_integrity,
    verify_plex_candidate,
)


class DummyPart:
    def __init__(self, file_path):
        self.file = file_path


class DummyMedia:
    def __init__(self, file_path):
        self.parts = [DummyPart(file_path)]


class DummyPlexTrack:
    def __init__(self, rating_key, title, artist, duration, file_path):
        self.ratingKey = rating_key
        self.title = title
        self.grandparentTitle = artist
        self.duration = duration
        self.media = [DummyMedia(file_path)]


def test_verify_plex_candidate_scoring():
    local_meta = EchosyncTrack(
        raw_title="Alone",
        artist_name="Alan Walker",
        album_title="Alone",
        duration_ms=161000,
        media=[EchosyncMedia(file_path="/data/music/Alan Walker/Alone.flac")],
    )

    # 1. Perfect candidate: same duration, same filename, same artist
    perfect_cand = DummyPlexTrack(
        rating_key="99901",
        title="Alone",
        artist="Alan Walker",
        duration=161500,  # Delta 500ms <= 3000ms -> +20
        file_path="/plex_media/Alan Walker/Alone.flac",  # Basename match -> +50
    )
    score = verify_plex_candidate(perfect_cand, local_meta)
    assert score >= 100.0  # 20 (duration) + 50 (file) + 30 (artist) = 100

    # 2. Version / duration mismatch: duration delta > 3000ms -> score 0.0
    remix_cand = DummyPlexTrack(
        rating_key="99902",
        title="Alone (Restrung)",
        artist="Alan Walker",
        duration=185000,  # Delta 24000ms > 3000ms
        file_path="/plex_media/Alan Walker/Alone (Restrung).flac",
    )
    assert verify_plex_candidate(remix_cand, local_meta) == 0.0


def test_plex_fast_path_returns_cached_item(monkeypatch):
    client = PlexClient.__new__(PlexClient)
    client.server = MagicMock()
    client.music_library = MagicMock()
    client.ensure_connection = MagicMock(return_value=True)

    dummy_item = DummyPlexTrack(
        "12345", "Alone", "Alan Walker", 161000, "/music/Alone.flac"
    )
    client.server.fetchItem.return_value = dummy_item

    meta = EchosyncTrack(
        raw_title="Alone",
        artist_name="Alan Walker",
        album_title="Alone",
        duration_ms=161000,
    )
    item, is_recovered = client.fetch_or_recover_track("12345", meta)

    assert item == dummy_item
    assert is_recovered is False
    client.server.fetchItem.assert_called_once_with(12345)
    client.music_library.search.assert_not_called()


def test_plex_404_triggers_recovery_matrix(monkeypatch):
    client = PlexClient.__new__(PlexClient)
    client.server = MagicMock()
    client.music_library = MagicMock()
    client.ensure_connection = MagicMock(return_value=True)

    # Fast path 404s
    client.server.fetchItem.side_effect = Exception("(404) not_found")

    # Live search candidates: candidate 1 is a mismatch, candidate 2 matches duration & filename
    cand_wrong = DummyPlexTrack(
        "99001", "Alone (Club Mix)", "Alan Walker", 240000, "/music/Alone (Club).flac"
    )
    cand_correct = DummyPlexTrack(
        "99002", "Alone", "Alan Walker", 161200, "/plex_container/music/Alone.flac"
    )
    client.music_library.search.return_value = [cand_wrong, cand_correct]

    meta = EchosyncTrack(
        raw_title="Alone",
        artist_name="Alan Walker",
        album_title="Alone",
        duration_ms=161000,
        media=[EchosyncMedia(file_path="C:/Music/Alan Walker/Alone.flac")],
    )

    item, is_recovered = client.fetch_or_recover_track("12345_stale", meta)

    assert item == cand_correct
    assert is_recovered is True
    assert item.ratingKey == "99002"
    client.music_library.search.assert_called_once_with(
        "Alone", libtype="track", maxresults=50
    )


def test_plex_recovery_rejects_version_mismatch(monkeypatch):
    client = PlexClient.__new__(PlexClient)
    client.server = MagicMock()
    client.music_library = MagicMock()
    client.ensure_connection = MagicMock(return_value=True)

    client.server.fetchItem.side_effect = Exception("(404) not_found")

    # Search only returns versions with duration delta > 3000ms
    cand_mismatch = DummyPlexTrack(
        "99001", "Alone (Extended)", "Alan Walker", 210000, "/music/Alone_ext.flac"
    )
    client.music_library.search.return_value = [cand_mismatch]

    meta = EchosyncTrack(
        raw_title="Alone",
        artist_name="Alan Walker",
        album_title="Alone",
        duration_ms=161000,
        media=[EchosyncMedia(file_path="C:/Music/Alan Walker/Alone.flac")],
    )

    item, is_recovered = client.fetch_or_recover_track("stale_key", meta)

    assert item is None
    assert is_recovered is False


def test_track_repo_update_external_identifiers(tmp_path):
    db_file = tmp_path / "test.db"
    db = MusicDatabase(database_path=str(db_file))
    Base.metadata.create_all(db.engine)

    with db.session_scope() as session:
        # Create Artist, Track, LocalMedia
        artist = Artist(name="Alan Walker", normalized_name="alan walker")
        session.add(artist)
        session.flush()

        track = Track(
            sync_id="track_sync_01",
            title="Alone",
            normalized_title="alone",
            artist_id=artist.id,
        )
        session.add(track)
        session.flush()

        media = LocalMedia(
            media_id="nanoid_media_01", track_id=track.id, file_path="/music/Alone.flac"
        )
        session.add(media)
        session.flush()

        # Initial external identifier with old rating key
        ext = ExternalIdentifier(
            media_id=media.media_id, plugin_source="plex", plugin_item_id="146900"
        )
        session.add(ext)
        session.commit()

        # Execute batch update
        updated = TrackRepository.update_external_identifiers(
            session,
            [(media.media_id, "99002")],
            provider="plex",
        )
        assert updated == 1

        refreshed_ext = (
            session.query(ExternalIdentifier)
            .filter_by(media_id=media.media_id, plugin_source="plex")
            .first()
        )
        assert refreshed_ext is not None
        assert refreshed_ext.plugin_item_id == "99002"
        assert refreshed_ext.raw_data.get("recovered_at") is not None


def test_verify_plex_candidate_without_basename_and_variant_guard():
    local_meta = EchosyncTrack(
        raw_title="Heat Waves",
        artist_name="Glass Animals",
        album_title="Dreamland",
        duration_ms=238000,
        media=[EchosyncMedia(file_path="/music/Glass Animals/05 - Heat Waves.flac")],
    )

    # Renamed file on Plex (no basename match), but exact title + artist + duration -> must pass >= 70
    renamed_cand = DummyPlexTrack(
        rating_key="151400",
        title="Heat Waves",
        artist="Glass Animals",
        duration=238800,
        file_path="/plex/Glass Animals/Heat Waves.flac",
    )
    assert verify_plex_candidate(renamed_cand, local_meta) >= 95.0

    # Same duration & artist, but instrumental variant -> must be rejected (0.0)
    inst_cand = DummyPlexTrack(
        rating_key="151483",
        title="Heat Waves (instrumental)",
        artist="Glass Animals",
        duration=238500,
        file_path="/plex/Glass Animals/Heat Waves (instrumental).flac",
    )
    assert verify_plex_candidate(inst_cand, local_meta) == 0.0

    # Wrong artist with identical title & duration -> must stay below 70.0
    wrong_artist = DummyPlexTrack(
        rating_key="151499",
        title="Heat Waves",
        artist="Cover Band XYZ",
        duration=238000,
        file_path="/plex/Cover Band XYZ/Heat Waves.flac",
    )
    assert verify_plex_candidate(wrong_artist, local_meta) < 70.0


def test_verify_playlist_integrity_detects_mismatches_and_missing():
    meta_ok = EchosyncTrack(
        raw_title="Alone",
        artist_name="Alan Walker",
        album_title="Alone",
        duration_ms=161000,
        media=[EchosyncMedia(file_path="/music/Alan Walker/Alone.flac")],
    )
    meta_hw = EchosyncTrack(
        raw_title="Heat Waves",
        artist_name="Glass Animals",
        album_title="Dreamland",
        duration_ms=238000,
        media=[EchosyncMedia(file_path="/music/Glass Animals/05 - Heat Waves.flac")],
    )
    meta_missing = EchosyncTrack(
        raw_title="Faded",
        artist_name="Alan Walker",
        album_title="Faded",
        duration_ms=212000,
    )

    plex_items = [
        DummyPlexTrack("101", "Alone", "Alan Walker", 161200, "/plex/Alan Walker/Alone.flac"),
        DummyPlexTrack("102", "Heat Waves (instrumental)", "Glass Animals", 238200, "/plex/hw_inst.flac"),
    ]
    expected_by_rk = {
        "101": {"meta": meta_ok, "media_id": "m1", "track_id": 1},
        "102": {"meta": meta_hw, "media_id": "m2", "track_id": 2},
        "103": {"meta": meta_missing, "media_id": "m3", "track_id": 3},
    }

    report = verify_playlist_integrity(plex_items, expected_by_rk)
    assert report["verified"] == 1
    assert report["expected"] == 3
    assert report["missing_count"] == 1
    assert report["missing_keys"] == ["103"]
    assert report["mismatch_count"] == 1
    assert report["mismatches"][0]["rating_key"] == "102"
    assert report["mismatches"][0]["reason"] == "version_mismatch"
