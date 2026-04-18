# Architecture Overview: Core, Providers & Services

This document describes the high‑level architecture of the three primary
packages inside **Echosync**: the `core` engine, the `providers` plugin layer,
and the `services` background workers.  It also includes a short summary of
what each Python module is responsible for.

> Note: this is a living reference.  When you add or modify files, please
> update the appropriate section below so future contributors can quickly
> understand the layout.

---

## 1. Core package

The `core` directory contains the shared business logic and data model that
underpins the application.  Nothing in `core` has external dependencies except
for standard library modules, which makes it easy to write unit tests and
deploy headless services.  Key responsibilities include:

* Configuration (`settings.py`, `config_manager`)
* Plugin and provider loading (`plugin_loader.py`, `provider.py`)
* Content models and matching engine (`content_models.py`, `matching_engine/`)
* Job scheduling and asynchronous task handling (`job_queue.py`)
* Request handling logic used by providers (`request_manager.py`)
* Database migration updates (`database_update_worker.py`)
* Utility helpers (path mapping, rate limiting, security, etc.)

### Core files and their purpose

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker and minimal imports. |
| `auto_importer.py` | Logic invoked by scheduled job to scan for new tracks and auto‑import them. |
| `caching/` | Subpackage for cache helpers used by matching and request layers. |
| `consensus.py` | Algorithms for deduplicating or merging track metadata across sources. |
| `content_models.py` | Data classes representing tracks, albums, artists and change sets. |
| `database_update_worker.py` | Worker that applies database schema or data migrations on startup.  Recent updates add periodic scheduling yields and assume the SQLite engine uses WAL mode so long-running imports do not block the web UI. |
| `enums.py` | Shared enumeration types (e.g. capabilities, provider types). |
| `error_handler.py` | Flask error handler wrappers used by web routes. |
| `health_check.py` | Simple utilities for startup health verification and liveness probes. |
| `job_queue.py` | In‑process queue for scheduling and running asynchronous jobs. |
| `matching_engine/` | Subpackage containing the track matching algorithms. |
| `media_scan_manager.py` | Orchestrates periodic library scans from media server providers. |
| `models.py` | ORM or business objects shared across services. |
| `path_helper.py` | Path normalization/helpers for remote path mapping. |
| `path_mapper.py` | Utility to rewrite paths when importing or exporting between systems. |
| `personalized_playlists.py` | Generation of user‑specific playlists (auto‑curate). |
| `plugin_loader.py` | Discovers and loads provider and service plugins at runtime. |
| `post_processor.py` | Post‑sync tasks such as metadata cleanup or tagging. |
| `provider.py` | Core provider interfaces, base classes, and registry. |
| `provider_base.py` | Abstract base class that concrete providers inherit from. |
| `rate_limiter.py` | Simple token bucket/rate‑limiting helpers for remote API calls. |
| `request_manager.py` | HTTP client wrapper with retry, backoff, and rate‑limit support. |
| `security.py` | Encryption/password helpers, token generation, and request filtering. |
| `settings.py` | Configuration manager (reads JSON config, defaults). |
| `sync_history.py` | Maintains a journal of synchronization events for audit/resume. |
| `system_jobs.py` | Definitions for recurring housekeeping jobs (e.g. database cleanup). |
| `tiered_logger.py` | Logging utilities that allow per‑provider verbosity levels. |
| `track_parser.py` | Parses and normalizes track strings from file names/tags. |
| `watchlist_scanner.py` | Periodic scan of provider watchlists to trigger imports. |
| `web_scan_manager.py` | Legacy scanning logic used by the old web UI (deprecated). |
| `wishlist_service.py` | Handles user wishes/requests for missing tracks. |

> **TIP:** Most files in `core` are imported by other modules; if you
>’re looking to understand a particular flow (e.g. sync execution), start
> with `services/sync_service.py` and follow calls into `core`.  The `matching_engine`
> subpackage warrants its own architectural document (see `MATCHING_ENGINE.md`).

---

## 2. Total Freedom Plugin Architecture (Formerly "Providers")

The legacy concept of hardcoded "Providers" has been deprecated. EchoSync now utilizes the **Total Freedom Plugin Architecture**.

Instead of writing rigid adapter classes, developers now write Plugins that interact with the core application via a comprehensive **Hook System**. This allows plugins to not just provide data, but to alter, intercept, or completely hijack almost any application state or lifecycle event.

Plugins are dynamically loaded via `core.plugin_loader`.

### The Hook System

The architecture relies on three types of hooks dispatched through the central `core.hook_manager.HookManager`:

1. **Event Hooks (Read-Only)**
   - **Purpose:** To notify plugins that an action has occurred so they can react (e.g., logging, triggering an external webhook, updating a dashboard).
   - **Behavior:** The plugin receives data but cannot modify the core application's state or the data in transit.
   - **Example:** `ON_PLAYLIST_SAVED` fires after a playlist is written to the database.

2. **Mutator Hooks (Modify in Transit)**
   - **Purpose:** To allow plugins to alter data before the core engine processes it.
   - **Behavior:** The plugin receives a payload, modifies it, and returns the modified payload. The core engine then continues using the altered data.
   - **Example:** `BEFORE_FILE_RENAME` allows a plugin to change the destination path string before `shutil.move` is executed.

3. **Skip Hooks (Hijack/Bypass)**
   - **Purpose:** To allow a plugin to completely take over a core function.
   - **Behavior:** The core engine checks the hook's return value. If the plugin returns a specific payload (or a flag like `"SKIP"` / `"ABORT"`), the core engine immediately aborts its default logic and uses the plugin's result instead.
   - **Example:** `AUTHENTICATE_USER` allows an OIDC plugin to validate a user. If successful, the core SQLite password check is entirely bypassed.

> **RULE: Point, Don't Print:** Do not hardcode exact code blocks or variable signatures in documentation. To see exactly what payload a hook receives, search the codebase for `hook_manager.apply_filters('HOOK_NAME'` or reference `docs/HOOKS_REFERENCE.md`.

---

## 3. Services

Services run as background components that perform ongoing work on behalf of
the user.  They are registered with the job queue (see `core.job_queue`) and
are generally triggered either on a schedule or by events such as incoming
webhooks.

The `services/` folder contains the currently supported workers.  More may be
added as features expand.

| Service module | Purpose |
|----------------|---------|
| `auto_importer.py` | Scans configured libraries for new files and queues them for import. also call metadata enhancer to write the correct metadata to each tracl |
| `download_manager.py` | Manages downloads from downloader providers (e.g. Soulseek). |
| `library_hygiene.py` | Periodic cleaning/renaming of local media library files. sub service of media manager |
| `media_manager.py` | Orchestrates removal and upgrading of tracks based on user ratings and preferences. |
| `metadata_enhancer.py` | Queries external services (AcoustID, MusicBrainz) to enrich track metadata. |
| `sync_service.py` | Core sync engine that compares sources and transfers tracks. |

Services often call into `core` for shared logic (matching engine, path mapping,
etc) and may expose configuration options through provider settings.

---

## 4. File‑level outlines (short descriptions)

The lists above already provide quick summaries, but for completeness the
following *all* Python modules (excluding `__pycache__`) are briefly
explained:

```text
core/__init__.py                   # package init
core/auto_importer.py              # see table above
core/caching/                      # cache helpers
core/consensus.py                  # merging duplicate metadata
core/content_models.py             # track/album/artist data classes
core/database_update_worker.py     # migration worker
core/enums.py                      # shared enums
core/error_handler.py              # flask error wrappers
core/health_check.py               # liveness/ready probes
core/job_queue.py                  # job scheduling and execution
core/matching_engine/              # matching logic (see separate doc)
core/media_scan_manager.py         # manages remote library scans
core/models.py                     # business/ORM objects
core/path_helper.py                # path normalization utilities
core/path_mapper.py                # remote-to-local path mapping logic
core/personalized_playlists.py     # auto-generated playlists based on prefs
core/plugin_loader.py              # discover/load provider & service modules
core/post_processor.py             # post-sync cleanup/processing
core/provider.py                   # core provider interfaces & registry
core/provider_base.py              # abstract provider base class
core/rate_limiter.py               # simple rate limiting helper
core/request_manager.py            # HTTP client wrapper with retries
core/security.py                   # crypto utilities and sensitive filters
core/settings.py                   # configuration manager
core/sync_history.py               # journal of sync operations
core/system_jobs.py                # definitions for recurring tasks
core/tiered_logger.py              # logging helpers with levels per component
core/track_parser.py               # parses music filenames/tags
core/watchlist_scanner.py          # scans provider watchlists
core/web_scan_manager.py           # legacy web UI scan logic
core/wishlist_service.py           # wishlist management

providers/__init__.py              # provider package init
providers/acoustid/                # acoustid plugin
providers/jellyfin/                # jellyfin plugin
providers/listenbrainz/            # listenbrainz plugin
providers/lrclib/                  # lyrics lookup plugin
providers/musicbrainz/             # musicbrainz plugin
providers/navidrome/               # navidrome plugin
providers/plex/                    # plex plugin
providers/slskd/                   # soulseek/slskd plugin
providers/spotify/                 # spotify plugin
providers/tidal/                   # tidal plugin

services/auto_importer.py          # see above
services/download_manager.py       # see above
services/library_hygiene.py        # see above
services/media_manager.py          # see above
services/metadata_enhancer.py      # see above
services/sync_service.py           # see above
```

> The above table is generated manually; automatically scraping the tree is
> possible, but readability suffers.  Keep this section updated when files are
> added/removed.

---

## 5. Architectural notes

* **Separation of concerns** – `core` is dependency‑free and contains pure
  logic.  Providers are thin adapters that implement the `Provider` contract
  and optionally expose web routes.  Services orchestrate background workflows
  by gluing together `core` and `providers`.
* **Plugin loader** – on startup the application loads every subpackage under
  `providers/` and `services/` via `core.plugin_loader`.  New modules simply need
  to register themselves with the loader (usually via module‑level code).
* **Configuration** – stored in `config/config.json` and accessed through
  `core.settings.config_manager`.  Provider settings are namespaced by their
  slug and support arbitrary JSON, which allows custom data such as path
  mappings to be persisted.
* **Transport** – the backend provides a Flask‑based REST API (`web/routes/*`).
  The Svelte frontend interacts with this API exclusively; providers may
  extend the API with their own endpoints (e.g. scan/purge actions).
* **Lifecycle** – the `run_api.py` entrypoint bootstraps the Flask app and
  background threads; `services` and `core` components use `asyncio` and the
  built‑in job queue for concurrency.

---

## 6. Keeping docs current

Whenever you introduce a new file, provider, or service, please add a brief
line to this document describing its purpose.  Doing so will save new
contributors significant onboarding time.

The codebase is large and evolving; this document is intentionally high‑level.
For deep dives—especially on matching logic—see the other files in `docs/`
such as `MATCHING_ENGINE.md`.

---

*Last updated: February 23 2026*