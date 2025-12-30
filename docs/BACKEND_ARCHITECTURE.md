# Backend Architecture & Layout

## Overview
SoulSync is structured with two main layers:
1. **Core**: Essential business logic (config, database, job queue, matching engine).
2. **Providers & Plugins**: Modular service connectors (Spotify, Plex, custom providers).

Each major component exposes a wrapper/API layer so the frontend (Svelte) can interact via HTTP without direct client access.

---

## Directory Structure

### Core Components
```
core/
├── __init__.py
├── config_manager.py          (config storage, database access)
├── database_update_worker.py  (async DB workers)
├── health_check.py            (service health)
├── job_queue.py               (async job scheduling)
├── matching_engine.py         (music matching logic)
├── models.py                  (Track, Album, Playlist data models)
├── provider_base.py           (base class for all providers)
├── provider_capabilities.py   (capability declarations)
├── provider_registry.py       (plugin/provider registration)
├── ... (other core modules)
```

**API Wrappers for Core:**
```
web/routes/
├── system.py          (health, status, settings, logs)
├── tracks.py          (canonical track CRUD)
├── library.py         (library management)
```

`web/services/` can hold shared utilities (e.g., SearchAdapter, SyncAdapter) that orchestrate core + provider logic.

---

### Bundled Providers (Official)
```
providers/
├── __init__.py
├── spotify/
│   ├── __init__.py
│   ├── client.py      (SpotifyClient: core logic)
│   └── adapter.py     (HTTP routes for settings, playlists, etc.)
├── plex/
│   ├── __init__.py
│   ├── client.py      (PlexClient: core logic)
│   └── adapter.py
├── jellyfin/
│   ├── __init__.py
│   ├── client.py
│   └── adapter.py
├── navidrome/
├── soulseek/
└── tidal/
```

**Removal Model:**
Users can simply delete unused providers (e.g., `rm -rf providers/tidal/`) with no code changes. The registry auto-discovers what's installed; deleted providers are silently skipped. No broken references.

---

### Plugins (Community Developed)
```
plugins/
├── __init__.py
├── plugin_system.py           (plugin lifecycle, auto-discovery)
├── adapter_registry.py        (load external adapters)
├── provider_adapter.py        (plugin interface, inherits from core.provider_base)
├── service_registry.py        (dynamic service discovery)
└── my_custom_provider/        (community plugin example)
    ├── __init__.py
    ├── client.py              (custom logic: inherits from provider_base)
    └── adapter.py             (optional: HTTP routes if custom endpoints needed)
```

**Plugin Deployment Model:**
When a user develops a new plugin, they provide:
1. `my_plugin/client.py` - the logic (inherits from core.provider_base).
2. `my_plugin/adapter.py` - HTTP routes (optional, only if exposing custom endpoints).

User drops these into plugins/, system auto-discovers on startup. Two files, done. Can also delete by removing the folder.

---

### API Layer (Flask)
```
web/
├── api_app.py                 (Flask app factory, blueprint registration)
├── routes/
│   ├── __init__.py
│   ├── providers.py           (GET /api/providers, /<id>/settings, POST settings)
│   ├── jobs.py                (GET /api/jobs, /jobs/active)
│   ├── tracks.py              (CRUD for canonical tracks)
│   ├── search.py              (unified search across providers)
│   ├── playlists.py           (sync/manage playlists)
│   ├── sync.py                (sync options/status)
│   ├── system.py              (health, status, settings, logs)
│   └── library.py             (library scan/manage)
├── services/
│   ├── provider_registry.py   (orchestrate provider clients)
│   ├── search_service.py      (aggregate search logic)
│   ├── sync_service.py        (playlist sync orchestration)
│   └── ... (other adapters)
└── schemas/ (optional)
    └── (validation schemas)
```

---

## Request Flow Example

**Svelte Frontend → Flask API → Core/Providers:**

1. User clicks "Save Spotify Settings" in Svelte UI.
2. POST /api/providers/spotify/settings { client_id, client_secret }
3. Flask route (providers.py) receives, validates, calls config_manager.set_service_credentials('spotify', {...})
4. config_manager persists to config.db and config.json.
5. Response: { success: true, settings: {...} }
6. Svelte store updates UI.

---

## Unified Provider/Plugin Model

**Providers and Plugins are architecturally identical:**
- Each has `client.py` (logic) and `adapter.py` (HTTP wrapper).
- Both discovered by the same registry (`core/provider_registry.py`).
- Only difference: bundled/official (providers/) vs. community (plugins/).

**Adding/Removing Providers or Plugins:**

*Add (Plugin):*
1. Create `plugins/my_provider/client.py` (inherits from `core.provider_base.py`).
2. Optionally add `plugins/my_provider/adapter.py` for custom HTTP routes.
3. Drop folder into `plugins/`.
4. System auto-discovers on startup; immediately available.

*Remove (Bundled or Plugin):*
1. Delete the provider/plugin folder (e.g., `rm -rf providers/tidal/`).
2. Restart the app.
3. No code changes, no broken references. System skips deleted providers/plugins.

**Registry Behavior:**
- `core/provider_registry.py` scans `providers/` and `plugins/` on startup.
- Only installed providers/plugins are registered and exposed via `/api/providers`.
- Deleted providers/plugins are silently ignored (no errors).

---

## Config & Database

**Location:** `config/` (mounted volume in Docker)
- `config.json` - settings (credentials, preferences)
- `config.db` - runtime state (job history, cache)

**Access:** `core/config_manager.py` (or `config/settings.py` if refactored)
- Provides get/set interface for settings.
- Persists to both JSON (user-facing) and DB (runtime).

Future: Consider consolidating into `core/config/` for clarity, but avoid moving for now to prevent reference breaks.

---

## Testing

**Location:** `tests/` (pytest suite)
- Test core logic, providers, API endpoints.
- Mock external services (Spotify, Plex) where needed.

---

## Background Services

**Service Monitor (Optional):**
- `backend_entry.py`: Can run separately as a daemon to monitor provider health, manage background jobs.
- Or: Integrate into Flask app as a background thread/task queue (e.g., Celery, APScheduler).

---

## Summary

| Layer | Directory | Purpose |
|-------|-----------|---------|
| Core | core/ | Essential business logic, config, DB, job queue |
| Core API | web/routes/system.py, tracks.py, library.py | HTTP access to core |
| Providers (bundled) | providers/ | Official service clients (auto-discovered, deletable) |
| Plugins (community) | plugins/ | User-provided service clients (auto-discovered, modular) |
| Providers/Plugins API | web/routes/providers.py | HTTP access to all provider/plugin settings, playlists |
| Flask App | web/api_app.py | Blueprint registration, CORS, middleware |
| Tests | tests/ | pytest suite |

This structure enables:
- Clean separation of concerns.
- Easy plugin development (copy plugin folder + optional API file).
- Modular testing.
- Clear deprecation path (move old UI to legacy/, keep active API clean).
