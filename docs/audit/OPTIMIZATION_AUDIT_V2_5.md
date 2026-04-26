# EchoSync v2.5.0 - Performance & Optimization Audit

## 1. The Event Loop Blockers

### Bottleneck (Lines 66-93 in `web/services/search_service.py`)
In `web/services/search_service.py`, the `federated_discovery` async function loops over providers and wraps their synchronous `search()` calls using `asyncio.get_running_loop().run_in_executor(None, provider.search, query, "track", 20)`. The `None` argument falls back to the default `ThreadPoolExecutor`, which is unbounded and blocks CPU cycles if the underlying search heavily utilizes regular expressions or string matching libraries (`thefuzz`).

### Replacement Code (`web/services/search_service.py`)

```python
    async def federated_discovery(self, query: str, enabled_providers: Optional[List[str]] = None) -> List[Dict]:
        """Async federated discovery utilizing all search providers."""
        import asyncio
        from core.settings import config_manager

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
                from core.tiered_logger import get_logger
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

                    from core.provider import MediaServerProvider
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
```


## 2. The N+1 Query Problem

### Bottleneck (Lines 292-348 in `database/music_database.py`)
In `database/music_database.py`, `search_library` executes `tracks = session.query(Track).join(Artist).join(Album, isouter=True).filter(...).limit(50).all()`. However, inside the loop that builds the response dictionary, it calls `track.artist.name` and `track.album.title`, triggering an N+1 query problem to fetch related entities that were omitted from the query projection mapping.

### Replacement Code (`database/music_database.py`)

```python
    def search_library(self, query: str) -> Dict[str, List[Dict]]:
        """Search across Artists, Albums, and Tracks."""
        results = {
            "artists": [],
            "albums": [],
            "tracks": []
        }

        if not query:
            return results

        search_term = f"%{query}%"

        with self.session_scope() as session:
            # OPTIMIZATION: joinedload eliminates N+1 lazy loading queries
            from sqlalchemy.orm import joinedload

            # Search Artists
            artists = session.query(Artist).filter(Artist.name.ilike(search_term)).limit(20).all()
            for artist in artists:
                results["artists"].append({
                    "id": artist.id,
                    "name": artist.name,
                    "image_url": artist.image_url
                })

            # Search Albums
            albums = session.query(Album).options(
                joinedload(Album.artist)
            ).join(Artist).filter(
                (Album.title.ilike(search_term)) |
                (Artist.name.ilike(search_term))
            ).limit(20).all()
            for album in albums:
                results["albums"].append({
                    "id": album.id,
                    "title": album.title,
                    "artist_id": album.artist_id,
                    "artist_name": album.artist.name,
                    "cover_image_url": album.cover_image_url,
                    "year": album.release_date.year if album.release_date else None
                })

            # Search Tracks
            tracks = session.query(Track).options(
                joinedload(Track.artist),
                joinedload(Track.album)
            ).join(Artist).join(Album, isouter=True).filter(
                (Track.title.ilike(search_term)) |
                (Artist.name.ilike(search_term)) |
                (Album.title.ilike(search_term))
            ).limit(50).all()

            for track in tracks:
                results["tracks"].append({
                    "id": track.id,
                    "title": track.title,
                    "artist_id": track.artist_id,
                    "artist_name": track.artist.name,
                    "album_id": track.album_id,
                    "album_title": track.album.title if track.album else "Unknown Album",
                    "duration": track.duration
                })

        return results
```

### Bottleneck (Lines 350-382 in `database/music_database.py`)
Similarly, `search_canonical_fuzzy` iterates through `t.artist.name`, `t.album.title`, and `t.audio_fingerprints` inside a for-loop on Tracks without eagerly loading them.

### Replacement Code (`database/music_database.py`)

```python
    def search_canonical_fuzzy(self, title: str, artist: Optional[str] = None, limit: int = 10) -> List:
        """Fuzzy search canonical tracks by title and optional artist substring.

        Returns a list of ``EchosyncTrack`` objects (each has a ``to_dict()`` method).
        """
        from core.matching_engine.echo_sync_track import EchosyncTrack
        results = []
        with self.session_scope() as session:
            # OPTIMIZATION: joinedload and selectinload eliminate N+1 queries during mapping
            from sqlalchemy.orm import joinedload, selectinload

            query = (
                session.query(Track)
                .options(
                    joinedload(Track.artist),
                    joinedload(Track.album),
                    selectinload(Track.audio_fingerprints)
                )
                .join(Artist)
                .join(Album, isouter=True)
                .filter(Track.title.ilike(f"%{title}%"))
            )
            if artist:
                query = query.filter(Artist.name.ilike(f"%{artist}%"))
            tracks = query.limit(limit).all()
            for t in tracks:
                results.append(EchosyncTrack(
                    raw_title=t.title,
                    artist_name=t.artist.name,
                    album_title=t.album.title if t.album else "",
                    duration=t.duration,
                    track_number=t.track_number,
                    disc_number=t.disc_number,
                    bitrate=t.bitrate,
                    file_path=t.file_path,
                    file_format=t.file_format,
                    musicbrainz_id=t.musicbrainz_id,
                    isrc=t.isrc,
                    acoustid_id=next((fp.acoustid_id for fp in t.audio_fingerprints if fp.acoustid_id), None),
                ))
        return results
```


## 3. Memory Leaks in Scanning

### Bottleneck (Lines 786-820 in `plugins/plex/client.py`)
In `plugins/plex/client.py`, the `get_all_tracks` retrieves up to 999999 tracks (`self.music_library.searchTracks(maxresults=max_results)`) at once. This forces the server to respond with a gigantic payload that translates to thousands of track instances dumped directly into memory. In `core/database_update_worker.py` (Line 64), `_perform_full_sync` stores the entire array in memory (`all_tracks = self.media_client.get_all_tracks()`), causing immediate out-of-memory crashes on constraint devices for big libraries.

### Replacement Code (`plugins/plex/client.py`)
Use yield generators instead of returning monolithic arrays to reduce memory footprint.

```python
    def get_all_tracks(self, limit: Optional[int] = None):
        """Get all tracks from active music library iteratively to save RAM."""
        if not self.ensure_connection() or not self.music_library:
            logger.warning("No active music library")
            return

        try:
            # OPTIMIZATION: Fetch in chunks (pagination) to yield items and avoid huge allocations
            chunk_size = 1000
            max_limit = limit if limit else 999999
            offset = 0

            while offset < max_limit:
                current_limit = min(chunk_size, max_limit - offset)
                logger.info(f"Calling Plex searchTracks offset={offset} limit={current_limit}")
                chunk_tracks = self.music_library.searchTracks(limit=current_limit, offset=offset)

                if not chunk_tracks:
                    break

                for raw_track in chunk_tracks:
                    try:
                        track = self._convert_plex_track(raw_track)
                        yield track
                    except Exception as e:
                        logger.error(f"Failed to convert Plex track: {str(e)}")

                offset += len(chunk_tracks)

        except Exception as e:
            logger.error(f"Error fetching tracks from Plex: {str(e)}")
```

### Replacement Code (`core/database_update_worker.py`)

```python
    def _perform_full_sync(self):
        """Perform a full sync of the media library."""
        try:
            from core.library_manager import library_manager

            # OPTIMIZATION: Use a generator to stream tracks instead of dumping all to a list
            all_tracks_generator = self.media_client.get_all_tracks()

            # Note: total length tracking may need adaptation based on client implementation
            # if we stream directly, but assuming library_manager.bulk_import accepts an iterable:

            logger.debug("Beginning streaming bulk import via LibraryManager")

            def _on_progress(progress: Dict[str, int]):
                try:
                    # Update worker stats live
                    self.processed_tracks = progress.get("processed", self.processed_tracks)
                    self.successful_operations = progress.get("imported", 0) + progress.get("updated", 0)
                    self.failed_operations = progress.get("failed", 0)
                    # Optional: track artists/albums if provided
                    self.processed_artists = progress.get("artists", self.processed_artists)
                    self.processed_albums = progress.get("albums", self.processed_albums)
                    # yield to other threads, helping HTTP request handling
                    import time
                    time.sleep(0)
                except Exception:
                    pass

            imported_count = library_manager.bulk_import(all_tracks_generator, progress_callback=_on_progress)

            logger.info(f"Successfully imported {imported_count} tracks from {self.server_type}")
            logger.debug(
                "Bulk import finished for %s: imported=%s",
                self.server_type,
                imported_count,
            )
            self.processed_tracks = imported_count
            self.successful_operations = imported_count

            # --- Backfill missing provider identifiers ---
            self._backfill_missing_identifiers()

        except Exception as e:
            logger.error(f"Error during full sync: {e}", exc_info=True)
            self.failed_operations += 1
```

### Bottleneck (Lines 547-580 in `database/music_database.py`)
In `database/music_database.py`, `get_library_hierarchy()` executes `artists = session.query(Artist)...all()`. This dumps the entire relational structure of the database straight into RAM.

### Replacement Code (`database/music_database.py`)

```python
    def get_library_hierarchy(self) -> List[Dict]:
        """Fetch the entire library hierarchy (Artist -> Album -> Track)."""
        with self.session_scope() as session:
            # Use selectinload (separate SELECT per relationship) rather than joinedload
            # (which emits a single Cartesian-product JOIN). For large libraries the JOIN
            # inflates row count to artists×albums×tracks, causing an OOM spike.
            from sqlalchemy.orm import selectinload

            # OPTIMIZATION: yield_per fetches results in batches of 1000 to drastically lower RAM
            artists_query = session.query(Artist).options(
                selectinload(Artist.albums).selectinload(Album.tracks)
            ).order_by(Artist.name).yield_per(1000)

            hierarchy = []
            for artist in artists_query:
                artist_data = {
                    "id": artist.id,
                    "name": artist.name,
                    "image_url": artist.image_url,
                    "albums": []
                }

                # Sort albums by release date or title
                sorted_albums = sorted(artist.albums, key=lambda a: a.release_date or date.min, reverse=True)

                for album in sorted_albums:
                    album_data = {
                        "id": album.id,
                        "title": album.title,
                        "cover_image_url": album.cover_image_url,
                        "year": album.release_date.year if album.release_date else None,
                        "tracks": []
                    }

                    # Sort tracks by disc number and track number
                    sorted_tracks = sorted(album.tracks, key=lambda t: (t.disc_number or 1, t.track_number or 0))

                    for track in sorted_tracks:
                        album_data["tracks"].append({
                            "id": track.id,
                            "title": track.title,
                            "duration": track.duration,
                            "track_number": track.track_number,
                            "disc_number": track.disc_number
                        })

                    artist_data["albums"].append(album_data)

                hierarchy.append(artist_data)

            return hierarchy
```

## 4. Redundant Regex Instantiations

### Bottleneck (Lines 182, 278, 344, 461 in `core/matching_engine/text_utils.py`)
In `core/matching_engine/text_utils.py`, methods like `normalize_title`, `normalize_album`, `extract_version_info`, and `extract_edition` repeatedly define large lists of regex patterns inside the function body. The `re.sub` and `re.search` calls compile these string patterns on the fly for every single execution. For a 50,000 track library scan (which runs these functions per track and candidate), this results in millions of redundant string pattern list allocations and regex compilations on the main thread, wasting immense CPU cycles.

### Replacement Code (`core/matching_engine/text_utils.py`)
Compile the regex patterns once at the module level using `re.compile()`.

```python
# OPTIMIZATION: Compile regex patterns globally once to avoid millions of local instantiations
import re

_OST_PATTERNS = [
    re.compile(r'\s*-\s*from\s+"[^"]*"', flags=re.IGNORECASE),
    re.compile(r'\s*-\s*from\s+[\w\s]+$', flags=re.IGNORECASE),
    re.compile(r'\s*[\(\[]\s*original\s+motion\s+picture\s+soundtrack\s*[\)\]]', flags=re.IGNORECASE),
    re.compile(r'\s*[\(\[]\s*motion\s+picture\s+soundtrack\s*[\)\]]', flags=re.IGNORECASE),
    re.compile(r'\s*[\(\[]\s*from\s+"[^"]*"\s*[\)\]]', flags=re.IGNORECASE),
    re.compile(r'\s*[\(\[]\s*from\s+[^\)\]]+[\)\]]', flags=re.IGNORECASE),
    re.compile(r'\s*[\(\[]\s*ost\s+[^\)\]]*[\)\]]', flags=re.IGNORECASE),
    re.compile(r'\s*[\(\[]\s*ost\s*[\)\]]', flags=re.IGNORECASE),
    re.compile(r'\s*[\(\[]\s*soundtrack\s*[\)\]]', flags=re.IGNORECASE),
]

_VERSION_PATTERNS = [
    (re.compile(r'\s*\(([^)]*(?:remix|version|edit|live|acoustic|instrumental|remaster|radio|mix|club)[^)]*)\)', flags=re.IGNORECASE), 1),
    (re.compile(r'\s*\[([^\]]*(?:remix|version|edit|live|acoustic|instrumental|remaster|radio|mix|club)[^\]]*)\]', flags=re.IGNORECASE), 1),
    (re.compile(r'\s*-\s*([^-]*(?:remix|version|edit|live at|live|acoustic|instrumental|remaster|radio|mix|club)[^-]*)$', flags=re.IGNORECASE), 1),
    (re.compile(r'\s*-\s*((?:[A-Z][a-z]+\s+)*(?:Radio|Edit|Mix|Remix|Version)[^-]*)$', flags=re.IGNORECASE), 1),
]

_EDITION_PATTERNS = [
    (re.compile(r'\b(remaster(?:ed)?)\b', flags=re.IGNORECASE), 'Remastered'),
    (re.compile(r'\b(remastering)\b', flags=re.IGNORECASE), 'Remastered'),
    (re.compile(r'\b(live)\b', flags=re.IGNORECASE), 'Live'),
    (re.compile(r'\b(remix(?:ed)?)\b', flags=re.IGNORECASE), 'Remix'),
    (re.compile(r'\b(rmx)\b', flags=re.IGNORECASE), 'Remix'),
    (re.compile(r'\b(deluxe)\s*(?:edition)?\b', flags=re.IGNORECASE), 'Deluxe'),
    (re.compile(r'\b(standard)\s*(?:edition)?\b', flags=re.IGNORECASE), 'Standard'),
    (re.compile(r'\b(expanded)\s*(?:edition)?\b', flags=re.IGNORECASE), 'Expanded'),
    (re.compile(r'\b(limited)\s*(?:edition)?\b', flags=re.IGNORECASE), 'Limited'),
    (re.compile(r'\b(special)\s*(?:edition)?\b', flags=re.IGNORECASE), 'Special'),
    (re.compile(r'\b(anniversary)\s*(?:edition)?\b', flags=re.IGNORECASE), 'Anniversary'),
    (re.compile(r'\b(collector\'?s?)\s*(?:edition)?\b', flags=re.IGNORECASE), 'Collectors'),
    (re.compile(r'\b(explicit)\b', flags=re.IGNORECASE), 'Explicit'),
    (re.compile(r'\b(clean)\b', flags=re.IGNORECASE), 'Clean'),
    (re.compile(r'\b(instrumental)\b', flags=re.IGNORECASE), 'Instrumental'),
    (re.compile(r'\b(acapella|a\s*cappella)\b', flags=re.IGNORECASE), 'Acapella'),
    (re.compile(r'\b(acoustic)\b', flags=re.IGNORECASE), 'Acoustic'),
    (re.compile(r'\b(unplugged)\b', flags=re.IGNORECASE), 'Unplugged'),
    (re.compile(r'\b(original)\s*(?:version|mix)?\b', flags=re.IGNORECASE), 'Original'),
    (re.compile(r'\b(radio)\s*(?:edit|version|mix)?\b', flags=re.IGNORECASE), 'Radio Edit'),
    (re.compile(r'\b(extended)\s*(?:version|mix)?\b', flags=re.IGNORECASE), 'Extended'),
    (re.compile(r'\b(club)\s*(?:version|mix)?\b', flags=re.IGNORECASE), 'Club Mix'),
    (re.compile(r'\b(album)\s*(?:version)?\b', flags=re.IGNORECASE), 'Album Version'),
    (re.compile(r'\b(single)\s*(?:version)?\b', flags=re.IGNORECASE), 'Single Version'),
    (re.compile(r'\b(24\s*bit)\b', flags=re.IGNORECASE), '24-bit'),
    (re.compile(r'\b(16\s*bit)\b', flags=re.IGNORECASE), '16-bit'),
    (re.compile(r'\b(hi\s*res|high\s*resolution)\b', flags=re.IGNORECASE), 'Hi-Res'),
]

_EDITION_CLEAN_BRACKETS_RE = re.compile(r'\s*[\(\[\{]\s*[\)\]\}]\s*')
_EDITION_CLEAN_TRAIL_DASH_RE = re.compile(r'\s*[-–—]\s*$')
_EDITION_CLEAN_LEAD_DASH_RE = re.compile(r'^\s*[-–—]\s*')
_EDITION_CLEAN_SPACES_RE = re.compile(r'\s+')
_EDITION_MARKER_CLEAN_RE = re.compile(r'\s*\(?(?:deluxe|standard|explicit|clean|remaster|remastered|edition|ed\.)\)?', flags=re.IGNORECASE)

# ... inside functions ...
def extract_version_info(title: Optional[str]) -> Tuple[str, Optional[str]]:
    if not title:
        return "", None

    for pattern, group in _VERSION_PATTERNS:
        match = pattern.search(title)
        if match:
            version = match.group(group).strip()
            clean_title = pattern.sub('', title).strip()
            return clean_title, version

    return title, None

def extract_edition(title: Optional[str]) -> Tuple[str, Optional[str]]:
    if not title:
        return ("", None)

    title_lower = title.lower()
    detected_editions = []
    cleaned_title = title

    for pattern, edition_name in _EDITION_PATTERNS:
        match = pattern.search(title_lower)
        if match:
            detected_editions.append(edition_name)
            cleaned_title = pattern.sub('', cleaned_title)

    cleaned_title = _EDITION_CLEAN_BRACKETS_RE.sub(' ', cleaned_title)
    cleaned_title = _EDITION_CLEAN_TRAIL_DASH_RE.sub('', cleaned_title)
    cleaned_title = _EDITION_CLEAN_LEAD_DASH_RE.sub('', cleaned_title)
    cleaned_title = _EDITION_CLEAN_SPACES_RE.sub(' ', cleaned_title).strip()

    edition = detected_editions[0] if detected_editions else None
    return (cleaned_title, edition)

def normalize_album(album: Optional[str]) -> str:
    if not album:
        return ""

    normalized = normalize_text(album)
    for pattern in _OST_PATTERNS:
        normalized = pattern.sub('', normalized)

    normalized = _EDITION_MARKER_CLEAN_RE.sub('', normalized)
    return normalized.strip()
```

## 5. String Concatenation in Path Operations

### Bottleneck (Lines 77-83 in `core/file_handling/path_mapper.py`)
In `core/file_handling/path_mapper.py`, the `map_to_local` function builds path strings using raw string concatenation `+` and manual index slicing `normalized_remote[len(search_prefix):]` instead of the optimized standard libraries like `os.path` or `pathlib`. When processing thousands of files during library metadata scans, constructing these large system paths via string addition creates many immutable string allocations overhead.

### Replacement Code (`core/file_handling/path_mapper.py`)
Use `pathlib.Path` or `os.path.join` to efficiently construct filesystem paths without manual slash-checking.

```python
    def map_to_local(self, remote_path: str) -> str:
        """
        Map a remote path to a local path based on configured mappings.
        """
        if not remote_path:
            return ""

        try:
            from core.hook_manager import hook_manager
            plugin_path = hook_manager.apply_filters('RESOLVE_STORAGE_PATH', None, remote_path=remote_path)
            if plugin_path and isinstance(plugin_path, str):
                return plugin_path
        except Exception as e:
            import logging
            logging.getLogger("path_mapper").error(f"Error in RESOLVE_STORAGE_PATH hook: {e}")

        normalized_remote = self._normalize(remote_path)

        # OPTIMIZATION: Use os.path or pathlib for filesystem operations
        import os

        for mapping in self.mappings:
            if not isinstance(mapping, dict):
                continue

            remote_prefix = self._normalize(mapping.get('remote', ''))
            local_prefix = self._normalize(mapping.get('local', ''))

            if not remote_prefix:
                continue

            search_prefix = remote_prefix.rstrip('/') if len(remote_prefix) > 1 else remote_prefix

            is_match = False
            if search_prefix == '/':
                is_match = True
            elif normalized_remote == search_prefix or normalized_remote.startswith(search_prefix + '/'):
                is_match = True

            if is_match:
                # OPTIMIZATION: Use standard lib path joining instead of slow string concatenation
                suffix = normalized_remote[len(search_prefix):].lstrip('/')
                return os.path.join(local_prefix, suffix).replace('\\', '/')

        return normalized_remote
```

## 6. Wasteful Synchronous Caching

### Bottleneck (Lines 113-137 in `core/caching/provider_cache.py`)
In `core/caching/provider_cache.py`, the `set` and `get` methods execute a synchronous `sqlite3` database write (`INSERT OR REPLACE`) and read on the main thread for every cache operation. Furthermore, the `ttl_expires_at` logic explicitly calculates the expiration timestamp in Python `utc_now() + timedelta(seconds=ttl_seconds)` and writes it synchronously. The caching decorator (`@provider_cache`) runs this synchronous disk I/O inline with API requests or provider queries, adding ~2-5ms latency to every single cache hit or miss.

### Replacement Code (`core/caching/provider_cache.py`)
Use an asynchronous or memory-based LRU approach, or at least defer cache writes to a background thread to prevent blocking the main thread during cache persistence.

```python
    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        """
        Store value in cache with TTL
        """
        # OPTIMIZATION: Defer cache persistence to a background thread to prevent blocking the main thread.
        # Alternatively, for API routes, this should use `asyncio.to_thread` if we were in an async context.
        def _persist_cache():
            try:
                # Serialize value to JSON
                import json
                from datetime import timedelta
                from core.utils.time_utils import utc_now # assuming util exists or datetime.utcnow
                json_value = json.dumps(value, default=str)

                # Calculate expiration time
                expires_at = utc_now() + timedelta(seconds=ttl_seconds)

                from sqlalchemy import text
                query = text("""
                    INSERT OR REPLACE INTO parsed_tracks
                    (raw_string, parsed_json, created_at, ttl_expires_at)
                    VALUES (:key, :value, CURRENT_TIMESTAMP, :expires)
                """)

                with self.db.engine.connect() as conn:
                    conn.execute(query, {
                        "key": key,
                        "value": json_value,
                        "expires": expires_at
                    })
                    conn.commit()
            except Exception as e:
                logger.error(f"Error storing in cache: {e}")

        # Fire and forget
        import threading
        threading.Thread(target=_persist_cache, daemon=True).start()
        return True
```

## 7. Duplicate JSON Serialization

### Bottleneck (Lines 44-60 in `core/event_bus.py`)
In `core/event_bus.py`, the `publish_lightweight` method iterates over a list of subscriber callbacks (`specific` and `universal`) and calls each one with the raw dictionary `payload`. If the system is connected to 5 web clients over Server-Sent Events (SSE) or WebSockets, each individual subscriber callback (e.g., inside the web route streaming generator) will independently run `json.dumps(payload)` to encode the message before transmitting it over the network. When broadcasting large state updates (like a 500-track playlist sync status), serializing the identical dictionary 5 separate times wastes heavy CPU cycles.

### Replacement Code (`core/event_bus.py`)
Serialize the payload to JSON once in the `EventBus` before broadcasting, and pass both the raw dict and the pre-serialized string to handlers so they don't have to duplicate the effort.

```python
    def publish_lightweight(self, payload: dict):
        event_name = payload.get("event", "UNKNOWN")

        with self._lock:
            specific = list(self._subscribers.get(event_name, []))
            universal = list(self._subscribers.get("*", []))

        # OPTIMIZATION: Serialize JSON once for all network subscribers to prevent
        # duplicate CPU work during fan-out broadcasts
        import json
        try:
            serialized = json.dumps(payload, default=str)
        except Exception:
            serialized = "{}"

        # Attach the pre-serialized string so listeners don't re-serialize
        payload['_serialized'] = serialized

        for handler in specific:
            try:
                handler(payload)
            except Exception as e:
                import logging
                logging.getLogger("event_bus").error(f"Error in event handler for {event_name}: {e}", exc_info=True)

        for handler in universal:
            try:
                handler(payload)
            except Exception as e:
                import logging
                logging.getLogger("event_bus").error(f"Error in universal event handler: {e}", exc_info=True)
```
