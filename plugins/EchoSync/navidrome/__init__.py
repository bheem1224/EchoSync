from .client import NavidromeClient
from .routes import router

ProviderClass = NavidromeClient
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
