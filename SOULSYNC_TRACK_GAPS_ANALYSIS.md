# SoulSyncTrack & Matching Engine Integration Gap Analysis

**Date**: March 3, 2026  
**Status**: Comprehensive Review Complete  
**Priority**: HIGH - Affects matching accuracy and download success

---

## Executive Summary

This analysis identifies disconnects in how providers and services construct `SoulSyncTrack` objects and utilize the matching engine. Key issues center around:

1. **Duration unit inconsistencies** (seconds vs milliseconds)
2. **Missing metadata extraction** (bitrate, sample_rate, bit_depth)
3. **Direct SoulSyncTrack construction** bypassing provider conversion
4. **Tidal provider not using SoulSyncTrack** at all
5. **Inconsistent matching engine usage**

---

## Critical Issues (Impact: High)

### 1. ✅ **FIXED: Slskd Duration Not Extracted** 
**Status**: Fixed in commit [current]  
**Location**: `providers/slskd/client.py`

**Problem**:
- Slskd API returns track duration in **seconds** under `file_data["length"]`
- Previous code passed this raw value to `TrackResult.duration` without conversion
- When creating `SoulSyncTrack`, code multiplied by 1000, but `duration` was often `None`
- Result: Download matching failed due to missing duration metadata

**Fix Applied**:
```python
# Extract length safely and convert to milliseconds
length_val = file_data.get('length')
duration_ms = None
try:
    if length_val is not None and length_val != '':
        duration_seconds = int(float(length_val))
        duration_ms = duration_seconds * 1000
except Exception:
    duration_ms = None

# Store in TrackResult as milliseconds
track = TrackResult(
    ...
    duration=duration_ms,  # Now in milliseconds
    ...
)
```

**Verification Needed**:
- Run download search and check logs for duration values
- Confirm matching engine receives duration_ms properly

---

### 2. ⚠️ **Tidal Provider: No SoulSyncTrack Conversion**
**Status**: Not Fixed  
**Location**: `providers/tidal/client.py`, `providers/tidal/adapter.py`  
**Priority**: HIGH

**Problem**:
- Tidal returns custom `Track` objects (simple dataclass with id, name, artists, album, duration)
- These are **never converted to SoulSyncTrack**
- Matching engine cannot be used for Tidal ↔ Library matching
- Playlist sync and download matching for Tidal tracks is broken

**Evidence**:
```python
# providers/tidal/client.py line 565
class Track:
    def __init__(self, id, name, artists, album, duration):
        self.id = id
        self.name = name
        self.artists = artists
        self.album = album
        self.duration = duration  # ⚠️ Unit unclear (seconds? ms?)

# search_tracks returns Track objects, NOT SoulSyncTrack
def search_tracks(self, query: str, limit: int = 10) -> List[Any]:
    ...
    track = Track(
        id=item.get('id'),
        name=item.get('title'),
        artists=[a['name'] for a in item.get('artists', [])],
        album=item.get('album', {}).get('title'),
        duration=item.get('duration')  # ⚠️ Not converted to SoulSyncTrack
    )
    tracks.append(track)
    return tracks
```

**Impact**:
- Tidal playlist tracks cannot be matched against local library
- Download manager cannot use Tidal as source for matching
- Quality-aware matching unavailable for Tidal

**Recommended Fix**:
```python
def _convert_tidal_track_to_soulsync(self, tidal_track_data: Dict[str, Any]) -> Optional[SoulSyncTrack]:
    """Convert Tidal API track to SoulSyncTrack."""
    try:
        # Extract artist names
        artists = tidal_track_data.get('artists', [])
        artist_name = artists[0].get('name') if artists else 'Unknown Artist'
        
        # Extract album
        album_data = tidal_track_data.get('album', {})
        album_title = album_data.get('title', 'Unknown Album')
        
        # Duration - Tidal API returns SECONDS
        duration_seconds = tidal_track_data.get('duration')
        duration_ms = int(duration_seconds * 1000) if duration_seconds else None
        
        # Extract ISRC if available
        isrc = tidal_track_data.get('isrc')
        
        return self.create_soul_sync_track(
            title=tidal_track_data.get('title', ''),
            artist=artist_name,
            album=album_title,
            duration_ms=duration_ms,
            isrc=isrc,
            provider_id=str(tidal_track_data.get('id')),
            source='tidal',
            # Tidal-specific metadata
            audio_quality=tidal_track_data.get('audioQuality'),  # e.g., "HI_RES", "LOSSLESS"
            audio_modes=tidal_track_data.get('audioModes', [])   # e.g., ["STEREO", "DOLBY_ATMOS"]
        )
    except Exception as e:
        logger.error(f"Error converting Tidal track: {e}")
        return None
```

**Action Required**:
1. Add `_convert_tidal_track_to_soulsync()` method to `TidalClient`
2. Update `search_tracks()` to return `List[SoulSyncTrack]`
3. Update `get_playlist()` to convert Track objects to SoulSyncTrack
4. Update `TidalAdapter` to use the conversion method

---

### 3. ⚠️ **Web Routes: Direct SoulSyncTrack Construction**
**Status**: Not Fixed  
**Location**: `web/routes/playlists.py` (lines 273, 420)  
**Priority**: MEDIUM

**Problem**:
- Playlist matching routes construct `SoulSyncTrack` directly from DB query results
- Bypasses provider conversion layers that normalize metadata
- Inconsistent with how providers create tracks

**Evidence**:
```python
# web/routes/playlists.py line 273
candidate_track = SoulSyncTrack(
    raw_title=raw_title_candidate,
    artist_name=candidate_row[4],
    album_title="",
    duration=candidate_row[2] if candidate_row[2] else 0,  # ⚠️ Empty album, no bitrate
    edition=edition_candidate,
)
```

**Impact**:
- Missing metadata (bitrate, sample_rate, file_format) not passed to matching engine
- Quality bonuses in matching profiles cannot be applied
- Inconsistent track representation across codebase

**Recommended Fix**:
- Create `MusicDatabase.row_to_soulsync_track()` helper method
- Use it consistently for DB → SoulSyncTrack conversion
- Ensure all available metadata is extracted

---

### 4. ⚠️ **Music Database: Incomplete Track Conversion**
**Status**: Not Fixed  
**Location**: `database/music_database.py` (line 465)  
**Priority**: MEDIUM

**Problem**:
- Similar to web routes issue
- Direct `SoulSyncTrack` construction from DB rows
- Missing metadata fields (bitrate, file_format, sample_rate, etc.)

**Evidence**:
```python
# database/music_database.py line 465
cand_obj = SoulSyncTrack(
    raw_title=candidate.title,
    artist_name=candidate.artist.name,
    album_title=candidate.album.title if candidate.album else "",
    duration=candidate.duration,  # ⚠️ Missing: bitrate, file_format, sample_rate, bit_depth
)
```

**Recommended Fix**:
Add comprehensive conversion helper:
```python
def track_row_to_soulsync(self, track_row: Track) -> SoulSyncTrack:
    """Convert DB Track row to SoulSyncTrack with all metadata."""
    return SoulSyncTrack(
        raw_title=track_row.title,
        artist_name=track_row.artist.name if track_row.artist else 'Unknown',
        album_title=track_row.album.title if track_row.album else '',
        duration=track_row.duration,
        track_number=track_row.track_number,
        disc_number=track_row.disc_number,
        bitrate=track_row.bitrate,
        file_format=track_row.file_format,
        file_path=track_row.file_path,
        sample_rate=track_row.sample_rate,
        bit_depth=track_row.bit_depth,
        file_size_bytes=track_row.file_size_bytes,
        release_year=track_row.year,
        isrc=track_row.isrc,
        musicbrainz_id=track_row.musicbrainz_recording_id,
        identifiers={"db_track_id": track_row.id}
    )
```

---

## Medium Priority Issues

### 5. ⚠️ **Navidrome: Inconsistent Duration Handling**
**Status**: Partially Fixed  
**Location**: `providers/navidrome/client.py`, `providers/navidrome/adapter.py`

**Problem**:
- Multiple locations handle duration conversion differently
- Some multiply by 1000, some assume already in ms
- Adapter correctly converts seconds → ms (line 51)
- Client wrapper class converts seconds → ms (line 111)
- BUT: Inconsistent assumptions about source units

**Evidence**:
```python
# providers/navidrome/adapter.py line 51 - CORRECT
duration_ms = int(duration_raw) * 1000  # Convert seconds to ms

# providers/navidrome/client.py line 111 - CORRECT
self.duration = navidrome_data.get('duration', 0) * 1000  # Convert to milliseconds

# BUT: Some places assume duration is already in ms
# providers/navidrome/adapter.py line 55
duration_ms = getattr(navidrome_track, 'duration', None)  # ⚠️ Assumes ms?
```

**Recommended Fix**:
- Document Navidrome API unit (seconds vs ms)
- Ensure all conversions happen at API boundary
- Add unit tests for duration conversion

---

### 6. ✅ **Jellyfin: Duration Unit Conversion**
**Status**: Correct  
**Location**: `providers/jellyfin/adapter.py`

**No Issue**: Correctly converts Jellyfin ticks to milliseconds:
```python
# providers/jellyfin/adapter.py line 60
duration_raw = raw_data.get('RunTimeTicks')
if duration_raw:
    duration_ms = int(duration_raw) // 10000  # Convert ticks to ms ✅
```

---

### 7. ✅ **Plex: Duration Handling**
**Status**: Correct  
**Location**: `providers/plex/client.py`

**No Issue**: Plex already returns duration in milliseconds:
```python
# providers/plex/client.py line 745
duration_ms = getattr(plex_track, 'duration', None)  # Already in ms ✅
```

---

### 8. ✅ **Spotify: Duration Handling**
**Status**: Correct  
**Location**: `providers/spotify/client.py`

**No Issue**: Spotify API returns `duration_ms`:
```python
# providers/spotify/client.py line 551
duration_ms=spotify_track_data.get('duration_ms'),  # Already in ms ✅
```

---

## Matching Engine Usage Gaps

### 9. ℹ️ **Matching Engine: Proper Usage Examples**
**Status**: Documentation  
**Locations**: Various services correctly use matching engine

**Good Examples**:
1. **Download Manager** (`services/download_manager.py`):
   - ✅ Uses `WeightedMatchingEngine` with `PROFILE_DOWNLOAD_SEARCH`
   - ✅ Applies quality bonuses (bitrate, format, sample_rate)
   - ✅ Duration tolerance correctly applied

2. **Match Service** (`services/match_service.py`):
   - ✅ Uses `PROFILE_EXACT_SYNC` for library matching  
   - ✅ Multiple scoring profiles for different use cases

3. **Playlist Routes** (`web/routes/playlists.py`):
   - ✅ Uses matching engine with both standard and title-duration-only modes
   - ⚠️ BUT: Candidates lack quality metadata (see Issue #3)

---

## Missing Metadata Extraction

### 10. ⚠️ **Technical Metadata Gaps Across Providers**

| Provider   | Duration | Bitrate | Sample Rate | Bit Depth | File Format | ISRC | MusicBrainz |
|------------|----------|---------|-------------|-----------|-------------|------|-------------|
| Spotify    | ✅       | ❌      | ❌          | ❌        | ❌          | ✅   | ❌          |
| Plex       | ✅       | ✅      | ✅          | ✅        | ✅          | ❌   | ❌          |
| Navidrome  | ✅       | ✅      | ✅          | ✅        | ✅          | ✅   | ✅          |
| Jellyfin   | ✅       | ✅      | ✅          | ✅        | ✅          | ✅   | ✅          |
| Tidal      | ⚠️       | ❌      | ❌          | ❌        | ❌          | ⚠️   | ❌          |
| Slskd      | ✅*      | ✅      | ✅*         | ✅*       | ✅          | ❌   | ❌          |

**Legend**:
- ✅ = Extracted and passed to SoulSyncTrack
- ❌ = Not available or not extracted
- ⚠️ = Partially available (Tidal has quality tiers but not extracted)
- ✅* = Parsed from filename/metadata, not from API

**Impact**:
- Spotify tracks cannot benefit from quality bonuses in matching
- Tidal quality tiers (HI_RES, LOSSLESS) not utilized
- Download manager cannot prefer higher-quality Slskd results accurately

---

## Recommended Action Plan

### Phase 1: Critical Fixes (This Week)
1. ✅ **Slskd duration extraction** - COMPLETE
2. ⚠️ **Tidal SoulSyncTrack conversion** - Add `_convert_tidal_track_to_soulsync()`
3. ⚠️ **Database track conversion helper** - Add `track_row_to_soulsync()` method

### Phase 2: Consistency Improvements (Next Sprint)
1. Create `MusicDatabase.row_to_soulsync_track()` helper
2. Update web routes to use database helper
3. Document duration units for each provider API
4. Add unit tests for all provider conversions

### Phase 3: Metadata Enhancement (Future)
1. Add Spotify audio features extraction (energy, danceability, tempo)
2. Extract Tidal quality tier metadata (HI_RES, LOSSLESS, DOLBY_ATMOS)
3. Enhance matching engine to use provider-specific quality signals
4. Add provider quality preference settings

---

## Testing Checklist

### For Each Provider:
- [ ] Duration extracted and in milliseconds
- [ ] Bitrate extracted (if available)
- [ ] Sample rate extracted (if available)
- [ ] Bit depth extracted (if available)
- [ ] File format/codec extracted (if available)
- [ ] ISRC extracted (if available)
- [ ] MusicBrainz IDs extracted (if available)
- [ ] SoulSyncTrack properly passed to matching engine
- [ ] Matching engine can apply quality bonuses

### End-to-End Tests:
- [ ] Download search finds candidates with duration matching
- [ ] Playlist sync matches tracks accurately across providers
- [ ] Quality profiles correctly prefer high-bitrate files
- [ ] Duration tolerance filters work as expected
- [ ] ISRC matching prioritized when available

---

## Additional Observations

### Good Practices Found:
1. **ProviderBase.create_soul_sync_track()** - Centralized factory method ensures normalization
2. **Adapter pattern** - Clean separation between provider API and SoulSync domain model
3. **Matching profiles** - Different scoring strategies for different use cases (sync vs download)

### Anti-Patterns Found:
1. **Direct SoulSyncTrack construction** - Bypasses provider normalization
2. **Inconsistent duration units** - Some APIs return seconds, some ms, conversions scattered
3. **Missing duration validation** - No checks for reasonable duration ranges (e.g., > 0, < 1 hour for typical tracks)

---

## Appendix: Provider API Duration Units Reference

| Provider   | API Duration Unit | Conversion Required |
|------------|------------------|---------------------|
| Spotify    | milliseconds     | ❌ No               |
| Plex       | milliseconds     | ❌ No               |
| Navidrome  | seconds          | ✅ Yes × 1000       |
| Jellyfin   | ticks (100ns)    | ✅ Yes ÷ 10000      |
| Tidal      | seconds          | ✅ Yes × 1000       |
| Slskd      | seconds          | ✅ Yes × 1000       |
| MusicBrainz| milliseconds     | ❌ No               |

---

**Report Generated by**: GitHub Copilot  
**Review Status**: Ready for Engineering Review  
**Next Steps**: Prioritize Phase 1 fixes and schedule Phase 2 improvements
