from .client import JellyfinClient
from .routes import router

ProviderClass = JellyfinClient
RouteBlueprint = router

__all__ = ['ProviderClass', 'RouteBlueprint']
