from typing import Any, Dict, List, Optional
from core.provider_base import ProviderBase
from core.provider import ProviderCapabilities
from core.enums import Capability
from core.matching_engine.soul_sync_track import SoulSyncTrack

class LocalMetadataProvider(ProviderBase):
    name = 'local_metadata'
    category = 'provider'
    supports_downloads = False
    enabled = True

    capabilities = ProviderCapabilities(
        capabilities=[
            Capability.FETCH_METADATA,
            Capability.TAG_FILES
        ]
    )

    def authenticate(self, **kwargs) -> bool:
        return True

    def search(self, query: str, type: str = "track", limit: int = 10, quality_profile: Optional[Dict[str, Any]] = None) -> List[SoulSyncTrack]:
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
        return True

    def get_logo_url(self) -> str:
        return ""
