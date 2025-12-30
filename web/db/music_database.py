"""Wrapper for music_database - ensures clean separation and easier debugging."""
from typing import List, Optional, Dict, Any, Tuple
from database.music_database import (
    MusicDatabase,
    DatabaseArtist,
    DatabaseAlbum,
    DatabaseTrack,
    DatabaseTrackWithMetadata,
    WatchlistArtist,
    SimilarArtist,
    DiscoveryTrack,
    RecentRelease
)
from core.models import Track


class MusicDatabaseWrapper:
    """Wrapper around MusicDatabase for web module access."""
    
    def __init__(self, database_path: str = None):
        self._db = MusicDatabase(database_path)

    # === Canonical Track Operations ===
    def create_track(self, track: Track) -> str:
        return self._db.create_track(track)

    def update_track(self, track: Track) -> None:
        return self._db.update_track(track)

    def get_track(self, track_id: str) -> Optional[Track]:
        return self._db.get_track(track_id)

    def find_track_by_provider_ref(self, provider: str, provider_id: str) -> Optional[Track]:
        return self._db.find_track_by_provider_ref(provider, provider_id)

    def find_track_by_isrc(self, isrc: str) -> Optional[Track]:
        return self._db.find_track_by_isrc(isrc)

    def find_track_by_musicbrainz_id(self, mbid: str) -> Optional[Track]:
        return self._db.find_track_by_musicbrainz_id(mbid)

    def fuzzy_match_tracks(self, title: str, artists: List[str], album: Optional[str] = None, threshold: float = 0.0) -> List[Track]:
        return self._db.fuzzy_match_tracks(title, artists, album, threshold)

    # === Statistics ===
    def get_statistics(self) -> Dict[str, int]:
        return self._db.get_statistics()

    def get_statistics_for_server(self, server_source: str = None) -> Dict[str, int]:
        return self._db.get_statistics_for_server(server_source)

    # === Cleanup ===
    def clear_all_data(self):
        return self._db.clear_all_data()

    def clear_server_data(self, server_source: str):
        return self._db.clear_server_data(server_source)

    def cleanup_orphaned_records(self) -> Dict[str, int]:
        return self._db.cleanup_orphaned_records()

    # === Artist Operations ===
    def insert_or_update_artist(self, plex_artist) -> bool:
        return self._db.insert_or_update_artist(plex_artist)

    def insert_or_update_media_artist(self, artist_obj, server_source: str = 'plex') -> bool:
        return self._db.insert_or_update_media_artist(artist_obj, server_source)

    def get_artist(self, artist_id: int) -> Optional[DatabaseArtist]:
        return self._db.get_artist(artist_id)

    def search_artists(self, query: str, limit: int = 50) -> List[DatabaseArtist]:
        return self._db.search_artists(query, limit)

    # === Album Operations ===
    def insert_or_update_album(self, plex_album, artist_id: int) -> bool:
        return self._db.insert_or_update_album(plex_album, artist_id)

    def insert_or_update_media_album(self, album_obj, artist_id: str, server_source: str = 'plex') -> bool:
        return self._db.insert_or_update_media_album(album_obj, artist_id, server_source)

    def get_albums_by_artist(self, artist_id: int) -> List[DatabaseAlbum]:
        return self._db.get_albums_by_artist(artist_id)

    def search_albums(self, title: str = "", artist: str = "", limit: int = 50, server_source: Optional[str] = None) -> List[DatabaseAlbum]:
        return self._db.search_albums(title, artist, limit, server_source)

    def check_album_exists(self, title: str, artist: str, confidence_threshold: float = 0.8) -> Tuple[Optional[DatabaseAlbum], float]:
        return self._db.check_album_exists(title, artist, confidence_threshold)

    def check_album_completeness(self, album_id: int, expected_track_count: Optional[int] = None) -> Tuple[int, int, bool]:
        return self._db.check_album_completeness(album_id, expected_track_count)

    def check_album_exists_with_completeness(self, title: str, artist: str, expected_track_count: Optional[int] = None, confidence_threshold: float = 0.8, server_source: Optional[str] = None) -> Tuple[Optional[DatabaseAlbum], float, int, int, bool]:
        return self._db.check_album_exists_with_completeness(title, artist, expected_track_count, confidence_threshold, server_source)

    def check_album_exists_with_editions(self, title: str, artist: str, confidence_threshold: float = 0.8, expected_track_count: Optional[int] = None, server_source: Optional[str] = None) -> Tuple[Optional[DatabaseAlbum], float]:
        return self._db.check_album_exists_with_editions(title, artist, confidence_threshold, expected_track_count, server_source)

    def get_album_completion_stats(self, artist_name: str) -> Dict[str, int]:
        return self._db.get_album_completion_stats(artist_name)

    # === Track Operations ===
    def insert_or_update_track(self, plex_track, album_id: int, artist_id: int) -> bool:
        return self._db.insert_or_update_track(plex_track, album_id, artist_id)

    def insert_or_update_media_track(self, track_obj, album_id: str, artist_id: str, server_source: str = 'plex') -> bool:
        return self._db.insert_or_update_media_track(track_obj, album_id, artist_id, server_source)

    def track_exists(self, track_id) -> bool:
        return self._db.track_exists(track_id)

    def track_exists_by_server(self, track_id, server_source: str) -> bool:
        return self._db.track_exists_by_server(track_id, server_source)

    def get_track_by_id(self, track_id) -> Optional[DatabaseTrackWithMetadata]:
        return self._db.get_track_by_id(track_id)

    def get_tracks_by_album(self, album_id: int) -> List[DatabaseTrack]:
        return self._db.get_tracks_by_album(album_id)

    def search_tracks(self, title: str = "", artist: str = "", limit: int = 50, server_source: str = None) -> List[DatabaseTrack]:
        return self._db.search_tracks(title, artist, limit, server_source)

    def check_track_exists(self, title: str, artist: str, confidence_threshold: float = 0.8, server_source: str = None) -> Tuple[Optional[DatabaseTrack], float]:
        return self._db.check_track_exists(title, artist, confidence_threshold, server_source)

    # === Metadata & Preferences ===
    def set_metadata(self, key: str, value: str):
        return self._db.set_metadata(key, value)

    def get_metadata(self, key: str) -> Optional[str]:
        return self._db.get_metadata(key)

    def set_preference(self, key: str, value: str):
        return self._db.set_preference(key, value)

    def get_preference(self, key: str) -> Optional[str]:
        return self._db.get_preference(key)

    def get_quality_profile(self) -> dict:
        return self._db.get_quality_profile()

    def set_quality_profile(self, profile: dict) -> bool:
        return self._db.set_quality_profile(profile)

    # === Wishlist ===
    def add_to_wishlist(self, spotify_track_data: Dict[str, Any], failure_reason: str = "Download failed", retry_count: int = 0) -> bool:
        return self._db.add_to_wishlist(spotify_track_data, failure_reason, retry_count)

    def remove_from_wishlist(self, spotify_track_id: str) -> bool:
        return self._db.remove_from_wishlist(spotify_track_id)

    def get_wishlist_tracks(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        return self._db.get_wishlist_tracks(limit)

    def update_wishlist_retry(self, spotify_track_id: str, success: bool, error_message: str = None) -> bool:
        return self._db.update_wishlist_retry(spotify_track_id, success, error_message)

    def get_wishlist_count(self) -> int:
        return self._db.get_wishlist_count()

    def clear_wishlist(self) -> bool:
        return self._db.clear_wishlist()

    def remove_wishlist_duplicates(self) -> int:
        return self._db.remove_wishlist_duplicates()

    # === Watchlist ===
    def add_artist_to_watchlist(self, spotify_artist_id: str, artist_name: str) -> bool:
        return self._db.add_artist_to_watchlist(spotify_artist_id, artist_name)

    def remove_artist_from_watchlist(self, spotify_artist_id: str) -> bool:
        return self._db.remove_artist_from_watchlist(spotify_artist_id)

    def is_artist_in_watchlist(self, spotify_artist_id: str) -> bool:
        return self._db.is_artist_in_watchlist(spotify_artist_id)

    def get_watchlist_artists(self) -> List[WatchlistArtist]:
        return self._db.get_watchlist_artists()

    def get_watchlist_count(self) -> int:
        return self._db.get_watchlist_count()

    def update_watchlist_artist_image(self, spotify_artist_id: str, image_url: str) -> bool:
        return self._db.update_watchlist_artist_image(spotify_artist_id, image_url)

    # === Similar Artists ===
    def add_or_update_similar_artist(self, source_artist_id: str, similar_artist_spotify_id: str, similar_artist_name: str) -> bool:
        return self._db.add_or_update_similar_artist(source_artist_id, similar_artist_spotify_id, similar_artist_name)

    def get_similar_artists_for_source(self, source_artist_id: str) -> List[SimilarArtist]:
        return self._db.get_similar_artists_for_source(source_artist_id)

    def has_fresh_similar_artists(self, source_artist_id: str, days_threshold: int = 30) -> bool:
        return self._db.has_fresh_similar_artists(source_artist_id, days_threshold)

    def get_top_similar_artists(self, limit: int = 50) -> List[SimilarArtist]:
        return self._db.get_top_similar_artists(limit)

    # === Discovery Pool ===
    def add_to_discovery_pool(self, track_data: Dict[str, Any]) -> bool:
        return self._db.add_to_discovery_pool(track_data)

    def rotate_discovery_pool(self, max_tracks: int = 2000, remove_count: int = 500):
        return self._db.rotate_discovery_pool(max_tracks, remove_count)

    def get_discovery_pool_tracks(self, limit: int = 100, new_releases_only: bool = False) -> List[DiscoveryTrack]:
        return self._db.get_discovery_pool_tracks(limit, new_releases_only)

    def should_populate_discovery_pool(self, hours_threshold: int = 24) -> bool:
        return self._db.should_populate_discovery_pool(hours_threshold)

    def update_discovery_pool_timestamp(self, track_count: int) -> bool:
        return self._db.update_discovery_pool_timestamp(track_count)

    def cleanup_old_discovery_tracks(self, days_threshold: int = 365) -> int:
        return self._db.cleanup_old_discovery_tracks(days_threshold)

    # === Recent Releases ===
    def add_recent_release(self, watchlist_artist_id: int, album_data: Dict[str, Any]) -> bool:
        return self._db.add_recent_release(watchlist_artist_id, album_data)

    def get_recent_releases(self, limit: int = 50) -> List[RecentRelease]:
        return self._db.get_recent_releases(limit)

    # === Database Info ===
    def get_database_info(self) -> Dict[str, Any]:
        return self._db.get_database_info()

    def get_database_info_for_server(self, server_source: str = None) -> Dict[str, Any]:
        return self._db.get_database_info_for_server(server_source)

    def wal_checkpoint(self, mode: str = "TRUNCATE") -> bool:
        return self._db.wal_checkpoint(mode)

    # === Library ===
    def get_library_artists(self, search_query: str = "", letter: str = "", page: int = 1, limit: int = 50) -> Dict[str, Any]:
        return self._db.get_library_artists(search_query, letter, page, limit)

    def close(self):
        return self._db.close()


# Singleton instance for app-wide use
_instance: Optional[MusicDatabaseWrapper] = None

def get_music_database() -> MusicDatabaseWrapper:
    """Get or create the singleton wrapper instance."""
    global _instance
    if _instance is None:
        _instance = MusicDatabaseWrapper()
    return _instance
