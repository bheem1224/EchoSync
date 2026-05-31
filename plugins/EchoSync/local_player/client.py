from typing import Any, Dict, List, Optional
from core.nexus_framework.plugin_SDK import PluginBase
from core.nexus_framework.plugin_SDK import ProviderCapabilities, PlaylistSupport, SearchCapabilities, MetadataRichness
from core.enums import Capability
from core.matching_engine.echo_sync_track import EchosyncTrack

class LocalPlayerProvider(PluginBase):
    name = 'EchoSync.local_player'
    category = 'provider'
    supports_downloads = False
    enabled = True

    capabilities = ProviderCapabilities(
        name='EchoSync.local_player',
        supports_playlists=PlaylistSupport.NONE,
        search=SearchCapabilities(tracks=False),
        metadata=MetadataRichness.LOW,
        supports_streaming=True,
    )

    def authenticate(self, **kwargs) -> bool:
        return True

    def search(self, query: str, type: str = "track", limit: int = 10, quality_profile: Optional[Dict[str, Any]] = None) -> List[EchosyncTrack]:
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
        return True

    def get_logo_url(self) -> str:
        return ""
