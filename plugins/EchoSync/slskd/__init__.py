from .client import SlskdProvider
from .routes import router

ProviderClass = SlskdProvider
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
