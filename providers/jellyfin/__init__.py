from providers.jellyfin.client import JellyfinClient
from providers.jellyfin.routes import bp

ProviderClass = JellyfinClient
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
