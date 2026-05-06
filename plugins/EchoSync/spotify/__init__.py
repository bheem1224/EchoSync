from plugins.EchoSync.spotify.client import SpotifyClient
from plugins.EchoSync.spotify.routes import bp

ProviderClass = SpotifyClient
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
