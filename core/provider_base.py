from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from core.matching_engine.soul_sync_track import SoulSyncTrack
from core.matching_engine import text_utils
from core.request_manager import RequestManager


class ProviderBase(ABC):
    """
    Abstract base class for all music providers (Spotify, Tidal, Plex, Jellyfin, etc.).
    
    KEY PRINCIPLE: Providers are DUMB - they only convert their native format to SoulSyncTrack.
    Core/Database/MatchingEngine are SMART - they process SoulSyncTrack objects.
    
    All providers must implement these methods.
    
    Attributes:
        http: RequestManager instance for making HTTP requests with rate limiting and retries.
              MANDATORY: All HTTP requests must use this, not requests.get() directly.
    """
    name: str  # Unique provider name (e.g., 'spotify', 'tidal', 'plex')
    category: str = 'provider'  # 'provider' (bundled, stable) or 'plugin' (community, unstable)
    supports_downloads: bool = False  # Indicates if provider supports downloads
    enabled: bool = True  # Flag to enable/disable provider without deleting files

    def __init__(self):
        """Initialize provider with HTTP client."""
        self.http = RequestManager(self.name)

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
        year: Optional[int] = None,
        track_number: Optional[int] = None,
        disc_number: Optional[int] = None,
        bitrate: Optional[int] = None,
        file_format: Optional[str] = None,
        file_path: Optional[str] = None,
            fingerprint: Optional[str] = None,
            quality_tags: Optional[list] = None,
        provider_id: Optional[str] = None,
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
            return val  # Already a string

        # Coerce inputs to strings where appropriate
        title_str = _coerce_to_str(title)
        artist_str = _coerce_to_str(artist)
        album_str = _coerce_to_str(album)
        
        # Debug log raw inputs before processing
        from core.tiered_logger import get_logger
        logger = get_logger("provider_base")
        logger.debug(
            "Factory raw inputs: title=%r artist=%r album=%r",
            title, artist, album
        )
        logger.debug(
            "Factory after coercion: title_str=%r artist_str=%r album_str=%r",
            title_str, artist_str, album_str
        )
        
        # Extract edition info from title (remaster, live, remix, etc.)
        clean_title, edition = text_utils.extract_edition(title_str) if title_str else (None, None)
        

        # Normalize text fields (handle None inputs)
        normalized_title = text_utils.normalize_title(clean_title) if clean_title else None
        normalized_artist = text_utils.normalize_artist(artist_str) if artist_str else None
        normalized_album = text_utils.normalize_album(album_str) if album_str else None
        
        # Debug log to trace normalization issues
        from core.tiered_logger import get_logger
        logger = get_logger("provider_base")
        logger.debug(
            "Factory normalization: title='%s'→'%s' artist='%s'→'%s' album='%s'→'%s'",
            title_str, normalized_title, artist_str, normalized_artist, album_str, normalized_album
        )
        
        # Validate required fields after normalization
        if not normalized_title or not normalized_title.strip():
            logger.warning(f"Skipping track creation - normalized title is empty (original: '{title_str}')")
            return None
        
        if not normalized_artist or not normalized_artist.strip():
            logger.warning(f"Skipping track creation - normalized artist is empty (original: '{artist_str}', title: '{normalized_title}')")
            return None
        
        # Parse duration
        parsed_duration = text_utils.parse_duration_to_ms(duration_ms)
        
        # Build identifiers list for ExternalIdentifiers table
        identifiers = []
        if provider_id and source:
            identifiers.append({
                'provider_source': source,
                'provider_item_id': str(provider_id),
                'raw_data': extra_fields or None
            })
        
        # Create SoulSyncTrack
        return SoulSyncTrack(
            raw_title=title_str,
            artist_name=artist_str,
            album_title=album_str,
            edition=edition,
            duration=parsed_duration,
            track_number=track_number,
            disc_number=disc_number,
            bitrate=bitrate,
            file_format=file_format,
            file_path=file_path,
            release_year=year,
            musicbrainz_id=musicbrainz_id,
                        isrc=isrc,
                        fingerprint=fingerprint,
                        quality_tags=quality_tags,
            identifiers=identifiers
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

