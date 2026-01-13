from providers.plex.client import PlexClient
from providers.plex.routes import bp

ProviderClass = PlexClient
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
