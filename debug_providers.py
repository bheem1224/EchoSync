
import sys
import os

# Add repo root to path
sys.path.insert(0, os.getcwd())

from core.provider import CAPABILITY_REGISTRY, ProviderRegistry
from web.services.provider_registry import list_providers

# Mock loading slskd and spotify
from providers.slskd.client import SlskdProvider
# Mock spotify registration (assuming it follows similar pattern)
class MockSpotifyProvider:
    name = 'spotify'
    category = 'syncservice'
    supports_downloads = False

ProviderRegistry.register(SlskdProvider)
ProviderRegistry.register(MockSpotifyProvider)

print("--- Capability Registry ---")
print(CAPABILITY_REGISTRY.keys())

print("\n--- Slskd Capability ---")
cap = CAPABILITY_REGISTRY.get('slskd')
print(f"Metadata: {cap.metadata.name}")
print(f"Search Tracks: {cap.search.tracks}")

print("\n--- List Providers Output ---")
providers = list_providers()
for p in providers:
    print(f"Provider: {p['name']}")
    print(f"Capabilities: {p.get('capabilities')}")
    if p['name'] == 'slskd':
        print(f"Check: search.tracks = {p['capabilities']['search']['tracks']}")
