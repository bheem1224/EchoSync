from providers.navidrome.client import NavidromeClient
from providers.navidrome.routes import bp

ProviderClass = NavidromeClient
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
