"""Search adapter that selects search-capable providers and aggregates results."""

from typing import List, Dict, Optional

from plugins.plugin_system import plugin_registry, PluginScope
from core.provider_capabilities import get_provider_capabilities


class SearchAdapter:
    def aggregate(self, query: str, provider_names: Optional[List[str]] = None, search_types: Optional[List[str]] = None) -> List[Dict]:
        """Aggregate search results from providers that support search.* capabilities.

        Args:
            query (str): search query text
            provider_names (List[str], optional): explicit provider names to include. Defaults to all search-capable providers.
            search_types (List[str], optional): kinds to search: tracks, artists, albums, playlists.
        """
        if search_types is None or len(search_types) == 0:
            search_types = ["tracks"]

        search_cap_keys = {
            "tracks": "tracks",
            "artists": "artists",
            "albums": "albums",
            "playlists": "playlists",
        }

        # Discover search-capable providers
        providers = plugin_registry.list_all()
        search_providers = []
        for p in providers:
            if not getattr(p, "enabled", True):
                continue
            try:
                caps = get_provider_capabilities(p.name)
            except KeyError:
                continue
            if not any(getattr(caps.search, search_cap_keys[k], False) for k in search_types if k in search_cap_keys):
                continue
            if provider_names and p.name not in provider_names:
                continue
            search_providers.append((p, caps))

        results: List[Dict] = []
        for provider, caps in search_providers:
            for kind in search_types:
                if not getattr(caps.search, search_cap_keys[kind], False):
                    continue
                # Stub result — real implementation would call provider adapter
                results.append({
                    "title": f"Sample {kind} result for '{query}'",
                    "artist": "Unknown",
                    "provider": provider.name,
                    "type": kind,
                    "metadata_richness": caps.metadata.name,
                    "confidence": 0.5,
                })

        return results

    def route_result(self, item: Dict, action: str, target: Optional[str] = None) -> Dict:
        """Route a search result to downstream handlers (download, metadata, library).

        This is a stub for now; it validates payload shape and echoes acceptance.
        """
        allowed_actions = {"download", "metadata", "library"}
        if not item:
            return {"accepted": False, "error": "Missing item to route."}
        if action not in allowed_actions:
            return {"accepted": False, "error": f"Unsupported action: {action}"}

        return {
            "accepted": True,
            "action": action,
            "target": target,
            "item": item,
        }
