import asyncio
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.db.echo_sync_track import EchosyncTrack
from core.nexus_framework.plugin_loader import PluginRegistry
from core.nexus_framework.plugin_SDK import (
    DownloaderProvider,
    MetadataRichness,
    PlaylistSupport,
    ProviderCapabilities,
    SearchCapabilities,
)
from core.request_manager import HttpError
from core.tiered_logger import get_logger

logger = get_logger("slskd_provider")


def _sanitize_peer_filename(filename: str) -> str:
    """Collapse any peer-supplied path to a safe local filename."""
    normalized = (filename or "").replace("\\", "/")
    basename = Path(normalized).name
    return basename or "downloaded_file"


@dataclass
class SearchResult:
    """Base class for search results"""

    username: str
    filename: str
    size: int
    bitrate: int | None
    duration: int | None
    quality: str
    free_upload_slots: int
    upload_speed: int
    queue_length: int
    result_type: str = "track"  # "track" or "album"


@dataclass
class TrackResult(SearchResult):
    """Individual track search result"""

    artist: str | None = None
    title: str | None = None
    album: str = ""  # Default to empty string instead of None for consistency
    track_number: int | None = None
    bit_depth: int | None = None
    sample_rate: int | None = None

    def __post_init__(self):
        self.result_type = "track"
        # Try to extract metadata from filename if not provided
        self._parse_filename_metadata()

    def _parse_filename_metadata(self):
        """Extract artist, title, album, bit depth, sample rate from filename patterns"""

        # Normalize path separators (handle both / and \ from Soulseek)
        normalized_path = self.filename.replace("\\", "/")

        # Split path into components for heuristic extraction
        path_parts = normalized_path.split("/")

        # Get just the filename (last component) without extension
        file_with_ext = path_parts[-1] if path_parts else self.filename
        clean_filename = Path(file_with_ext).stem

        # 1. Parse Technical Metadata (Bit Depth / Sample Rate) only if not already set
        # Look for patterns like "24bit", "24-bit", "24b", "96kHz", "44.1kHz", "44100Hz"
        # Search in the full filename/path in case metadata is in directory structure

        # Bit Depth
        if self.bit_depth is None:
            bit_depth_match = re.search(
                r"(\d+)\s*[-_]?(?:bit|b)(?![a-zA-Z])", self.filename, re.IGNORECASE
            )
            if bit_depth_match:
                try:
                    self.bit_depth = int(bit_depth_match.group(1))
                except ValueError:
                    pass

        # Sample Rate
        if self.sample_rate is None:
            sample_rate_match = re.search(
                r"(\d+(?:\.\d+)?)\s*(?:k?hz)", self.filename, re.IGNORECASE
            )
            if sample_rate_match:
                try:
                    val_str = sample_rate_match.group(1)
                    unit_str = sample_rate_match.group(0).lower()
                    val = float(val_str)
                    if "khz" in unit_str:
                        self.sample_rate = int(val * 1000)
                    else:
                        self.sample_rate = int(val)
                except ValueError:
                    pass

        # 2. Parse Artist/Title/Album if missing
        if not self.title or not self.artist:
            # Common patterns for track naming (in order of specificity)
            # Strategy: Try to extract only when confident
            # Pattern 1: Track number + full title (e.g., "01 - All Remaining Content Here")
            # Pattern 2: Artist - Title split (e.g., "Artist Name - Song Title")
            patterns = [
                (
                    r"^(\d+)\s*[-\.]\s*(.+)$",
                    "track_and_title",
                ),  # "01 - Title" (keep everything after number)
                (r"^(.+?)\s*[-–]\s*(.+)$", "artist_and_title"),  # "Artist - Title"
            ]

            for pattern, pattern_type in patterns:
                match = re.match(pattern, clean_filename)
                if match:
                    groups = match.groups()
                    if pattern_type == "track_and_title":
                        # Pattern 1: Track number followed by everything else is the title
                        try:
                            self.track_number = int(groups[0])
                            self.title = self.title or groups[1].strip()
                        except (ValueError, IndexError):
                            pass
                    elif pattern_type == "artist_and_title":
                        # Pattern 2: Split by first dash - artist and title
                        # Only set if we don't have either artist or title
                        if len(groups) == 2:
                            self.artist = self.artist or groups[0].strip()
                            self.title = self.title or groups[1].strip()
                    break

        # Fallback: use the clean filename (not full path) as title if nothing was extracted
        if not self.title:
            self.title = clean_filename

        # Heuristic Path Extraction: Extract artist/album from directory structure
        if len(path_parts) > 1:  # Has directory structure
            # Get meaningful directory parts (skip filename which is last)
            dir_parts = [p for p in path_parts[:-1] if p and not p.startswith("@")]

            # Skip generic/system folder patterns
            generic_folders_pattern = r"^(music|downloads?|library|media|my music|users?|documents?|desktop|lossless|flac|mp3|high.*quality|lossy|\d{4}|\d{2,})$"
            meaningful_dirs = [
                d
                for d in dir_parts
                if d and not re.match(generic_folders_pattern, d, re.IGNORECASE)
            ]

            # Extract artist and album from remaining folder hierarchy
            # If we have at least 2 meaningful directories: Artist/Album structure
            # If we have at least 1: likely Album
            if meaningful_dirs:
                # Parent folder (closest to file) is likely the album
                parent_folder = meaningful_dirs[-1] if meaningful_dirs else None
                # Grandparent folder (one level up) is likely the artist
                grandparent_folder = (
                    meaningful_dirs[-2] if len(meaningful_dirs) >= 2 else None
                )

                # Use heuristic extraction ONLY if parsed values are missing or "Unknown"
                if not self.artist or self.artist.lower() in [
                    "unknown artist",
                    "unknown",
                    "",
                ]:
                    if grandparent_folder:
                        self.artist = grandparent_folder

                if not self.album or self.album.lower() in [
                    "unknown album",
                    "unknown",
                    "",
                ]:
                    if parent_folder:
                        self.album = parent_folder


def _is_raw_file_eligible(
    raw_file: dict[str, Any],
    basic_filters: dict[str, Any] | None = None,
    quality_profile: dict[str, Any] | None = None,
    includes: list[str] | None = None,
    excludes: list[str] | None = None,
) -> bool:
    """Zero-allocation gate checking raw JSON file descriptors prior to object creation."""
    # 1. Reject locked files
    if (
        raw_file.get("isLocked") is True
        or raw_file.get("locked") is True
        or raw_file.get("is_locked") is True
    ):
        return False

    filename = raw_file.get("filename", "")
    if not filename:
        return False

    # 2. Extension check
    file_ext = Path(filename).suffix.lower().lstrip(".")
    audio_extensions = {"mp3", "flac", "ogg", "aac", "wma", "wav", "m4a", "dsf", "dff"}
    if file_ext not in audio_extensions:
        return False

    allowed_extensions = (
        basic_filters.get("allowed_extensions") if basic_filters else None
    )
    if allowed_extensions:
        allowed_set = {e.lower().lstrip(".") for e in allowed_extensions}
        if file_ext not in allowed_set:
            return False

    # 3. Reject duration deltas > tolerance
    length_val = raw_file.get("length")
    target_duration_ms = (
        basic_filters.get("target_duration_ms") if basic_filters else None
    )
    duration_tolerance_ms = (
        basic_filters.get("duration_tolerance_ms", 3000) if basic_filters else 3000
    )
    if length_val is not None and length_val != "" and target_duration_ms:
        try:
            duration_seconds = float(length_val)
            target_seconds = float(target_duration_ms) / 1000.0
            tol_seconds = float(duration_tolerance_ms) / 1000.0
            if (
                duration_seconds > 0
                and abs(duration_seconds - target_seconds) > tol_seconds
            ):
                return False
        except (ValueError, TypeError):
            pass

    # 4. Filter expression / includes / excludes check on raw filename
    filter_expr = basic_filters.get("filter_expression") if basic_filters else None
    if filter_expr and filter_expr.lower() not in filename.lower():
        return False

    if includes:
        for inc in includes:
            if (
                isinstance(inc, str)
                and inc.strip()
                and inc.lower() not in filename.lower()
            ):
                return False

    if excludes:
        for exc in excludes:
            if isinstance(exc, str) and exc.strip() and exc.lower() in filename.lower():
                return False

    # 5. Format & Size verification across profile tiers
    size_bytes = raw_file.get("size", 0) or 0
    size_mb = size_bytes / (1024 * 1024) if size_bytes else 0

    if quality_profile:
        formats = quality_profile.get("formats", [])
        if formats:
            matching_tiers = [
                f
                for f in formats
                if (f.get("type") or f.get("format") or "").lower() == file_ext
            ]
            if matching_tiers:
                tier_passed = False
                for tier in matching_tiers:
                    min_mb = tier.get("min_size_mb", 0)
                    max_mb = tier.get("max_size_mb", 0)
                    if min_mb and size_mb and size_mb < min_mb:
                        continue
                    if max_mb and size_mb and size_mb > max_mb:
                        continue

                    # Native bit depth check if present on raw_file
                    raw_bd = raw_file.get("bitDepth") or raw_file.get("bit_depth")
                    tier_bds = tier.get("bit_depths", [])
                    if tier_bds and raw_bd is not None:
                        if str(raw_bd).strip() not in [
                            str(b).strip() for b in tier_bds
                        ]:
                            continue

                    # Native sample rate check if present on raw_file
                    raw_sr = raw_file.get("sampleRate") or raw_file.get("sample_rate")
                    tier_srs = tier.get("sample_rates", [])
                    if tier_srs and raw_sr is not None:
                        try:
                            sr_val = float(raw_sr)
                            sr_khz = f"{sr_val / 1000:.1f}".rstrip("0").rstrip(".")
                            sr_hz = str(int(sr_val))
                            allowed_sr = [str(s).strip().lower() for s in tier_srs]
                            if (
                                sr_khz not in allowed_sr
                                and sr_hz not in allowed_sr
                                and str(int(sr_val)) not in allowed_sr
                            ):
                                continue
                        except (ValueError, TypeError):
                            pass

                    tier_passed = True
                    break
                if not tier_passed:
                    return False

        # Fake FLAC heuristic
        if file_ext == "flac" and length_val and size_bytes:
            try:
                dur_sec = float(length_val)
                if dur_sec > 0:
                    advanced_filters = quality_profile.get("advanced_filters", {})
                    fake_min_bps = int(
                        advanced_filters.get("fake_flac_min_bytes_per_second", 70000)
                    )
                    fake_min_kbps = int(advanced_filters.get("fake_flac_min_kbps", 500))
                    approx_bps = size_bytes / dur_sec
                    approx_kbps = (size_bytes * 8.0) / (dur_sec * 1000.0)
                    if approx_bps < fake_min_bps or approx_kbps < fake_min_kbps:
                        return False
            except (ValueError, TypeError):
                pass

    # 6. Min bitrate check
    min_bitrate = basic_filters.get("min_bitrate", 0) if basic_filters else 0
    raw_bitrate = raw_file.get("bitRate") or raw_file.get("bitrate")
    if min_bitrate > 0 and raw_bitrate:
        try:
            if int(raw_bitrate) < min_bitrate:
                return False
        except (ValueError, TypeError):
            pass

    return True


class SlskdProvider(DownloaderProvider):
    """
    Stateless, high-efficiency API wrapper for Slskd.
    Follows "Dumb Executor" pattern - no orchestration logic.
    """

    name = "EchoSync.slskd"
    supports_downloads = True
    supports_pre_filtering = True
    rate_limit = 5.0  # High throughput allowed
    capabilities = ProviderCapabilities(
        name="slskd",
        supports_playlists=PlaylistSupport.NONE,
        search=SearchCapabilities(
            tracks=False, artists=False, albums=False, playlists=False
        ),
        metadata=MetadataRichness.LOW,
        supports_cover_art=False,
        supports_lyrics=False,
        supports_user_auth=True,
        supports_library_scan=False,
        supports_streaming=False,
        supports_downloads=True,
        supports_pre_filtering=True,
        max_concurrency=3,
        max_concurrent_searches=3,
    )

    def __init__(self):
        super().__init__()  # Initialize rate-limited http client
        self.base_url: str | None = None
        self.api_key: str | None = None
        self.download_path: Path = Path("./downloads")
        self._loop_semaphores: dict[Any, asyncio.Semaphore] = {}
        self._setup_client()
        self._register_health_check()

    @property
    def search_semaphore(self) -> asyncio.Semaphore:
        """Lazy per-running-event-loop semaphore to prevent cross-event-loop lock errors."""
        loop = asyncio.get_running_loop()
        if not hasattr(self, "_loop_semaphores"):
            self._loop_semaphores = {}
        if loop not in self._loop_semaphores:
            limit = getattr(self.capabilities, "max_concurrent_searches", 3)
            self._loop_semaphores[loop] = asyncio.Semaphore(limit)
        return self._loop_semaphores[loop]

    def _register_health_check(self):
        """Register periodic health check for Slskd API."""
        if not self.is_configured():
            return

        from core.event_bus import event_bus
        from core.health_check import HealthCheckResult

        def slskd_health_check() -> HealthCheckResult:
            try:
                # Try a lightweight API call to check connectivity and soulseek connection state
                try:
                    import requests

                    # Query session/server status
                    response = requests.get(
                        f"{self.base_url}/api/v0/session",
                        headers={"X-API-Key": self.api_key},
                        timeout=5,
                    )
                    if response.status_code == 200:
                        sess_data = response.json() if response.content else {}
                        # Check server connectivity status if provided
                        server_state = sess_data.get("state") or sess_data.get(
                            "serverState"
                        )
                        is_connected = sess_data.get("connected", True)
                        if server_state and str(server_state).lower() in [
                            "disconnected",
                            "faulted",
                            "degraded",
                        ]:
                            is_connected = False

                        if not is_connected:
                            event_bus.publish(
                                {
                                    "event": "SERVICE_DEGRADED",
                                    "service": "EchoSync.slskd",
                                    "reason": f"Soulseek state degraded: {server_state or 'disconnected'}",
                                }
                            )
                            return HealthCheckResult(
                                service_name="slskd",
                                status="degraded",
                                message=f"Slskd API reachable but Soulseek disconnected (state: {server_state})",
                            )

                        return HealthCheckResult(
                            service_name="slskd",
                            status="healthy",
                            message="Slskd API is reachable and connected",
                        )
                    else:
                        event_bus.publish(
                            {
                                "event": "SERVICE_DEGRADED",
                                "service": "EchoSync.slskd",
                                "reason": f"HTTP {response.status_code}",
                            }
                        )
                        return HealthCheckResult(
                            service_name="slskd",
                            status="degraded",
                            message=f"Slskd API returned status {response.status_code}",
                        )
                except Exception as api_err:
                    return HealthCheckResult(
                        service_name="slskd",
                        status="unhealthy",
                        message=f"Slskd API error: {api_err!s}",
                    )
            except Exception as e:
                return HealthCheckResult(
                    service_name="slskd",
                    status="unhealthy",
                    message=f"Slskd health check error: {e!s}",
                )

        self.sdk.health.register(slskd_health_check, interval_seconds=300)

    async def delete_transfer(
        self, username: str, transfer_id: str | None = None
    ) -> bool:
        """
        Delete a transfer from slskd daemon memory.
        If transfer_id is supplied, calls DELETE /api/v0/transfers/downloads/{username}/{transfer_id}.
        Otherwise calls DELETE /api/v0/transfers/downloads/{username}.
        """
        if not self.base_url:
            return False
        try:
            if transfer_id:
                endpoint = f"transfers/downloads/{username}/{transfer_id}"
            else:
                endpoint = f"transfers/downloads/{username}"
            await self._make_request("DELETE", endpoint)
            logger.info(
                "Evicted transfer from slskd memory: username=%s, transfer_id=%s",
                username,
                transfer_id,
            )
            return True
        except Exception as e:
            logger.warning(
                "Failed to evict transfer from slskd (%s / %s): %s",
                username,
                transfer_id,
                e,
            )
            return False

    async def reconnect_server(self) -> bool:
        """
        Attempt to trigger Soulseek reconnection via POST /api/v0/server/connect.
        """
        if not self.base_url:
            return False
        try:
            res = await self._make_request("POST", "server/connect")
            logger.info("Triggered slskd server reconnect: %s", res)
            return True
        except Exception as e:
            logger.warning("Failed to trigger slskd reconnect: %s", e)
            return False

    def _setup_client(self):
        # Retrieve Slskd connection details from namespaced config facade
        slskd_url = self.config.get("slskd_url") or self.config.get("server_url")
        api_key = self.config.get("api_key") or ""

        # Fallback: if URL isn't stored in namespaced config DB, check global config
        if not slskd_url:
            try:
                slskd_url = self.sdk.config.get("soulseek.slskd_url", "")
                if slskd_url:
                    logger.debug("Using slskd_url from global config as fallback")
            except Exception:
                slskd_url = None

        if not slskd_url:
            logger.warning("Slskd URL not configured")
            return

        # Apply Docker URL resolution if running in container
        if self.sdk.config.get("IS_DOCKER") and "localhost" in slskd_url:
            slskd_url = slskd_url.replace("localhost", "host.docker.internal")
            logger.info(f"Docker detected, using {slskd_url} for slskd connection")

        self.base_url = slskd_url.rstrip("/")
        self.api_key = api_key

        # Prefer global storage settings (from config manager) but fall back to per-provider values
        try:
            storage_cfg = self.sdk.config.get_all().get("storage", {}) or {}
        except Exception:
            storage_cfg = {}

        # Handle download path with Docker translation
        download_path_str = storage_cfg.get("download_dir") or "./downloads"
        if (
            self.sdk.config.get("IS_DOCKER")
            and len(download_path_str) >= 3
            and download_path_str[1] == ":"
            and download_path_str[0].isalpha()
        ):
            # Convert Windows path (E:/path) to WSL mount path (/mnt/e/path)
            drive_letter = download_path_str[0].lower()
            rest_of_path = download_path_str[2:].replace(
                "\\", "/"
            )  # Remove E: and convert backslashes
            download_path_str = f"/host/mnt/{drive_letter}{rest_of_path}"
            logger.info(f"Docker detected, using {download_path_str} for downloads")

        self.download_path = Path(download_path_str)
        try:
            self.download_path.mkdir(parents=True, exist_ok=True)
        except Exception:
            # best-effort directory creation; continue even if it fails
            pass

        logger.info(f"Slskd provider configured at {self.base_url}")

    def _get_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    async def _make_request(
        self, method: str, endpoint: str, **kwargs
    ) -> dict[str, Any] | None:
        """Unified request handler using self.http (RequestManager)"""
        if not self.base_url:
            logger.error("Slskd client not configured")
            return None

        url = f"{self.base_url}/api/v0/{endpoint}"

        try:
            headers = self._get_headers()

            logger.debug(f"Slskd API Request: {method} {url}")
            if kwargs.get("json"):
                logger.debug(f"Payload: {kwargs.get('json')}")

            # RequestManager.request is synchronous, so run in executor to avoid blocking
            # This respects the PluginBase rate limit configuration
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None, lambda: self.http.request(method, url, headers=headers, **kwargs)
            )

            if response.status_code in [200, 201, 204]:
                if not response.content:
                    return {}
                return response.json()
            # Fallback for any non-raising 2xx-adjacent path
            return None

        except HttpError as e:
            # RequestManager raises HttpError for 4xx/5xx responses.
            # 404 on a search DELETE is expected (search already expired on the slskd side).
            if e.status == 404 and "searches/" in url and method == "DELETE":
                logger.debug(
                    f"Search not found for deletion (already expired on slskd): {url}"
                )
            elif e.status == 409 and "searches" in url and method == "POST":
                # 409 = search slots full; caller handles cleanup + retry.
                raise
            else:
                logger.error(f"API request failed: {e}")
            return None

        except Exception as e:
            logger.error(f"Error making API request: {e}")
            return None

    def _convert_to_echosync_track(self, result: TrackResult) -> EchosyncTrack:
        """Convert TrackResult to EchosyncTrack with injected technical stats (Dumb Provider)."""
        safe_filename = _sanitize_peer_filename(result.filename)
        file_ext = (
            Path(result.filename).suffix.lower().lstrip(".") or result.quality or "flac"
        )

        # Dumb provider: store raw peer filename/path, leave detailed parsing to DownloadManager
        echo_track = self.create_echo_sync_track(
            title=safe_filename,
            artist=result.artist or "Unknown Artist",
            album=result.album or "",
            duration_ms=result.duration if result.duration else None,
            track_number=result.track_number,
            bitrate=result.bitrate,
            sample_rate=result.sample_rate,
            bit_depth=result.bit_depth,
            file_size_bytes=result.size,
            file_format=file_ext,
            file_path=result.filename,
            source="slskd",
            provider_id=result.filename,
        )

        if echo_track:
            echo_track.raw_title = result.filename
            if echo_track.media and len(echo_track.media) > 0:
                echo_track.media[0].file_path = result.filename
                echo_track.media[0].bit_depth = result.bit_depth
                echo_track.media[0].sample_rate = result.sample_rate
                echo_track.media[0].bitrate = result.bitrate
                echo_track.media[0].file_size_bytes = result.size
                echo_track.media[0].file_format = file_ext
            else:
                from core.db.echo_sync_track import EchosyncMedia

                echo_track.media = [
                    EchosyncMedia(
                        file_path=result.filename,
                        file_format=file_ext,
                        bitrate=result.bitrate,
                        sample_rate=result.sample_rate,
                        bit_depth=result.bit_depth,
                        file_size_bytes=result.size,
                    )
                ]
            echo_track.identifiers["username"] = result.username
            echo_track.identifiers["size"] = result.size
            echo_track.identifiers["free_upload_slots"] = result.free_upload_slots
            echo_track.identifiers["upload_speed"] = result.upload_speed
            echo_track.identifiers["queue_length"] = result.queue_length
            echo_track.identifiers["provider_item_id"] = result.filename
            echo_track.identifiers["plugin_item_id"] = result.filename
            echo_track.identifiers["local_filename"] = safe_filename
            echo_track.identifiers["bitrate"] = result.bitrate

            if result.bit_depth:
                echo_track.identifiers["bit_depth"] = result.bit_depth
            if result.sample_rate:
                echo_track.identifiers["sample_rate"] = result.sample_rate
            if result.size:
                echo_track.identifiers["size"] = result.size

        return echo_track

    def _process_search_responses(
        self,
        responses_data: list[dict[str, Any]],
        quality_profile: dict[str, Any] | None = None,
        cancel_event: Any | None = None,
        basic_filters: dict[str, Any] | None = None,
        includes: list[str] | None = None,
        excludes: list[str] | None = None,
    ) -> list[TrackResult]:
        """Process search responses into TrackResult objects with zero-allocation pre-filtering.

        Provider-side pre-filtering directly inspects raw JSON file payloads. It rejects
        locked files, duration outliers, tier bounds mismatches, and format criteria before
        allocating Python domain objects or executing regex.
        """
        all_tracks = []

        index = 0
        for response_data in responses_data:
            if cancel_event and cancel_event.is_set():
                return []
            username = response_data.get("username", "")
            files = response_data.get("files", [])

            for file_data in files:
                index += 1
                if cancel_event and cancel_event.is_set():
                    return []
                if index % 500 == 0:
                    time.sleep(0.005)  # Yield GIL

                if not _is_raw_file_eligible(
                    file_data,
                    basic_filters=basic_filters,
                    quality_profile=quality_profile,
                    includes=includes,
                    excludes=excludes,
                ):
                    continue

                filename = file_data.get("filename", "")
                size = file_data.get("size", 0)
                file_ext = Path(filename).suffix.lower().lstrip(".")

                # Normalize DSD extensions
                if file_ext in ["dsf", "dff"]:
                    quality = "dsd"
                elif file_ext in ["flac", "mp3", "ogg", "aac", "wma", "wav"]:
                    quality = file_ext
                else:
                    quality = "unknown"

                # Safely extract length (seconds) and convert to milliseconds
                length_val = file_data.get("length")
                duration_ms = None
                try:
                    if length_val is not None and length_val != "":
                        duration_seconds = int(float(length_val))
                        duration_ms = duration_seconds * 1000
                except Exception:
                    duration_ms = None

                # Extract native bit_depth and sample_rate
                bit_depth = file_data.get("bitDepth") or file_data.get("bit_depth")
                sample_rate = file_data.get("sampleRate") or file_data.get(
                    "sample_rate"
                )

                # Create TrackResult (duration stored in milliseconds)
                track = TrackResult(
                    username=username,
                    filename=filename,
                    size=size,
                    bitrate=file_data.get("bitRate"),
                    duration=duration_ms,
                    quality=quality,
                    bit_depth=int(bit_depth) if bit_depth is not None else None,
                    sample_rate=int(sample_rate) if sample_rate is not None else None,
                    free_upload_slots=response_data.get("freeUploadSlots", 0),
                    upload_speed=response_data.get("uploadSpeed", 0),
                    queue_length=response_data.get("queueLength", 0),
                )
                all_tracks.append(track)

        return all_tracks

    async def _async_search(
        self,
        query: str,
        basic_filters: dict[str, Any] = None,
        timeout: int = 60,
        quality_profile: dict[str, Any] | None = None,
        includes: list[str] | None = None,
        excludes: list[str] | None = None,
        cancel_event: Any | None = None,
    ) -> list[EchosyncTrack]:
        """
        Atomic Search: Post -> Poll -> Parse -> Delete.
        Applies coarse filtering (basic_filters) before returning.

        Concurrency: Limited to 3 concurrent searches (Soulseek IP ban protection).
        Default timeout: 60 seconds (12 polls at 5s intervals).
        """
        # Acquire semaphore slot (max 3 concurrent searches — Soulseek IP ban protection)
        async with self.search_semaphore:
            return await self._do_async_search(
                query,
                basic_filters,
                timeout,
                quality_profile,
                includes=includes,
                excludes=excludes,
                cancel_event=cancel_event,
            )

    async def _check_soulseek_connected(self) -> bool:
        """Return True only if slskd reports it is connected and logged in to the Soulseek network."""
        try:
            app_state = await self._make_request("GET", "application")
            if not app_state:
                return False
            server_state = (app_state.get("server") or {}).get("state", "")
            connected = "loggedin" in server_state.lower() or (
                "connected" in server_state.lower()
                and "disconnected" not in server_state.lower()
            )
            if not connected:
                logger.warning(
                    f"slskd is not connected to the Soulseek network (state='{server_state}')"
                )
            return connected
        except Exception as e:
            logger.warning(f"Could not determine slskd network state: {e}")
            return False

    async def _cleanup_all_searches(self) -> int:
        """DELETE every active search on slskd to free search slots. Returns number deleted."""
        try:
            searches = await self._make_request("GET", "searches")
            if not searches or not isinstance(searches, list):
                return 0
            deleted = 0
            for s in searches:
                sid = s.get("id") if isinstance(s, dict) else None
                if not sid:
                    continue
                try:
                    await self._make_request("DELETE", f"searches/{sid}")
                    deleted += 1
                except Exception:
                    pass
            if deleted:
                logger.info(f"Cleaned up {deleted} stale search(es) from slskd")
            return deleted
        except Exception as e:
            logger.warning(f"Failed to clean up stale searches: {e}")
            return 0

    async def _do_async_search(
        self,
        query: str,
        basic_filters: dict[str, Any] = None,
        timeout: int = 60,
        quality_profile: dict[str, Any] | None = None,
        includes: list[str] | None = None,
        excludes: list[str] | None = None,
        cancel_event: Any | None = None,
    ) -> list[EchosyncTrack]:
        """Internal async search implementation (called under semaphore lock)."""
        if not self.base_url:
            logger.error("Slskd client not configured")
            return []

        search_id = None
        try:
            if cancel_event and cancel_event.is_set():
                return []

            logger.info(f"Starting atomic search for: '{query}'")

            # Guard: slskd must be connected to the Soulseek network.
            if not await self._check_soulseek_connected():
                logger.warning(
                    "Aborting search — slskd is not connected to the Soulseek network"
                )
                return []

            search_data = {
                "searchText": query,
                "timeout": timeout * 1000,
                "filterResponses": True,
                "minimumResponseFileCount": 1,
                "minimumPeerUploadSpeed": 0,
            }

            # 1. Post Search (with one 409 recovery attempt)
            async def _post_search():
                return await self._make_request("POST", "searches", json=search_data)

            try:
                response = await _post_search()
            except HttpError as exc:
                if exc.status == 409:
                    logger.warning(
                        "Search slots full (HTTP 409) — clearing stale searches and retrying once"
                    )
                    await self._cleanup_all_searches()
                    await asyncio.sleep(1)
                    response = await self._make_request(
                        "POST", "searches", json=search_data
                    )
                else:
                    raise
            if not response:
                return []

            if isinstance(response, dict):
                search_id = response.get("id")
            elif isinstance(response, list) and len(response) > 0:
                search_id = (
                    response[0].get("id") if isinstance(response[0], dict) else None
                )

            if not search_id:
                logger.error("No search ID returned")
                return []

            # 2. Poll for search completion and results in 5s intervals up to 60s (12 polls max)
            poll_interval = 5.0
            max_polls = max(1, int(timeout / poll_interval))
            all_responses = []
            terminal_state = False
            elapsed_time = 0.0

            logger.info(
                f"Polling for search completion in 5s intervals up to {timeout}s (max {max_polls} polls)..."
            )

            for poll_count in range(max_polls):
                if cancel_event and cancel_event.is_set():
                    logger.info("Search aborted by cancellation request")
                    if search_id:
                        try:
                            await self._make_request("DELETE", f"searches/{search_id}")
                            logger.debug(f"Atomic cleanup: Deleted search {search_id}")
                            search_id = None
                        except Exception as e:
                            logger.warning(
                                f"Failed to delete search {search_id} on cancellation: {e}"
                            )
                    return []

                # Wait 5 seconds between polls
                await asyncio.sleep(poll_interval)
                elapsed_time += poll_interval

                # Check search state to see if it's complete
                search_state = await self._make_request("GET", f"searches/{search_id}")
                if search_state:
                    state = search_state.get("state", "").lower()
                    logger.debug(
                        f"Poll {poll_count + 1}/{max_polls} ({elapsed_time:.0f}s): Search state = '{state}'"
                    )

                    # Check for terminal states (e.g. responselimitreached, filelimitreached, timedout, completed, etc.)
                    terminal_states = {
                        "completed",
                        "complete",
                        "done",
                        "finished",
                        "timedout",
                        "cancelled",
                        "errored",
                        "failed",
                        "responselimitreached",
                        "filelimitreached",
                    }
                    if any(ts in state for ts in terminal_states):
                        terminal_state = True
                        logger.info(
                            f"Search reached terminal state: {state} (after {elapsed_time:.0f}s)"
                        )

                # Get current responses
                responses_data = await self._make_request(
                    "GET", f"searches/{search_id}/responses"
                )
                if responses_data and isinstance(responses_data, list):
                    all_responses = responses_data
                    response_count = len(all_responses)
                    logger.debug(
                        f"Poll {poll_count + 1}/{max_polls} ({elapsed_time:.0f}s): Got {response_count} responses"
                    )

                    if response_count >= 150:
                        logger.info(
                            f"Got {response_count} responses (threshold reached), stopping"
                        )
                        break
                else:
                    logger.debug(
                        f"Poll {poll_count + 1}/{max_polls} ({elapsed_time:.0f}s): No responses yet"
                    )

                # Exit immediately on terminal state
                if terminal_state:
                    logger.info("Exiting polling loop due to terminal state")
                    break

            if not all_responses:
                logger.info("Search complete but no responses received")

            # 3. Parse Results with Zero-Allocation Stream Pre-Filtering
            track_results = self._process_search_responses(
                all_responses,
                quality_profile=quality_profile,
                cancel_event=cancel_event,
                basic_filters=basic_filters,
                includes=includes,
                excludes=excludes,
            )
            logger.info(f"Search yielded {len(track_results)} filtered candidates")

            if cancel_event and cancel_event.is_set():
                return []

            # 4. Convert surviving TrackResult objects to EchosyncTrack
            valid_tracks = []
            for idx, tr in enumerate(track_results):
                if cancel_event and cancel_event.is_set():
                    return []
                if idx > 0 and idx % 500 == 0:
                    time.sleep(0.005)  # Yield GIL

                echo_track = self._convert_to_echosync_track(tr)
                if echo_track:
                    valid_tracks.append(echo_track)

            logger.info(f"Total valid candidate tracks: {len(valid_tracks)}")
            return valid_tracks

        except Exception as e:
            logger.error(f"Error in atomic search: {e}")
            return []
        finally:
            # 5. DELETE Search (Atomic cleanup)
            if search_id:
                try:
                    await self._make_request("DELETE", f"searches/{search_id}")
                    logger.debug(f"Atomic cleanup: Deleted search {search_id}")
                except Exception as e:
                    logger.warning(f"Failed to delete search {search_id}: {e}")

    async def _async_download(
        self, username: str, filename: str, file_size: int = 0
    ) -> str | None:
        if not self.base_url:
            return None

        try:
            logger.info(
                f"Initiating download: '{filename}' from user '{username}' (size: {file_size})"
            )

            # Slskd API format: POST /transfers/downloads/{username}
            # Body: Array of file objects with filename and size
            download_data = [
                {
                    "filename": filename,  # Remote file path on peer's system
                    "size": file_size,
                }
            ]

            # Username goes in the URL path, not the payload
            endpoint = f"transfers/downloads/{username}"
            response = await self._make_request("POST", endpoint, json=download_data)

            if response is not None:
                # Slskd returns the download information
                # The download "ID" for tracking is typically the filename
                # But we need to return something that can be used to check status later
                logger.info(f"Download initiated successfully for {filename}")
                # Return the username and filename as a compound ID
                # Format: username|filename
                return f"{username}|{filename}"

            logger.error(f"Download request failed for {filename} from {username}")
            return None

        except Exception as e:
            logger.error(f"Error starting download: {e}")
            return None

    async def _async_get_download_status(
        self, download_id: str
    ) -> dict[str, Any] | None:
        """
        Get status for a specific download.
        download_id format: \"username|filename\"
        """
        if not self.base_url:
            return None

        try:
            # Parse compound ID
            if "|" not in download_id:
                # Legacy download entry from before compound ID format was implemented
                # Skip silently - these will eventually be cleaned up by periodic cleanup task
                logger.debug(
                    f"Skipping legacy download_id without username prefix: {download_id[:80]}"
                )
                return None

            username, filename = download_id.split("|", 1)
            safe_filename = _sanitize_peer_filename(filename)

            # Query the transfers endpoint to find this download
            # GET /api/v0/transfers/downloads returns all downloads grouped by username
            all_downloads = await self._make_request("GET", "transfers/downloads")

            if all_downloads and isinstance(all_downloads, dict):
                # Response format: {\"username\": {\"directories\": [{\"directory\": \"...\", \"files\": [...]}]}}
                user_data = all_downloads.get(username, {})
                if isinstance(user_data, dict):
                    directories = user_data.get("directories", [])
                    for directory in directories:
                        if isinstance(directory, dict):
                            files = directory.get("files", [])
                            for file_data in files:
                                if isinstance(file_data, dict):
                                    file_filename = file_data.get("filename", "")
                                    # Match by filename
                                    if file_filename == filename:
                                        # Map slskd composite status to our status
                                        state_lower = file_data.get("state", "").lower()
                                        status = "unknown"
                                        if (
                                            "succeeded" in state_lower
                                            or "finished" in state_lower
                                        ):
                                            status = "complete"
                                        elif any(
                                            x in state_lower
                                            for x in [
                                                "error",
                                                "reject",
                                                "abort",
                                                "cancel",
                                                "timedout",
                                                "failed",
                                            ]
                                        ):
                                            status = "failed"
                                        elif (
                                            "queued" in state_lower
                                            or "initializing" in state_lower
                                        ):
                                            status = "queued"
                                        elif (
                                            "downloading" in state_lower
                                            or "transferring" in state_lower
                                            or "inprogress" in state_lower
                                        ):
                                            status = "downloading"
                                        elif "completed" in state_lower:
                                            status = "complete"

                                        return {
                                            "id": download_id,
                                            "status": status,
                                            "filename": safe_filename,
                                            "remote_filename": filename,
                                            "local_path": str(
                                                self.download_path / safe_filename
                                            ),
                                            "username": username,
                                            "progress": file_data.get(
                                                "percentComplete", 0
                                            ),
                                            "size": file_data.get("size", 0),
                                        }

            # Not found - might be completed and removed
            logger.debug(f"Download not found in active transfers: {download_id}")
            return None

        except Exception as e:
            logger.error(f"Error getting download status: {e}")
            return None

    async def _async_cancel_download(self, provider_id: str) -> bool:
        """Cancel/delete an active or queued download transfer from slskd."""
        if not self.base_url or not provider_id:
            return False

        try:
            if "|" not in provider_id:
                return False

            username, filename = provider_id.split("|", 1)

            # Query downloads to find file transfer id if available, or delete by username
            all_downloads = await self._make_request("GET", "transfers/downloads")
            file_id = None
            if all_downloads and isinstance(all_downloads, dict):
                user_data = all_downloads.get(username, {})
                if isinstance(user_data, dict):
                    for directory in user_data.get("directories", []):
                        if isinstance(directory, dict):
                            for file_data in directory.get("files", []):
                                if (
                                    isinstance(file_data, dict)
                                    and file_data.get("filename") == filename
                                ):
                                    file_id = file_data.get("id")
                                    break

            if file_id:
                try:
                    await self._make_request(
                        "DELETE", f"transfers/downloads/{username}/{file_id}"
                    )
                    logger.info(
                        f"Cancelled slskd download for user '{username}', file ID {file_id}"
                    )
                    return True
                except Exception:
                    pass

            # Fallback delete by username
            await self._make_request("DELETE", f"transfers/downloads/{username}")
            logger.info(f"Cleared slskd downloads for user '{username}'")
            return True
        except Exception as e:
            logger.warning(f"Failed to cancel slskd download '{provider_id}': {e}")
            return False

    # Public Sync Wrappers for Provider Interface

    def cancel_download(self, download_id: str) -> bool:
        """Synchronous wrapper for cancel_download"""
        try:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(self._async_cancel_download(download_id))
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error in synchronous cancel_download: {e}")
            return False

    def search(
        self,
        query: str,
        type: str | None = "track",
        cancel_event: Any | None = None,
        **kwargs,
    ) -> list[EchosyncTrack]:
        """Synchronous wrapper for atomic search"""
        if cancel_event is None:
            cancel_event = kwargs.get("cancel_event")
        limit = kwargs.get("limit", 10)
        basic_filters = kwargs.get("basic_filters")
        quality_profile = kwargs.get("quality_profile")
        includes = kwargs.get("includes")
        excludes = kwargs.get("excludes")
        try:
            loop = asyncio.new_event_loop()
            try:
                results = loop.run_until_complete(
                    self._async_search(
                        query,
                        basic_filters,
                        quality_profile=quality_profile,
                        includes=includes,
                        excludes=excludes,
                        cancel_event=cancel_event,
                    )
                )
                return results[:limit]
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error in synchronous search: {e}")
            return []

    def download(self, username: str, filename: str, file_size: int = 0) -> str | None:
        """Synchronous wrapper for download"""
        try:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(
                    self._async_download(username, filename, file_size)
                )
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error in synchronous download: {e}")
            return None

    def get_download_status(self, download_id: str) -> dict[str, Any] | None:
        """Synchronous wrapper for status"""
        try:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(
                    self._async_get_download_status(download_id)
                )
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error in synchronous get_download_status: {e}")
            return None

    # Required Abstract Methods Stubs

    def search_tracks(self, query: str) -> list[EchosyncTrack]:
        return self.search(query)

    def get_track_by_id(self, item_id: str) -> EchosyncTrack | None:
        return None

    def get_artist_details(self, artist_id: str) -> dict[str, Any]:
        return {}

    def get_logo_url(self) -> str:
        return "/assets/slskd-logo.png"

    def authenticate(self, **kwargs) -> bool:
        # Simple health check
        try:
            loop = asyncio.new_event_loop()
            try:
                res = loop.run_until_complete(self._make_request("GET", "session"))
                return res is not None
            finally:
                loop.close()
        except Exception as e:
            logger.debug(f"Slskd authenticate check failed: {e}")
            return False

    def is_configured(self) -> bool:
        return bool(self.base_url)

    # Legacy stubs (not used but required by abstract base class if not careful)
    def get_track(self, track_id: str) -> EchosyncTrack | None:
        return None

    def get_album(self, album_id: str) -> dict[str, Any] | None:
        return None

    def get_artist(self, artist_id: str) -> dict[str, Any] | None:
        return None

    def get_user_playlists(self, user_id: str | None = None) -> list[dict[str, Any]]:
        return []

    def get_playlist_tracks(self, playlist_id: str) -> list[EchosyncTrack]:
        return []


# Register the provider
PluginRegistry.register(SlskdProvider)
