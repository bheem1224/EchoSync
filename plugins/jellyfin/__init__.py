from plugins.jellyfin.client import JellyfinClient
from plugins.jellyfin.routes import bp

ProviderClass = JellyfinClient
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
