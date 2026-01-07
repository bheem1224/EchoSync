# Architecture Analysis: Providers vs Plugins

## Current Structure

### **Providers** (`core/provider_base.py` + `core/provider_types.py`)
- **Base Class**: `ProviderBase` (abstract)
- **Subclasses**:
  - `DownloaderProvider` (slskd/Soulseek)
  - `MediaServerProvider` (Plex, Jellyfin, Navidrome)
  - `SyncServiceProvider` (Spotify, TIDAL)
- **Registration**: `ProviderRegistry` (singleton class-based registry)
- **Usage**: Instantiated at startup; methods called directly from services
- **Design**: Type-hierarchical; assumes providers are core features

### **Plugins** (`plugins/plugin_system.py` + `plugins/adapter_registry.py`)
- **System**: `PluginType` enum with roles (PLAYLIST_PROVIDER, SEARCH_PROVIDER, etc.)
- **Registration**: `AdapterRegistry` (separate runtime instance registry)
- **Design**: Track-centric; plugins enrich/attach data to tracks without owning storage
- **Purpose**: Loose coupling; plugins can be loaded/unloaded without affecting core

### **Key Difference**
| Aspect | Provider | Plugin |
|--------|----------|--------|
| Registration | Class registry (static) | Adapter registry (runtime) |
| Ownership | Implied to be built-in | Optional/external |
| Data model | Provider-owned | Track-centric (no ownership) |
| Use case | Tight core integrations | Extensible add-ons |
| Stability | Expected stable | Can fail without breaking app |

---

## Unified Base Proposal

**Problem**: Both systems mirror each other; duplication of registration and interface patterns.

**Solution**: Create single `ExtensionBase` with a `type: str` field to distinguish:
```python
class ExtensionBase(ABC):
    type: str  # "provider" | "plugin"
    name: str
    
    @abstractmethod
    def initialize(self) -> bool: pass
    
    @abstractmethod
    def shutdown(self) -> bool: pass
```

**Benefits**:
- Single registry; cleaner codebase
- Providers as "built-in plugins" conceptually
- Easier to move Tidal (or any provider) to plugins folder

**Drawback**: Requires refactoring all provider classes

---

## Missing: Media Server Scan/Refresh

### Current Gap
- **MediaServerProvider** has `get_all_tracks()`, `get_library_stats()` (read-only)
- **No method** to trigger a library refresh (Plex library scan, Jellyfin metadata refresh, etc.)

### Required Addition to `MediaServerProvider`

```python
@abstractmethod
def trigger_library_scan(self, path: Optional[str] = None) -> bool:
    """
    Trigger a library refresh/scan on the media server.
    Returns True if scan initiated successfully.
    """
    pass

@abstractmethod
def get_scan_status(self) -> Dict[str, Any]:
    """
    Get current scan status. Must support polling for completion.
    Returns: {
        'scanning': bool,
        'progress': float (0-100),
        'eta_seconds': int or None,
        'error': str or None
    }
    """
    pass
```

### Implementation Examples
- **Plex**: `PUT /library/sections/{sectionId}/refresh` → poll `/library/sections/{sectionId}/refreshing`
- **Jellyfin**: `POST /Library/Refresh` or per-folder refresh
- **Navidrome**: `POST /rest/admin/scanMediaLibrary.view`

---

## Wiring Checklist for Playlist Sync

### Backend
1. [ ] Add `trigger_library_scan()` + `get_scan_status()` to `MediaServerProvider`
2. [ ] Implement in `PlexClient`, `JellyfinClient`, `NavidromeClient`
3. [ ] Replace `/api/playlists/analyze` stub with:
   - Fetch source playlists + tracks
   - Match against target library using `MusicMatchingEngine`
   - Return detailed results (matched, missing, confidence)
4. [ ] Wire `download_missing` + `quality_profile` flags through:
   - `SyncAdapter.trigger_sync()` → `PlaylistSyncService.sync_playlist()`
   - Pass quality to `SoulseekClient.search() / .download()`
5. [ ] Add `/api/library/scan` endpoint to trigger media server refresh
6. [ ] Create `/api/library/scan-status` to poll scan progress

### Frontend
1. [ ] Analysis modal: wire real track results from `/api/playlists/analyze`
2. [ ] Show quality profile UI dropdown (already done)
3. [ ] After download, optionally show "Refresh Library" button
4. [ ] Add library scan progress indicator if user triggers refresh

### Services
1. [ ] `PlaylistSyncService` should accept `quality_profile` parameter
2. [ ] Pass quality to download methods:
   ```python
   await self.soulseek_client.filter_results_by_quality_preference(
       results, 
       quality_profile=quality_profile
   )
   ```
3. [ ] Track sync result includes quality used + download count

---

## Priority Implementation Order

### Phase 1: Core Changes (High Impact)
1. Add `trigger_library_scan()` + `get_scan_status()` to `MediaServerProvider`
2. Implement in Plex, Jellyfin, Navidrome clients
3. Implement real `/api/playlists/analyze` logic

### Phase 2: Wiring (Medium Impact)
4. Pass `quality_profile` through sync → download flow
5. Wire `download_missing` flag to actually download
6. Add `/api/library/scan` + `/api/library/scan-status` endpoints

### Phase 3: Polish (Low Impact)
7. UI for library refresh trigger + status polling
8. Consider unified `ExtensionBase` refactor (optional, large)
9. Move TIDAL to plugins if needed

---

## Code Locations

| File | Component | Change |
|------|-----------|--------|
| `core/provider_types.py` | `MediaServerProvider` | Add scan methods |
| `providers/plex/client.py` | `PlexClient` | Impl. scan trigger |
| `providers/jellyfin/client.py` | `JellyfinClient` | Impl. scan trigger |
| `providers/navidrome/client.py` | `NavidromeClient` | Impl. scan trigger |
| `web/routes/playlists.py` | POST `/analyze` | Real matching logic |
| `web/routes/library.py` | *NEW* | Scan endpoints |
| `services/sync_service.py` | `PlaylistSyncService` | Accept quality_profile |
| `providers/soulseek/client.py` | `SoulseekClient` | Accept quality in download flow |

