from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict


class PlaylistSupport(Enum):
    NONE = auto()
    READ = auto()
    READ_WRITE = auto()


class MetadataRichness(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()


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


# Central registry of known provider capabilities
CAPABILITY_REGISTRY: Dict[str, ProviderCapabilities] = {
    'spotify': ProviderCapabilities(
        name='spotify',
        supports_playlists=PlaylistSupport.READ,
        search=SearchCapabilities(tracks=True, artists=True, albums=True, playlists=True),
        metadata=MetadataRichness.HIGH,
        supports_cover_art=True,
        supports_lyrics=False,
        supports_user_auth=True,
        supports_library_scan=False,
        supports_streaming=True,
        supports_downloads=False,
    ),
    'tidal': ProviderCapabilities(
        name='tidal',
        supports_playlists=PlaylistSupport.READ,
        search=SearchCapabilities(tracks=True, artists=True, albums=True, playlists=True),
        metadata=MetadataRichness.HIGH,
        supports_cover_art=True,
        supports_lyrics=False,
        supports_user_auth=True,
        supports_library_scan=False,
        supports_streaming=True,
        supports_downloads=False,
    ),
    'plex': ProviderCapabilities(
        name='plex',
        supports_playlists=PlaylistSupport.READ_WRITE,
        search=SearchCapabilities(tracks=True, artists=True, albums=True, playlists=False),
        metadata=MetadataRichness.HIGH,
        supports_cover_art=True,
        supports_lyrics=False,
        supports_user_auth=True,
        supports_library_scan=True,
        supports_streaming=False,
        supports_downloads=False,
    ),
    'jellyfin': ProviderCapabilities(
        name='jellyfin',
        supports_playlists=PlaylistSupport.READ_WRITE,
        search=SearchCapabilities(tracks=True, artists=True, albums=True, playlists=False),
        metadata=MetadataRichness.MEDIUM,
        supports_cover_art=True,
        supports_lyrics=False,
        supports_user_auth=True,
        supports_library_scan=True,
        supports_streaming=False,
        supports_downloads=False,
    ),
    'navidrome': ProviderCapabilities(
        name='navidrome',
        supports_playlists=PlaylistSupport.READ_WRITE,
        search=SearchCapabilities(tracks=True, artists=True, albums=True, playlists=True),
        metadata=MetadataRichness.MEDIUM,
        supports_cover_art=True,
        supports_lyrics=False,
        supports_user_auth=True,
        supports_library_scan=True,
        supports_streaming=False,
        supports_downloads=False,
    ),
    'soulseek': ProviderCapabilities(
        name='soulseek',
        supports_playlists=PlaylistSupport.NONE,
        search=SearchCapabilities(tracks=True, artists=False, albums=False, playlists=False),
        metadata=MetadataRichness.LOW,
        supports_cover_art=False,
        supports_lyrics=False,
        supports_user_auth=True,
        supports_library_scan=False,
        supports_streaming=False,
        supports_downloads=True,
    ),
    'listenbrainz': ProviderCapabilities(
        name='listenbrainz',
        supports_playlists=PlaylistSupport.READ,
        search=SearchCapabilities(tracks=False, artists=False, albums=False, playlists=True),
        metadata=MetadataRichness.MEDIUM,
        supports_cover_art=False,
        supports_lyrics=False,
        supports_user_auth=False,
        supports_library_scan=False,
        supports_streaming=False,
        supports_downloads=False,
    ),
}


def get_provider_capabilities(provider: str) -> ProviderCapabilities:
    """Return capabilities for a provider key, raising KeyError if unknown."""
    return CAPABILITY_REGISTRY[provider]
