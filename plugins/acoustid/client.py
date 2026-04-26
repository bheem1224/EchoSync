from typing import List, Optional, Dict, Any
from core.caching.provider_cache import provider_cache
from core.provider_base import ProviderBase
from core.provider import ProviderCapabilities, PlaylistSupport, SearchCapabilities, MetadataRichness
from core.enums import Capability
from core.settings import config_manager
from core.file_handling.storage import get_storage_service
from core.matching_engine.echo_sync_track import EchosyncTrack
from core.tiered_logger import get_logger

logger = get_logger("provider.acoustid")

class AcoustIDProvider(ProviderBase):
    name = "acoustid"
    service_type = "metadata"
    capabilities = ProviderCapabilities(
        name='acoustid',
        supports_playlists=PlaylistSupport.NONE,
        search=SearchCapabilities(tracks=False, artists=False, albums=False, playlists=False),
        metadata=MetadataRichness.LOW,
        supports_cover_art=False,
        supports_lyrics=False,
        supports_user_auth=False,
        supports_library_scan=False,
        supports_streaming=False,
        supports_downloads=False,
        supports_fingerprinting=True,  # Special capability for fingerprinting
    )

    def __init__(self):
        super().__init__()
        self.api_base = "https://api.acoustid.org/v2"
        
        # Configure rate limit: 1 request/second per AcoustID API guidelines
        from core.request_manager import RateLimitConfig
        self.http.rate = RateLimitConfig(requests_per_second=1.0)

    def _get_api_key(self) -> Optional[str]:
        """Get AcoustID API key from config database with proper decryption."""
        try:
            from database.config_database import get_config_database
            config_db = get_config_database()
            
            # Get or create service ID
            service_id = config_db.get_or_create_service_id(self.name)
            if not service_id:
                return None
            
            # Get API key from database (automatically decrypts if marked sensitive)
            api_key = config_db.get_service_config(service_id, 'api_key')
            if api_key:
                api_key = str(api_key).strip()
                logger.debug(f"AcoustID API key loaded from config DB (length={len(api_key)})")
                return api_key or None
        except Exception as e:
            logger.debug(f"Could not load AcoustID API key from config DB: {e}")
        
        # Fallback to direct config get with decryption
        api_key = config_manager.get('acoustid.api_key')
        if api_key:
            api_key = str(api_key).strip()
            logger.debug(f"AcoustID API key loaded from config.json (length={len(api_key)})")
        return api_key or None

    def _get_submit_keys(self) -> tuple[Optional[str], Optional[str]]:
        """Get AcoustID client and user API keys for submission endpoints."""
        client_key: Optional[str] = None
        user_key: Optional[str] = None

        try:
            storage = get_storage_service()
            client_key = storage.get_service_config(self.name, 'api_key')
            user_key = storage.get_service_config(self.name, 'user_api_key')
        except Exception as e:
            logger.debug(f"Could not load AcoustID submission keys from storage service: {e}")

        client_key = str(client_key).strip() if client_key else None
        user_key = str(user_key).strip() if user_key else None

        if not client_key:
            client_key = self._get_api_key()

        if not user_key:
            cfg_user_key = config_manager.get('acoustid.user_api_key')
            if cfg_user_key:
                user_key = str(cfg_user_key).strip()

        return client_key or None, user_key or None

    @provider_cache(ttl_seconds=2592000)
    def resolve_fingerprint_details(self, fingerprint: str, duration: int) -> Dict[str, Any]:
        """
        Resolve fingerprint and return both AcoustID result ID and MBID candidates.

        Returns:
            {
                "acoustid_id": Optional[str],
                "mbids": List[str],
                "score": Optional[float]
            }
        """
        api_key = self._get_api_key()
        if not api_key:
            logger.warning("AcoustID API key not configured")
            return {"acoustid_id": None, "mbids": [], "score": None}

        if not fingerprint or not fingerprint.strip():
            logger.warning("Empty fingerprint provided")
            return {"acoustid_id": None, "mbids": [], "score": None}

        duration = int(duration)
        payload = {
            'client': api_key,
            'meta': 'recordingids',
            'fingerprint': fingerprint.strip(),
            'duration': duration
        }

        try:
            logger.debug(f"AcoustID payload: fingerprint_len={len(fingerprint)}, duration={duration}, api_key_len={len(api_key)}")
            response = self.http.post(f"{self.api_base}/lookup", data=payload)

            if response.status_code != 200:
                if response.status_code == 400:
                    logger.warning(
                        f"AcoustID lookup rejected (400). Response: {response.text[:200]}"
                    )
                else:
                    logger.error(f"AcoustID API error: {response.status_code} - {response.text[:200]}")
                return {"acoustid_id": None, "mbids": [], "score": None}

            data = response.json()
            if data.get('status') != 'ok':
                logger.error(f"AcoustID API returned error status: {data}")
                return {"acoustid_id": None, "mbids": [], "score": None}

            results = data.get('results') or []
            mbids: List[str] = []
            seen_mbid = set()
            best_result: Optional[Dict[str, Any]] = None
            best_score = -1.0

            for result in results:
                if not isinstance(result, dict):
                    continue

                try:
                    score = float(result.get('score') or 0.0)
                except Exception:
                    score = 0.0

                if best_result is None or score > best_score:
                    best_result = result
                    best_score = score

                for recording in result.get('recordings', []) or []:
                    if not isinstance(recording, dict):
                        continue
                    mbid = str(recording.get('id') or '').strip()
                    if mbid and mbid not in seen_mbid:
                        seen_mbid.add(mbid)
                        mbids.append(mbid)

            acoustid_id = None
            if isinstance(best_result, dict):
                result_id = str(best_result.get('id') or '').strip()
                if result_id:
                    acoustid_id = result_id

            return {
                "acoustid_id": acoustid_id,
                "mbids": mbids,
                "score": best_score if best_score >= 0.0 else None,
            }
        except Exception as e:
            logger.error(f"Failed to resolve fingerprint: {e}")
            return {"acoustid_id": None, "mbids": [], "score": None}

    def resolve_fingerprint(self, fingerprint: str, duration: int) -> List[str]:
        """
        Exchange Chromaprint for MusicBrainz Recording IDs.

        Args:
            fingerprint: The raw fingerprint string
            duration: Duration in seconds (integer)

        Returns:
            List of MusicBrainz Recording IDs (MBIDs)
        """
        details = self.resolve_fingerprint_details(fingerprint, duration)
        mbids = details.get('mbids') or []
        return [str(mbid).strip() for mbid in mbids if str(mbid).strip()]

    def submit_fingerprint(self, fingerprint: str, duration: int, mbid: str) -> bool:
        """Submit fingerprint to AcoustID for community contribution."""
        client_key, user_key = self._get_submit_keys()
        if not client_key or not user_key:
            logger.debug("Skipping AcoustID submit: missing client or user API key")
            return False

        # Opt-in check: only submit if auto_contribute is enabled in settings
        try:
            storage = get_storage_service()
            auto_contribute = storage.get_service_config(self.name, 'auto_contribute')
            if not (auto_contribute == 'true' or auto_contribute is True):
                logger.debug("Skipping AcoustID submission: auto_contribute is disabled")
                return False
        except Exception as e:
            logger.debug(f"Could not verify AcoustID auto_contribute flag: {e}")
            return False

        if not fingerprint or not str(fingerprint).strip() or not mbid or not str(mbid).strip():
            logger.debug("Skipping AcoustID submit: missing fingerprint or MBID")
            return False

        try:
            duration_int = int(duration)
        except Exception:
            logger.debug("Skipping AcoustID submit: invalid duration")
            return False

        payload = {
            'client': client_key,
            'user': user_key,
            'fingerprint.0': str(fingerprint).strip(),
            'duration.0': duration_int,
            'mbid.0': str(mbid).strip(),
        }

        try:
            response = self.http.post(f"{self.api_base}/submit", data=payload)
            if response.status_code != 200:
                logger.warning(f"AcoustID submit failed ({response.status_code}): {response.text[:200]}")
                return False

            data = response.json() or {}
            if data.get('status') != 'ok':
                logger.warning(f"AcoustID submit returned non-ok response: {data}")
                return False

            logger.info("Submitted AcoustID fingerprint contribution")
            return True
        except Exception as e:
            logger.warning(f"AcoustID submit failed: {e}")
            return False

    # Implement abstract methods
    def authenticate(self, **kwargs) -> bool:
        return True

    def search(self, query: str, type: str = "track", limit: int = 10) -> List[EchosyncTrack]:
        return []

    def get_track(self, track_id: str) -> Optional[EchosyncTrack]:
        return None

    def get_album(self, album_id: str) -> Optional[Dict[str, Any]]:
        return None

    def get_artist(self, artist_id: str) -> Optional[Dict[str, Any]]:
        return None

    def get_user_playlists(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return []

    def get_playlist_tracks(self, playlist_id: str) -> List[EchosyncTrack]:
        return []

    def is_configured(self) -> bool:
        return bool(self._get_api_key())

    def get_logo_url(self) -> str:
        return "https://acoustid.org/static/logo.png"
