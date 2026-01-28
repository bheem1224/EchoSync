from providers.slskd.client import SlskdProvider
from providers.slskd.routes import bp

ProviderClass = SlskdProvider
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
