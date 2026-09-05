from .client import NavidromeClient
from .routes import router

ProviderClass = NavidromeClient
RouteBlueprint = router

__all__ = ["ProviderClass", "RouteBlueprint"]
