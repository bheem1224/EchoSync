from .client import PlexClient
from .routes import bp

ProviderClass = PlexClient
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
