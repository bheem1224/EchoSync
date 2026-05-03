from abc import ABC, abstractmethod
from enum import Enum, auto
from dataclasses import dataclass
from typing import Protocol
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import inspect

from core.enums import Capability
from core.matching_engine.echo_sync_track import EchosyncTrack
from core.matching_engine import text_utils
from core.request_manager import RequestManager

class _ConfigFacade:
    def __init__(self, plugin_id: str):
        _verify_caller(plugin_id)
        self.kvs = KVS(plugin_id)
    def get(self, key: str, default=None): return self.kvs.get(key, default)
    def set(self, key: str, value: str): self.kvs.set(key, value, is_sensitive=False)

class _SecretsFacade:
    def __init__(self, plugin_id: str):
        _verify_caller(plugin_id)
        self.plugin_id = plugin_id
    def get(self, key: str, default=None):
        from database.config_database import get_config_database
        val = get_config_database().get_account_metadata(0, f"{self.plugin_id}_{key}")
        return val if val is not None else default
    def set(self, key: str, value: str):
        from database.config_database import get_config_database
        get_config_database().set_account_metadata(0, f"{self.plugin_id}_{key}", value, is_sensitive=True)

class _AccountsSDKFacade:
    def get_token(self, account_id: int):
        from database.config_database import get_config_database
        token = get_config_database().get_account_token(account_id)
        if not token: return None
        
        caller_mod = inspect.currentframe().f_back.f_globals.get('__name__', '')
        # Simple extraction of author.plugin_name from something like plugins.author_plugin_name
        caller_plugin_id = caller_mod.split('.')[-1] if '.' in caller_mod else caller_mod
        
        account_owner_plugin_id = token.get('provider', '')
        
        # Determine if caller has privileged mode
        from core.settings import config_manager
        privileged = False
        try:
            import json
            manifest_path = config_manager.get_plugins_dir() / caller_plugin_id / "manifest.json"
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text())
                privileged = manifest.get('privileged', False)
        except Exception:
            pass

        if caller_plugin_id == account_owner_plugin_id or privileged:
            return token
            
        # Redact lateral tokens
        redacted = dict(token)
        redacted['access_token'] = 'REDACTED'
        redacted['refresh_token'] = 'REDACTED'
        return redacted

    def save_token(self, account_id: int, access_token: str, refresh_token: str, expires_at: int):
        from database.config_database import get_config_database
        get_config_database().save_account_token(account_id, access_token, refresh_token, 'Bearer', expires_at)

class _PluginsSDKFacade:
    def invoke(self, target_plugin_id: str, action: str, payload: dict):
        # Determine if target is enabled/exists
        from core.plugin_loader import PluginRegistry
        if PluginRegistry.is_provider_disabled(target_plugin_id):
            raise Exception(f"Plugin {target_plugin_id} is disabled or not found")
        
        provider = PluginRegistry.get_provider_class(target_plugin_id)
        if not provider:
            raise Exception(f"Plugin {target_plugin_id} not found")
            
        instance = PluginRegistry.create_instance(target_plugin_id)
        if hasattr(instance, 'handle_ipc'):
            return instance.handle_ipc(action, payload)
        return None

class _FileSDKFacade:
    def delete(self, file_path: str):
        from core.settings import config_manager
        import os
        from pathlib import Path
        import shutil
        
        # Check dry run mode
        if config_manager.get('system.dry_run', False):
            from core.tiered_logger import get_logger
            logger = get_logger("plugin_SDK")
            logger.info(f"DRY RUN: Intercepted deletion of {file_path}")
            return True
            
        # Physical soft delete
        try:
            p = Path(file_path)
            if not p.exists(): return False
            
            # Find root mount. For simplicity, we assume music_dir
            music_dir = Path(config_manager.get('music_dir', ''))
            
            # Create hidden trash if needed
            trash_dir = music_dir / ".trash"
            trash_dir.mkdir(exist_ok=True)
            
            # Move instead of unlink
            dest = trash_dir / p.name
            shutil.move(str(p), str(dest))
            return True
        except Exception as e:
            from core.tiered_logger import get_logger
            logger = get_logger("plugin_SDK")
            logger.error(f"Failed to soft delete {file_path}: {e}")
            return False

class _NetworkSDKFacade:
    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id
        from core.request_manager import RequestManager
        self._manager = RequestManager(provider=plugin_id)

    def _check_allowlist(self, url: str):
        from core.settings import config_manager
        import json
        from urllib.parse import urlparse
        
        try:
            # Core always allowed
            if self.plugin_id == "core" or self.plugin_id.startswith("core."):
                return

            manifest_path = config_manager.get_plugins_dir() / self.plugin_id.replace('plugin.', '') / "manifest.json"
            if not manifest_path.exists():
                raise PermissionError(f"Plugin manifest not found for {self.plugin_id}")

            manifest = json.loads(manifest_path.read_text())
            allowlist = manifest.get('network_domains', [])
            
            if "*" in allowlist:
                return

            parsed = urlparse(url)
            domain = parsed.netloc.split(':')[0] # Remove port
            
            for pattern in allowlist:
                if pattern.startswith("*."):
                    suffix = pattern[1:] # ".example.com"
                    if domain.endswith(suffix) or domain == suffix[1:]:
                        return
                elif domain == pattern:
                    return
            
            raise PermissionError(f"Network access to '{domain}' blocked. Domain not in 'network_domains' allowlist.")
        except Exception as e:
            if isinstance(e, PermissionError): raise
            # Fail closed on manifest errors for security
            raise PermissionError(f"Security check failed for network request: {e}")

    def get(self, url: str, **kwargs):
        self._check_allowlist(url)
        return self._manager.get(url, **kwargs)

    def post(self, url: str, **kwargs):
        self._check_allowlist(url)
        return self._manager.post(url, **kwargs)

    def put(self, url: str, **kwargs):
        self._check_allowlist(url)
        return self._manager.put(url, **kwargs)

    def delete(self, url: str, **kwargs):
        self._check_allowlist(url)
        return self._manager.delete(url, **kwargs)

class _SDK:
    def __init__(self):
        # We don't know the plugin_id here yet as it's a global singleton,
        # but facade methods will verify caller.
        self.accounts = _AccountsSDKFacade()
        self.plugins = _PluginsSDKFacade()
        self.file = _FileSDKFacade()
        
    def _get_plugin_id(self):
        caller_mod = inspect.currentframe().f_back.f_back.f_globals.get('__name__', '')
        # Handle plugins.{author}.{plugin_name}
        if caller_mod.startswith('plugins.'):
            parts = caller_mod.split('.')
            # parts[0] is 'plugins', parts[1] is author, parts[2] is plugin_name
            if len(parts) >= 3:
                base_id = f"{parts[1]}.{parts[2]}"
                if '.beta' in caller_mod:
                    return f"{base_id}@beta"
                return base_id
            return parts[1] # fallback for single-part names
        
        # Handle core.providers.{name}
        if caller_mod.startswith('core.providers.'):
            return caller_mod.split('.')[2]

        return caller_mod.replace('plugins.', '').replace('core.', '').split('.')[0]

    @property
    def network(self):
        return _NetworkSDKFacade(self._get_plugin_id())
        
    @property
    def dry_run(self) -> bool:
        from core.settings import config_manager
        return config_manager.get('system.dry_run', False)

    def schedule(self, interval_minutes: int):
        def decorator(func):
            func._schedule_interval = interval_minutes
            return func
        return decorator

sdk = _SDK()

class WasmPluginWrapper:
    """Wrapper to safely execute .wasm plugins via wasmtime-py"""
    def __init__(self, wasm_path: str):
        self.wasm_path = wasm_path
        
        try:
            import wasmtime
            
            # Initialize rigid sandbox configuration
            config = wasmtime.Config()
            
            # Prevent malicious compilation or infinite loops
            config.consume_fuel = True
            config.epoch_interruption = True
            # Max memory usage for WASM is natively constrained by the module's memory limits,
            # but we disable unsafe features.
            config.wasm_simd = False
            config.wasm_multi_memory = False
            
            self.engine = wasmtime.Engine(config)
            
            # The WASI config acts as our syscall interceptor.
            # By providing a blank WasiConfig (no preopened directories, no network capabilities),
            # any WASI syscall attempting I/O will instantly trap and fail.
            self.wasi_config = wasmtime.WasiConfig()
            
            self.store = wasmtime.Store(self.engine)
            self.store.set_wasi(self.wasi_config)
            
            # Limit execution cycles (fuel) to prevent CPU DoS
            self.store.add_fuel(10_000_000)
            
            # Compile and validate the WASM binary
            self.module = wasmtime.Module.from_file(self.engine, self.wasm_path)
            
        except ImportError:
            # Non-fatal if wasmtime is not installed on the system
            pass
        except Exception as e:
            from core.tiered_logger import get_logger
            get_logger("wasm_sandbox").error(f"Failed to instantiate WASM runtime sandbox for {self.wasm_path}: {e}")


def _verify_caller(expected_plugin_id: str):
    caller = inspect.currentframe().f_back.f_back
    if not caller: return
    caller_mod = caller.f_globals.get('__name__', '')
    # Bypass for core
    if caller_mod.startswith('core.') or caller_mod.startswith('providers.'): return
    # Validate community plugin format
    caller_id = caller_mod.split('.')[-1] if '.' in caller_mod else caller_mod
    
    # expected_plugin_id is usually plugin.author.name or just name. Handle both
    base_expected = expected_plugin_id.split('.')[-1]
    
    if caller_id != base_expected and caller_id != expected_plugin_id:
         raise PermissionError(f"Namespace Isolation Violation: {caller_mod} attempted to access {expected_plugin_id}")


class KVS:
    def __init__(self, plugin_id: str):
        import inspect
        frame = inspect.currentframe()
        try:
            caller_module = inspect.getmodule(frame.f_back)
            if caller_module and not caller_module.__name__.startswith("core."):
                if not caller_module.__name__.startswith(f"plugins.{plugin_id}"):
                    raise PermissionError(f"Cross-namespace data access forbidden. Caller '{caller_module.__name__}' cannot access KVS for '{plugin_id}'.")
        finally:
            del frame
        self.plugin_id = plugin_id

    def get(self, key: str, default=None) -> str:
        from database.config_database import get_config_database
        from core.security import decrypt_string
        db = get_config_database()
        val = None
        with db._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT value, is_sensitive FROM config_kvs WHERE namespace=? AND key=?", (self.plugin_id, key))
            row = c.fetchone()
            if row:
                val, is_sensitive = row[0], row[1]
                if is_sensitive and val:
                    try:
                        val = decrypt_string(val)
                    except Exception:
                        pass
        return val if val is not None else default

    def set(self, key: str, value: str, is_sensitive: bool = False) -> None:
        from database.config_database import get_config_database
        from core.security import encrypt_string
        db = get_config_database()
        if is_sensitive and value:
            value = encrypt_string(value)
        with db._get_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO config_kvs (namespace, key, value, is_sensitive) VALUES (?, ?, ?, ?)", (self.plugin_id, key, value, is_sensitive))
            conn.commit()

class StateKVS:
    def __init__(self, plugin_id: str):
        import inspect
        frame = inspect.currentframe()
        try:
            caller_module = inspect.getmodule(frame.f_back)
            if caller_module and not caller_module.__name__.startswith("core."):
                if not caller_module.__name__.startswith(f"plugins.{plugin_id}"):
                    raise PermissionError(f"Cross-namespace data access forbidden. Caller '{caller_module.__name__}' cannot access StateKVS for '{plugin_id}'.")
        finally:
            del frame
        self.plugin_id = plugin_id

    def get(self, key: str, default=None) -> str:
        from database.working_database import get_working_database
        from core.security import decrypt_string
        db = get_working_database()
        val = None
        with db.session_scope() as session:
            from sqlalchemy.sql import text
            res = session.execute(text("SELECT value, is_sensitive FROM plugin_state_kvs WHERE namespace=:ns AND key=:k"), {"ns": self.plugin_id, "k": key}).fetchone()
            if res:
                val, is_sensitive = res[0], res[1]
                if is_sensitive and val:
                    try:
                        val = decrypt_string(val)
                    except Exception:
                        pass
        return val if val is not None else default

    def set(self, key: str, value: str, is_sensitive: bool = False) -> None:
        from database.working_database import get_working_database
        from core.security import encrypt_string
        db = get_working_database()
        if is_sensitive and value:
            value = encrypt_string(value)
        with db.session_scope() as session:
            from sqlalchemy.sql import text
            session.execute(text("INSERT OR REPLACE INTO plugin_state_kvs (namespace, key, value, is_sensitive) VALUES (:ns, :k, :v, :sens)"), {"ns": self.plugin_id, "k": key, "v": value, "sens": is_sensitive})

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


class PluginBase(ABC):
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
    version: str = "Unknown"  # Version string for the provider/plugin


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
        self.config = _ConfigFacade(self.name)
        self.secrets = _SecretsFacade(self.name)

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
        **kwargs,
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


class SyncServiceProvider(PluginBase):
    """
    Interface for sync service providers (Spotify, Tidal).
    """
    @abstractmethod
    def get_user_playlists(self, user_id: Optional[str] = None) -> List[Any]:
        pass

    @abstractmethod
    def get_playlist_tracks(self, playlist_id: str) -> List[Any]:
        pass

@dataclass(frozen=True)
class SearchCapabilities:
    tracks: bool = False
    artists: bool = False
    albums: bool = False
    playlists: bool = False

@dataclass(frozen=True)
class ProviderCapabilities:
    name: str
    supports_playlists: 'PlaylistSupport'
    search: SearchCapabilities
    metadata: 'MetadataRichness'
    supports_cover_art: bool = False
    supports_lyrics: bool = False
    supports_user_auth: bool = False
    supports_library_scan: bool = False
    supports_streaming: bool = False
    supports_downloads: bool = False
    supports_pre_filtering: bool = False
    playlist_algorithms: list = None  # List of algorithm IDs (e.g., ['spotify_mood'])
    supports_fingerprinting: bool = False  # Audio fingerprinting (AcoustID)
    supports_metadata_fetch: bool = False  # Metadata fetching (MusicBrainz)

    def to_enum_list(self) -> List['Capability']:
        """Adapter pattern to translate ProviderCapabilities dataclass back to legacy Enums."""
        caps = []
        if getattr(self, 'supports_fingerprinting', False):
            caps.append(Capability.RESOLVE_FINGERPRINT)
        if getattr(self, 'supports_metadata_fetch', False):
            caps.append(Capability.FETCH_METADATA)
        return caps

class PlaylistSupport(Enum):
    NONE = auto()
    READ = auto()
    READ_WRITE = auto()


class MetadataRichness(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()

class DisabledProvider(PluginBase):
    """
    Placeholder class for disabled providers.
    Used to keep metadata in the registry without loading the actual module.
    """
    def __init__(self, name: str, version: str = "Unknown", category: str = "provider"):
        self.name = name
        self.version = version
        self.category = category
        self.is_disabled = True

    def is_configured(self) -> bool:
        return False

class Provider(Protocol):
    """
    Strict Contract that all future providers (Python or Rust) must adhere to.
    """

    def search_tracks(self, query: str) -> List[EchosyncTrack]:
        """
        Search for tracks based on a query string.
        """
        ...

    def get_track_by_id(self, item_id: str) -> Optional[EchosyncTrack]:
        """
        Retrieve a specific track by its ID.
        """
        ...

    def get_artist_details(self, artist_id: str) -> Dict[str, Any]:
        """
        Retrieve details about an artist.
        """
        ...


class DownloaderProvider(PluginBase):
    """
    Interface for downloader-style providers (Soulseek/slskd).
    """
    @abstractmethod
    def search(self, query: str, limit: int = 10) -> List[Any]:
        pass

    @abstractmethod
    def download(self, username: str, filename: str, file_size: int = 0) -> Optional[str]:
        pass

    @abstractmethod
    def get_download_status(self, download_id: str) -> Optional[Dict[str, Any]]:
        pass

class MediaServerProvider(PluginBase):
    """
    Base interface for media server providers (Plex, Jellyfin, Navidrome).
    Provides shared library scan polling logic; subclasses implement server-specific API calls.
    """
    def __init__(self):
        super().__init__()
        self._scan_state = {
            'scanning': False,
            'progress': 0.0,
            'eta_seconds': None,
            'error': None
        }

    @abstractmethod
    def get_library_stats(self) -> Dict[str, int]:
        pass

    @abstractmethod
    def get_all_artists(self) -> List[Any]:
        pass

    @abstractmethod
    def get_all_albums(self) -> List[Any]:
        pass

    @abstractmethod
    def get_all_tracks(self) -> List[Any]:
        pass

    def trigger_library_scan(self, path: Optional[str] = None) -> bool:
        """
        Public method: Trigger a library refresh/scan on the media server.
        Calls server-specific _trigger_scan_api() implementation.
        """
        from core.tiered_logger import get_logger
        logger = get_logger("MediaServerProvider")
        try:
            success = self._trigger_scan_api(path)
            if success:
                self._scan_state['scanning'] = True
                self._scan_state['error'] = None
                logger.info(f"{self.name} library scan initiated")
            return success
        except Exception as e:
            logger.error(f"Error triggering {self.name} scan: {e}", exc_info=True)
            self._scan_state['error'] = str(e)
            return False

    @abstractmethod
    def _trigger_scan_api(self, path: Optional[str] = None) -> bool:
        """
        Server-specific: Trigger scan on the media server API.
        Returns: True if API call succeeded.
        """
        pass

    def get_scan_status(self) -> Dict[str, Any]:
        """
        Public method: Get current scan status. Calls server-specific _get_scan_status_api().
        """
        from core.tiered_logger import get_logger
        logger = get_logger("MediaServerProvider")
        try:
            api_status = self._get_scan_status_api()
            # Merge API status into cached state
            self._scan_state.update(api_status)
            return self._scan_state.copy()
        except Exception as e:
            logger.error(f"Error getting {self.name} scan status: {e}", exc_info=True)
            self._scan_state['error'] = str(e)
            return self._scan_state.copy()

    @abstractmethod
    def _get_scan_status_api(self) -> Dict[str, Any]:
        """
        Server-specific: Poll scan status from the media server API.
        Returns: partial dict with 'scanning', 'progress', 'eta_seconds', 'error' keys.
        """
        pass

    @abstractmethod
    def get_content_changes_since(self, last_update: Optional[Any] = None) -> Any:
        """
        Get content changes since the last update timestamp.
        Enables incremental syncs by detecting only new/modified content.
        """
        pass
