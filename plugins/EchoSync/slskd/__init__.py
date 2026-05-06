from plugins.EchoSync.slskd.client import SlskdProvider
from plugins.EchoSync.slskd.routes import bp

ProviderClass = SlskdProvider
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
