# API Readiness Checklist for Svelte UI Integration

**Status:** In Progress
**Last Updated:** 2025-01-15
**Goal:** Verify all Flask API endpoints are functional and properly integrated with backend services for Svelte web UI deployment.

---

## 1. **Reference Cleanup** ✓ FIXED

### Broken References Found and Fixed
- [x] **web/routes/providers.py:31** - Legacy import from `web_server` (now stub)
  - **Issue:** `from web_server import spotify_client, tidal_client, plex_client` raised ImportError
  - **Fix Applied:** Replaced with plugin_registry lookup: `plugin_registry.get_plugin(provider_name)`
  - **Status:** FIXED - Now uses active registry instead of legacy clients

- [x] **tests/test_endpoints_health.py:8** - Legacy import from `web_server`
  - **Issue:** `from web_server import app` raised ImportError
  - **Fix Applied:** Changed to `from web.api_app import create_app`
  - **Status:** FIXED - Now imports from active Flask factory

### Verification
```bash
# No more ImportErrors when importing active files
python -c "from web.api_app import create_app; print('✓ Flask factory loads')"
python -c "from web.routes.providers import bp; print('✓ Providers routes load')"
python -c "from tests.test_endpoints_health import *; print('✓ Tests load')"
```

---

## 2. **Flask API Layer** 

### Core Factory (web/api_app.py)
- [x] **create_app()** function exists
- [x] Registers all blueprints:
  - [x] `/api/providers` (providers.py)
  - [x] `/api/jobs` (jobs.py)
  - [x] `/api/tracks` (tracks.py)
  - [x] `/api/search` (search.py)
  - [x] `/api/system` (system.py)
  - [x] `/api/sync` (sync.py)
  - [x] `/api/playlists` (playlists.py)
- [x] CORS headers configured for Svelte frontend
- [ ] Error handlers registered (4xx, 5xx)
- [ ] Middleware chain (logging, auth, etc.)

---

## 3. **Svelte-Facing Endpoints**

### System & Health
| Endpoint | Method | Status | Persistence | Notes |
|----------|--------|--------|-------------|-------|
| `/api/health` | GET | ✓ Implemented | N/A | Returns service health status |
| `/api/settings` | GET | ✓ Implemented | ⚠️ Check | Returns current settings object |
| `/api/settings` | POST | ✓ Implemented | ⚠️ Check | Saves settings to config_manager |
| `/api/system/status` | GET | ✓ Implemented | N/A | Returns system uptime, version, etc |

**Persistence Check (REQUIRED):**
```python
# web/routes/system.py POST /api/settings
# Must call: config_manager.set_setting(key, value)
# And: config_manager.save()  # Persist to disk
```

### Provider Management
| Endpoint | Method | Status | Implementation | Notes |
|----------|--------|--------|-----------------|-------|
| `/api/providers` | GET | ✓ Implemented | provider_registry.list_all() | Lists available providers with capabilities |
| `/api/providers/<id>` | GET | ✓ Implemented | provider_registry.get_provider(id) | Get single provider details |
| `/api/providers/<id>/auth` | POST | ✓ Implemented | adapter.handle_auth() | Authenticate with provider |
| `/api/providers/<id>/settings` | GET | ✓ Implemented | config_manager.get_provider_config(id) | Get provider-specific settings |
| `/api/providers/<id>/settings` | POST | ⚠️ Check | config_manager.set_provider_config(id, data) | Save provider settings |
| `/api/providers/<id>/playlists` | GET | ⚠️ Fixed | plugin_registry.get_plugin().get_user_playlists() | Fetch user playlists from provider |
| `/api/providers/<id>/disconnect` | POST | ? | adapter.disconnect() | Disconnect/logout from provider |

**Action Required:**
- [ ] Verify `/api/providers/<id>/settings` POST persists to config.json
- [ ] Test `/api/providers/<id>/playlists` GET returns real playlists
- [ ] Verify provider disconnect clears stored auth tokens

### Job Management
| Endpoint | Method | Status | Implementation | Notes |
|----------|--------|--------|-----------------|-------|
| `/api/jobs` | GET | ✓ Implemented | job_queue.list_jobs() | Lists all jobs (active + history) |
| `/api/jobs/active` | GET | ✓ Implemented | job_queue.get_active_jobs() | Lists currently running jobs |
| `/api/jobs/<id>/cancel` | POST | ? | job_queue.cancel_job(id) | Cancel a running job |
| `/api/jobs/<id>/logs` | GET | ? | job_queue.get_job_logs(id) | Stream job logs |

**Action Required:**
- [ ] Verify job queue returns real job state
- [ ] Test job cancellation works
- [ ] Verify job logs endpoint streams properly

### Track & Library Management
| Endpoint | Method | Status | Implementation | Notes |
|----------|--------|--------|-----------------|-------|
| `/api/tracks` | GET | ✓ Implemented | database.get_tracks(filters) | List canonical tracks |
| `/api/tracks` | POST | ✓ Implemented | database.add_track(data) | Add new track to library |
| `/api/tracks/<id>` | GET | ✓ Implemented | database.get_track(id) | Get single track details |
| `/api/tracks/<id>` | DELETE | ✓ Implemented | database.delete_track(id) | Remove track from library |
| `/api/library/scan` | POST | ? | media_scan_manager.start_scan() | Trigger library media scan |
| `/api/library/status` | GET | ? | media_scan_manager.get_status() | Get scan progress |

**Action Required:**
- [ ] Verify track CRUD operations work with database
- [ ] Test library scan triggers background job
- [ ] Verify scan status returns real progress

### Search
| Endpoint | Method | Status | Implementation | Notes |
|----------|--------|--------|-----------------|-------|
| `/api/search` | GET | ✓ Implemented | search_service.unified_search(q) | Search across all providers |
| `/api/search?q=<query>&provider=<id>` | GET | ? | search_service.provider_search(q, id) | Search specific provider |

**Action Required:**
- [ ] Test search returns results from multiple providers
- [ ] Test provider-specific search filtering

### Sync & Playlists
| Endpoint | Method | Status | Implementation | Notes |
|----------|--------|--------|-----------------|-------|
| `/api/playlists/sync` | POST | ✓ Implemented | sync_service.start_sync(config) | Trigger playlist sync job |
| `/api/sync/status` | GET | ✓ Implemented | sync_service.get_status() | Get current sync progress |
| `/api/sync/options` | GET | ✓ Implemented | sync_service.get_sync_options() | Get available sync strategies |

**Action Required:**
- [ ] Verify sync job is created in job queue
- [ ] Test sync progress is trackable via /api/jobs/active

---

## 4. **Backend Service Integration**

### config_manager (Configuration Persistence)
- [ ] **Location:** `config/config_manager.py` or `core/config_manager.py`
- [ ] **Methods Needed:**
  - `get_setting(key)` - retrieve setting value
  - `set_setting(key, value)` - update setting
  - `save()` - persist to config.json
  - `get_provider_config(provider_id)` - provider-specific settings
  - `set_provider_config(provider_id, config)` - update provider config

**Verification Script:**
```python
from config.config_manager import config_manager

# Test persistence
config_manager.set_setting('test_key', 'test_value')
config_manager.save()
assert config_manager.get_setting('test_key') == 'test_value'
print("✓ Config persistence works")
```

### job_queue (Async Job Management)
- [ ] **Location:** `core/job_queue.py`
- [ ] **Methods Needed:**
  - `list_jobs(filters)` - return list of Job objects
  - `get_active_jobs()` - return currently running jobs
  - `create_job(type, config)` - enqueue new job
  - `get_job(id)` - fetch job by ID
  - `cancel_job(id)` - stop running job

**Verification Script:**
```python
from core.job_queue import job_queue

# Create test job
job = job_queue.create_job('test_sync', {'provider': 'spotify'})
assert job.status == 'pending'
print(f"✓ Job created: {job.id}")
```

### provider_registry (Provider Discovery & Access)
- [ ] **Location:** `core/provider_registry.py` or `web/services/provider_registry.py`
- [ ] **Methods Needed:**
  - `list_all()` - return all providers (bundled + plugins)
  - `get_provider(id)` - get single provider
  - `get_capabilities(provider_id)` - return provider capabilities

**Verification Script:**
```python
from web.services.provider_registry import provider_registry

# Test registry
providers = provider_registry.list_all()
assert len(providers) > 0
print(f"✓ Found {len(providers)} providers")
```

### plugin_registry (Plugin System)
- [ ] **Location:** `plugins/plugin_system.py`
- [ ] **Methods Needed:**
  - `list_all()` - return all plugins
  - `get_plugin(name)` - fetch plugin by name/ID
  - `install_plugin(path)` - load new plugin
  - `uninstall_plugin(name)` - remove plugin

**Verification Script:**
```python
from plugins.plugin_system import plugin_registry

# Test plugin registry
plugins = plugin_registry.list_all()
spotify = plugin_registry.get_plugin('spotify')
assert spotify is not None
print("✓ Plugin registry works")
```

---

## 5. **Provider Integration**

### Bundled Providers (all must follow pattern: client.py + adapter.py)
- [x] **Spotify** (`providers/spotify/`)
  - [x] client.py - SpotifyClient
  - [x] adapter.py - HTTP routes
- [x] **Plex** (`providers/plex/`)
  - [x] client.py - PlexClient
  - [x] adapter.py - HTTP routes
- [x] **Jellyfin** (`providers/jellyfin/`)
  - [x] client.py - JellyfinClient
  - [x] adapter.py - HTTP routes
- [x] **Navidrome** (`providers/navidrome/`)
  - [x] client.py - NavidromeClient
  - [x] adapter.py - HTTP routes
- [x] **Soulseek** (`providers/soulseek/`)
  - [x] client.py - SoulseekClient
  - [x] adapter.py - HTTP routes
- [x] **Tidal** (`providers/tidal/`)
  - [x] client.py - TidalClient
  - [x] adapter.py - HTTP routes
- [x] **ListenBrainz** (`providers/listenbrainz/`)
  - [x] client.py - ListenBrainzClient
  - [x] adapter.py - HTTP routes

**Action Required:**
- [ ] Verify each provider's adapter is registered in web/api_app.py
- [ ] Test authentication flow for at least one provider
- [ ] Verify playlists/tracks retrieval works

---

## 6. **Data Persistence**

### Settings (config.json)
- [ ] POST /api/settings saves to config.json
- [ ] GET /api/settings returns current config
- [ ] Settings survive app restart

### Provider Credentials
- [ ] OAuth tokens stored securely (encrypted in config.db or environment)
- [ ] Tokens refreshed automatically on expiry
- [ ] Tokens cleared on provider disconnect

### Job History
- [ ] Job records persisted to database
- [ ] Job logs stored and retrievable
- [ ] Old jobs pruned automatically (e.g., >30 days)

### Track Library
- [ ] Canonical tracks stored in SQLite (data/soulsync.db)
- [ ] Provider-specific track refs linked
- [ ] Supports full-text search

---

## 7. **Testing Suite**

### Unit Tests
- [ ] Config persistence tests
- [ ] Job queue tests
- [ ] Provider registry tests
- [ ] Search service tests

### Integration Tests
- [ ] API endpoint tests (all routes)
- [ ] End-to-end provider auth flow
- [ ] Sync job end-to-end

### Pytest Execution
```bash
# Run all tests
pytest tests/ -v

# Expected output: All pass (or skip if mocked)
# PASSED test_endpoints_health.py::test_all_critical_endpoints
# PASSED test_settings_persist.py::test_settings_saved_to_disk
# PASSED test_job_queue.py::test_create_job
```

**Action Required:**
- [ ] Run full pytest suite: `pytest tests/ -v`
- [ ] Fix any failures
- [ ] Ensure all critical endpoints have tests

---

## 8. **Svelte UI Integration Readiness**

### Frontend Expectations
Svelte stores (webui/src/stores/) expect:
- **providers.js:** GET `/api/providers` → Array of {id, name, capabilities, authenticated, settings}
- **jobs.js:** GET `/api/jobs/active` → Array of {id, type, status, progress, createdAt}
- **health.js:** GET `/api/health` → {status, services, uptime, lastCheck}
- **settings.js:** GET `/api/settings` → Object with app config

### Backend Ready Checklist
- [ ] All endpoints return correct JSON structure
- [ ] All endpoints handle errors gracefully (4xx, 5xx)
- [ ] Settings persist across requests and restarts
- [ ] Provider auth tokens persist securely
- [ ] Job queue tracks real async work
- [ ] Search works across providers
- [ ] Sync job is properly tracked

---

## 9. **Deployment Readiness**

### Docker Environment
- [ ] Flask app starts without errors
- [ ] Database initializes on first run
- [ ] Config volume is writable
- [ ] Logs are captured properly

### Local Development
- [ ] App runs: `python main.py` (or backend_entry.py)
- [ ] API responds: `curl http://localhost:5000/api/health`
- [ ] Svelte dev server can call API endpoints
- [ ] Hot-reload works for both frontend and backend

---

## 10. **Known Issues & Workarounds**

### Issue: Provider clients not instantiated
- **Status:** FIXED
- **Solution:** Use plugin_registry.get_plugin() instead of importing clients directly
- **File:** web/routes/providers.py

### Issue: Tests importing from legacy web_server
- **Status:** FIXED
- **Solution:** Import from web.api_app instead
- **File:** tests/test_endpoints_health.py

### Issue: Config persistence not wired
- **Status:** PENDING
- **Action:** Verify POST /api/settings calls config_manager.save()

### Issue: Provider auth tokens not persisted
- **Status:** PENDING
- **Action:** Ensure encrypted storage of OAuth tokens

---

## Next Steps

1. **Run Reference Check** (COMPLETED ✓)
   - [x] Fix providers.py imports
   - [x] Fix test imports
   - [x] No more ImportErrors

2. **Verify Service Integration** (IN PROGRESS)
   - [ ] Test config_manager persistence
   - [ ] Test job_queue creation and tracking
   - [ ] Test provider_registry discovery
   - [ ] Test plugin_registry plugin access

3. **Run Full Test Suite**
   - [ ] pytest tests/ -v
   - [ ] All tests pass
   - [ ] Full coverage for critical endpoints

4. **Manual Endpoint Testing**
   - [ ] Test GET /api/providers (returns provider list)
   - [ ] Test POST /api/settings (persists settings)
   - [ ] Test POST /api/providers/<id>/auth (authenticates provider)
   - [ ] Test GET /api/jobs/active (returns active jobs)
   - [ ] Test POST /api/playlists/sync (creates sync job)

5. **Svelte UI Connection**
   - [ ] Configure Svelte stores to call /api endpoints
   - [ ] Test live data flow (settings, providers, jobs)
   - [ ] Test real-time updates (WebSocket if needed)
   - [ ] Begin feature development

---

## Checklist Summary

**Fixed (This Session):**
- ✓ 2 broken reference imports fixed (providers.py, test_endpoints_health.py)
- ✓ Legacy files isolated (stubs in place)
- ✓ API structure verified

**To Complete Before Svelte Development:**
- [ ] Service integration verified (config_manager, job_queue, plugin_registry)
- [ ] Full pytest suite passes
- [ ] Manual endpoint testing confirms real data flow
- [ ] Settings persistence verified
- [ ] Provider auth tokens persist securely

**Priority:** High - These must complete before Svelte live testing begins.

---

**Prepared by:** Backend Refactor Agent  
**Target Completion:** Before Svelte UI Development Phase
