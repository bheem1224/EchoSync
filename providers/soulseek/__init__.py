from providers.soulseek.client import SoulseekClient

# Register with ProviderRegistry
from core.provider_registry import ProviderRegistry
ProviderRegistry.register(SoulseekClient)

__all__ = ['SoulseekClient', 'soulseek_bp']


