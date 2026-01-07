# Core Improvements: Unified Provider System & Shared Scanning

## Summary
Successfully consolidated the ProviderBase architecture and implemented a shared library scanning system across all media servers (Plex, Jellyfin, Navidrome) using the template method pattern.

## Changes Made

### 1. ProviderBase - Unified Type System
**File**: [core/provider_base.py](../core/provider_base.py)

Added `type` field to ProviderBase for unified provider/plugin system:
```python
type: str = 'provider'  # 'provider' or 'plugin'; allows future plugin support
```

**Benefits**:
- Future-proofs the system for plugin integration without major refactoring
- Provides clear distinction between providers and plugins
- Maintains backward compatibility

### 2. MediaServerProvider - Shared Scan Logic
**File**: [core/provider_types.py](../core/provider_types.py)

Implemented template method pattern for library scanning:

#### Public Methods (Shared Logic)
- `trigger_library_scan(path)`: Handles error state management, logging, delegates to `_trigger_scan_api()`
- `get_scan_status()`: Polls API status, merges with cached state, handles exceptions

#### Protected Template Methods (Server-Specific)
- `_trigger_scan_api(path)`: Server-specific scan initiation logic
- `_get_scan_status_api()`: Server-specific status polling logic

**Benefits**:
- Single source of truth for scan polling behavior
- Eliminates code duplication across Plex/Jellyfin/Navidrome
- New media servers only implement 2 API-specific methods instead of full scanning logic
- Consistent error handling and state tracking

### 3. Media Server Client Updates

#### Plex Client
**File**: [providers/plex/client.py](../providers/plex/client.py)
- Implemented `_trigger_scan_api()`: Calls `library.update()` on Plex server
- Implemented `_get_scan_status_api()`: Checks `library.refreshing` and server activities
- Removed deprecated `is_library_scanning()` method

#### Jellyfin Client
**File**: [providers/jellyfin/client.py](../providers/jellyfin/client.py)
- Implemented `_trigger_scan_api()`: Calls `/Items/{id}/Refresh` endpoint
- Implemented `_get_scan_status_api()`: Checks scheduled tasks for running scans
- Removed deprecated `is_library_scanning()` method

#### Navidrome Client
**File**: [providers/navidrome/client.py](../providers/navidrome/client.py)
- Implemented `_trigger_scan_api()`: Returns `True` (Navidrome has no explicit scanning)
- Implemented `_get_scan_status_api()`: Returns idle status (Navidrome always current)
- Removed deprecated `is_library_scanning()` method

### 4. Library API Endpoints
**File**: [web/routes/library.py](../web/routes/library.py)

Updated endpoints to use hybrid registry lookup:
- **POST /api/library/scan**: Triggers scan on active media server
  - Query param: `path` (optional server-specific path)
  - Returns: `{success, server, message}` or error
  
- **GET /api/library/scan-status**: Polls scan status
  - Returns: `{server, scanning, progress, eta_seconds, error}`

**Registry Lookup Logic**:
1. Try AdapterRegistry first (instance-based)
2. Fall back to ProviderRegistry (class-based instantiation)
3. Ensure fallback doesn't break existing ProviderRegistry usage

## Architecture Pattern

### Template Method Pattern
```python
# In MediaServerProvider base class
def trigger_library_scan(self, path=None):
    """Public method - handles logging and state"""
    success = self._trigger_scan_api(path)  # Delegate to subclass
    if success:
        self._scan_state['scanning'] = True
    return success

# In Plex/Jellyfin/Navidrome subclasses
def _trigger_scan_api(self, path=None):
    """Server-specific implementation only"""
    # ... Plex/Jellyfin/Navidrome-specific API calls
```

**Advantages**:
- Loose coupling: Subclasses don't need to know about error handling or logging
- Easy to extend: New servers only implement 2 methods
- Testable: Mock the template methods for unit tests
- Maintainable: All retry/error logic in one place

## State Management

### Per-Provider Scan State
Each MediaServerProvider instance maintains:
```python
self._scan_state = {
    'scanning': bool,
    'progress': float,  # 0-100 or -1 if unknown
    'eta_seconds': int | None,
    'error': str | None
}
```

State is:
- Initialized on instance creation
- Updated when scans are triggered
- Merged with API responses on status polls
- Returned to client with proper error info

## Backward Compatibility

### Registry System
- ProviderRegistry: Class-based static registry (unchanged)
- AdapterRegistry: Instance-based runtime registry (expanded)
- Library endpoints try AdapterRegistry first, fallback to ProviderRegistry

### Existing Code
- All existing provider functionality preserved
- No breaking changes to ProviderRegistry API
- Removed only deprecated `is_library_scanning()` method (internal use only)

## Next Steps

### In Progress (Quality Profile & Playlist Sync)
1. **Implement Playlist Analysis** 
   - Real matching logic in `/api/playlists/analyze` using MusicMatchingEngine
   - Return `{matched_tracks, missing_tracks, quality_stats}`

2. **Wire Quality Profile Propagation**
   - Flow: UI dropdown → /api/playlists/sync → SoulseekClient._async_download
   - Filter results using quality waterfall (FLAC → MP3-320 → MP3-128 → ...)

### Future Improvements
- Add plugin registration to ProviderBase using type field
- Implement download progress tracking (extend to all clients)
- Add library refresh hooks for post-scan cleanup
- Support partial scans by library section/path

## Testing Recommendations

1. **Unit Tests for Scan Logic**
   - Test error handling in public methods
   - Test state transitions (idle → scanning → complete)
   - Mock `_trigger_scan_api()` and `_get_scan_status_api()`

2. **Integration Tests**
   - Test actual Plex/Jellyfin/Navidrome scans with test servers
   - Verify endpoint responses with real provider instances
   - Test registry fallback logic

3. **Manual Testing Checklist**
   - [ ] POST /api/library/scan initiates scan on active server
   - [ ] GET /api/library/scan-status returns correct progress
   - [ ] Plex: Shows scanning=true while refreshing
   - [ ] Jellyfin: Shows scanning=true for running refresh tasks
   - [ ] Navidrome: Always returns scanning=false
   - [ ] Error responses include helpful messages

## File Manifest

### Modified Files
- [core/provider_base.py](../core/provider_base.py) - Added type field
- [core/provider_types.py](../core/provider_types.py) - Implemented shared scan system
- [providers/plex/client.py](../providers/plex/client.py) - Template method implementations
- [providers/jellyfin/client.py](../providers/jellyfin/client.py) - Template method implementations
- [providers/navidrome/client.py](../providers/navidrome/client.py) - Template method implementations
- [web/routes/library.py](../web/routes/library.py) - Hybrid registry lookup

### Lines Changed
- ProviderBase: +1 line (type field)
- MediaServerProvider: +80 lines (shared logic + template methods)
- Plex client: ~50 lines refactored (public → template methods)
- Jellyfin client: ~55 lines refactored
- Navidrome client: ~15 lines refactored
- Total: ~200 lines of focused, well-documented changes

## Validation

✅ All modified files compile without errors (Pylance check)
✅ No breaking changes to existing ProviderRegistry usage
✅ Backward compatible with current provider implementations
✅ Registry endpoints properly fallback between registries

