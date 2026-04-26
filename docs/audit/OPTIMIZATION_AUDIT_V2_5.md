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
