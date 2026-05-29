from .client import SpotifyClient
from .routes import bp

ProviderClass = SpotifyClient
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
