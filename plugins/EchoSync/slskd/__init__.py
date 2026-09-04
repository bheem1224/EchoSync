from .client import SlskdProvider
from .routes import router
from . import plugin

ProviderClass = SlskdProvider
RouteBlueprint = router

__all__ = ['ProviderClass', 'RouteBlueprint', 'plugin']
