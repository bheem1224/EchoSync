from plugins.EchoSync.tidal.client import TidalClient
from plugins.EchoSync.tidal.routes import bp

ProviderClass = TidalClient
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
