from typing import Any

from core.db.echo_sync_track import EchosyncTrack
from core.nexus_framework.plugin_SDK import (
    MetadataRichness,
    PlaylistSupport,
    PluginBase,
    ProviderCapabilities,
    SearchCapabilities,
)


class LocalPlayerProvider(PluginBase):
    name = "EchoSync.local_player"
    category = "provider"
    supports_downloads = False
    enabled = True

    capabilities = ProviderCapabilities(
        name="EchoSync.local_player",
        supports_playlists=PlaylistSupport.NONE,
        search=SearchCapabilities(tracks=False),
        metadata=MetadataRichness.LOW,
        supports_streaming=True,
    )

    def authenticate(self, **kwargs) -> bool:
        return True

    def search(
        self,
        query: str,
        type: str = "track",
        limit: int = 10,
        quality_profile: dict[str, Any] | None = None,
    ) -> list[EchosyncTrack]:
        return []

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

    def is_configured(self) -> bool:
        return True

    def get_logo_url(self) -> str:
        return ""
