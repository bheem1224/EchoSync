"""Unit tests for services.library_service reactive caching and db_read_lease."""

from unittest.mock import MagicMock, patch

from core.event_bus import event_bus
from services.library_service import (
    LibraryAdapter,
    get_database_stats,
    invalidate_stats_cache,
)
import web.services.library_service as web_library_service


def test_get_database_stats_caching():
    invalidate_stats_cache()

    mock_db = MagicMock()
    mock_db.count_artists.return_value = 10
    mock_db.count_albums.return_value = 25
    mock_db.count_tracks.return_value = 150

    with (
        patch("services.library_service.get_database", return_value=mock_db),
        patch("services.library_service._get_database_size_mb", return_value=42.5),
    ):
        # First call: populates cache
        stats1 = get_database_stats()
        assert stats1["total_tracks"] == 150
        assert stats1["total_artists"] == 10
        assert stats1["total_albums"] == 25
        assert stats1["database_size_mb"] == 42.5
        assert mock_db.count_tracks.call_count == 1

        # Second call: served from cache
        stats2 = get_database_stats()
        assert stats2 == stats1
        assert mock_db.count_tracks.call_count == 1

        # Force refresh: queries DB again
        stats3 = get_database_stats(force_refresh=True)
        assert stats3 == stats1
        assert mock_db.count_tracks.call_count == 2


def test_invalidate_stats_cache():
    invalidate_stats_cache()

    mock_db = MagicMock()
    mock_db.count_artists.return_value = 5
    mock_db.count_albums.return_value = 12
    mock_db.count_tracks.return_value = 80

    with (
        patch("services.library_service.get_database", return_value=mock_db),
        patch("services.library_service._get_database_size_mb", return_value=20.0),
    ):
        stats1 = get_database_stats()
        assert mock_db.count_tracks.call_count == 1

        invalidate_stats_cache()

        stats2 = get_database_stats()
        assert mock_db.count_tracks.call_count == 2
        assert stats2["total_tracks"] == 80


def test_reactive_event_bus_invalidation():
    invalidate_stats_cache()

    mock_db = MagicMock()
    mock_db.count_artists.return_value = 7
    mock_db.count_albums.return_value = 14
    mock_db.count_tracks.return_value = 95

    with (
        patch("services.library_service.get_database", return_value=mock_db),
        patch("services.library_service._get_database_size_mb", return_value=25.0),
    ):
        stats1 = get_database_stats()
        assert mock_db.count_tracks.call_count == 1

        # Publish library mutation event
        event_bus.publish({"event": "library_synced"})

        # Allow background dispatcher thread to process
        import time
        time.sleep(0.1)

        stats2 = get_database_stats()
        assert mock_db.count_tracks.call_count == 2


def test_library_adapter_overview():
    invalidate_stats_cache()

    mock_db = MagicMock()
    mock_db.count_artists.return_value = 3
    mock_db.count_albums.return_value = 6
    mock_db.count_tracks.return_value = 40

    with (
        patch("services.library_service.get_database", return_value=mock_db),
        patch("services.library_service._get_database_size_mb", return_value=15.0),
    ):
        adapter = LibraryAdapter()
        overview = adapter.overview()

        assert "servers" in overview
        assert len(overview["servers"]) == 1
        assert overview["servers"][0]["track_count"] == 40
        assert overview["stats"]["total_tracks"] == 40
        assert overview["stats"]["database_size_mb"] == 15.0


def test_web_services_compatibility_reexports():
    assert web_library_service.LibraryAdapter is LibraryAdapter
    assert web_library_service.get_database_stats is get_database_stats
    assert web_library_service.invalidate_stats_cache is invalidate_stats_cache

