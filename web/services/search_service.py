"""Search adapter that selects search-capable providers and aggregates results."""

import asyncio
from typing import List, Dict, Optional

from core.provider import ProviderRegistry, get_provider_capabilities, MediaServerProvider
from core.settings import config_manager
from core.tiered_logger import get_logger


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

        # Discover search-capable providers from the central registry.
        search_providers = []
        for provider_name in ProviderRegistry.list_providers():
            try:
                provider = ProviderRegistry.create_instance(provider_name)
                caps = get_provider_capabilities(provider.name)
            except Exception:
                continue
            if not any(getattr(caps.search, search_cap_keys[k], False) for k in search_types if k in search_cap_keys):
                continue
            if provider_names and provider.name not in provider_names:
                continue
            search_providers.append((provider, caps))

        results: List[Dict] = []
        for provider, caps in search_providers:
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
                        
                        item_dict["provider"] = provider.name
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

    async def federated_discovery(self, query: str, enabled_providers: Optional[List[str]] = None) -> List[Dict]:
        """Async federated discovery utilizing all search providers."""
        
        search_providers = []
        for provider_name in ProviderRegistry.list_providers():
            if enabled_providers is not None and provider_name not in enabled_providers:
                continue
                
            try:
                provider = ProviderRegistry.create_instance(provider_name)
                caps = get_provider_capabilities(provider.name)
                if getattr(caps.search, 'tracks', False):
                    search_providers.append(provider)
            except Exception:
                continue
                
        async def fetch_provider(provider):
            try:
                # OPTIMIZATION: Use asyncio.to_thread instead of run_in_executor to better
                # handle GIL and thread isolation for CPU-heavy matching logic
                results = await asyncio.wait_for(
                    asyncio.to_thread(provider.search, query, "track", 20),
                    timeout=5.0
                )
                return provider.name, results
            except Exception as e:
                get_logger("search_adapter").error(f"Discovery timeout/error for {provider.name}: {e}")
                return provider.name, []

        tasks = [fetch_provider(p) for p in search_providers]
        gathered = await asyncio.gather(*tasks, return_exceptions=True)
        
        dedup_map = {}
        for res in gathered:
            if isinstance(res, Exception):
                continue
            provider_name, items = res
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
                    if provider_name not in dedup_map[match_key]["sources"]:
                        dedup_map[match_key]["sources"].append(provider_name)
                else:
                    cover_art = i_dict.get("cover_art_url") or i_dict.get("cover") or ""
                    
                    try:
                        prov_instance = ProviderRegistry.create_instance(provider_name)
                        is_local = isinstance(prov_instance, MediaServerProvider)
                    except Exception:
                        is_local = False
                    
                    dedup_map[match_key] = {
                        "id": str(i_dict.get("id", match_key)),
                        "title": title,
                        "artist": artist,
                        "sources": [provider_name],
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
