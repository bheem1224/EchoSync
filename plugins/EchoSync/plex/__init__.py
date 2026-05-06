from plugins.EchoSync.plex.client import PlexClient
from plugins.EchoSync.plex.routes import bp

ProviderClass = PlexClient
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
