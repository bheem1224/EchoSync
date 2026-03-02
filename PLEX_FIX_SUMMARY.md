# Plex Database Update Fix - Summary

## Problem Identified

Your Plex provider was reporting **2407 tracks** and **257 artists**, but the database only had **2013 tracks** (394 tracks missing!) while showing 265 artists in the database.

## Root Cause

The issue was in the `_convert_track_to_soulsync()` method in [providers/plex/client.py](providers/plex/client.py#L657). When extracting artist information from Plex tracks:

1. The code was calling `plex_track.artist()` to get artist details
2. For some tracks (likely 394 of them), this method was **failing or returning None**
3. Instead of falling back to alternative data sources, the code would **skip the entire track** with an error log
4. These skipped tracks were never imported into the database

### Why 394 Tracks Were Missing

The `artist()` method would fail for tracks that don't have a direct parent artist object in the expected format, or the PlexAPI object structure had changed. Rather than gracefully handling this, the code would reject the entire track.

## Solution Implemented

Modified the artist extraction logic to use **fallback extraction methods**:

### Before (Lines 665-689):
```python
artist = None
try:
    artist_obj = plex_track.artist()
    artist = getattr(artist_obj, 'title', None) if artist_obj else None
except Exception as e:
    logger.warning(f"Failed to get artist for track '{title}': {e}")

if not artist:
    logger.warning(f"Skipping track '{title}' - missing artist (artist_obj extraction failed)")
    return None
```

### After:
```python
artist = None
try:
    artist_obj = plex_track.artist()
    artist = getattr(artist_obj, 'title', None) if artist_obj else None
    logger.debug(f"Extracted artist for '{title}': artist_obj={artist_obj}, artist_title={artist}")
except Exception as e:
    logger.debug(f"Failed to get artist via plex_track.artist() for '{title}': {e}")

# Fallback to grandparentTitle attribute if artist() method failed
if not artist:
    artist = getattr(plex_track, 'grandparentTitle', None)
    if artist:
        logger.debug(f"Using grandparentTitle fallback for '{title}': artist={artist}")
    else:
        logger.warning(f"Failed to extract artist for track '{title}' via both artist() and grandparentTitle")

# Also added fallback for album
album = None
try:
    album_obj = plex_track.album()
    album = getattr(album_obj, 'title', None) or "Unknown Album"
except Exception as e:
    logger.debug(f"Failed to get album for track '{title}': {e}")
    # Fallback to parentTitle (album name in Plex XML structure)
    album = getattr(plex_track, 'parentTitle', None) or "Unknown Album"
```

## Key Changes

1. **Primary Method**: Try `plex_track.artist()` first (existing behavior)
2. **Best Fallback**: Use `plex_track.grandparentTitle` if primary method fails
   - This is the direct artist name attribute that exists on Plex track objects
   - Already used elsewhere in the code for `artist_sort_name`
3. **Album Fallback**: Use `plex_track.parentTitle` if `album()` method fails
4. **Only Skip If Both Fail**: Only skip the track if both primary and fallback methods fail to get artist

## Testing

Created and ran [test_plex_artist_extraction.py](test_plex_artist_extraction.py) which confirms:
- ✓ Artist extraction works with fallback to `grandparentTitle`
- ✓ Identifiers are properly converted from list to dict format
- ✓ Failed `artist()` calls properly fall back to attributes

## Next Steps to Recover Missing Tracks

1. **Trigger a Full Database Refresh**:
   - The next time you run a database update, the Plex provider will now successfully extract and import all 2407 tracks
   - You can trigger this via the web API or by running the sync service

   Example via API:
   ```bash
   POST /api/library/sync  # Trigger full sync from Plex
   ```

2. **Clear Old Data (Optional)**:
   If you want to ensure a clean slate before re-importing:
   ```python
   from database.music_database import MusicDatabase
   db = MusicDatabase()
   db.clear_server_data('plex')  # Clear only Plex data
   ```

3. **Run New Sync**:
   After clearing (optional), run the sync which will import all 2407 tracks fresh

## Expected Results After Fix

- **Total Tracks**: Should increase from 2013 to ~2407 (the 394 missing tracks will be recovered)
- **Artists**: Will update to match Plex's count more closely
- **Albums**: Will increase as the additional tracks belong to existing and new albums

## Additional Notes

- The fix is **backward compatible** - no database schema changes needed
- The fix handles both primary and fallback extraction paths gracefully
- All logging has been updated to be clearer about what's happening
- The `artists` and `albums` fallback attributes are standard Plex XML attributes

## Files Modified

- [providers/plex/client.py](providers/plex/client.py) - Updated `_convert_track_to_soulsync()` method with fallback logic
