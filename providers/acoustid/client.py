from typing import List, Optional, Dict, Any
from core.provider_base import ProviderBase
from core.enums import Capability
from core.settings import config_manager
from core.matching_engine.soul_sync_track import SoulSyncTrack
from core.tiered_logger import get_logger

logger = get_logger("provider.acoustid")

class AcoustIDProvider(ProviderBase):
    name = "acoustid"
    service_type = "metadata"
    capabilities = [Capability.RESOLVE_FINGERPRINT]

    def __init__(self):
        super().__init__()
        self.api_base = "https://api.acoustid.org/v2"
        
        # Configure rate limit: 1 request/second per AcoustID API guidelines
        from core.request_manager import RateLimitConfig
        self.http.rate = RateLimitConfig(requests_per_second=1.0)

    def _get_api_key(self) -> Optional[str]:
        # Try service credentials first
        creds = config_manager.get_service_credentials(self.name)
        if creds and creds.get('api_key'):
            api_key = str(creds.get('api_key')).strip()
            logger.debug(f"AcoustID API key loaded from config DB (length={len(api_key)})")
            return api_key or None
        # Fallback to direct config get
        api_key = config_manager.get('acoustid.api_key')
        if api_key:
            api_key = str(api_key).strip()
            logger.debug(f"AcoustID API key loaded from config.json (length={len(api_key)})")
        return api_key or None

    def resolve_fingerprint(self, fingerprint: str, duration: int) -> List[str]:
        """
        Exchange Chromaprint for MusicBrainz Recording IDs.

        Args:
            fingerprint: The raw fingerprint string
            duration: Duration in seconds (integer)

        Returns:
            List of MusicBrainz Recording IDs (MBIDs)
        """
        api_key = self._get_api_key()
        if not api_key:
            logger.warning("AcoustID API key not configured")
            return []

        # Validate fingerprint
        if not fingerprint or not fingerprint.strip():
            logger.warning("Empty fingerprint provided")
            return []

        # Force integer duration (API rejects floats)
        duration = int(duration)

        payload = {
            'client': api_key,
            'meta': 'recordingids',
            'fingerprint': fingerprint.strip(),
            'duration': duration
        }

        try:
            # Debug: Log exact payload before sending
            logger.debug(f"AcoustID payload: fingerprint_len={len(fingerprint)}, duration={duration}, api_key_len={len(api_key)}")
            
            # Use POST with data (not params) per AcoustID API docs
            response = self.http.post(f"{self.api_base}/lookup", data=payload)

            if response.status_code != 200:
                if response.status_code == 400:
                    logger.warning(
                        f"AcoustID lookup rejected (400). Response: {response.text[:200]}"
                    )
                else:
                    logger.error(f"AcoustID API error: {response.status_code} - {response.text[:200]}")
                return []

            data = response.json()
            if data.get('status') != 'ok':
                logger.error(f"AcoustID API returned error status: {data}")
                return []

            mbids = []
            for result in data.get('results', []):
                for recording in result.get('recordings', []):
                    if 'id' in recording:
                        mbids.append(recording['id'])

            # Deduplicate
            return list(set(mbids))

        except Exception as e:
            logger.error(f"Failed to resolve fingerprint: {e}")
            return []

    # Implement abstract methods
    def authenticate(self, **kwargs) -> bool:
        return True

    def search(self, query: str, type: str = "track", limit: int = 10) -> List[SoulSyncTrack]:
        return []

    def get_track(self, track_id: str) -> Optional[SoulSyncTrack]:
        return None

    def get_album(self, album_id: str) -> Optional[Dict[str, Any]]:
        return None

    def get_artist(self, artist_id: str) -> Optional[Dict[str, Any]]:
        return None

    def get_user_playlists(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return []

    def get_playlist_tracks(self, playlist_id: str) -> List[SoulSyncTrack]:
        return []

    def is_configured(self) -> bool:
        return bool(self._get_api_key())

    def get_logo_url(self) -> str:
        return "https://acoustid.org/static/logo.png"
