from unittest.mock import MagicMock
from pathlib import Path
from core.db.echo_sync_track import EchosyncTrack
from services.metadata_enhancer import RetroactiveEnhancer


def test_identify_file_handles_single_echosync_track_from_search_metadata(monkeypatch):
    enhancer = RetroactiveEnhancer()
    file_path = Path("/data/downloads/test_track.flac")

    # Mock provider search_metadata returning a SINGLE EchosyncTrack object (not a list)
    returned_track = EchosyncTrack(
        raw_title="Gangsta as I Wanna Be",
        artist_name="Spice 1",
        album_title="Thug Reunion",
        musicbrainz_id="b33979f4-030a-40f6-8946-63f807e96524",
    )

    mock_provider = MagicMock()
    mock_provider.search_metadata.return_value = returned_track
    mock_provider.get_metadata.return_value = returned_track

    # Mock echosync_core.extract_metadata
    import echosync_core
    monkeypatch.setattr(echosync_core, "extract_metadata", lambda path: {
        "title": "Gangsta as I Wanna Be",
        "artist": "Spice 1",
        "album": "Thug Reunion",
    })

    # Mock _get_plugin on enhancer
    monkeypatch.setattr(enhancer, "_get_plugin", lambda cap, **kwargs: mock_provider)

    metadata, confidence = enhancer.identify_file(file_path)

    assert metadata is not None
    assert confidence >= 0.85
