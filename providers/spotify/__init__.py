from providers.spotify.client import SpotifyClient
from providers.spotify.routes import bp

ProviderClass = SpotifyClient
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
