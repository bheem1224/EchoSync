from plugins.EchoSync.navidrome.client import NavidromeClient
from plugins.EchoSync.navidrome.routes import bp

ProviderClass = NavidromeClient
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
