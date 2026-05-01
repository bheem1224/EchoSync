from plugins.plex.client import PlexClient
from plugins.plex.routes import bp

ProviderClass = PlexClient
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
