from providers.tidal.client import TidalClient
from providers.tidal.routes import bp

ProviderClass = TidalClient
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
