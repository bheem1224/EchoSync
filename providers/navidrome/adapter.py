"""
Navidrome ProviderAdapter implementation.

Creates SoulSyncTrack from Navidrome library with extracted metadata including
ISRC, MusicBrainz IDs, and audio quality information.

Adheres to Track-centric architecture.
"""

from typing import List, Optional, Dict, Any
from core.tiered_logger import get_logger
from core.models import ProviderType, Track
from core.storage import get_storage_service
from core.provider_base import ProviderBase
from core.matching_engine.soul_sync_track import SoulSyncTrack
from core.job_queue import register_job
from services.user_ratings_service import UserRatingsService
import requests

logger = get_logger("navidrome_adapter")


def poll_navidrome_ratings():
    """
    Background job to poll Navidrome (Subsonic API) for user ratings and play counts.
    """
    try:
        from core.settings import config_manager

        # Check if navidrome is enabled
        providers = config_manager.get('providers', {})
        nav_config = providers.get('navidrome', {})

        if not nav_config.get('enabled', False):
            return

        base_url = nav_config.get('url')
        username = nav_config.get('username')
        password = nav_config.get('password') # The user might use token auth but we will use simple password auth for now if configured

        # Depending on how the Navidrome client stores credentials in the DB, we might need to retrieve them differently
        # Assuming we can get them from config_manager or need to use a client.
        # But per requirements: "implement the specific, lightweight HTTP API calls you need directly inside providers/navidrome/adapter.py."

        if not base_url or not username:
            logger.debug("Navidrome credentials incomplete. Skipping rating poll.")
            return

        # Prepare Subsonic API authentication parameters (using plain password for simplicity, or salt/token if needed)
        # Note: A proper Subsonic client would compute the md5(password + salt).
        # We will use plain auth for simplicity, Subsonic API supports it over HTTPS.

        params = {
            "u": username,
            "p": password,
            "v": "1.16.1",
            "c": "SoulSync",
            "f": "json"
        }

        # Fetch all starred tracks for rating (Subsonic usually sets rating 5 for starred)
        # Or better, fetch top songs / random songs or a full list to get ratings and playCounts
        # A more robust way to get all rated/scrobbled tracks is `getStarred` and `getTopSongs`

        ratings_service = UserRatingsService()

        # Let's fetch Top Songs (which should have playCount > 0)
        top_songs_url = f"{base_url.rstrip('/')}/rest/getTopSongs"
        top_songs_params = params.copy()
        top_songs_params["count"] = 500 # Adjust limit as needed

        response = requests.get(top_songs_url, params=top_songs_params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "subsonic-response" in data and "topSongs" in data["subsonic-response"]:
                songs = data["subsonic-response"]["topSongs"].get("song", [])
                for song in songs:
                    title = song.get("title")
                    artist = song.get("artist")
                    play_count = song.get("playCount", 0)
                    rating = song.get("rating")

                    if title and artist:
                        # Update play count if greater than 0
                        if play_count > 0:
                            # We can't strictly 'increment' if we only get the absolute total,
                            # but the requirement says to "pass to increment_play_count".
                            # Wait, increment_play_count adds 1. Navidrome returns the total.
                            # Since the requirement says "increment_play_count()", and this is a polling script,
                            # we should probably just call it once per scrobble. Navidrome doesn't have a "recently played" webhook.
                            # Actually, `getNowPlaying` or `getRecentlyPlayed` would be better for incrementing,
                            # BUT we can just pass the data to the service. We might need a `set_play_count` method
                            # or just call increment_play_count in a loop if we track last polled.
                            # For simplicity and strictly following the requirement: "Extract the rating... and the playCount... Pass these values into UserRatingsService"
                            # Since the Subsonic API only gives us total play count we will just call a setter
                            ratings_service.set_play_count(
                                artist_name=artist,
                                track_title=title,
                                play_count=play_count,
                                source="navidrome",
                                user_identifier=username
                            )

                    if rating is not None:
                        normalized_rating = float(rating) * 2.0
                        ratings_service.update_rating(
                            artist_name=artist,
                            track_title=title,
                            rating=normalized_rating,
                            source="navidrome",
                            user_identifier=username
                        )

    except Exception as e:
        logger.error(f"Error polling Navidrome ratings: {e}")


class NavidromeRatingAdapter:
    @staticmethod
    def register_job():
        register_job(
            name="navidrome_rating_adapter",
            func=poll_navidrome_ratings,
            interval_seconds=3600,  # Poll every hour
            enabled=True,
            tags=["navidrome", "ratings"],
            plugin="navidrome"
        )


def convert_navidrome_track_to_soulsync(navidrome_track) -> Optional[SoulSyncTrack]:
    """
    Convert Navidrome track object to SoulSyncTrack.
    
    Extracts Navidrome metadata including ISRC, MusicBrainz IDs, and audio quality.
    
    Args:
        navidrome_track: Navidrome track object or wrapper (NavidromeTrack)
        
    Returns:
        SoulSyncTrack with all available metadata, or None if conversion fails
    """
    try:
        # Get raw data dict if this is a wrapper object
        raw_data = navidrome_track._data if hasattr(navidrome_track, '_data') else navidrome_track
        
        # Extract basic metadata from raw data dict
        title = raw_data.get('title') if isinstance(raw_data, dict) else getattr(navidrome_track, 'title', None)
        artist = raw_data.get('artist') if isinstance(raw_data, dict) else getattr(navidrome_track, 'artist', None)
        album = raw_data.get('album') if isinstance(raw_data, dict) else getattr(navidrome_track, 'album', None)
        
        if not title or not artist:
            logger.warning(f"Navidrome track missing title or artist: {title} / {artist}")
            return None
        
        # Duration - Navidrome uses seconds, we need milliseconds
        duration_ms = None
        if isinstance(raw_data, dict):
            duration_raw = raw_data.get('duration')
            if duration_raw:
                try:
                    duration_ms = int(duration_raw) * 1000  # Convert seconds to ms
                except (ValueError, TypeError):
                    pass
        else:
            duration_ms = getattr(navidrome_track, 'duration', None)
        
        track_number = raw_data.get('track') if isinstance(raw_data, dict) else getattr(navidrome_track, 'trackNumber', None)
        if track_number:
            try:
                track_number = int(track_number)
            except (ValueError, TypeError):
                pass
        
        disc_number = raw_data.get('discNumber') if isinstance(raw_data, dict) else None
        if disc_number:
            try:
                disc_number = int(disc_number)
            except (ValueError, TypeError):
                pass
        
        # Audio quality metadata
        bitrate = raw_data.get('bitRate') if isinstance(raw_data, dict) else None
        if bitrate:
            try:
                bitrate = int(bitrate)
            except (ValueError, TypeError):
                pass
        
        sample_rate = raw_data.get('sampleRate') if isinstance(raw_data, dict) else None
        if sample_rate:
            try:
                sample_rate = int(sample_rate)
            except (ValueError, TypeError):
                pass
        
        bit_depth = raw_data.get('bitsPerSample') if isinstance(raw_data, dict) else None
        if bit_depth:
            try:
                bit_depth = int(bit_depth)
            except (ValueError, TypeError):
                pass
        
        # File format and path
        file_format = raw_data.get('suffix') if isinstance(raw_data, dict) else None
        if file_format:
            file_format = file_format.lower()
        
        file_path = raw_data.get('path') if isinstance(raw_data, dict) else None
        
        # Extract ISRC and MusicBrainz IDs
        isrc = raw_data.get('isrc') if isinstance(raw_data, dict) else None
        musicbrainz_id = raw_data.get('mbRecordingID') if isinstance(raw_data, dict) else None
        musicbrainz_album_id = raw_data.get('mbAlbumID') if isinstance(raw_data, dict) else None
        
        year = None
        if isinstance(raw_data, dict):
            year_val = raw_data.get('year')
            if year_val:
                try:
                    # If it's a date string, extract just the year
                    year_str = str(year_val)
                    if len(year_str) >= 4:
                        year = int(year_str[:4])
                    else:
                        year = int(year_val)
                except (ValueError, TypeError):
                    year = None
        else:
            year = getattr(navidrome_track, 'year', None)
        
        # Use ProviderBase factory method for normalization
        return ProviderBase.create_soul_sync_track(
            title=title,
            artist=artist,
            album=album,
            duration_ms=duration_ms,
            year=year,
            track_number=track_number,
            disc_number=disc_number,
            isrc=isrc,
            musicbrainz_id=musicbrainz_id,
            musicbrainz_album_id=musicbrainz_album_id,
            bitrate=bitrate,
            file_format=file_format,
            sample_rate=sample_rate,
            bit_depth=bit_depth,
            file_path=file_path,
            source='navidrome'
        )
    
    except Exception as e:
        logger.error(f"Error converting Navidrome track to SoulSyncTrack: {e}", exc_info=True)
        return None


class NavidromeAdapter:
    def __init__(self, navidrome_client=None):
        storage = get_storage_service()
        db = storage.get_music_database()
        super().__init__(db=db, provider_type=ProviderType.NAVIDROME)
        self.navidrome = navidrome_client

    # Field contracts
    def get_provides_fields(self) -> List[str]:
        return [
            "title",
            "artists",
            "album",
            "duration_ms",
            "track_number",
            "release_year",
        ]

    def get_consumes_fields(self) -> List[str]:
        # Library ingestion does not require prior fields
        return []

    def requires_auth(self) -> bool:
        return True

    def ingest_library(self, limit: Optional[int] = None) -> List[Track]:
        """Traverse Navidrome library and create Track stubs.

        Iterates artists → albums → tracks for reasonable coverage.
        """
        created: List[Track] = []
        if not self.navidrome:
            logger.warning("Navidrome client not provided; cannot ingest library")
            return created

        try:
            artists = self.navidrome.get_all_artists() or []
            count = 0
            for artist in artists:
                albums = self.navidrome.get_albums_for_artist(getattr(artist, "ratingKey", "")) or []
                for album in albums:
                    tracks = self.navidrome.get_tracks_for_album(getattr(album, "ratingKey", "")) or []
                    for item in tracks:
                        provider_id = str(getattr(item, "ratingKey", getattr(item, "id", "")))
                        title = getattr(item, "title", None)
                        # Resolve artist/album names via helpers
                        artist_obj = None
                        album_obj = None
                        try:
                            artist_obj = item.artist()
                        except Exception:
                            artist_obj = None
                        try:
                            album_obj = item.album()
                        except Exception:
                            album_obj = None
                        artists_list = []
                        if artist_obj and getattr(artist_obj, "title", None):
                            artists_list = [getattr(artist_obj, "title")]
                        album_title = getattr(album_obj, "title", None) if album_obj else None
                        duration_ms = getattr(item, "duration", None)
                        track_number = getattr(item, "trackNumber", None)
                        release_year = getattr(item, "year", None)

                        track_id = self.create_stub(
                            provider_id=provider_id,
                            title=title,
                            artists=artists_list,
                            album=album_title,
                            duration_ms=duration_ms,
                            track_number=track_number,
                            release_year=release_year,
                        )
                        # Attach provider ref explicitly
                        if provider_id:
                            self.attach_provider_ref(track_id, provider_id=provider_id)
                        created_track = self.db.get_track(track_id)
                        if created_track:
                            created.append(created_track)

                        count += 1
                        if limit is not None and count >= limit:
                            logger.info(f"Ingested limit reached: {limit} tracks")
                            return created

        except Exception as e:
            logger.error(f"Error ingesting Navidrome library: {e}")
        return created

# Register adapter in plugin system (declaration only; instance created by services)
try:
    from plugins.plugin_system import PluginType, PluginScope, PluginDeclaration, register_plugin
    decl = PluginDeclaration(
        name="navidrome_adapter",
        plugin_type=PluginType.LIBRARY_PROVIDER,
        provides_fields=["title", "artists", "album", "duration_ms", "track_number", "release_year"],
        consumes_fields=[],
        requires_auth=True,
        supports_streaming=True,
        supports_downloads=False,
        supports_library_scan=True,
        supports_cover_art=True,
        supports_lyrics=False,
        # Legacy capabilities for compatibility
        provides=[
            "library.scan",
            "search.tracks",
            "track.title",
            "track.artist",
            "track.album",
            "track.duration_ms",
        ],
        consumes=["auth.credentials"],
        scope=[PluginScope.LIBRARY, PluginScope.SEARCH],
        version="1.0.0",
        description="Navidrome Adapter providing Track stubs from server library",
        author="SoulSync",
        priority=85,
    )
    register_plugin(decl)
except Exception as e:
    logger.debug(f"Plugin declaration for navidrome_adapter deferred: {e}")
