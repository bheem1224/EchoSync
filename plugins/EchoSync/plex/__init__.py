from .client import PlexClient
from .routes import router

ProviderClass = PlexClient
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
