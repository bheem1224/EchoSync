from .client import TidalClient
from .routes import bp

ProviderClass = TidalClient
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
