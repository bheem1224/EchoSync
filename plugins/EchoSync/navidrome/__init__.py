from .client import NavidromeClient
from .routes import bp

ProviderClass = NavidromeClient
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
