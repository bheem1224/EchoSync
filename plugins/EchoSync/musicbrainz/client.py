from typing import List, Optional, Dict, Any
import re

from core.caching.plugin_cache import plugin_cache
from core.nexus_framework.plugin_SDK import PluginBase
from core.nexus_framework.plugin_SDK import (
    ProviderCapabilities,
    PlaylistSupport,
    SearchCapabilities,
    MetadataRichness
)
from core.request_manager import RateLimitConfig
import asyncio
import hashlib
from rapidfuzz import fuzz

from core.matching_engine.echo_sync_track import EchosyncTrack
from .models import PluginMusicbrainzCache
from core.nexus_framework.plugin_SDK import sdk
from core.tiered_logger import get_logger

def _safe_getattr(obj: Any, attr: str, default: Any = None) -> Any:
    """AST-compliant alternative to getattr()."""
    if hasattr(obj, attr):
        try:
            return obj.__getattribute__(attr)
        except AttributeError:
            return default
    return default

logger = get_logger("provider.musicbrainz")


class MusicBrainzClient(PluginBase):
    """Dedicated metadata provider used by discovery and enrichment flows."""

    name = "EchoSync.musicbrainz"
    supports_isrc_lookup = True
    service_type = "metadata"
    capabilities = ProviderCapabilities(
        name="EchoSync.musicbrainz",
        supports_playlists=PlaylistSupport.NONE,
        search=SearchCapabilities(tracks=True, artists=True, albums=True, playlists=False),
        metadata=MetadataRichness.HIGH,
        supports_cover_art=True,
        supports_lyrics=False,
        supports_user_auth=True,
        supports_library_scan=False,
        supports_streaming=False,
        supports_downloads=False,
        supports_metadata_fetch=True,
        supports_batching=True,
    )

    def __init__(self):
        super().__init__()
        self.http.rate = RateLimitConfig(requests_per_second=1.0)
        self.http._session.headers.update(
            {
                "User-Agent": "Echosync/0.1.0 ( https://github.com/echosync/echosync )",
                "Accept": "application/json",
            }
        )
        self.api_base = self.config.get("api_base_url") or "https://musicbrainz.org/ws/2"
        self._search_queue = []
        self._batch_task = None
        self._lock = asyncio.Lock()

    @plugin_cache(ttl_seconds=2592000)
    def _fetch_artist_track_dicts(self, artist_name: str) -> List[Dict[str, Any]]:
        """Cached paginated recording fetch returning JSON-serialisable dicts.

        Separating the API calls from EchosyncTrack construction keeps the
        plugin_cache round-trip (JSON → SQLite → JSON) lossless.  Called
        exclusively by get_artist_tracks.
        """
        artist_name = str(artist_name or "").strip()
        if not artist_name:
            return []

        raw: List[Dict[str, Any]] = []
        offset = 0
        limit = 100
        max_records = 500

        try:
            while len(raw) < max_records:
                if re.fullmatch(r"[0-9a-fA-F-]{36}", artist_name):
                    query = f'arid:{artist_name}'
                else:
                    query = f'artist:"{artist_name}"'
                response = self.http.get(
                    f"{self.api_base}/recording",
                    params={
                        "fmt": "json",
                        "query": query,
                        "limit": limit,
                        "offset": offset,
                    },
                )

                if response.status_code != 200:
                    logger.warning(
                        "MusicBrainz get_artist_tracks failed for '%s' (status=%s)",
                        artist_name,
                        response.status_code,
                    )
                    break

                payload = response.json() or {}
                recordings = payload.get("recordings", []) or []
                if not recordings:
                    break

                for recording in recordings:
                    title = str(recording.get("title") or "").strip()
                    if not title:
                        continue

                    artist_credit = recording.get("artist-credit") or []
                    provider_artist = ""
                    for entry in artist_credit:
                        if isinstance(entry, dict):
                            provider_artist += str(entry.get("name") or "")
                            provider_artist += str(entry.get("joinphrase") or "")
                    provider_artist = provider_artist.strip() or artist_name

                    releases = recording.get("releases") or []
                    album_title = ""
                    release_year = None
                    if releases:
                        first_release = releases[0] or {}
                        album_title = str(first_release.get("title") or "")
                        date_value = str(first_release.get("date") or "")
                        if len(date_value) >= 4 and date_value[:4].isdigit():
                            release_year = int(date_value[:4])

                    recording_mbid = str(recording.get("id") or "").strip() or None
                    isrc = None
                    isrc_list = recording.get("isrcs") or []
                    if isrc_list:
                        isrc = str(isrc_list[0] or "").strip() or None

                    raw.append({
                        "title": title,
                        "artist": provider_artist,
                        "album": album_title or "Unknown Album",
                        "mbid": recording_mbid,
                        "isrc": isrc,
                        "year": release_year,
                    })
                    if len(raw) >= max_records:
                        break

                if len(recordings) < limit:
                    break
                offset += limit

        except Exception as exc:
            logger.error(
                "Failed to fetch artist tracks for '%s': %s", artist_name, exc, exc_info=True
            )

        # Deduplicate by artist+title to keep discovery diff deterministic.
        deduped: Dict[str, Dict[str, Any]] = {}
        for d in raw:
            key = f"{d['artist']}|{d['title']}"
            if key not in deduped:
                deduped[key] = d
        return list(deduped.values())

    def get_artist_tracks(self, artist_name: str) -> List[EchosyncTrack]:
        """Fetch a full-ish artist tracklist from MusicBrainz recordings search.

        The discovery engine uses EchosyncTrack.sync_id to diff these results
        against local libraries, so tracks must be created through the standard
        factory path to ensure deterministic IDs.
        """
        tracks: List[EchosyncTrack] = []
        for d in self._fetch_artist_track_dicts(artist_name):
            track_obj = self.create_echo_sync_track(
                title=d["title"],
                artist=d["artist"],
                album=d["album"],
                musicbrainz_id=d["mbid"],
                isrc=d["isrc"],
                year=d["year"],
                provider_id=d["mbid"],
                source=self.name,
            )
            if track_obj:
                tracks.append(track_obj)
        return tracks

    @plugin_cache(ttl_seconds=604800)
    def search_metadata(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Compatibility search API used by metadata_enhancer fallback logic.

        Returns lightweight recording dictionaries so the enhancer can run
        weighted matching and then call get_metadata() on the winning MBID.
        """
        query = str(query or "").strip()
        if not query:
            return []

        safe_limit = max(1, min(int(limit or 10), 100))
        try:
            response = self.http.get(
                f"{self.api_base}/recording",
                params={
                    "fmt": "json",
                    "query": query,
                    "limit": safe_limit,
                },
            )
            if response.status_code != 200:
                logger.warning(
                    "MusicBrainz search_metadata failed (status=%s, query=%s)",
                    response.status_code,
                    query,
                )
                return []

            payload = response.json() or {}
            recordings = payload.get("recordings", []) or []
            results: List[Dict[str, Any]] = []

            for recording in recordings:
                mbid = str(recording.get("id") or "").strip()
                if not mbid:
                    continue

                artist_credit = recording.get("artist-credit") or []
                artist_parts: List[str] = []
                for entry in artist_credit:
                    if isinstance(entry, dict):
                        artist_parts.append(str(entry.get("name") or ""))
                        artist_parts.append(str(entry.get("joinphrase") or ""))
                artist_name = "".join(artist_parts).strip()

                releases = recording.get("releases") or []
                album_title = ""
                if releases:
                    album_title = str((releases[0] or {}).get("title") or "").strip()

                isrc_values = recording.get("isrcs") or []
                duration_ms = recording.get("length")
                try:
                    duration_ms = int(duration_ms) if duration_ms is not None else None
                except Exception:
                    duration_ms = None

                results.append(
                    {
                        "title": str(recording.get("title") or "").strip(),
                        "artist": artist_name,
                        "album": album_title,
                        "duration": duration_ms,
                        "isrc": str(isrc_values[0]).strip() if isrc_values else None,
                        "mbid": mbid,
                    }
                )

            return results
        except Exception as exc:
            logger.warning(f"MusicBrainz search_metadata exception for '{query}': {exc}")
            return []


    def _escape_lucene(self, text: str) -> str:
        """Escape special characters for strict Lucene queries."""
        if not text:
            return ""
        # The characters to escape in Lucene: + - & || ! ( ) { } [ ] ^ " ~ * ? : \ /
        import re
        escaped = re.sub(r'([+\-&|!(){}\[\]^"~*?:\\/])', r'\\\1', text)
        return escaped

    async def search_recording_strict(self, artist: str, title: str, immediate: bool = False) -> List[EchosyncTrack]:
        if not artist or not title:
            return []

        # 1. Check Cache
        lookup_str = f"{artist}||{title}".lower()
        lookup_hash = hashlib.sha256(lookup_str.encode('utf-8')).hexdigest()

        with self.sdk.db.get_plugin_session() as session:
            cached = session.query(PluginMusicbrainzCache).filter_by(lookup_hash=lookup_hash).first()
            if cached:
                # Convert back to EchosyncTrack objects
                try:
                    metadata_list = cached.metadata_json
                    return [EchosyncTrack(**m) for m in metadata_list]
                except Exception as e:
                    logger.warning(f"Failed to parse cached MusicBrainz data: {e}")

        # 2. Immediate Bypass
        if immediate:
            safe_artist = self._escape_lucene(artist)
            safe_title = self._escape_lucene(title)
            query = f'artist:"{safe_artist}" AND recording:"{safe_title}"'
            try:
                loop = asyncio.get_running_loop()
                import functools
                get_func = functools.partial(
                    self.http.get,
                    f"{self.api_base}/recording",
                    params={
                        "fmt": "json",
                        "query": query,
                        "inc": "releases+artists",
                        "limit": 3,
                    }
                )
                response = await loop.run_in_executor(None, get_func)

                if response.status_code != 200:
                    logger.warning(
                        "MusicBrainz immediate search failed (status=%s, query=%s)",
                        response.status_code,
                        query,
                    )
                    return []

                payload = response.json() or {}
                recordings = payload.get("recordings", []) or []
                results = []

                for recording in recordings:
                    rec_title = str(recording.get("title") or "").strip()
                    if not rec_title:
                        continue

                    # Extract artist
                    artist_credit = recording.get("artist-credit") or []
                    artist_parts = []
                    for entry in artist_credit:
                        if isinstance(entry, dict) and "artist" in entry:
                            artist_parts.append(str(entry.get("name") or ""))
                            artist_parts.append(str(entry.get("joinphrase") or ""))
                    rec_artist = "".join(artist_parts).strip()

                    mbid = str(recording.get("id"))
                    releases = recording.get("releases") or []
                    first_release = releases[0] if releases else {}
                    album = str(first_release.get("title") or "Unknown Album")

                    duration_ms = None
                    dur = recording.get("length")
                    if dur and str(dur).isdigit():
                        duration_ms = int(dur)

                    track = self.create_echo_sync_track(
                        title=rec_title,
                        artist=rec_artist or "Unknown Artist",
                        album=album,
                        musicbrainz_id=mbid,
                        duration_ms=duration_ms,
                        provider_id=mbid,
                        source=self.name,
                    )

                    isrcs = recording.get("isrcs") or []
                    if isrcs:
                        track.isrc = str(isrcs[0])

                    results.append(track)
                    if len(results) >= 3:
                        break

                # Cache successful results
                if results:
                    try:
                        with self.sdk.db.get_plugin_session() as session:
                            if not session.query(PluginMusicbrainzCache).filter_by(lookup_hash=lookup_hash).first():
                                metadata_json = [t.model_dump() for t in results]
                                cached_entry = PluginMusicbrainzCache(
                                    id=lookup_hash,
                                    lookup_hash=lookup_hash,
                                    mbid=results[0].musicbrainz_id,
                                    metadata_json=metadata_json
                                )
                                session.add(cached_entry)
                    except Exception as e:
                        logger.error(f"Failed to cache immediate MusicBrainz result: {e}")

                return results

            except Exception as e:
                logger.error(f"Exception during immediate MusicBrainz search: {e}")
                return []

        # 3. Queue for Micro-batching
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        async with self._lock:
            self._search_queue.append((artist, title, lookup_hash, future))
            if self._batch_task is None or self._batch_task.done():
                self._batch_task = asyncio.create_task(self._process_batch())

        # 4. Await batched result
        try:
            return await future
        except Exception as e:
            logger.error(f"Error awaiting batched result: {e}")
            return []

    async def _process_batch(self):
        await asyncio.sleep(0.1)  # 100ms debounce

        async with self._lock:
            if not self._search_queue:
                return
            batch = self._search_queue[:]
            self._search_queue.clear()

        # Construct Lucene OR query
        query_parts = []
        for artist, title, _, _ in batch:
            safe_artist = self._escape_lucene(artist)
            safe_title = self._escape_lucene(title)
            query_parts.append(f'(artist:"{safe_artist}" AND recording:"{safe_title}")')

        full_query = " OR ".join(query_parts)

        # Max items per page is 100
        try:
            # We run the synchronous http.get in an executor to avoid blocking the event loop
            loop = asyncio.get_running_loop()
            import functools
            get_func = functools.partial(
                self.http.get,
                f"{self.api_base}/recording",
                params={
                    "fmt": "json",
                    "query": full_query,
                    "inc": "releases+artists",
                    "limit": len(batch) * 3, # up to 3 per request
                }
            )
            response = await loop.run_in_executor(None, get_func)

            if response.status_code != 200:
                logger.warning(f"MusicBrainz batch search failed (status={response.status_code})")
                for _, _, _, future in batch:
                    if not future.done():
                        future.set_result([])
                return

            payload = response.json() or {}
            recordings = payload.get("recordings", []) or []

            # Map results to original queries
            for artist, title, lookup_hash, future in batch:
                best_matches = []
                for recording in recordings:
                    rec_title = str(recording.get("title") or "").strip()
                    if not rec_title:
                        continue

                    # Extract artist
                    artist_credit = recording.get("artist-credit") or []
                    artist_parts = []
                    for entry in artist_credit:
                        if isinstance(entry, dict) and "artist" in entry:
                            artist_parts.append(str(entry.get("name") or ""))
                            artist_parts.append(str(entry.get("joinphrase") or ""))
                    rec_artist = "".join(artist_parts).strip()

                    # Simple matching
                    title_score = fuzz.ratio(title.lower(), rec_title.lower())
                    artist_score = fuzz.ratio(artist.lower(), rec_artist.lower())

                    if title_score > 80 and artist_score > 80:
                        mbid = str(recording.get("id"))
                        releases = recording.get("releases") or []
                        first_release = releases[0] if releases else {}
                        album = str(first_release.get("title") or "Unknown Album")

                        duration_ms = None
                        dur = recording.get("length")
                        if dur and str(dur).isdigit():
                            duration_ms = int(dur)

                        track = self.create_echo_sync_track(
                            title=rec_title,
                            artist=rec_artist or "Unknown Artist",
                            album=album,
                            musicbrainz_id=mbid,
                            duration_ms=duration_ms,
                            provider_id=mbid,
                            source=self.name,
                        )

                        isrcs = recording.get("isrcs") or []
                        if isrcs:
                            track.isrc = str(isrcs[0])

                        best_matches.append(track)
                        if len(best_matches) >= 3:
                            break

                # Resolve future
                if not future.done():
                    future.set_result(best_matches)

                # Cache successful results
                if best_matches:
                    try:
                        with self.sdk.db.get_plugin_session() as session:
                            # Avoid duplicates
                            if not session.query(PluginMusicbrainzCache).filter_by(lookup_hash=lookup_hash).first():
                                metadata_json = [t.model_dump() for t in best_matches]
                                cached_entry = PluginMusicbrainzCache(
                                    id=lookup_hash,
                                    lookup_hash=lookup_hash,
                                    mbid=best_matches[0].musicbrainz_id,
                                    metadata_json=metadata_json
                                )
                                session.add(cached_entry)
                    except Exception as e:
                        logger.error(f"Failed to cache MusicBrainz batch result: {e}")

        except Exception as e:
            logger.error(f"Exception during MusicBrainz batch processing: {e}")
            for _, _, _, future in batch:
                if not future.done():
                    future.set_result([])

    def search_by_isrc(self, isrc: str) -> Optional[EchosyncTrack]:
        """Implement PluginBase.search_by_isrc via the MusicBrainz ISRC endpoint."""
        isrc = str(isrc or "").strip().upper()
        if not isrc:
            return None
        try:
            response = self.http.get(
                f"{self.api_base}/isrc/{isrc}",
                params={"fmt": "json", "inc": "artists+releases"},
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json() or {}
            recordings = data.get("recordings") or []
            if not recordings:
                return None

            recording = recordings[0]
            artist_credit = recording.get("artist-credit") or []
            artist_parts: List[str] = []
            for entry in artist_credit:
                if isinstance(entry, dict) and "artist" in entry:
                    artist_parts.append(str(entry.get("name") or ""))
                    artist_parts.append(str(entry.get("joinphrase") or ""))
            artist_str = "".join(artist_parts).strip() or ""

            releases = recording.get("releases") or []
            first_release = releases[0] if releases else {}
            release_date = str(first_release.get("date") or "")
            release_year = int(release_date[:4]) if len(release_date) >= 4 and release_date[:4].isdigit() else None

            duration_ms = recording.get("length")
            try:
                duration_ms = int(duration_ms) if duration_ms is not None else None
            except (TypeError, ValueError):
                duration_ms = None

            return self.create_echo_sync_track(
                title=str(recording.get("title") or ""),
                artist=artist_str,
                album=str(first_release.get("title") or "") or None,
                musicbrainz_id=str(recording.get("id") or "") or None,
                isrc=isrc,
                year=release_year,
                duration_ms=duration_ms,
                source=self.name,
            )
        except Exception as exc:
            logger.warning("MusicBrainz search_by_isrc(%s) failed: %s", isrc, exc)
            return None

    def get_metadata(self, mbid: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed metadata for a recording MBID."""
        mbid = str(mbid or "").strip()
        if not mbid:
            return None

        try:
            response = self.http.get(
                f"{self.api_base}/recording/{mbid}",
                params={"fmt": "json", "inc": "artists+releases+isrcs+media"},
            )
            if response.status_code != 200:
                return None

            data = response.json() or {}
            result = {
                "title": data.get("title"),
                "recording_id": data.get("id"),
                "artist": "",
                "artist_id": "",
                "album": "",
                "release_id": "",
                "date": "",
                "track_number": None,
                "disc_number": None,
                "cover_art_url": None,
                "isrc": None,
            }

            credits = data.get("artist-credit") or []
            if credits:
                name_parts = []
                for credit in credits:
                    if isinstance(credit, dict):
                        name_parts.append(str(credit.get("name") or ""))
                        name_parts.append(str(credit.get("joinphrase") or ""))
                result["artist"] = "".join(name_parts).strip()
                if isinstance(credits[0], dict) and isinstance(credits[0].get("artist"), dict):
                    result["artist_id"] = credits[0]["artist"].get("id") or ""

            releases = data.get("releases") or []
            if releases:
                release = releases[0] or {}
                result["album"] = release.get("title") or ""
                result["release_id"] = release.get("id") or ""
                result["date"] = release.get("date") or ""
            isrcs = data.get("isrcs") or []
            if isrcs:
                result["isrc"] = isrcs[0]

            return result

        except Exception as exc:
            logger.error(f"Failed to fetch metadata for {mbid}: {exc}")
            return None

    def get_metadata_batch(self, mbids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch full metadata for multiple recording MBIDs in batches up to 50."""
        mbids = [str(m).strip() for m in mbids if str(m).strip()]
        if not mbids:
            return {}
            
        results = {}
        # Max limit for search API is 100, we'll chunk by 50 to be safe
        chunk_size = 50
        for i in range(0, len(mbids), chunk_size):
            chunk = mbids[i:i+chunk_size]
            query_parts = [f"reid:{mbid}" for mbid in chunk]
            full_query = " OR ".join(query_parts)
            
            try:
                response = self.http.get(
                    f"{self.api_base}/recording",
                    params={
                        "fmt": "json",
                        "query": full_query,
                        "inc": "artists+releases+isrcs+media",
                        "limit": len(chunk)
                    }
                )
                if response.status_code != 200:
                    logger.warning(f"Batch metadata fetch failed: {response.status_code}")
                    continue
                    
                data = response.json() or {}
                for recording in data.get("recordings", []) or []:
                    rec_id = str(recording.get("id") or "").strip()
                    if not rec_id or rec_id not in chunk:
                        continue
                        
                    result = {
                        "title": recording.get("title"),
                        "recording_id": rec_id,
                        "artist": "",
                        "artist_id": "",
                        "album": "",
                        "release_id": "",
                        "date": "",
                        "track_number": None,
                        "disc_number": None,
                        "cover_art_url": None,
                        "isrc": None,
                    }

                    credits = recording.get("artist-credit") or []
                    if credits:
                        name_parts = []
                        for credit in credits:
                            if isinstance(credit, dict):
                                name_parts.append(str(credit.get("name") or ""))
                                name_parts.append(str(credit.get("joinphrase") or ""))
                        result["artist"] = "".join(name_parts).strip()
                        if isinstance(credits[0], dict) and isinstance(credits[0].get("artist"), dict):
                            result["artist_id"] = credits[0]["artist"].get("id") or ""

                    releases = recording.get("releases") or []
                    if releases:
                        release = releases[0] or {}
                        result["album"] = release.get("title") or ""
                        result["release_id"] = release.get("id") or ""
                        result["date"] = release.get("date") or ""
                    isrcs = recording.get("isrcs") or []
                    if isrcs:
                        result["isrc"] = isrcs[0]

                    results[rec_id] = result
            except Exception as exc:
                logger.error(f"Failed to fetch batch metadata: {exc}")
                
        return results

    @plugin_cache(ttl_seconds=2592000)
    def get_release(self, release_id: str) -> Optional[Dict[str, Any]]:
        """Fetch full release data for the album memory cache in MetadataEnhancerService.

        Returns a dict with:
          - ``album``: release title
          - ``cover_art_url``: front cover URL from the Cover Art Archive (or None)
          - ``tracks``: list of track dicts, each carrying title, artist,
            track_number, disc_number, recording_id, release_id, isrc,
            duration_ms, date, cover_art_url

        Called at most once per release per 30-day cache window, eliminating
        N−1 redundant AcoustID / MusicBrainz calls when an entire album lands
        in the download directory at once.
        """
        release_id = str(release_id or "").strip()
        if not release_id:
            return None

        try:
            response = self.http.get(
                f"{self.api_base}/release/{release_id}",
                params={"fmt": "json", "inc": "recordings+artist-credits"},
            )
            if response.status_code != 200:
                return None

            data = response.json() or {}
            album_title = str(data.get("title") or "").strip()
            release_date = str(data.get("date") or "").strip()
            cover_art_url = None

            tracks: List[Dict[str, Any]] = []
            for medium in data.get("media", []) or []:
                disc_number = int(medium.get("position") or 1)
                for track_entry in medium.get("tracks", []) or []:
                    recording = track_entry.get("recording") or {}
                    raw_pos = track_entry.get("number") or track_entry.get("position")
                    try:
                        track_number: Optional[int] = int(
                            str(raw_pos).split("/")[0].strip()
                        )
                    except (TypeError, ValueError):
                        track_number = None

                    artist_credit = recording.get("artist-credit") or []
                    artist_parts: List[str] = []
                    for entry in artist_credit:
                        if isinstance(entry, dict):
                            artist_parts.append(str(entry.get("name") or ""))
                            artist_parts.append(str(entry.get("joinphrase") or ""))
                    artist_str = "".join(artist_parts).strip()
                    if not artist_str:
                        for entry in data.get("artist-credit", []) or []:
                            if isinstance(entry, dict):
                                artist_str += str(entry.get("name") or "")
                                artist_str += str(entry.get("joinphrase") or "")
                        artist_str = artist_str.strip()

                    recording_id = str(recording.get("id") or "").strip() or None
                    title = str(
                        recording.get("title") or track_entry.get("title") or ""
                    ).strip()
                    duration_ms = recording.get("length")
                    try:
                        duration_ms = int(duration_ms) if duration_ms is not None else None
                    except (TypeError, ValueError):
                        duration_ms = None

                    isrc_list = recording.get("isrcs") or []
                    isrc = str(isrc_list[0]).strip() if isrc_list else None

                    tracks.append({
                        "title": title,
                        "artist": artist_str,
                        "album": album_title,
                        "track_number": track_number,
                        "disc_number": disc_number,
                        "recording_id": recording_id,
                        "release_id": release_id,
                        "isrc": isrc,
                        "duration_ms": duration_ms,
                        "date": release_date,
                        "cover_art_url": cover_art_url,
                    })

            return {"album": album_title, "cover_art_url": cover_art_url, "tracks": tracks}
        except Exception as exc:
            logger.warning("MusicBrainzClient.get_release(%s) failed: %s", release_id, exc)
            return None

    def _get_cover_art(self, release_id: str) -> Optional[str]:  # noqa: ARG002
        # Cover art is sourced from the media server (Plex/Jellyfin) during library
        # sync. We never query coverartarchive.org so that the enhancer stays fast
        # and does not consume bandwidth on redirected image HEAD requests.
        return None

    # PluginBase abstract methods
    def authenticate(self, **kwargs) -> bool:
        return True

    def search(
        self,
        query: str,
        type: str = "track",
        limit: int = 10,
        quality_profile: Optional[Dict[str, Any]] = None,
    ) -> List[EchosyncTrack]:
        if type != "track":
            return []
        return self.get_artist_tracks(query)[:limit]

    def get_track(self, track_id: str) -> Optional[EchosyncTrack]:
        metadata = self.get_metadata(track_id)
        if not metadata:
            return None
        return self.create_echo_sync_track(
            title=metadata.get("title") or "",
            artist=metadata.get("artist") or "",
            album=metadata.get("album") or "Unknown Album",
            musicbrainz_id=metadata.get("recording_id"),
            isrc=metadata.get("isrc"),
            provider_id=metadata.get("recording_id"),
            source=self.name,
        )

    def get_album(self, album_id: str) -> Optional[Dict[str, Any]]:
        return None

    def get_artist(self, artist_id: str) -> Optional[Dict[str, Any]]:
        tracks = self.get_artist_tracks(artist_id)
        return {"id": artist_id, "tracks": tracks}

    def get_user_playlists(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return []

    def get_playlist_tracks(self, playlist_id: str) -> List[EchosyncTrack]:
        return []

    def get_active_access_token(self, account_id: Optional[int] = None) -> Optional[str]:
        """Return a decrypted access token for the first (or specified) authenticated account.

        Returns None when no authenticated account is available, which means the
        client falls back to anonymous / read-only API access.
        """
        try:
            accounts = self.accounts.get_all()
            if not accounts:
                return None

            if account_id is not None:
                target = next((a for a in accounts if a.get("id") == account_id), None)
            else:
                # Prefer active + authenticated, fall back to first authenticated
                target = next(
                    (a for a in accounts if a.get("is_authenticated") and a.get("is_active")),
                    next((a for a in accounts if a.get("is_authenticated")), None),
                )

            if not target:
                return None

            return self.accounts.get_token(target.get("id"))

            # get_account_token in StorageService handles database access safely
            token_row = storage.get_account_token(target["id"])
            if not token_row:
                return None

            if token_row and token_row.get("access_token"):
                # StorageService.get_account_token should return decrypted token
                return token_row["access_token"]
            return None
        except Exception as e:
            logger.debug(f"Could not load MusicBrainz access token: {e}")
            return None

    def submit_isrc(self, mbid: str, isrc: str, account_id: Optional[int] = None) -> bool:
        """Submit an ISRC–recording association to MusicBrainz.

        Requires the user to have authenticated with the ``submit_isrc`` scope.
        Returns True on success, False otherwise.

        Args:
            mbid: MusicBrainz recording MBID (UUID).
            isrc: ISRC code to associate with the recording (e.g. "USRC17607839").
            account_id: Specific account ID to use; defaults to the active authenticated account.
        """
        mbid = str(mbid or "").strip()
        isrc = str(isrc or "").strip()
        if not mbid or not isrc:
            logger.warning("submit_isrc called with empty mbid or isrc")
            return False

        # Opt-in check: only submit if auto_contribute is enabled in settings
        try:
            from core.nexus_framework.plugin_SDK import sdk
            auto_contribute = sdk.config.get('auto_contribute')
            if not (auto_contribute == "true" or auto_contribute is True):
                logger.debug("Skipping MusicBrainz ISRC submission: auto_contribute is disabled")
                return False
        except Exception as e:
            logger.debug(f"Could not verify MusicBrainz auto_contribute flag: {e}")
            return False

        access_token = self.get_active_access_token(account_id)
        if not access_token:
            logger.warning("MusicBrainz submit_isrc: no authenticated account available")
            return False

        xml_body = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<metadata xmlns="http://musicbrainz.org/ns/mmd-2.0#">'
            f'<recording id="{mbid}">'
            '<isrc-list><isrc id="' + isrc + '"/></isrc-list>'
            '</recording>'
            '</metadata>'
        )
        try:
            resp = self.http.post(
                f"{self.api_base}/recording/{mbid}",
                params={"client": "Echosync-0.1.0-https://github.com/echosync/echosync"},
                data=xml_body,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/xml; charset=UTF-8",
                },
            )
            if resp.status_code in (200, 204):
                logger.info(f"ISRC {isrc} submitted for MBID {mbid}")
                return True
            logger.warning(f"MusicBrainz ISRC submission returned {resp.status_code}: {resp.text[:200]}")
            return False
        except Exception as e:
            logger.error(f"MusicBrainz submit_isrc failed: {e}")
            return False

    def is_configured(self) -> bool:
        return True

    def get_logo_url(self) -> str:
        return "https://musicbrainz.org/static/images/entity/musicbrainz_logo.svg"


# Backward compatibility alias for older imports.
MusicBrainzProvider = MusicBrainzClient

# Ensure plugin loader/runtime registry can resolve this provider class.

