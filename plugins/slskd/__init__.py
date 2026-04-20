from plugins.slskd.client import SlskdProvider
from plugins.slskd.routes import bp

ProviderClass = SlskdProvider
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
