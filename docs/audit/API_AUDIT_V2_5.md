# EchoSync v2.5.0 - External API Call Audit Matrix

## Executive Summary
This audit traces outbound network calls across the EchoSync v2.5.0 architecture, focusing on the newly decoupled Nexus Framework where external calls have moved to `plugins/`. It specifically evaluates our resilience to external rate limits (429 handling) and caching optimizations (the "Playlist Polling Problem").

## Global Architectural Analysis

### 1. The Playlist Polling Problem
**Diagnosis:** Across the board (Spotify, Tidal, Plex), playlist fetching is generally *not* utilizing `ETag`, `snapshot_id`, or `If-Modified-Since` headers to prevent redundant payload transfers. 
While `SpotifyClient` caches the full playlist (via `self.cache_manager.save_playlist`), it does so *after* fetching the full playlist using the generic Spotipy SDK. The `force_refresh` flag dictates whether we skip the network entirely based on a local cache miss/hit, but when a network call *is* made, the full playlist is downloaded instead of doing a lightweight `snapshot_id` or `ETag` check first.

### 2. Rate Limit Resilience (429 Too Many Requests)
**Diagnosis:** The new `core.request_manager.RequestManager` acts as a centralized throttling and retry mechanism.
* **Pro:** It automatically applies a `requests_per_second` sleep (token bucket style) via a threading lock.
* **Con:** When encountering a `429 Too Many Requests`, `RequestManager._should_retry` correctly identifies it and triggers `_backoff_sleep` (exponential backoff with jitter). However, **it completely ignores the `Retry-After` header** returned by the server. It blindly sleeps for a calculated backoff (e.g., `0.5 * 2^attempt`) instead of respecting the server's exact requested wait time.
* **Spotipy (Spotify):** `SpotifyClient` uses the external `spotipy` library for requests, which bypasses `RequestManager` entirely. `Spotipy` has its own retry logic but checking how strictly it respects `Retry-After` might be necessary, though standard `Spotipy` implementations typically do.

---

## Service Tracking Matrices

### Spotify
| File Path | Function / Method | Endpoint / Action | Polling/Caching Status | Justification |
| :--- | :--- | :--- | :--- | :--- |
| `plugins/spotify/client.py` | `get_playlist_tracks` | `self.sp.playlist_tracks` | Cached locally, but full payload downloaded on refresh | Syncs Spotify playlists. Does not use `snapshot_id` to prevent redundant downloads. |
| `plugins/spotify/client.py` | `get_user_playlists` | `self.sp.current_user_playlists` | Uncached generator | Fetches user playlists for UI and sync setup. |
| `plugins/spotify/client.py` | `search_by_isrc` | `self.sp.search` | Uncached | Matches local tracks to Spotify IDs using ISRC for synchronization. |
| `plugins/spotify/client.py` | `_raw_track`, `get_album`, `get_artist` | `self.sp.track`/`album`/`artist` | Cached (`@provider_cache`) | Fetches metadata for display and matching. |
| `plugins/spotify/client.py` | `create_playlist`, `add_tracks...` | `self.sp.user_playlist_create`, etc. | Uncached | Write operations for outbound sync. |

**Architectural Analysis:**
The Spotify plugin uses the `spotipy` library, bypassing `RequestManager`. The primary polling issue is in `get_playlist_tracks`. While Spotify provides a `snapshot_id` in the playlist object, we don't store or compare it before calling `playlist_tracks`. We just hit the API if `force_refresh=True` or the local cache expired.
**Actionable Solution:** Store the `snapshot_id` alongside the cached playlist. When checking for updates, fetch *only* the playlist metadata. If the `snapshot_id` matches our cached version, abort the track fetch.

### MusicBrainz
| File Path | Function / Method | Endpoint / Action | Polling/Caching Status | Justification |
| :--- | :--- | :--- | :--- | :--- |
| `plugins/musicbrainz/client.py` | `_fetch_artist_track_dicts` | `GET /ws/2/recording` | Cached (`@provider_cache`) | Fetches tracklists for artists. |
| `plugins/musicbrainz/client.py` | `search` | `GET /ws/2/recording` | Uncached (relies on RateLimitConfig) | Discovers metadata for track matching. |

**Architectural Analysis:**
MusicBrainz heavily throttles to 1 request/second, properly configured via `RequestManager`. It relies strictly on local caching (`@provider_cache`) rather than ETags.
**Actionable Solution:** Ensure `RequestManager` parses the `Retry-After` header if we hit the limit, rather than blindly retrying, as MusicBrainz issues strict bans for ignoring 429s.

### Tidal
| File Path | Function / Method | Endpoint / Action | Polling/Caching Status | Justification |
| :--- | :--- | :--- | :--- | :--- |
| `plugins/tidal/api_v2.py` | `get_user_playlists` | `GET /my-collection/playlists` | Uncached pagination | Fetches user playlists. |
| `plugins/tidal/api_v2.py` | `get_playlist_tracks` | `GET /playlists/{id}/relationships/items`| Uncached | Syncs Tidal playlists. |
| `plugins/tidal/client.py` | Various | Uses `api_v2.py` or `RequestManager` | Partially cached | Translates to Echosync objects. |

**Architectural Analysis:**
Tidal API calls in `api_v2.py` use raw `requests.get` without passing through the rate-limited `RequestManager`, creating a massive vulnerability for 429 bans when syncing large playlists.
**Actionable Solution:** Refactor `api_v2.py` to accept and use the `self._http` (`RequestManager`) instance initialized in `TidalClient`, ensuring global rate limits and retries apply to V2 API calls. Use ETags for playlist tracks if the Tidal API supports it.

### ListenBrainz
| File Path | Function / Method | Endpoint / Action | Polling/Caching Status | Justification |
| :--- | :--- | :--- | :--- | :--- |
| `plugins/listenbrainz/client.py` | Various | HTTP via `RequestManager` | Uses `RequestManager` | Scrobbling / Listening history sync. |

**Architectural Analysis:**
Standard implementation using `RequestManager` with 2 RPS. No specific playlist polling vulnerabilities identified as ListenBrainz is primarily an append-only time-series API (scrobbling).

### Plex / Jellyfin
| File Path | Function / Method | Endpoint / Action | Polling/Caching Status | Justification |
| :--- | :--- | :--- | :--- | :--- |
| `plugins/plex/client.py` | `get_playlist_tracks` | `self.server.playlist().items()` | Uncached (uses PlexAPI SDK) | Fetches local media server playlists. |
| `plugins/jellyfin/client.py`| `get_playlist_tracks` | `GET /Playlists/{id}/Items` | Uncached | Fetches local media server playlists. |

**Architectural Analysis:**
Both use server SDKs or direct requests. Since these are usually local network calls, rate limiting is less critical, but redundant data transfer is high for large playlists.
**Actionable Solution:** Both Plex and Jellyfin provide update timestamps/hashes for playlists. Cache the playlist state and compare `updatedAt` before requesting the full items list.

### AcoustID
| File Path | Function / Method | Endpoint / Action | Polling/Caching Status | Justification |
| :--- | :--- | :--- | :--- | :--- |
| `plugins/acoustid/client.py` | `submit_fingerprint` | `POST /v2/submit` (implied via SDK) | Auto-submit disabled by default | Submits newly discovered audio fingerprints to the community database. |
| `plugins/acoustid/client.py` | `lookup` | `GET /v2/lookup` | Local SQLite Fast-Path, then Network | Audio fingerprint identification. |

**Architectural Analysis:**
AcoustID auto-submission is correctly gated behind an `auto_contribute` flag. Lookups use a "Local-First" SQLite fast-path before hitting the network, which is excellent for rate limiting. However, when it does hit the network, it should respect 429s.

### LRCLIB
| File Path | Function / Method | Endpoint / Action | Polling/Caching Status | Justification |
| :--- | :--- | :--- | :--- | :--- |
| `plugins/lrclib/client.py` | `create_lrc_file` | `get_lyrics` (via lrclib SDK) | Local `.lrc` sidecar | Fetches synchronized lyrics. |

**Architectural Analysis:**
LRClib uses an external SDK (`from lrclib import LrcLibAPI`). It smartly avoids network calls if the `.lrc` file already exists locally. If it doesn't, it attempts a direct fetch, falling back to a search. Rate limits depend entirely on the external SDK's implementation.

### Slskd (Soulseek)
| File Path | Function / Method | Endpoint / Action | Polling/Caching Status | Justification |
| :--- | :--- | :--- | :--- | :--- |
| `plugins/slskd/client.py` | `_async_get_download_status` | `GET /api/v0/transfers/downloads` | Uncached / Aggressively polled | Checks progress of pending Soulseek downloads. |

**Architectural Analysis:**
The `get_download_status` function fetches *all* downloads for a specific username (`GET transfers/downloads`) and filters them locally. If called frequently in a loop for multiple files, this leads to massive redundant JSON payloads and CPU usage.
**Actionable Solution:** The status checker should either use a global state cache that updates periodically (so multiple track checks don't spam the API), or utilize a more specific endpoint if Slskd provides one. Also, `RequestManager` must be used strictly here to prevent self-DDOSing the local Slskd daemon.
