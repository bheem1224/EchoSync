"""Unified Nexus Framework Plugin Contracts, Base Classes, and Capability Descriptors."""

from __future__ import annotations

from abc import ABC
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
import re
from typing import Any, Protocol

from core.db.echo_sync_track import EchosyncTrack
from core.enums import Capability
from core.matching_engine import text_utils
from core.nexus_framework.sdk.facades import (
    StateKVS,
    _AccountsSDKFacade,
    _AliasBroker,
    _AttributeBroker,
    _call_check_plugin_permission,
    _ConfigFacade,
    _DatabaseFacade,
    _FileSDKFacade,
    _LibrarySDKFacade,
    _PluginModelFacade,
    _PluginsSDKFacade,
    _SecretsFacade,
    _WorkingSDKFacade,
    sdk,
)
from core.request_manager import RequestManager
from time_utils import utc_now


def hookimpl(func: Callable[..., Any] | None = None, **kwargs: Any) -> Callable[..., Any]:
    """Decorator marking a method or function as a plugin hook implementation."""

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        fn._is_hookimpl = True  # type: ignore[attr-defined]
        fn._hookimpl_opts = kwargs  # type: ignore[attr-defined]
        return fn

    if func is not None:
        return decorator(func)
    return decorator


def verify_file_signature(file_path: str | Path, title: str, artist: str) -> bool:
    """Verify the native cryptographic Content-Addressed Acoustic Proof (ECHOSYNC_SIGNATURE).

    Extracts the physical ECHOSYNC_SIGNATURE tag from the container, decodes the raw
    PCM stream, and verifies the BLAKE3 signature matches BLAKE3(pcm_hash:title:artist).
    Returns True if valid and untampered, False otherwise.
    """
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        return False

    try:
        import echosync_core

        raw_tags = echosync_core.extract_metadata(str(path)) or {}
        sig = raw_tags.get("echosync_signature") or raw_tags.get("ECHOSYNC_SIGNATURE")
        if not sig:
            return False

        return bool(
            echosync_core.verify_audio_signature(
                str(path), str(title).strip(), str(artist).strip(), str(sig).strip()
            )
        )
    except Exception:
        return False


@dataclass
class PluginRef:
    """Reference to a track in a specific plugin."""

    plugin: str
    plugin_id: str
    plugin_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=utc_now)

    def validate(self) -> None:
        """Validate the plugin reference fields."""
        if not self.plugin_id:
            raise ValueError("Plugin ID cannot be empty.")
        if self.plugin_url and not re.match(r"^https?://", self.plugin_url):
            raise ValueError("Plugin URL must start with http:// or https://.")


class WasmPluginWrapper:
    """Wrapper to safely execute .wasm plugins via wasmtime-py."""

    def __init__(self, wasm_path: str):
        self.wasm_path = wasm_path

        try:
            import wasmtime

            config = wasmtime.Config()
            config.consume_fuel = True
            config.epoch_interruption = True
            config.wasm_simd = False
            config.wasm_multi_memory = False

            self.engine = wasmtime.Engine(config)
            self.wasi_config = wasmtime.WasiConfig()
            self.store = wasmtime.Store(self.engine)
            self.store.set_wasi(self.wasi_config)
            self.store.add_fuel(10_000_000)
            self.module = wasmtime.Module.from_file(self.engine, self.wasm_path)
        except ImportError:
            pass
        except Exception as e:
            from core.tiered_logger import get_logger

            get_logger("wasm_sandbox").error(f"Failed to instantiate WASM runtime sandbox for {self.wasm_path}: {e}")


class PluginBase(ABC):
    """
    Abstract base class for all music providers and plugins.

    KEY PRINCIPLE: Providers convert their native format to EchosyncTrack.
    Core/Database/MatchingEngine process EchosyncTrack objects.

    Attributes:
        http: RequestManager instance for making HTTP requests with rate limiting and retries.
    """

    name: str
    category: str = "provider"
    supports_downloads: bool = False
    enabled: bool = True
    version: str = "Unknown"
    metadata_quality_score: int = 50
    supports_isrc_lookup: bool = False
    capabilities: ProviderCapabilities = None  # type: ignore[assignment]
    rate_limit: float = None  # type: ignore[assignment]
    kvs: StateKVS

    def __init__(self):
        """Initialize provider with HTTP client and governed SDK facades."""
        from core.request_manager import RateLimitConfig

        rate_config = None
        if self.rate_limit:
            rate_config = RateLimitConfig(requests_per_second=self.rate_limit)

        self.http = RequestManager(self.name, rate=rate_config)

        self._name = self.name
        self.sdk = sdk
        self.config = _ConfigFacade(self.name)
        self.secrets = _SecretsFacade(self.name)
        self.accounts = _AccountsSDKFacade()
        self.plugins = _PluginsSDKFacade()
        self.file = _FileSDKFacade()
        self.kvs = StateKVS(self.name)

        self.aliases = _AliasBroker(self.name)
        self.attributes = _AttributeBroker(self.name)
        self.db = _DatabaseFacade(self.name)
        self.library = _LibrarySDKFacade(self.name)
        self.working = _WorkingSDKFacade(self.name)
        self.models = _PluginModelFacade()

    async def _async_cancel_download(self, provider_id: str) -> bool:
        """Cancel an active or queued download transfer on the provider. Returns True if cancelled."""
        return False

    def get_database_connection(self, write_access: bool = False, require_library: bool = True):
        """Return an SQLAlchemy engine connected to the plugin's isolated SQLite database."""
        import os

        from sqlalchemy import create_engine, event

        from core.settings import config_manager
        from database.config_database import get_config_database

        if require_library and not _call_check_plugin_permission(self.name, "database.read_library"):
            raise PermissionError(f"Plugin '{self.name}' lacks 'permissions.database.read_library' permission.")
        if write_access and not (
            _call_check_plugin_permission(self.name, "database.mutate_working")
            or _call_check_plugin_permission(self.name, "privileged_mode")
        ):
            raise PermissionError(
                f"Plugin '{self.name}' lacks 'permissions.database.mutate_working' or 'privileged_mode' permission for write access."
            )

        db = get_config_database()
        plugin_id_int = db.get_service_id(self.name)
        if not plugin_id_int:
            import binascii

            plugin_id_int = binascii.crc32(self.name.lower().encode("utf-8")) & 0xFFFFFFFF

        channel = config_manager.get_plugin_channel(self.name) or "stable"
        db_file_name = f"{plugin_id_int}@beta.db" if channel == "beta" else f"{plugin_id_int}.db"

        plugin_data_dir = "/data/plugins/data/"
        os.makedirs(plugin_data_dir, exist_ok=True)

        db_path = os.path.join(plugin_data_dir, db_file_name)
        engine = create_engine(f"sqlite:///{db_path}")

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("ATTACH DATABASE 'file:/data/music.db?mode=ro' AS music_lib")
                working_mode = "rw" if write_access else "ro"
                if working_mode not in ("ro", "rw", "rwc"):
                    raise ValueError(f"Invalid attach database mode: {working_mode}")
                cursor.execute(f"ATTACH DATABASE 'file:/data/working.db?mode={working_mode}' AS working")
            except Exception:
                pass
            cursor.close()

        return engine

    @property
    def logger(self):
        from core.tiered_logger import get_logger

        return get_logger(f"plugin.{self._name}")

    def get_oauth_redirect_uri(self) -> str:
        """Calculate the standardized redirect URI for this provider using the OAuth sidecar."""
        from core.settings import config_manager

        host = config_manager.get("server_url") or config_manager.get("base_ip")
        if not host:
            import socket

            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                host = s.getsockname()[0]
                s.close()
            except Exception:
                host = "localhost"

        if host.startswith("http://") or host.startswith("https://"):
            host = host.split("://")[-1]
        host = host.split("/")[0].split(":")[0]
        provider_name = self.name.split(".")[-1]
        return f"https://{host}:5001/api/oauth/callback/plugins/{provider_name}"

    def handle_oauth_callback(self, args: dict[str, str]) -> Any:
        """Handle an OAuth callback from the sidecar."""
        raise NotImplementedError("This provider does not implement handle_oauth_callback")

    def authenticate(self, **kwargs: Any) -> bool:
        """Authenticate the provider (OAuth, API key, etc.)."""

    def search(
        self,
        query: str,
        type: str = "track",
        limit: int = 10,
        quality_profile: dict[str, Any] | None = None,
        includes: list[str] | None = None,
        excludes: list[str] | None = None,
        **kwargs: Any,
    ) -> list[EchosyncTrack]:
        """Search for tracks. Must return EchosyncTrack objects."""

    def get_track(self, track_id: str) -> EchosyncTrack | None:
        """Fetch a single track by ID. Must return EchosyncTrack object."""

    def get_metadata(self, mbid: str) -> dict[str, Any] | None:
        """Fetch full metadata for a recording/track."""
        return None

    def get_metadata_batch(self, mbids: list[str]) -> dict[str, dict[str, Any]]:
        """Fetch metadata for multiple recordings/tracks at once."""
        return {}

    def get_album(self, album_id: str) -> dict[str, Any] | None:
        """Fetch a single album by ID."""

    def get_artist(self, artist_id: str) -> dict[str, Any] | None:
        """Fetch a single artist by ID."""

    def get_user_playlists(self, user_id: str | None = None) -> list[dict[str, Any]]:
        """Fetch playlists for a user (if supported)."""

    def get_playlist_tracks(self, playlist_id: str) -> list[EchosyncTrack]:
        """Fetch tracks for a playlist. Must return List[EchosyncTrack]."""

    def add_tracks_to_playlist(self, playlist_id: str, provider_track_ids: list[str]) -> bool:
        """Add tracks to a playlist using provider-specific item IDs."""
        raise NotImplementedError(f"add_tracks_to_playlist not implemented for {self.name} provider")

    def remove_tracks_from_playlist(self, playlist_id: str, provider_track_ids: list[str]) -> bool:
        """Remove tracks from a playlist using provider-specific item IDs."""
        raise NotImplementedError(f"remove_tracks_from_playlist not implemented for {self.name} provider")

    def is_configured(self) -> bool:
        """Return True if provider is configured and ready to use."""

    def get_logo_url(self) -> str:
        """Return a URL or path to the provider's logo/icon."""

    def search_by_isrc(self, isrc: str) -> EchosyncTrack | None:
        """Look up a single track by its ISRC code."""
        return None

    @staticmethod
    def create_echo_sync_track(
        title: str,
        artist: str,
        album_artist: str | None = None,
        album: str | None = None,
        duration_ms: int | None = None,
        isrc: str | None = None,
        musicbrainz_id: str | None = None,
        musicbrainz_album_id: str | None = None,
        year: int | None = None,
        track_number: int | None = None,
        disc_number: int | None = None,
        bitrate: int | None = None,
        sample_rate: int | None = None,
        bit_depth: int | None = None,
        file_size_bytes: int | None = None,
        added_at: datetime | None = None,
        file_format: str | None = None,
        file_path: str | None = None,
        fingerprint: str | None = None,
        quality_tags: list[Any] | None = None,
        provider_id: str | None = None,
        source: str | None = None,
        **extra_fields: Any,
    ) -> EchosyncTrack | None:
        """Factory method to create EchosyncTrack with normalized metadata."""

        def _coerce_to_str(val: Any) -> str | None:
            if val is None:
                return None
            if callable(val):
                try:
                    val = val()
                except Exception:
                    return str(val)
            if isinstance(val, (list, tuple)):
                parts = []
                for it in val:
                    if isinstance(it, str):
                        parts.append(it)
                    else:
                        parts.append(str(getattr(it, "name", getattr(it, "title", it))))
                return " ".join([p for p in parts if p])
            if not isinstance(val, str):
                for attr in ("name", "title", "tag", "artist"):
                    if hasattr(val, attr):
                        try:
                            return str(getattr(val, attr))
                        except Exception:
                            continue
                return str(val)
            return val

        title_str = _coerce_to_str(title)
        artist_str = _coerce_to_str(artist)
        album_str = _coerce_to_str(album)

        clean_title, edition = text_utils.extract_edition(title_str) if title_str else (None, None)
        normalized_title = text_utils.normalize_title(clean_title) if clean_title else None
        normalized_artist = text_utils.normalize_artist(artist_str) if artist_str else None

        if not normalized_title or not normalized_title.strip():
            from core.tiered_logger import get_logger

            get_logger("provider_base").debug(
                f"Skipping track creation - normalized title is empty (original: '{title_str}')"
            )
            return None

        if not normalized_artist or not normalized_artist.strip():
            artist_str = "Unknown Artist"

        parsed_duration = text_utils.parse_duration_to_ms(duration_ms)
        parsed_track_number = text_utils.parse_int_safe(track_number)
        parsed_disc_number = text_utils.parse_int_safe(disc_number)

        identifiers = []
        if provider_id and source:
            identifiers.append(
                {
                    "plugin_source": source,
                    "plugin_item_id": str(provider_id),
                    "raw_data": extra_fields or None,
                }
            )

        from core.matching_engine.track_parser import normalize_track_dto
        from core.models.entities import _coerce_duration_ms

        track_kwargs: dict[str, Any] = dict(
            raw_title=title_str,
            title=clean_title or title_str,
            display_title=title_str,
            artist_name=artist_str,
            album_artist=album_artist,
            album_title=album_str,
            edition=edition,
            duration_ms=parsed_duration,
            track_number=parsed_track_number,
            disc_number=parsed_disc_number,
            release_year=year,
            musicbrainz_id=musicbrainz_id,
            isrc=isrc,
            fingerprint=fingerprint,
            quality_tags=quality_tags,
            identifiers=identifiers,
        )

        media_list = list(extra_fields.pop("media", []))
        has_media_params = any(
            [
                file_path,
                file_format,
                bitrate,
                sample_rate,
                bit_depth,
                file_size_bytes,
                added_at,
            ]
        )
        if has_media_params:
            from core.db.echo_sync_track import EchosyncMedia

            media = EchosyncMedia(
                file_path=file_path,
                file_format=file_format,
                bitrate=bitrate,
                sample_rate=sample_rate,
                bit_depth=bit_depth,
                duration_ms=parsed_duration,
                file_size_bytes=file_size_bytes,
                added_at=added_at,
            )
            media_list.append(media)

        if media_list:
            track_kwargs["media"] = media_list

        import dataclasses

        if "duration" in extra_fields and track_kwargs.get("duration_ms") is None:
            track_kwargs["duration_ms"] = _coerce_duration_ms(None, extra_fields.get("duration"))

        valid_fields = {f.name for f in dataclasses.fields(EchosyncTrack)}
        for k, v in extra_fields.items():
            if k in valid_fields:
                track_kwargs[k] = v

        return normalize_track_dto(EchosyncTrack(**track_kwargs))

    @staticmethod
    def extract_guid_identifier(guid_id: str, identifier_type: str) -> str | None:
        """Extract specific identifier from external URI/GUID format."""
        if not guid_id:
            return None

        target_prefix = identifier_type.lower()
        if target_prefix not in guid_id.lower():
            return None

        return text_utils.clean_guid_id(guid_id)


class SyncServiceProvider(PluginBase):
    """Interface for streaming and playlist sync service providers."""

    def get_user_playlists(self, user_id: str | None = None) -> list[Any]:
        pass

    def get_playlist_tracks(self, playlist_id: str) -> list[Any]:
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
    supports_playlists: PlaylistSupport
    search: SearchCapabilities
    metadata: MetadataRichness
    supports_cover_art: bool = False
    supports_lyrics: bool = False
    supports_user_auth: bool = False
    supports_library_scan: bool = False
    supports_streaming: bool = False
    supports_downloads: bool = False
    supports_pre_filtering: bool = False
    max_concurrency: int = 3
    max_concurrent_searches: int = 3
    pre_filters: list[Any] = None  # type: ignore[assignment]
    playlist_algorithms: list[Any] = None  # type: ignore[assignment]
    supports_fingerprinting: bool = False
    fingerprint_algorithms: list[Any] = None  # type: ignore[assignment]
    supports_metadata_fetch: bool = False
    supports_isrc_lookup: bool = False
    supports_batching: bool = False
    supports_metrics: bool = False

    def to_enum_list(self) -> list[Capability]:
        """Translate ProviderCapabilities dataclass back to legacy Capability Enums."""
        caps = []
        if getattr(self, "supports_fingerprinting", False):
            caps.append(Capability.RESOLVE_FINGERPRINT)
        if getattr(self, "supports_metadata_fetch", False):
            caps.append(Capability.FETCH_METADATA)
        if getattr(self, "supports_isrc_lookup", False):
            caps.append(Capability.FETCH_BY_ISRC)
        if getattr(self, "supports_pre_filtering", False):
            caps.append(Capability.CLIENT_PREFILTER)
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
    """Placeholder class for disabled providers."""

    def __init__(self, name: str, version: str = "Unknown", category: str = "provider"):
        self.name = name
        self.version = version
        self.category = category
        self.is_disabled = True

    def is_configured(self) -> bool:
        return False


class Provider(Protocol):
    """Strict contract that providers adhere to."""

    def search_tracks(self, query: str) -> list[EchosyncTrack]:
        ...

    def get_track_by_id(self, item_id: str) -> EchosyncTrack | None:
        ...

    def get_artist_details(self, artist_id: str) -> dict[str, Any]:
        ...


class DownloaderProvider(PluginBase):
    """Interface for downloader-style providers."""

    def search(self, query: str, limit: int = 10) -> list[Any]:
        pass

    def download(self, username: str, filename: str, file_size: int = 0) -> str | None:
        pass

    def get_download_status(self, download_id: str) -> dict[str, Any] | None:
        pass

    def cancel_download(self, download_id: str) -> bool:
        pass


class MediaServerProvider(PluginBase):
    """Base interface for media server providers."""

    def __init__(self):
        super().__init__()
        self._scan_state: dict[str, Any] = {
            "scanning": False,
            "progress": 0.0,
            "eta_seconds": None,
            "error": None,
        }

    def get_library_stats(self) -> dict[str, int]:
        pass

    def get_all_artists(self) -> list[Any]:
        pass

    def get_all_albums(self) -> list[Any]:
        pass

    def get_all_tracks(self) -> list[Any]:
        pass

    def trigger_library_scan(self, path: str | None = None) -> bool:
        from core.tiered_logger import get_logger

        log = get_logger("MediaServerProvider")
        try:
            success = self._trigger_scan_api(path)
            if success:
                self._scan_state["scanning"] = True
                self._scan_state["error"] = None
                log.info(f"{self.name} library scan initiated")
            return success
        except Exception as e:
            log.error(f"Error triggering {self.name} scan: {e}", exc_info=True)
            self._scan_state["error"] = str(e)
            return False

    def _trigger_scan_api(self, path: str | None = None) -> bool:
        pass

    def get_scan_status(self) -> dict[str, Any]:
        from core.tiered_logger import get_logger

        log = get_logger("MediaServerProvider")
        try:
            api_status = self._get_scan_status_api()
            self._scan_state.update(api_status)
            return self._scan_state.copy()
        except Exception as e:
            log.error(f"Error getting {self.name} scan status: {e}", exc_info=True)
            self._scan_state["error"] = str(e)
            return self._scan_state.copy()

    def _get_scan_status_api(self) -> dict[str, Any]:
        pass

    def get_content_changes_since(self, last_update: Any | None = None) -> Any:
        pass


def provision_plugin_table(plugin_id: int, table_schema: str) -> None:
    """Deprecated: Plugins must provision their own isolated SQLite databases."""
    raise NotImplementedError(
        "provision_plugin_table is deprecated. Use raw sqlite3/sqlalchemy to a local plugin .db file instead."
    )
