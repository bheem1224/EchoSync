"""
Jellyfin ProviderAdapter implementation.

Populates library-related Track fields (file_path, file_format, bitrate, duration_ms)
and attaches Jellyfin ProviderRef. Adheres to Track-centric architecture.
"""

from typing import List, Optional, Dict, Any
from core.tiered_logger import get_logger
from core.models import ProviderType, Track
from core.file_handling.storage import get_storage_service
from core.provider_base import ProviderBase
from core.matching_engine.soul_sync_track import SoulSyncTrack

logger = get_logger("jellyfin_adapter")


def convert_jellyfin_track_to_soulsync(jellyfin_track) -> Optional[SoulSyncTrack]:
    """
    Convert Jellyfin track object to SoulSyncTrack.
    
    Extracts Jellyfin metadata including audio quality info, ISRC, and MusicBrainz IDs.
    
    Args:
        jellyfin_track: Jellyfin track object or wrapper (JellyfinTrack)
        
    Returns:
        SoulSyncTrack with all available metadata, or None if conversion fails
    """
    try:
        # Get raw data dict if this is a wrapper object
        raw_data = jellyfin_track._data if hasattr(jellyfin_track, '_data') else jellyfin_track
        
        # Extract basic metadata from raw data
        title = raw_data.get('Name') if isinstance(raw_data, dict) else getattr(jellyfin_track, 'title', None)
        
        # Handle artist - Jellyfin provides ArtistItems list
        artist = None
        if isinstance(raw_data, dict):
            artist_items = raw_data.get('ArtistItems', [])
            if artist_items and isinstance(artist_items, list):
                artist = artist_items[0].get('Name') if isinstance(artist_items[0], dict) else str(artist_items[0])
        if not artist:
            artist = getattr(jellyfin_track, 'artist', None)
        
        album = raw_data.get('Album') if isinstance(raw_data, dict) else getattr(jellyfin_track, 'album', None)
        
        if not title or not artist:
            logger.warning(f"Jellyfin track missing title or artist: {title} / {artist}")
            return None
        
        # Duration - already converted in wrapper, or convert from ticks
        duration_ms = None
        if isinstance(raw_data, dict):
            duration_raw = raw_data.get('RunTimeTicks')
            if duration_raw:
                try:
                    duration_ms = int(duration_raw) // 10000  # Convert ticks to ms
                except (ValueError, TypeError):
                    pass
        else:
            duration_ms = getattr(jellyfin_track, 'duration', None)
        
        track_number = raw_data.get('IndexNumber') if isinstance(raw_data, dict) else getattr(jellyfin_track, 'trackNumber', None)
        disc_number = raw_data.get('ParentIndexNumber') if isinstance(raw_data, dict) else None
        
        # Extract file metadata
        file_path = raw_data.get('Path') if isinstance(raw_data, dict) else None
        file_format = raw_data.get('Container') if isinstance(raw_data, dict) else None
        if file_format:
            file_format = file_format.lower()
        
        # Audio quality metadata
        bitrate = raw_data.get('Bitrate') if isinstance(raw_data, dict) else None
        sample_rate = None
        bit_depth = None
        
        # Jellyfin stores MediaSources with detailed audio info
        if isinstance(raw_data, dict):
            media_sources = raw_data.get('MediaSources', [])
            if media_sources and isinstance(media_sources, list):
                source = media_sources[0]
                if isinstance(source, dict):
                    bitrate = source.get('Bitrate') or bitrate
                    
                    # Audio streams contain sample rate and bit depth
                    media_streams = source.get('MediaStreams', [])
                    for stream in media_streams:
                        if isinstance(stream, dict):
                            stream_type = stream.get('Type', '')
                            if 'Audio' in stream_type:
                                sample_rate = stream.get('SampleRate') or sample_rate
                                bit_depth = stream.get('BitDepth') or bit_depth
                                break
        
        # Extract ISRC and MusicBrainz IDs from ProviderIds
        isrc = None
        musicbrainz_id = None
        musicbrainz_album_id = None
        
        if isinstance(raw_data, dict):
            provider_ids = raw_data.get('ProviderIds', {})
            if isinstance(provider_ids, dict):
                isrc = provider_ids.get('Isrc')
                # MusicBrainz recording
                musicbrainz_id = provider_ids.get('MusicBrainzRecording') or provider_ids.get('MusicBrainz')
                # MusicBrainz album
                musicbrainz_album_id = provider_ids.get('MusicBrainzAlbum')
        
        year = None
        if isinstance(raw_data, dict):
            year_val = raw_data.get('ProductionYear')
            if year_val:
                try:
                    year = int(year_val)
                except (ValueError, TypeError):
                    pass
        else:
            year = getattr(jellyfin_track, 'year', None)
        
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
            source='jellyfin'
        )
    
    except Exception as e:
        logger.error(f"Error converting Jellyfin track to SoulSyncTrack: {e}", exc_info=True)
        return None


class JellyfinAdapter:
    def __init__(self, jellyfin_client=None):
        storage = get_storage_service()
        db = storage.get_music_database()
        super().__init__(db=db, provider_type=ProviderType.JELLYFIN)
        self.jellyfin = jellyfin_client

    def get_provides_fields(self) -> List[str]:
        return [
            "file_path",
            "file_format",
            "bitrate",
            "duration_ms",
            "title",
            "artists",
            "album",
        ]

    def get_consumes_fields(self) -> List[str]:
        return []

    def requires_auth(self) -> bool:
        return True

    def attach_file_metadata(self, track_id: str, file_path: str, file_format: Optional[str] = None,
                             bitrate: Optional[int] = None, duration_ms: Optional[int] = None) -> Track:
        """Attach local file metadata to an existing Track and mark status as verified if present."""
        track = self.db.get_track(track_id)
        if not track:
            raise ValueError(f"Track {track_id} not found")
        # Enrich metadata
        updates: Dict[str, Any] = {
            "file_path": file_path,
            "file_format": file_format,
            "bitrate": bitrate,
            "duration_ms": duration_ms,
        }
        updates = {k: v for k, v in updates.items() if v is not None}
        track = self.enrich_track(track_id, **updates)
        try:
            from core.models import DownloadStatus
            status = DownloadStatus.VERIFIED.value if file_path else DownloadStatus.COMPLETE.value
            track = self.update_download_status(track_id, status=status)
        except Exception:
            pass
        return track

    def ingest_library(self, limit: Optional[int] = None) -> List[Track]:
        """Scan Jellyfin music library and populate canonical tracks."""
        created: List[Track] = []
        if not self.jellyfin:
            logger.warning("Jellyfin client not provided; cannot ingest library")
            return created
        getter = getattr(self.jellyfin, "get_all_tracks", None)
        if not getter:
            logger.warning("Jellyfin client missing get_all_tracks")
            return created
        try:
            items = self.jellyfin.get_all_tracks() or []
            if limit is not None:
                items = items[:limit]
            for item in items:
                provider_id = str(getattr(item, "id", getattr(item, "Id", "")))
                title = getattr(item, "title", getattr(item, "Name", None))
                artists = getattr(item, "artists", []) or ([getattr(item, "AlbumArtist", None)] if getattr(item, "AlbumArtist", None) else [])
                album = getattr(item, "album", getattr(item, "Album", None))
                duration_ms = getattr(item, "duration", getattr(item, "RunTimeTicks", None))
                # Create stub and attach ref
                track_id = self.create_stub(provider_id=provider_id, title=title, artists=artists, album=album, duration_ms=duration_ms)
                # File metadata
                file_path = getattr(item, "Path", None)
                file_format = getattr(item, "Container", None)
                bitrate = getattr(item, "Bitrate", None)
                self.enrich_track(track_id, file_path=file_path, file_format=file_format, bitrate=bitrate)
                if provider_id:
                    self.attach_provider_ref(track_id, provider_id=provider_id)
                updated = self.update_download_status(track_id, status="verified")
                if updated:
                    created.append(updated)
        except Exception as e:
            logger.error(f"Error ingesting Jellyfin library: {e}")
        return created

# Register adapter in plugin system
try:
    from plugins.plugin_system import PluginType, PluginScope, PluginDeclaration, register_plugin
    decl = PluginDeclaration(
        name="jellyfin_adapter",
        plugin_type=PluginType.LIBRARY_PROVIDER,
        provides_fields=["file_path", "file_format", "bitrate", "duration_ms", "title", "artists", "album"],
        consumes_fields=[],
        requires_auth=True,
        supports_streaming=True,
        supports_downloads=False,
        supports_library_scan=True,
        supports_cover_art=True,
        supports_lyrics=False,
        provides=["library.scan", "library.tag_write", "track.title", "track.artist", "track.album", "track.duration_ms"],
        consumes=["auth.credentials"],
        scope=[PluginScope.LIBRARY],
        version="1.0.0",
        description="Jellyfin adapter populating local file metadata for canonical tracks",
        author="SoulSync",
        priority=90,
    )
    register_plugin(decl)
except Exception as e:
    logger.debug(f"Plugin declaration for jellyfin_adapter deferred: {e}")
