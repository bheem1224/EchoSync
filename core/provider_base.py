from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from core.enums import Capability
from core.matching_engine.echo_sync_track import EchosyncTrack
from core.matching_engine import text_utils
from core.request_manager import RequestManager

if TYPE_CHECKING:
    from core.provider import ProviderCapabilities




class _PluginSecrets:
    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id

    def get(self, key: str, default=None) -> str:
        from database.config_database import get_config_database
        from core.security import decrypt_string
        db = get_config_database()
        service_id = db.get_or_create_service_id(f"plugin_{self.plugin_id}")
        val = db.get_service_config(service_id, key)
        if val is None:
            return default
        return decrypt_string(val) if str(val).startswith('enc:') else val

    def set(self, key: str, value: str) -> None:
        from database.config_database import get_config_database
        from core.security import encrypt_string
        db = get_config_database()
        service_id = db.get_or_create_service_id(f"plugin_{self.plugin_id}")
        enc_val = encrypt_string(value) if value else None
        db.set_service_config(service_id, key, enc_val, is_sensitive=True)

class _PluginConfig:
    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id

    def get(self, key: str, default=None) -> Any:
        from core.settings import config_manager
        return config_manager.get(f"plugins.{self.plugin_id}.{key}", default)

    def set(self, key: str, value: Any) -> None:
        from core.settings import config_manager
        config_manager.set(f"plugins.{self.plugin_id}.{key}", value)

class _PluginCoreSystemFacade:
    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id

    def toggle_feature(self, feature_key: str, enabled: bool) -> None:
        from core.settings import config_manager
        from core.event_bus import event_bus
        config_manager.set(feature_key, enabled)
        event_bus.publish({
            "event": "FEATURE_TOGGLED",
            "plugin_id": self.plugin_id,
            "feature": feature_key,
            "enabled": enabled
        })

    def get_setting(self, feature_key: str, default=None) -> Any:
        from core.settings import config_manager
        return config_manager.get(feature_key, default)

class _PluginModelFacade:
    def __init__(self):
        # Lazy imports to avoid circular dependencies
        pass

    @property
    def Track(self):
        from database.music_database import Track
        return Track

    @property
    def Album(self):
        from database.music_database import Album
        return Album

    @property
    def Artist(self):
        from database.music_database import Artist
        return Artist

    @property
    def Download(self):
        from database.working_database import Download
        return Download

    @property
    def UserRating(self):
        from database.working_database import UserRating
        return UserRating

    @property
    def PlaybackHistory(self):
        from database.working_database import PlaybackHistory
        return PlaybackHistory


class ProviderBase(ABC):
    """
    Abstract base class for all music providers (Spotify, Tidal, Plex, Jellyfin, etc.).
    
    KEY PRINCIPLE: Providers are DUMB - they only convert their native format to EchosyncTrack.
    Core/Database/MatchingEngine are SMART - they process EchosyncTrack objects.
    
    All providers must implement these methods.
    
    Attributes:
        http: RequestManager instance for making HTTP requests with rate limiting and retries.
              MANDATORY: All HTTP requests must use this, not requests.get() directly.
    """
    name: str  # Unique provider name (e.g., 'spotify', 'tidal', 'plex')
    category: str = 'provider'  # 'provider' (bundled, stable) or 'plugin' (community, unstable)
    supports_downloads: bool = False  # Indicates if provider supports downloads
    enabled: bool = True  # Flag to enable/disable provider without deleting files

    # Set to True in providers that can resolve metadata by ISRC code.
    # Providers that set this to True MUST implement search_by_isrc().
    supports_isrc_lookup: bool = False

    # Typed capability class for registry detection
    capabilities: 'ProviderCapabilities' = None

    # Default rate limit (requests per second). Can be overridden by subclasses.
    # None = unlimited/config driven.
    rate_limit: float = None

    def __init__(self):
        """Initialize provider with HTTP client."""
        from core.request_manager import RequestManager, RateLimitConfig

        # Configure rate limiting if specified by subclass
        rate_config = None
        if self.rate_limit:
            rate_config = RateLimitConfig(requests_per_second=self.rate_limit)

        self.http = RequestManager(self.name, rate=rate_config)

        # Sandbox API facades for Plugin Architecture
        self._name = self.name
        self.secrets = _PluginSecrets(self._name)
        self.config = _PluginConfig(self._name)
        self.core_system = _PluginCoreSystemFacade(self._name)
        self.models = _PluginModelFacade()

    @property
    def logger(self):
        from core.tiered_logger import get_logger
        return get_logger(f"plugin.{self._name}")

    def get_oauth_redirect_uri(self) -> str:
        """
        Calculates the standardized redirect URI for this provider using the OAuth sidecar.
        Falls back to detecting primary local IP if not explicitly set in config.
        """
        from core.settings import config_manager

        # Determine the base host to use. Try server_url, then base_ip.
        host = config_manager.get('server_url')
        if not host:
             host = config_manager.get('base_ip')

        # If we still don't have a valid host, attempt dynamic IP detection
        if not host:
             import socket
             try:
                 # Create a dummy socket connection to a public DNS to determine the primary interface IP
                 s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                 # Doesn't have to be reachable, just needs to route correctly
                 s.connect(("8.8.8.8", 80))
                 host = s.getsockname()[0]
                 s.close()
             except Exception:
                 host = "localhost" # Last resort fallback

        # Ensure scheme is present (strip if mistakenly entered)
        if host.startswith("http://") or host.startswith("https://"):
            host = host.split("://")[-1]

        # Ensure no trailing slashes or paths
        host = host.split("/")[0]

        # Strip existing port if present
        host = host.split(":")[0]

        # The OAuth sidecar runs securely on port 5001
        return f"https://{host}:5001/api/oauth/callback/{self.name}"

    def handle_oauth_callback(self, args: Dict[str, str]) -> Any:
        """
        Handle an OAuth callback from the sidecar.
        Providers must override this if they support OAuth.

        Args:
            args: The query parameters from the callback request.

        Returns:
            A Flask response (string, tuple, or redirect)
        """
        raise NotImplementedError("This provider does not implement handle_oauth_callback")

    @abstractmethod
    def authenticate(self, **kwargs) -> bool:
        """Authenticate the provider (OAuth, API key, etc.)."""
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        type: str = "track",
        limit: int = 10,
        quality_profile: Optional[Dict[str, Any]] = None,
        includes: Optional[List[str]] = None,
        excludes: Optional[List[str]] = None,
    ) -> List[EchosyncTrack]:
        """Search for tracks. Must return EchosyncTrack objects.

        Args:
            quality_profile: Optional active quality profile for provider-side pre-filtering.
            includes: Optional list of terms that must all appear in a result's filename
                      (client-side text filter, AND semantics).
            excludes: Optional list of terms where any match causes the result to be dropped
                      (client-side text filter, OR semantics).
        """
        pass

    @abstractmethod
    def get_track(self, track_id: str) -> Optional[EchosyncTrack]:
        """Fetch a single track by ID. Must return EchosyncTrack object."""
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
    def get_playlist_tracks(self, playlist_id: str) -> List[EchosyncTrack]:
        """Fetch tracks for a playlist. Must return List[EchosyncTrack]."""
        pass

    def add_tracks_to_playlist(self, playlist_id: str, provider_track_ids: List[str]) -> bool:
        """Add tracks to a playlist using provider-specific IDs (e.g., Plex ratingKeys, Spotify URIs).
        
        This is the RECOMMENDED method for adding tracks to playlists.
        Providers should override this to accept a list of string IDs instead of track objects.
        
        Args:
            playlist_id: The playlist ID in this provider's system
            provider_track_ids: List of provider-specific track IDs (e.g., ['1', '2', '3'] for Plex)
            
        Returns:
            True if successful, False otherwise
        """
        # Default implementation: not supported by this provider
        raise NotImplementedError(f"add_tracks_to_playlist not implemented for {self.name} provider")

    def remove_tracks_from_playlist(self, playlist_id: str, provider_track_ids: List[str]) -> bool:
        """Remove tracks from a playlist using provider-specific IDs.

        Args:
            playlist_id: The playlist ID in this provider's system
            provider_track_ids: List of provider-specific track IDs to remove

        Returns:
            True if successful, False otherwise
        """
        raise NotImplementedError(f"remove_tracks_from_playlist not implemented for {self.name} provider")

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if provider is configured and ready to use."""
        pass

    @abstractmethod
    def get_logo_url(self) -> str:
        """Return a URL or path to the provider's logo/icon."""
        pass

    def search_by_isrc(self, isrc: str) -> Optional[EchosyncTrack]:
        """Look up a single track by its ISRC code.

        Providers that support ISRC lookup MUST set ``supports_isrc_lookup = True``
        and override this method.  The default implementation returns ``None`` so
        that existing providers that do not support this capability are unaffected.

        Args:
            isrc: A canonical 12-character ISRC (no hyphens, already validated).

        Returns:
            A ``EchosyncTrack`` populated with as much metadata as the provider
            can supply, or ``None`` if the ISRC was not found.
        """
        return None

    # ===== HELPER METHODS (Reusable by all providers) =====
    
    @staticmethod
    def create_echo_sync_track(
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
    ) -> EchosyncTrack:
        """
        Factory method to create EchosyncTrack with normalized metadata.
        
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
            **extra_fields: Additional EchosyncTrack fields
            
        Returns:
            EchosyncTrack with normalized metadata
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
        
        # Create EchosyncTrack
        return EchosyncTrack(
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

