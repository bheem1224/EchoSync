from providers.soulseek.client import SoulseekClient
from providers.soulseek.routes import bp

ProviderClass = SoulseekClient
RouteBlueprint = bp

__all__ = ['ProviderClass', 'RouteBlueprint']
