from .client import JellyfinClient
from .routes import bp

ProviderClass = JellyfinClient
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
