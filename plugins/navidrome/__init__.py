from plugins.navidrome.client import NavidromeClient
from plugins.navidrome.routes import bp

ProviderClass = NavidromeClient
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
