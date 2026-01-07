from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from core.matching_engine.soul_sync_track import SoulSyncTrack
from core.matching_engine import text_utils


class ProviderBase(ABC):
    """
    Abstract base class for all music providers (Spotify, Tidal, Plex, Jellyfin, etc.).
    
    KEY PRINCIPLE: Providers are DUMB - they only convert their native format to SoulSyncTrack.
    Core/Database/MatchingEngine are SMART - they process SoulSyncTrack objects.
    
    All providers must implement these methods.
    """
    name: str  # Unique provider name (e.g., 'spotify', 'tidal', 'plex')
    category: str = 'provider'  # 'provider' (bundled, stable) or 'plugin' (community, unstable)
    supports_downloads: bool = False  # Indicates if provider supports downloads
    enabled: bool = True  # Flag to enable/disable provider without deleting files

    @abstractmethod
    def authenticate(self, **kwargs) -> bool:
        """Authenticate the provider (OAuth, API key, etc.)."""
        pass

    @abstractmethod
    def search(self, query: str, type: str = "track", limit: int = 10) -> List[SoulSyncTrack]:
        """Search for tracks. Must return SoulSyncTrack objects."""
        pass

    @abstractmethod
    def get_track(self, track_id: str) -> Optional[SoulSyncTrack]:
        """Fetch a single track by ID. Must return SoulSyncTrack object."""
        pass

    @abstractmethod
    def get_album(self, album_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single album by ID."""
        pass

    @abstractmethod
    def get_artist(self, artist_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single artist by ID."""
        pass

    @abstractmethod
    def get_user_playlists(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch playlists for a user (if supported)."""
        pass

    @abstractmethod
    def get_playlist_tracks(self, playlist_id: str) -> List[SoulSyncTrack]:
        """Fetch tracks for a playlist. Must return List[SoulSyncTrack]."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if provider is configured and ready to use."""
        pass

    @abstractmethod
    def get_logo_url(self) -> str:
        """Return a URL or path to the provider's logo/icon."""
        pass

    # ===== HELPER METHODS (Reusable by all providers) =====
    
    @staticmethod
    def create_soul_sync_track(
        title: str,
        artist: str,
        album: Optional[str] = None,
        duration_ms: Optional[int] = None,
        isrc: Optional[str] = None,
        musicbrainz_id: Optional[str] = None,
        musicbrainz_album_id: Optional[str] = None,
        musicbrainz_artist_id: Optional[str] = None,
        year: Optional[int] = None,
        track_number: Optional[int] = None,
        disc_number: Optional[int] = None,
        bitrate: Optional[int] = None,
        file_format: Optional[str] = None,
        source: Optional[str] = None,
        **extra_fields
    ) -> SoulSyncTrack:
        """
        Factory method to create SoulSyncTrack with normalized metadata.
        
        This centralizes normalization logic used by all providers.
        Providers call this after extracting their native data.
        
        Args:
            title: Track title
            artist: Primary artist
            album: Album name
            duration_ms: Duration in milliseconds
            isrc: International Standard Recording Code
            musicbrainz_id: MusicBrainz Recording ID
            musicbrainz_album_id: MusicBrainz Album ID
            musicbrainz_artist_id: MusicBrainz Artist ID
            year: Release year
            track_number: Track position
            disc_number: Disc number
            bitrate: Bitrate in kbps
            file_format: File format (mp3, flac, etc.)
            source: Provider name (spotify, plex, etc.)
            **extra_fields: Additional SoulSyncTrack fields
            
        Returns:
            SoulSyncTrack with normalized metadata
        """
        # Defensive coercion helpers for provider-provided values
        def _coerce_to_str(val):
            if val is None:
                return None
            # If it's callable (some provider libs expose methods), call it
            if callable(val):
                try:
                    val = val()
                except Exception:
                    # Fallback to string representation
                    return str(val)
            # If it's a list (e.g., artist objects), try to join names
            if isinstance(val, (list, tuple)):
                parts = []
                for it in val:
                    if isinstance(it, str):
                        parts.append(it)
                    else:
                        # Try common attributes
                        parts.append(str(getattr(it, 'name', getattr(it, 'title', it))))
                return ' '.join([p for p in parts if p])
            # If object has name/title attribute, prefer that
            if not isinstance(val, str):
                for attr in ('name', 'title', 'tag', 'artist'):
                    if hasattr(val, attr):
                        try:
                            return str(getattr(val, attr))
                        except Exception:
                            continue
                return str(val)

        # Coerce inputs to strings where appropriate
        title_str = _coerce_to_str(title)
        artist_str = _coerce_to_str(artist)
        album_str = _coerce_to_str(album)

        # Extract version info from title
        clean_title, version = text_utils.extract_version_info(title_str)

        # Normalize text fields
        normalized_title = text_utils.normalize_title(clean_title)
        normalized_artist = text_utils.normalize_artist(artist_str)
        normalized_album = text_utils.normalize_album(album_str) if album_str else None
        
        # Parse duration
        parsed_duration = text_utils.parse_duration_to_ms(duration_ms)
        
        # Detect quality tags
        quality_tags = text_utils.detect_quality_tags(bitrate, file_format)
        
        # Create SoulSyncTrack
        return SoulSyncTrack(
            title=normalized_title,
            artist=normalized_artist,
            album=normalized_album,
            duration_ms=parsed_duration,
            isrc=isrc.strip().upper() if isrc else None,
            musicbrainz_id=musicbrainz_id,
            musicbrainz_album_id=musicbrainz_album_id,
            musicbrainz_artist_id=musicbrainz_artist_id,
            year=year,
            track_number=track_number,
            disc_number=disc_number,
            bitrate=bitrate,
            file_format=file_format,
            quality_tags=quality_tags,
            version=version,
            source=source,
            **extra_fields
        )
    
    @staticmethod
    def extract_guid_identifier(guid_id: str, identifier_type: str) -> Optional[str]:
        """
        Extract specific identifier from Plex guid format.
        
        Args:
            guid_id: Full guid ID string
            identifier_type: Type to extract ('isrc', 'musicbrainz', 'acoustid')
            
        Returns:
            Clean identifier or None if not found
        """
        if not guid_id:
            return None
        
        target_prefix = identifier_type.lower()
        
        # Check if this guid contains our target type
        if target_prefix not in guid_id.lower():
            return None
        
        # Extract the ID part after ://
        clean_id = text_utils.clean_guid_id(guid_id)
        return clean_id

