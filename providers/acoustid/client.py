from typing import List, Optional, Dict, Any
from core.provider_base import ProviderBase
from core.enums import Capability
from core.settings import config_manager
from core.matching_engine.soul_sync_track import SoulSyncTrack
from core.tiered_logger import get_logger

logger = get_logger("provider.acoustid")

class AcoustIDProvider(ProviderBase):
    name = "acoustid"
    capabilities = [Capability.RESOLVE_FINGERPRINT]

    def __init__(self):
        super().__init__()
        self.api_base = "https://api.acoustid.org/v2"

    def _get_api_key(self) -> Optional[str]:
        # Try service credentials first
        creds = config_manager.get_service_credentials(self.name)
        if creds and creds.get('api_key'):
            return creds.get('api_key')
        # Fallback to direct config get
        return config_manager.get('acoustid.api_key')

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

        params = {
            'client': api_key,
            'meta': 'recordingids',
            'fingerprint': fingerprint,
            'duration': duration
        }

        try:
            # Using self.http (RequestManager)
            # RequestManager handles rate limiting and retries
            response = self.http.get(f"{self.api_base}/lookup", params=params)

            if response.status_code != 200:
                logger.error(f"AcoustID API error: {response.status_code} - {response.text}")
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
