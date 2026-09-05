from . import plugin
from .client import SlskdProvider
from .routes import router

ProviderClass = SlskdProvider
RouteBlueprint = router

__all__ = ["ProviderClass", "RouteBlueprint", "plugin"]
