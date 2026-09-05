from . import client
from .client import SpotifyClient
from .routes import bp, router

spotify = SpotifyClient
ProviderClass = SpotifyClient
RouteBlueprint = router

__all__ = [
    "ProviderClass",
    "RouteBlueprint",
    "SpotifyClient",
    "bp",
    "client",
    "router",
    "spotify",
]
