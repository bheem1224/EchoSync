import asyncio
import os
import re
from typing import List, Optional, Dict, Any, Union, Tuple
from dataclasses import dataclass
import time
from pathlib import Path
from core.tiered_logger import get_logger
from core.settings import config_manager
from core.provider import get_provider_capabilities, DownloaderProvider, ProviderRegistry
from core.matching_engine.soul_sync_track import SoulSyncTrack

logger = get_logger("slskd_provider")

@dataclass
class SearchResult:
    """Base class for search results"""
    username: str
    filename: str
    size: int
    bitrate: Optional[int]
    duration: Optional[int]
    quality: str
    free_upload_slots: int
    upload_speed: int
    queue_length: int
    result_type: str = "track"  # "track" or "album"

@dataclass
class TrackResult(SearchResult):
    """Individual track search result"""
    artist: Optional[str] = None
    title: Optional[str] = None
    album: Optional[str] = None
    track_number: Optional[int] = None
    bit_depth: Optional[int] = None
    sample_rate: Optional[int] = None

    def __post_init__(self):
        self.result_type = "track"
        # Try to extract metadata from filename if not provided
        self._parse_filename_metadata()

    def _parse_filename_metadata(self):
        """Extract artist, title, album, bit depth, sample rate from filename patterns"""
        import re
        import os

        # Get just the filename without extension and path
        base_name = os.path.splitext(os.path.basename(self.filename))[0]

        # 1. Parse Technical Metadata (Bit Depth / Sample Rate)
        # Look for patterns like "24bit", "24-bit", "24b", "96kHz", "44.1kHz", "44100Hz"

        # Bit Depth
        bit_depth_match = re.search(r'(\d+)\s*[-_]?(?:bit|b)(?![a-zA-Z])', self.filename, re.IGNORECASE)
        if bit_depth_match:
            try:
                self.bit_depth = int(bit_depth_match.group(1))
            except ValueError:
                pass

        # Sample Rate
        sample_rate_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:k?hz)', self.filename, re.IGNORECASE)
        if sample_rate_match:
            try:
                val_str = sample_rate_match.group(1)
                unit_str = sample_rate_match.group(0).lower()
                val = float(val_str)
                if 'khz' in unit_str:
                    self.sample_rate = int(val * 1000)
                else:
                    self.sample_rate = int(val)
            except ValueError:
                pass

        # 2. Parse Artist/Title/Album if missing
        if not self.title or not self.artist:
            # Common patterns for track naming
            patterns = [
                r'^(\d+)\s*[-\.]\s*(.+?)\s*[-–]\s*(.+)$',  # "01 - Artist - Title" or "01. Artist - Title"
                r'^(.+?)\s*[-–]\s*(.+)$',  # "Artist - Title"
                r'^(\d+)\s*[-\.]\s*(.+)$',  # "01 - Title" or "01. Title"
            ]

            for pattern in patterns:
                match = re.match(pattern, base_name)
                if match:
                    groups = match.groups()
                    if len(groups) == 3:  # Track number, artist, title
                        try:
                            self.track_number = int(groups[0])
                            self.artist = self.artist or groups[1].strip()
                            self.title = self.title or groups[2].strip()
                        except ValueError:
                            # First group might not be a number
                            self.artist = self.artist or groups[0].strip()
                            self.title = self.title or f"{groups[1]} - {groups[2]}".strip()
                    elif len(groups) == 2:
                        if groups[0].isdigit():  # Track number and title
                            try:
                                self.track_number = int(groups[0])
                                self.title = self.title or groups[1].strip()
                            except ValueError:
                                pass
                        else:  # Artist and title
                            self.artist = self.artist or groups[0].strip()
                            self.title = self.title or groups[1].strip()
                    break

        # Fallback: use filename as title if nothing was extracted
        if not self.title:
            self.title = base_name

        # Try to extract album from directory path
        if not self.album and '/' in self.filename:
            path_parts = self.filename.split('/')
            if len(path_parts) >= 2:
                # Look for album-like directory names
                for part in reversed(path_parts[:-1]):  # Exclude filename
                    if part and not part.startswith('@'):  # Skip system directories
                        # Clean up common patterns
                        cleaned = re.sub(r'^\d+\s*[-\.]\s*', '', part)  # Remove leading numbers
                        if len(cleaned) > 3:  # Must be substantial
                            self.album = cleaned
                            break

class SlskdProvider(DownloaderProvider):
    """
    Stateless, high-efficiency API wrapper for Slskd.
    Follows "Dumb Executor" pattern - no orchestration logic.
    """
    name = "slskd"
    supports_downloads = True

    def __init__(self):
        super().__init__()
        self.base_url: Optional[str] = None
        self.api_key: Optional[str] = None
        self.download_path: Path = Path("./downloads")
        # Capability flags
        self.capabilities = get_provider_capabilities('slskd')
        # Concurrency limiter: Slskd can only handle 5 concurrent searches (IP ban protection)
        self._search_semaphore = asyncio.Semaphore(5)
        self._setup_client()
        self._register_health_check()
    
    def _register_health_check(self):
        """Register periodic health check for Slskd API."""
        from core.health_check import register_health_check_job, HealthCheckResult
        
        def slskd_health_check() -> HealthCheckResult:
            try:
                configured = self.is_configured()
                if not configured:
                    return HealthCheckResult(
                        service_name="slskd",
                        status="unhealthy",
                        message="Slskd not configured"
                    )
                
                # Try a lightweight API call to check connectivity
                try:
                    import requests
                    response = requests.get(
                        f"{self.base_url}/api/v0/session",
                        headers={"X-API-Key": self.api_key},
                        timeout=5
                    )
                    if response.status_code == 200:
                        return HealthCheckResult(
                            service_name="slskd",
                            status="healthy",
                            message="Slskd API is reachable"
                        )
                    else:
                        return HealthCheckResult(
                            service_name="slskd",
                            status="degraded",
                            message=f"Slskd API returned status {response.status_code}"
                        )
                except Exception as api_err:
                    return HealthCheckResult(
                        service_name="slskd",
                        status="unhealthy",
                        message=f"Slskd API error: {str(api_err)}"
                    )
            except Exception as e:
                return HealthCheckResult(
                    service_name="slskd",
                    status="unhealthy",
                    message=f"Slskd health check error: {str(e)}"
                )
        
        register_health_check_job("slskd_health_check", slskd_health_check, interval_seconds=300)

    def _setup_client(self):
        config = config_manager.get_soulseek_config()

        if not config.get('slskd_url'):
            logger.warning("Slskd URL not configured")
            return

        # Apply Docker URL resolution if running in container
        slskd_url = config.get('slskd_url', '')
        if os.path.exists('/.dockerenv') and 'localhost' in slskd_url:
            slskd_url = slskd_url.replace('localhost', 'host.docker.internal')
            logger.info(f"Docker detected, using {slskd_url} for slskd connection")

        self.base_url = slskd_url.rstrip('/')
        self.api_key = config.get('api_key', '')

        # Prefer global storage settings (from config manager) but fall back to per-provider values
        try:
            storage_cfg = config_manager.get_all().get('storage', {}) or {}
        except Exception:
            storage_cfg = {}

        # Handle download path with Docker translation
        download_path_str = storage_cfg.get('download_dir') or config.get('download_path', './downloads')
        if os.path.exists('/.dockerenv') and len(download_path_str) >= 3 and download_path_str[1] == ':' and download_path_str[0].isalpha():
            # Convert Windows path (E:/path) to WSL mount path (/mnt/e/path)
            drive_letter = download_path_str[0].lower()
            rest_of_path = download_path_str[2:].replace('\\', '/')  # Remove E: and convert backslashes
            download_path_str = f"/host/mnt/{drive_letter}{rest_of_path}"
            logger.info(f"Docker detected, using {download_path_str} for downloads")

        self.download_path = Path(download_path_str)
        try:
            self.download_path.mkdir(parents=True, exist_ok=True)
        except Exception:
            # best-effort directory creation; continue even if it fails
            pass

        logger.info(f"Slskd provider configured at {self.base_url}")

    def _get_headers(self) -> Dict[str, str]:
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['X-API-Key'] = self.api_key
        return headers

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Unified request handler using self.http (RequestManager)"""
        if not self.base_url:
            logger.error("Slskd client not configured")
            return None

        url = f"{self.base_url}/api/v0/{endpoint}"

        try:
            headers = self._get_headers()

            logger.debug(f"Slskd API Request: {method} {url}")
            if kwargs.get('json'):
                logger.debug(f"Payload: {kwargs.get('json')}")

            # RequestManager.request is synchronous, so run in executor to avoid blocking
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.http.request(method, url, headers=headers, **kwargs)
            )

            if response.status_code in [200, 201, 204]:
                if not response.content:
                    return {}
                return response.json()
            else:
                # Reduce noise for expected 404s (e.g. search deletion)
                if response.status_code == 404 and 'searches/' in url and method == 'DELETE':
                    logger.debug(f"Search not found for deletion (expected): {url}")
                else:
                    logger.error(f"API request failed: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error making API request: {e}")
            return None

    def _convert_to_soulsync_track(self, result: TrackResult) -> SoulSyncTrack:
        """Convert TrackResult to SoulSyncTrack with injected technical stats"""
        # Create base track
        soul_track = self.create_soul_sync_track(
            title=result.title or result.filename,
            artist=result.artist or "Unknown Artist",
            album=result.album or "Unknown Album",
            duration_ms=(result.duration * 1000) if result.duration else None,
            track_number=result.track_number,
            bitrate=result.bitrate,
            file_format=result.quality,
            file_path=result.filename,
            source="slskd",
            provider_id=result.filename, # Use filename as unique ID for Soulseek
        )

        # Manually inject metadata into identifiers for Matching Engine
        if soul_track:
             soul_track.identifiers['username'] = result.username
             soul_track.identifiers['size'] = result.size
             soul_track.identifiers['free_upload_slots'] = result.free_upload_slots
             soul_track.identifiers['upload_speed'] = result.upload_speed
             soul_track.identifiers['queue_length'] = result.queue_length
             soul_track.identifiers['provider_item_id'] = result.filename
             soul_track.identifiers['bitrate'] = result.bitrate

             # Technical metadata
             if result.bit_depth:
                soul_track.bit_depth = result.bit_depth
                soul_track.identifiers['bit_depth'] = result.bit_depth
             if result.sample_rate:
                soul_track.sample_rate = result.sample_rate
                soul_track.identifiers['sample_rate'] = result.sample_rate
             if result.size:
                soul_track.file_size_bytes = result.size

        return soul_track

    def _process_search_responses(self, responses_data: List[Dict[str, Any]]) -> List[TrackResult]:
        """Process search response data into TrackResult objects"""
        all_tracks = []

        # Audio file extensions to filter for
        audio_extensions = {'.mp3', '.flac', '.ogg', '.aac', '.wma', '.wav', '.m4a', '.dsf', '.dff'}

        for response_data in responses_data:
            username = response_data.get('username', '')
            files = response_data.get('files', [])

            for file_data in files:
                filename = file_data.get('filename', '')
                size = file_data.get('size', 0)

                file_ext = Path(filename).suffix.lower().lstrip('.')

                # Only process audio files
                if f'.{file_ext}' not in audio_extensions:
                    continue

                # Normalize DSD extensions
                if file_ext in ['dsf', 'dff']:
                    quality = 'dsd'
                elif file_ext in ['flac', 'mp3', 'ogg', 'aac', 'wma', 'wav']:
                    quality = file_ext
                else:
                    quality = 'unknown'

                # Create TrackResult
                track = TrackResult(
                    username=username,
                    filename=filename,
                    size=size,
                    bitrate=file_data.get('bitRate'),
                    duration=file_data.get('length'),
                    quality=quality,
                    free_upload_slots=response_data.get('freeUploadSlots', 0),
                    upload_speed=response_data.get('uploadSpeed', 0),
                    queue_length=response_data.get('queueLength', 0)
                )
                all_tracks.append(track)

        return all_tracks

    async def _async_search(self, query: str, basic_filters: Dict[str, Any] = None, timeout: int = 180) -> List[SoulSyncTrack]:
        """
        Atomic Search: Post -> Poll -> Parse -> Delete.
        Applies coarse filtering (basic_filters) before returning.
        
        Concurrency: Limited to 5 concurrent searches (Slskd/Soulseek IP ban protection).
        
        Smart polling:
        - Phase 1 (0-45s): Poll every 5s for quick responsiveness
        - Phase 2 (45s+): Poll every 30s to minimize API calls
        - Exit immediately upon terminal state (completed, timedout, failed, etc.)
        
        Default timeout: 180 seconds (3 minutes) to allow extended waiting for slskd responses.
        """
        # Acquire semaphore slot (max 5 concurrent searches for IP ban protection)
        async with self._search_semaphore:
            return await self._do_async_search(query, basic_filters, timeout)

    async def _do_async_search(self, query: str, basic_filters: Dict[str, Any] = None, timeout: int = 180) -> List[SoulSyncTrack]:
        """Internal async search implementation (called under semaphore lock)."""
        if not self.base_url:
            logger.error("Slskd client not configured")
            return []

        search_id = None
        try:
            logger.info(f"Starting atomic search for: '{query}'")

            search_data = {
                'searchText': query,
                'timeout': timeout * 1000,
                'filterResponses': True,
                'minimumResponseFileCount': 1,
                'minimumPeerUploadSpeed': 0
            }

            # 1. Post Search
            response = await self._make_request('POST', 'searches', json=search_data)
            if not response:
                return []

            if isinstance(response, dict):
                search_id = response.get('id')
            elif isinstance(response, list) and len(response) > 0:
                search_id = response[0].get('id') if isinstance(response[0], dict) else None

            if not search_id:
                logger.error("No search ID returned")
                return []

            # 2. Poll for search completion and results
            # Smart polling strategy:
            # - Phase 1 (0-45s): Poll every 5s for quick responsiveness
            # - Phase 2 (45s+): Poll every 30s to minimize API calls
            initial_phase_duration = 45.0  # First 45 seconds
            initial_phase_interval = 5.0   # Poll every 5s during initial phase
            main_phase_interval = 30.0     # Poll every 30s after initial phase
            
            all_responses = []
            terminal_state = False
            elapsed_time = 0.0

            logger.info(f"Polling for search completion (5s intervals for 45s, then 30s intervals, timeout: {timeout}s)...")
            
            for poll_count in range(int(timeout / main_phase_interval) + 10):  # Safety upper bound
                # Determine polling interval based on elapsed time
                if elapsed_time < initial_phase_duration:
                    poll_interval = initial_phase_interval
                    phase_name = "initial"
                else:
                    poll_interval = main_phase_interval
                    phase_name = "main"
                
                # Check search state to see if it's complete
                search_state = await self._make_request('GET', f'searches/{search_id}')
                if search_state:
                    state = search_state.get('state', '').lower()
                    logger.debug(f"Poll {poll_count + 1} ({phase_name} phase, {elapsed_time:.0f}s): Search state = '{state}'")
                    
                    # Check for terminal states (exit immediately)
                    if state in ['completed', 'complete', 'done', 'finished', 'timedout', 'cancelled', 'errored', 'failed']:
                        terminal_state = True
                        logger.info(f"Search reached terminal state: {state} (after {elapsed_time:.0f}s)")

                # Get current responses
                responses_data = await self._make_request('GET', f'searches/{search_id}/responses')
                if responses_data and isinstance(responses_data, list):
                    all_responses = responses_data
                    response_count = len(all_responses)
                    logger.debug(f"Poll {poll_count + 1} ({phase_name} phase, {elapsed_time:.0f}s): Got {response_count} responses")
                    
                    # Exit early if we have a LOT of responses (prevent excessive waiting)
                    if response_count >= 150:
                        logger.info(f"Got {response_count} responses (threshold reached), stopping")
                        break
                else:
                    logger.debug(f"Poll {poll_count + 1} ({phase_name} phase, {elapsed_time:.0f}s): No responses yet")
                
                # Exit immediately on terminal state (don't continue polling)
                if terminal_state:
                    logger.info(f"Exiting polling loop due to terminal state")
                    break
                
                # Exit if overall timeout exceeded
                if elapsed_time >= timeout:
                    logger.warning(f"Polling timeout exceeded ({elapsed_time:.0f}s >= {timeout}s)")
                    break
                
                # Wait before next poll
                await asyncio.sleep(poll_interval)
                elapsed_time += poll_interval

            if not all_responses:
                logger.info(f"Search complete but no responses received")
                
            # 3. Parse Results
            track_results = self._process_search_responses(all_responses)
            logger.info(f"Search yielded {len(track_results)} raw candidates")

            # 4. Apply Coarse Filters (Extensions, Min Bitrate)
            valid_tracks = []
            allowed_extensions = basic_filters.get('allowed_extensions') if basic_filters else None
            min_bitrate = basic_filters.get('min_bitrate', 0) if basic_filters else 0

            for tr in track_results:
                # Extension Check
                if allowed_extensions:
                    ext = Path(tr.filename).suffix.lower().lstrip('.')
                    if ext not in allowed_extensions:
                        continue

                # Bitrate Check (skip if None, assume okay or let MatchingEngine decide)
                if min_bitrate > 0 and tr.bitrate and tr.bitrate < min_bitrate:
                    continue

                # Convert to SoulSyncTrack
                soul_track = self._convert_to_soulsync_track(tr)
                if soul_track:
                    valid_tracks.append(soul_track)

            logger.info(f"After coarse filtering: {len(valid_tracks)} candidates")
            return valid_tracks

        except Exception as e:
            logger.error(f"Error in atomic search: {e}")
            return []
        finally:
            # 5. DELETE Search (Atomic cleanup)
            if search_id:
                try:
                    await self._make_request('DELETE', f'searches/{search_id}')
                    logger.debug(f"Atomic cleanup: Deleted search {search_id}")
                except Exception as e:
                    logger.warning(f"Failed to delete search {search_id}: {e}")

    async def _async_download(self, username: str, filename: str, file_size: int = 0) -> Optional[str]:
        if not self.base_url:
            return None

        try:
            logger.info(f"Initiating download: '{filename}' from user '{username}' (size: {file_size})")
            download_data = [
                {
                    "filename": filename,
                    "size": file_size,
                    "path": str(self.download_path)
                }
            ]

            # Try main endpoint
            endpoint = f'transfers/downloads/{username}'
            response = await self._make_request('POST', endpoint, json=download_data)

            if response is not None:
                # Try to extract download ID
                if isinstance(response, dict) and 'id' in response:
                    return response['id']
                elif isinstance(response, list) and len(response) > 0 and 'id' in response[0]:
                    return response[0]['id']
                # Fallback to filename if API doesn't return ID (some versions don't)
                return filename

            logger.error(f"Download request failed for {filename} from {username}")
            return None

        except Exception as e:
            logger.error(f"Error starting download: {e}")
            return None

    async def _async_get_download_status(self, download_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status for a specific download ID.
        Note: Slskd API makes it hard to get status by ID directly if it's not active.
        We might need to fetch all and filter, or use specific endpoints.
        """
        if not self.base_url:
            return None

        try:
            # Try direct ID endpoint
            response = await self._make_request('GET', f'transfers/downloads/{download_id}')

            data = None
            if response:
                if isinstance(response, dict):
                    data = response
                elif isinstance(response, list) and len(response) > 0:
                    data = response[0]

            # If direct lookup failed, try finding in all downloads (fallback)
            if not data:
                all_downloads = await self._make_request('GET', 'transfers/downloads')
                if all_downloads:
                    for user_data in all_downloads:
                        for directory in user_data.get('directories', []):
                            for file_data in directory.get('files', []):
                                if file_data.get('id') == download_id or file_data.get('filename') == download_id:
                                    data = file_data
                                    data['username'] = user_data.get('username') # inject username
                                    break
                            if data: break
                        if data: break

            if data:
                # Normalize status
                state = data.get('state', '').lower()
                status = "unknown"
                if state in ['completed', 'succeeded', 'finished']:
                    status = "complete"
                elif state in ['queued', 'initializing']:
                    status = "queued"
                elif state in ['downloading', 'transferring']:
                    status = "downloading"
                elif state in ['failed', 'error', 'aborted', 'cancelled']:
                    status = "failed"

                return {
                    'id': data.get('id', download_id),
                    'status': status,
                    'progress': data.get('percentComplete', 0.0),
                    'speed': data.get('averageSpeed', 0),
                    'filename': data.get('filename'),
                    'size': data.get('size', 0),
                    'time_remaining': data.get('timeRemaining')
                }

            return None

        except Exception as e:
            logger.error(f"Error getting download status: {e}")
            return None

    # Public Sync Wrappers for Provider Interface

    def search(self, query: str, basic_filters: Dict[str, Any] = None, limit: int = 10) -> List[SoulSyncTrack]:
        """Synchronous wrapper for atomic search"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                results = loop.run_until_complete(self._async_search(query, basic_filters))
                return results[:limit]
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error in synchronous search: {e}")
            return []

    def download(self, username: str, filename: str, file_size: int = 0) -> Optional[str]:
        """Synchronous wrapper for download"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self._async_download(username, filename, file_size))
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error in synchronous download: {e}")
            return None

    def get_download_status(self, download_id: str) -> Optional[Dict[str, Any]]:
        """Synchronous wrapper for status"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self._async_get_download_status(download_id))
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error in synchronous get_download_status: {e}")
            return None

    # Required Abstract Methods Stubs

    def search_tracks(self, query: str) -> List[SoulSyncTrack]:
        return self.search(query)

    def get_track_by_id(self, item_id: str) -> Optional[SoulSyncTrack]:
        return None

    def get_artist_details(self, artist_id: str) -> Dict[str, Any]:
        return {}

    def get_logo_url(self) -> str:
        return "/assets/slskd-logo.png"

    def authenticate(self, **kwargs) -> bool:
        # Simple health check
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                res = loop.run_until_complete(self._make_request('GET', 'session'))
                return res is not None
            finally:
                loop.close()
        except:
            return False

    def is_configured(self) -> bool:
        return bool(self.base_url)

    # Legacy stubs (not used but required by abstract base class if not careful)
    def get_track(self, track_id: str) -> Optional[SoulSyncTrack]: return None
    def get_album(self, album_id: str) -> Optional[Dict[str, Any]]: return None
    def get_artist(self, artist_id: str) -> Optional[Dict[str, Any]]: return None
    def get_user_playlists(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]: return []
    def get_playlist_tracks(self, playlist_id: str) -> List[SoulSyncTrack]: return []


# Register the provider
ProviderRegistry.register(SlskdProvider)
