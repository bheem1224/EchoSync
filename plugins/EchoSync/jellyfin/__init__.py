from .client import JellyfinClient
from .routes import router

ProviderClass = JellyfinClient
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
