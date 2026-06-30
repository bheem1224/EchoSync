"""Search adapter that selects search-capable providers and aggregates results."""

import asyncio
from typing import List, Dict, Optional, Tuple

from core.nexus_framework.plugin_loader import get_plugin_capabilities
from core.nexus_framework.plugin_SDK import MediaServerProvider

from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry
from core.settings import config_manager
from core.tiered_logger import get_logger


def get_local_track_details(title: str, artist_name: str, isrc: Optional[str] = None, musicbrainz_id: Optional[str] = None) -> Tuple[bool, Optional[int]]:
    """Query the local database to check if a track exists, returning (exists, artist_id)."""
    try:
        from database.music_database import get_database, Track, Artist
        db = get_database()
        with db.session_scope() as session:
            track = None
            if musicbrainz_id:
                track = session.query(Track).filter(Track.musicbrainz_id == musicbrainz_id).first()
            if not track and isrc:
                track = session.query(Track).filter(Track.isrc == isrc).first()
            if not track and title and artist_name:
                track = session.query(Track).join(Artist).filter(
                    Track.title.ilike(title),
                    Artist.name.ilike(artist_name)
                ).first()
            if track:
                return True, track.artist_id
    except Exception:
        pass
    return False, None


class SearchAdapter:
    def aggregate_stream(
        self,
        query: str,
        plugin_ids: Optional[List[int]] = None,
        plugin_names: Optional[List[str]] = None,
        search_types: Optional[List[str]] = None
    ):
        """Aggregate search results from providers and yield them as chunks."""
        import queue
        import threading
        import asyncio
        from core.nexus_framework.plugin_loader import PluginRegistry, get_plugin_capabilities
        from core.nexus_framework.plugin_SDK import MediaServerProvider

        q = queue.Queue()

        async def async_worker():
            try:
                # 1. Local Database Query
                local_results = []
                try:
                    from database.music_database import get_database
                    db = get_database()
                    local_data = db.search_library(query)
                    for track in local_data.get("tracks", []):
                        local_results.append({
                            "id": f"local_track_{track['id']}",
                            "title": track["title"],
                            "artist": track["artist_name"],
                            "artist_id": track["artist_id"],
                            "album_id": track["album_id"],
                            "album": track["album_title"],
                            "duration": track.get("duration"),
                            "is_local": True,
                            "source": "local",
                            "type": "tracks",
                            "plugin": "library",
                            "metadata_quality_score": 100
                        })
                    for album in local_data.get("albums", []):
                        local_results.append({
                            "id": f"local_album_{album['id']}",
                            "title": album["title"],
                            "artist": album["artist_name"],
                            "artist_id": album["artist_id"],
                            "cover_art": album.get("cover_image_url"),
                            "is_local": True,
                            "source": "local",
                            "type": "albums",
                            "plugin": "library",
                            "metadata_quality_score": 100
                        })
                    for artist in local_data.get("artists", []):
                        local_results.append({
                            "id": f"local_artist_{artist['id']}",
                            "name": artist["name"],
                            "is_local": True,
                            "source": "local",
                            "type": "artists",
                            "plugin": "library",
                            "metadata_quality_score": 100
                        })
                except Exception as e:
                    get_logger("search_adapter").error(f"Local search failed: {e}")

                # Yield local results instantly
                q.put(("local", local_results))

                seen_items = set()
                for item in local_results:
                    isrc = item.get("isrc")
                    title = item.get("title") or item.get("name")
                    artist = item.get("artist") or ""
                    if isrc:
                        seen_items.add(isrc.lower())
                    elif title:
                        seen_items.add(f"{str(title).lower()}:{str(artist).lower()}")

                # 2. Discover external providers capable of search
                search_providers = []
                for plugin_id in PluginRegistry.list_plugins():
                    try:
                        provider = PluginRegistry.create_instance(plugin_id)
                        caps = get_plugin_capabilities(plugin_id)
                    except Exception:
                        continue
                    
                    search_cap_keys = ["tracks", "artists", "albums", "playlists"]
                    if not any(getattr(caps.search, k, False) for k in (search_types or ["tracks"]) if k in search_cap_keys):
                        continue
                    if plugin_ids and plugin_id not in plugin_ids:
                        continue
                    if plugin_names is not None:
                        prov_names_lower = [p.lower() for p in plugin_names]
                        if provider.name.lower() not in prov_names_lower:
                            continue
                    search_providers.append((provider, caps, plugin_id))

                async def query_provider(provider, caps, plugin_id):
                    try:
                        provider_results = []
                        for kind in (search_types or ["tracks"]):
                            search_cap_keys = {
                                "tracks": "tracks",
                                "artists": "artists",
                                "albums": "albums",
                                "playlists": "playlists",
                            }
                            if not getattr(caps.search, search_cap_keys[kind], False):
                                continue
                            
                            search_type_singular = kind[:-1] if kind.endswith("s") else kind
                            # run blocking search in thread
                            raw_items = await asyncio.to_thread(provider.search, query, type=search_type_singular, limit=10)
                            if not raw_items:
                                continue
                                
                            for item in raw_items:
                                if hasattr(item, 'to_dict'):
                                    item_dict = item.to_dict()
                                elif isinstance(item, dict):
                                    item_dict = dict(item)
                                else:
                                    continue
                                
                                item_dict["plugin_id"] = provider.plugin_id_int
                                item_dict["type"] = kind
                                item_dict["confidence"] = getattr(item_dict, "confidence", 1.0)
                                
                                if "title" not in item_dict and "name" in item_dict:
                                    item_dict["title"] = item_dict["name"]
                                if "artist" not in item_dict and "artist_name" in item_dict:
                                    item_dict["artist"] = item_dict["artist_name"]
                                    
                                is_local_provider = isinstance(provider, MediaServerProvider)
                                
                                title = item_dict.get("title") or "Unknown"
                                artist = item_dict.get("artist") or "Unknown"
                                isrc = item_dict.get("isrc") or item_dict.get("identifiers", {}).get("isrc")
                                mb_id = item_dict.get("musicbrainz_id") or item_dict.get("identifiers", {}).get("musicbrainz_recording_id")
                                
                                is_local_db, local_artist_id = get_local_track_details(title, artist, isrc, mb_id)
                                item_dict["is_local"] = is_local_db or is_local_provider
                                if local_artist_id:
                                    item_dict["artist_id"] = local_artist_id
                                    
                                item_dict["source"] = "local" if (is_local_provider or provider.name in ("local_metadata", "local_server")) else provider.name
                                
                                external_url = item_dict.get("external_url") or item_dict.get("url")
                                if not external_url:
                                    ext_urls = item_dict.get("external_urls", {})
                                    if isinstance(ext_urls, dict) and ext_urls:
                                        external_url = next(iter(ext_urls.values()), None)
                                    if not external_url:
                                        if mb_id:
                                            external_url = f"https://musicbrainz.org/recording/{mb_id}"
                                        else:
                                            spot_id = item_dict.get("identifiers", {}).get("spotify_id")
                                            if spot_id:
                                                external_url = f"https://open.spotify.com/track/{spot_id}"
                                item_dict["external_url"] = external_url
                                item_dict["metadata_quality_score"] = getattr(provider, "metadata_quality_score", 50)
                                
                                provider_results.append(item_dict)
                        
                        return provider.name, provider_results
                    except Exception as e:
                        get_logger("search_adapter").error(f"Search failed for {provider.name}: {e}")
                        return provider.name, []

                tasks = [query_provider(provider, caps, plugin_id) for provider, caps, plugin_id in search_providers]
                
                for task in asyncio.as_completed(tasks):
                    provider_name, items = await task
                    
                    # Deduplicate and sort chunk items
                    valid_items = []
                    for item in items:
                        isrc = item.get("isrc")
                        title = item.get("title") or item.get("name")
                        artist = item.get("artist") or ""
                        
                        match_key = None
                        if isrc:
                            match_key = isrc.lower()
                        elif title:
                            match_key = f"{str(title).lower()}:{str(artist).lower()}"
                            
                        if match_key:
                            if match_key in seen_items:
                                continue
                            seen_items.add(match_key)
                        
                        valid_items.append(item)
                    
                    # Sort chunk items by metadata_quality_score descending
                    valid_items.sort(key=lambda x: x.get("metadata_quality_score", 50), reverse=True)
                    
                    q.put((provider_name, valid_items))
            except Exception as e:
                get_logger("search_adapter").error(f"Error in aggregate_stream: {e}")
            finally:
                q.put(None)

        def thread_target():
            asyncio.run(async_worker())

        t = threading.Thread(target=thread_target)
        t.daemon = True
        t.start()

        try:
            while True:
                chunk = q.get()
                if chunk is None:
                    break
                yield chunk
        except GeneratorExit:
            return
        except Exception as e:
            get_logger("search_adapter").error(f"Error in aggregate_stream yield loop: {e}")

    def aggregate(
        self,
        query: str,
        plugin_ids: Optional[List[int]] = None,
        plugin_names: Optional[List[str]] = None,
        search_types: Optional[List[str]] = None
    ) -> List[Dict]:
        """Aggregate search results from providers that support search.* capabilities.

        Args:
            query (str): search query text
            plugin_ids (List[int], optional): explicit plugin IDs to include. Defaults to all search-capable plugins.
            plugin_names (List[str], optional): explicit plugin names to filter by.
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
            if plugin_names is not None:
                prov_names_lower = [p.lower() for p in plugin_names]
                if provider.name.lower() not in prov_names_lower:
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
                        is_local_provider = isinstance(provider, MediaServerProvider)
                        
                        # Database lookup for is_local and artist_id
                        title = item_dict.get("title") or "Unknown"
                        artist = item_dict.get("artist") or "Unknown"
                        isrc = item_dict.get("isrc") or item_dict.get("identifiers", {}).get("isrc")
                        mb_id = item_dict.get("musicbrainz_id") or item_dict.get("identifiers", {}).get("musicbrainz_recording_id")
                        
                        is_local_db, local_artist_id = get_local_track_details(title, artist, isrc, mb_id)
                        
                        item_dict["is_local"] = is_local_db or is_local_provider
                        if local_artist_id:
                            item_dict["artist_id"] = local_artist_id
                            
                        # Payload serialization enhancements
                        item_dict["source"] = "local" if (is_local_provider or provider.name in ("local_metadata", "local_server")) else provider.name
                        
                        external_url = item_dict.get("external_url") or item_dict.get("url")
                        if not external_url:
                            ext_urls = item_dict.get("external_urls", {})
                            if isinstance(ext_urls, dict) and ext_urls:
                                external_url = next(iter(ext_urls.values()), None)
                            if not external_url:
                                if mb_id:
                                    external_url = f"https://musicbrainz.org/recording/{mb_id}"
                                else:
                                    spot_id = item_dict.get("identifiers", {}).get("spotify_id")
                                    if spot_id:
                                        external_url = f"https://open.spotify.com/track/{spot_id}"
                        item_dict["external_url"] = external_url
                        
                        results.append(item_dict)
                except Exception as e:
                    get_logger("search_adapter").error(f"Search failed for {provider.name} ({kind}): {e}")

        return results

    async def federated_discovery(
        self,
        query: str,
        enabled_plugin_ids: Optional[List[int]] = None,
        enabled_plugins: Optional[List[str]] = None
    ) -> List[Dict]:
        """Async federated discovery utilizing all search providers."""
        
        search_providers = []
        for plugin_id in PluginRegistry.list_plugins():
            if enabled_plugin_ids is not None and plugin_id not in enabled_plugin_ids:
                continue
                
            try:
                provider = PluginRegistry.create_instance(plugin_id)
                if enabled_plugins is not None:
                    prov_names_lower = [p.lower() for p in enabled_plugins]
                    if provider.name.lower() not in prov_names_lower:
                        continue
                        
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
                    
                isrc = i_dict.get("isrc") or i_dict.get("identifiers", {}).get("isrc")
                title = i_dict.get("title") or i_dict.get("name") or "Unknown"
                artist = i_dict.get("artist") or i_dict.get("artist_name") or "Unknown"
                mb_id = i_dict.get("musicbrainz_id") or i_dict.get("identifiers", {}).get("musicbrainz_recording_id")
                
                match_key = None
                if isrc:
                    match_key = isrc
                else:
                    match_key = f"{str(title).lower()}:{str(artist).lower()}"
                    
                try:
                    from core.nexus_framework.plugin_loader import generate_plugin_id
                    prov_instance = PluginRegistry.create_instance(plugin_id)
                    
                    local_meta_id = generate_plugin_id('echosync.local_metadata')
                    local_server_id = generate_plugin_id('echosync.local_server')
                    is_local_provider = isinstance(prov_instance, MediaServerProvider) or plugin_id in [local_meta_id, local_server_id]
                    provider_name = prov_instance.name
                except Exception:
                    is_local_provider = False
                    provider_name = "unknown"
                    
                is_local_db, local_artist_id = get_local_track_details(title, artist, isrc, mb_id)
                is_local = is_local_db or is_local_provider
                
                source = "local" if (is_local_provider or provider_name in ("local_metadata", "local_server")) else provider_name
                
                external_url = i_dict.get("external_url") or i_dict.get("url")
                if not external_url:
                    ext_urls = i_dict.get("external_urls", {})
                    if isinstance(ext_urls, dict) and ext_urls:
                        external_url = next(iter(ext_urls.values()), None)
                    if not external_url:
                        if mb_id:
                            external_url = f"https://musicbrainz.org/recording/{mb_id}"
                        else:
                            spot_id = i_dict.get("identifiers", {}).get("spotify_id")
                            if spot_id:
                                external_url = f"https://open.spotify.com/track/{spot_id}"
                
                if match_key in dedup_map:
                    if plugin_id not in dedup_map[match_key]["sources"]:
                        dedup_map[match_key]["sources"].append(plugin_id)
                    if is_local:
                        dedup_map[match_key]["is_local"] = True
                        dedup_map[match_key]["ownership_state"] = "downloaded"
                    if local_artist_id:
                        dedup_map[match_key]["artist_id"] = local_artist_id
                else:
                    cover_art = i_dict.get("cover_art_url") or i_dict.get("cover") or ""
                    
                    entry = {
                        "id": str(i_dict.get("id", match_key)),
                        "title": title,
                        "artist": artist,
                        "sources": [plugin_id],
                        "ownership_state": "downloaded" if is_local else "missing",
                        "cover_art": cover_art,
                        "source": source,
                        "is_local": is_local,
                        "external_url": external_url,
                        "plugin": provider_name
                    }
                    if local_artist_id:
                        entry["artist_id"] = local_artist_id
                    dedup_map[match_key] = entry
                    
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
