"""Search adapter that selects search-capable providers and aggregates results."""

import asyncio
from typing import List, Dict, Optional

from core.nexus_framework.plugin_loader import get_plugin_capabilities
from core.nexus_framework.plugin_SDK import MediaServerProvider

from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry
from core.settings import config_manager
from core.tiered_logger import get_logger


class SearchAdapter:
    def aggregate(self, query: str, plugin_ids: Optional[List[int]] = None, search_types: Optional[List[str]] = None) -> List[Dict]:
        """Aggregate search results from providers that support search.* capabilities.

        Args:
            query (str): search query text
            plugin_ids (List[int], optional): explicit plugin IDs to include. Defaults to all search-capable plugins.
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

        # Discover search-capable providers from the central registry.
        search_providers = []
        for plugin_id in PluginRegistry.list_plugins():
            try:
                provider = PluginRegistry.create_instance(plugin_id)
                caps = get_plugin_capabilities(plugin_id)
            except Exception:
                continue
            if not any(getattr(caps.search, search_cap_keys[k], False) for k in search_types if k in search_cap_keys):
                continue
            if plugin_ids and plugin_id not in plugin_ids:
                continue
            search_providers.append((provider, caps, plugin_id))

        results: List[Dict] = []
        for provider, caps, plugin_id in search_providers:
            for kind in search_types:
                if not getattr(caps.search, search_cap_keys[kind], False):
                    continue
                
                try:
                    search_type_singular = kind[:-1] if kind.endswith("s") else kind
                    provider_results = provider.search(query, type=search_type_singular, limit=10)
                    if not provider_results:
                        continue
                        
                    for item in provider_results:
                        if hasattr(item, 'to_dict'):
                            item_dict = item.to_dict()
                        elif isinstance(item, dict):
                            item_dict = dict(item)
                        else:
                            continue
                        
                        item_dict["plugin_id"] = plugin_id
                        item_dict["type"] = kind
                        item_dict["confidence"] = getattr(item_dict, "confidence", 1.0)
                        
                        if "title" not in item_dict and "name" in item_dict:
                            item_dict["title"] = item_dict["name"]
                        if "artist" not in item_dict and "artist_name" in item_dict:
                            item_dict["artist"] = item_dict["artist_name"]
                            
                        # MediaServerProviders are considered local
                        item_dict["is_local"] = isinstance(provider, MediaServerProvider)
                        
                        results.append(item_dict)
                except Exception as e:
                    get_logger("search_adapter").error(f"Search failed for {provider.name} ({kind}): {e}")

        return results

    async def federated_discovery(self, query: str, enabled_plugin_ids: Optional[List[int]] = None) -> List[Dict]:
        """Async federated discovery utilizing all search providers."""
        
        search_providers = []
        for plugin_id in PluginRegistry.list_plugins():
            if enabled_plugin_ids is not None and plugin_id not in enabled_plugin_ids:
                continue
                
            try:
                provider = PluginRegistry.create_instance(plugin_id)
                caps = get_plugin_capabilities(plugin_id)
                if getattr(caps.search, 'tracks', False):
                    search_providers.append((provider, plugin_id))
            except Exception:
                continue
                
        async def fetch_provider(provider, plugin_id):
            try:
                # OPTIMIZATION: Use asyncio.to_thread instead of run_in_executor to better
                # handle GIL and thread isolation for CPU-heavy matching logic
                results = await asyncio.wait_for(
                    asyncio.to_thread(provider.search, query, "track", 20),
                    timeout=10.0
                )
                return plugin_id, results
            except Exception as e:
                get_logger("search_adapter").error(f"Discovery timeout/error for {plugin_id}: {e}")
                return plugin_id, []

        tasks = [fetch_provider(p, pid) for p, pid in search_providers]
        gathered = await asyncio.gather(*tasks, return_exceptions=True)
        
        dedup_map = {}
        for res in gathered:
            if isinstance(res, Exception):
                continue
            plugin_id, items = res
            if not items:
                continue
                
            for item in items:
                if hasattr(item, 'to_dict'):
                    i_dict = item.to_dict()
                elif isinstance(item, dict):
                    i_dict = dict(item)
                else:
                    continue
                    
                isrc = i_dict.get("isrc")
                title = i_dict.get("title") or i_dict.get("name") or "Unknown"
                artist = i_dict.get("artist") or i_dict.get("artist_name") or "Unknown"
                
                match_key = None
                if isrc:
                    match_key = isrc
                else:
                    match_key = f"{str(title).lower()}:{str(artist).lower()}"
                    
                if match_key in dedup_map:
                    if plugin_id not in dedup_map[match_key]["sources"]:
                        dedup_map[match_key]["sources"].append(plugin_id)
                else:
                    cover_art = i_dict.get("cover_art_url") or i_dict.get("cover") or ""
                    
                    try:
                        from core.nexus_framework.plugin_loader import generate_plugin_id
                        prov_instance = PluginRegistry.create_instance(plugin_id)
                        
                        # Compare to specific plugin IDs if needed
                        local_meta_id = generate_plugin_id('echosync.local_metadata')
                        local_server_id = generate_plugin_id('echosync.local_server')
                        is_local = isinstance(prov_instance, MediaServerProvider) or plugin_id in [local_meta_id, local_server_id]
                    except Exception:
                        is_local = False
                    
                    dedup_map[match_key] = {
                        "id": str(i_dict.get("id", match_key)),
                        "title": title,
                        "artist": artist,
                        "sources": [plugin_id],
                        "ownership_state": "downloaded" if is_local else "missing",
                        "cover_art": cover_art
                    }
                    
        return list(dedup_map.values())

    def route_result(self, item: Dict, action: str, target: Optional[str] = None) -> Dict:
        """Route a search result to downstream handlers (download, metadata, library, play).

        This is a stub for now; it validates payload shape and echoes acceptance.
        """
        allowed_actions = {"download", "metadata", "library", "play"}
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
