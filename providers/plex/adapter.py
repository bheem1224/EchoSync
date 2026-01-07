"""
Plex ProviderAdapter implementation.

Populates library-related Track fields (file_path, file_format, bitrate, duration_ms)
and attaches Plex ProviderRef. Adheres to Track-centric architecture.
"""

from typing import List, Optional, Dict, Any
from utils.logging_config import get_logger
from core.models import ProviderType, Track
from sdk.storage_service import get_storage_service
from core.provider_base import ProviderBase
from core.matching_engine.soul_sync_track import SoulSyncTrack

logger = get_logger("plex_adapter")


def convert_plex_track_to_soulsync(plex_track) -> Optional[SoulSyncTrack]:
    """
    Convert Plex track object to SoulSyncTrack.

    Extracts Plex-specific metadata including file size, bit rate, bit depth, sample rate.

    Args:
        plex_track: Plex track object

    Returns:
        SoulSyncTrack with all available metadata, or None if conversion fails
    """
    try:
        # Extract basic metadata
        title = getattr(plex_track, 'title', None)

        # Handle artist and album extraction robustly
        artist_obj = plex_track.artist() if callable(plex_track.artist) else None
        artist = getattr(artist_obj, 'title', None) if artist_obj else None

        album_obj = plex_track.album() if callable(plex_track.album) else None
        album = getattr(album_obj, 'title', None) if album_obj else None

        # Debug logging to inspect artist and album objects
        logger.debug(f"[PLEX ADAPTER] Raw artist object: {artist_obj}")
        logger.debug(f"[PLEX ADAPTER] Raw album object: {album_obj}")

        if not title or not artist:
            logger.error(f"[PLEX ADAPTER] MISSING REQUIRED FIELDS: title='{title}', artist='{artist}' - skipping track")
            return None

        duration_ms = getattr(plex_track, 'duration', None)
        year = getattr(plex_track, 'year', None)
        track_number = getattr(plex_track, 'trackNumber', None)
        disc_number = getattr(plex_track, 'discNumber', None)

        # Extract file metadata
        file_path = None
        file_format = None
        bitrate = None
        bit_depth = None
        sample_rate = None
        file_size = None

        if hasattr(plex_track, 'media') and plex_track.media:
            media = plex_track.media[0]
            bitrate = getattr(media, 'bitrate', None)

            if hasattr(media, 'parts') and media.parts:
                part = media.parts[0]
                file_path = getattr(part, 'file', None)
                file_size = getattr(part, 'size', None)

            # Extract additional audio properties
            streams = getattr(media, 'audioStreams', [])
            if streams:
                stream = streams[0]
                bit_depth = getattr(stream, 'bitDepth', None)
                sample_rate = getattr(stream, 'sampleRate', None)

            # Extract container from Plex format
            container = getattr(media, 'container', None)
            if container:
                file_format = container.lower()

        # Use ProviderBase factory method for normalization
        return ProviderBase.create_soul_sync_track(
            title=title,
            artist=artist,
            album=album,
            duration_ms=duration_ms,
            year=year,
            track_number=track_number,
            disc_number=disc_number,
            bitrate=bitrate,
            bit_depth=bit_depth,
            sample_rate=sample_rate,
            file_size=file_size,
            file_format=file_format,
            file_path=file_path,
            source='plex'
        )

    except Exception as e:
        logger.error(f"[PLEX ADAPTER] EXCEPTION converting track: {e}", exc_info=True)
        return None
