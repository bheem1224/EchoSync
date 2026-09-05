from unittest.mock import MagicMock, patch

from core.db.echo_sync_track import EchosyncTrack
from database.working_database import ReviewTask, get_working_database
from services.isrc_lookup_service import dispatch_isrc_lookup
from services.metadata_enhancer import RetroactiveEnhancer
from web.routes.metadata_review import ISRCLookupRequest, lookup_review_queue_item_isrc


def test_dispatch_isrc_lookup_waterfall_to_spotify():
    mb_provider = MagicMock()
    mb_provider.name = "EchoSync.musicbrainz"
    mb_provider.supports_isrc_lookup = True
    mb_provider.search_by_isrc.return_value = None  # MusicBrainz misses

    spotify_provider = MagicMock()
    spotify_provider.name = "EchoSync.spotify"
    spotify_provider.supports_isrc_lookup = True
    spotify_track = EchosyncTrack(
        raw_title="Starboy",
        artist_name="The Weeknd",
        album_title="Starboy",
        release_year=2016,
        isrc="USUM71607007",
    )
    spotify_track.identifiers = {"source": "EchoSync.spotify"}
    spotify_provider.search_by_isrc.return_value = spotify_track

    with patch(
        "core.nexus_framework.plugin_loader.PluginRegistry.get_plugins_with_capability"
    ) as mock_plugins:
        mock_plugins.return_value = [mb_provider, spotify_provider]
        res = dispatch_isrc_lookup("USUM71607007")

        assert res is not None
        assert res.raw_title == "Starboy"
        assert res.artist_name == "The Weeknd"
        assert res.identifiers.get("source") == "EchoSync.spotify"


def test_metadata_enhancer_identifies_via_isrc_waterfall(tmp_path):
    file_path = tmp_path / "track_with_isrc.mp3"
    file_path.write_bytes(b"dummy audio content")

    enhancer = RetroactiveEnhancer()

    spotify_track = EchosyncTrack(
        raw_title="Blinding Lights",
        artist_name="The Weeknd",
        album_title="After Hours",
        release_year=2020,
        isrc="USUG11904206",
    )
    spotify_track.identifiers = {"source": "EchoSync.spotify"}

    with (
        patch("echosync_core.extract_metadata", return_value={"isrc": "USUG11904206"}),
        patch(
            "services.isrc_lookup_service.dispatch_isrc_lookup",
            return_value=spotify_track,
        ),
    ):
        result_meta, confidence = enhancer.identify_file(file_path)

        assert result_meta is not None
        assert confidence == 0.92
        assert result_meta['raw_title'] == "Blinding Lights"


def test_review_queue_isrc_lookup_uses_waterfall(tmp_path):
    file_path = tmp_path / "song.mp3"
    file_path.write_bytes(b"fake data")

    db = get_working_database()
    with db.session_scope() as session:
        task = ReviewTask(
            file_path=str(file_path),
            status="pending",
            track_data={"isrc": "USUG11904206"},
        )
        session.add(task)
        session.flush()
        task_id = task.id

    spotify_track = EchosyncTrack(
        raw_title="Blinding Lights",
        artist_name="The Weeknd",
        album_title="After Hours",
        release_year=2020,
        isrc="USUG11904206",
    )
    spotify_track.identifiers = {"source": "EchoSync.spotify"}

    with patch(
        "services.isrc_lookup_service.dispatch_isrc_lookup", return_value=spotify_track
    ):
        req = ISRCLookupRequest(isrc="USUG11904206")
        res = lookup_review_queue_item_isrc(task_id, req)

        assert res["success"] is True
        assert res["match_found"] is True
        assert res["message"] == "Match found via EchoSync.spotify"
        assert "title" in res["updated_fields"]
        assert "artist" in res["updated_fields"]
        assert res["metadata"]["title"] == "Blinding Lights"
        assert res["metadata"]["artist"] == "The Weeknd"


def test_review_queue_isrc_lookup_no_match(tmp_path):
    file_path = tmp_path / "song_missing.mp3"
    file_path.write_bytes(b"fake data")

    db = get_working_database()
    with db.session_scope() as session:
        task = ReviewTask(
            file_path=str(file_path),
            status="pending",
            track_data={"isrc": "USUG11904206"},
        )
        session.add(task)
        session.flush()
        task_id = task.id

    with patch("services.isrc_lookup_service.dispatch_isrc_lookup", return_value=None):
        req = ISRCLookupRequest(isrc="USUG11904206")
        res = lookup_review_queue_item_isrc(task_id, req)

        assert res["success"] is True
        assert res["match_found"] is False
        assert res["metadata"] is None
        assert res["message"] == "No matching record found across configured providers"
