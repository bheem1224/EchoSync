from plugins.EchoSync.jellyfin.client import JellyfinClient
from plugins.EchoSync.jellyfin.routes import bp

ProviderClass = JellyfinClient
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
