from plugins.tidal.client import TidalClient
from plugins.tidal.routes import bp

ProviderClass = TidalClient
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
