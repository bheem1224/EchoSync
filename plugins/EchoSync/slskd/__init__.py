from .client import SlskdProvider
from .routes import bp

ProviderClass = SlskdProvider
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
