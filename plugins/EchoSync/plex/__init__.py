from .client import PlexClient
from .routes import router

ProviderClass = PlexClient
RouteBlueprint = router

__all__ = ['ProviderClass', 'RouteBlueprint']
