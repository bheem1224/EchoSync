from plugins.spotify.client import SpotifyClient
from plugins.spotify.routes import bp

ProviderClass = SpotifyClient
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
