from typing import Optional
from providers.spotify.client import SpotifyClient
from providers.plex.client import PlexClient
from providers.jellyfin.client import JellyfinClient
from providers.navidrome.client import NavidromeClient
from providers.soulseek.client import SoulseekClient
from providers.tidal.client import TidalClient
from core.matching_engine import MusicMatchingEngine
from services.sync_service import PlaylistSyncService
from config.settings import config_manager
from database.music_database import get_database

class ServiceRegistry:
    """
    Centralized factory/registry for all core service clients.
    Ensures single instantiation and consistent usage.
    """

    def get_providers_by_type(self, provider_type: str):
        from core.provider_registry import ProviderRegistry
        return ProviderRegistry.get_providers_by_type(provider_type)

    def create_instances_by_type(self, provider_type: str, *args, **kwargs):
        from core.provider_registry import ProviderRegistry
        return ProviderRegistry.create_instance_by_type(provider_type, *args, **kwargs)
    def __init__(self):
        self._clients = {}
        self._adapters = {}

    def get_provider_client(self, name: str, account_id: Optional[str] = None):
        from core.provider_registry import ProviderRegistry
        if name not in self._clients:
            try:
                db = get_database()
                with db._get_connection() as conn:
                    c = conn.cursor()
                    c.execute("SELECT id FROM services WHERE name = ?", (name,))
                    row = c.fetchone()
                    service_id = row[0] if row else None
                active_id = None
                if service_id:
                    accounts = db.get_accounts(service_id=service_id, is_active=True)
                    if accounts:
                        active_id = accounts[0].get('id')
                self._clients[name] = ProviderRegistry.create_instance(name, account_id=active_id) if active_id else ProviderRegistry.create_instance(name)
            except Exception:
                self._clients[name] = ProviderRegistry.create_instance(name)
        return self._clients[name]

    def get_adapter(self, name: str):
        """Get or create a ProviderAdapter instance for a provider name."""
        from plugins.adapter_registry import AdapterRegistry
        if name not in self._adapters:
            # Inject existing provider client if available
            client = None
            try:
                client = self.get_provider_client(name)
            except Exception:
                client = None
            # Create adapter instance with injected client where applicable
            if name == 'spotify':
                self._adapters[name] = AdapterRegistry.create_instance(name, spotify_client=client)
            elif name == 'tidal':
                self._adapters[name] = AdapterRegistry.create_instance(name, tidal_client=client)
            elif name == 'plex':
                self._adapters[name] = AdapterRegistry.create_instance(name, plex_client=client)
            elif name == 'jellyfin':
                self._adapters[name] = AdapterRegistry.create_instance(name, jellyfin_client=client)
            elif name == 'navidrome':
                self._adapters[name] = AdapterRegistry.create_instance(name, navidrome_client=client)
            elif name == 'soulseek':
                self._adapters[name] = AdapterRegistry.create_instance(name, soulseek_client=client)
            elif name == 'listenbrainz':
                self._adapters[name] = AdapterRegistry.create_instance(name, listenbrainz_client=client)
            else:
                # Default creation without client injection
                self._adapters[name] = AdapterRegistry.create_instance(name)
        return self._adapters[name]

    def get_plex_client(self):
        return self.get_provider_client('plex')

    def get_jellyfin_client(self):
        return self.get_provider_client('jellyfin')

    def get_navidrome_client(self):
        return self.get_provider_client('navidrome')

    def get_soulseek_client(self):
        return self.get_provider_client('soulseek')

    # Remove get_tidal_client; use get_provider_client('tidal') instead

    def get_matching_engine(self):
        if 'matching_engine' not in self._clients:
            self._clients['matching_engine'] = MusicMatchingEngine()
        return self._clients['matching_engine']

    def get_sync_service(self):
        if 'sync_service' not in self._clients:
            self._clients['sync_service'] = PlaylistSyncService(
                self.get_provider_client('spotify'),
                self.get_plex_client(),
                self.get_provider_client('soulseek'),
                self.get_jellyfin_client(),
                self.get_navidrome_client()
            )
        return self._clients['sync_service']

service_registry = ServiceRegistry()
