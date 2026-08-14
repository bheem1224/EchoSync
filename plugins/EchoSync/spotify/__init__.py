from .client import SpotifyClient
from .routes import router, bp

ProviderClass = SpotifyClient
RouteBlueprint = router

__all__ = ['ProviderClass', 'RouteBlueprint', 'router', 'bp']
