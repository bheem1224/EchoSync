# New Fields Population - Status Report

## Summary

The new database fields (ISRC, MusicBrainz IDs, audio quality metadata, etc.) **ARE being extracted and stored correctly** by the system. The converters are working, the database is accepting the data, and the infrastructure is in place.

**However:** The fields may appear empty in your database if your Plex/Jellyfin/Navidrome servers don't have that metadata populated in their libraries.

## What Was Fixed

### 1. **Database Schema** ✅
- Added 13 new columns to the `tracks` table:
  - `isrc` - International Standard Recording Code
  - `musicbrainz_id` - MusicBrainz Recording ID
  - `musicbrainz_album_id` - MusicBrainz Album ID
  - `version` - Remix/Live/Acoustic etc.
  - `is_compilation` - Compilation flag
  - `disc_number` / `total_discs` - Multi-disc support
  - `track_total` - Total tracks in release
  - `file_format` - Audio container (flac, mp3, etc.)
  - `quality_tags` - Quality indicators (JSON)
  - `sample_rate` - Hz (44100, 48000, etc.)
  - `bit_depth` - Bits (16, 24, etc.)
  - `file_size` - Bytes
  - `featured_artists` - Collaborators (JSON)
  - `fingerprint` / `fingerprint_confidence` - Audio fingerprint

### 2. **Provider Adapters** ✅
All three providers now extract these fields from their APIs:

- **Plex** (`providers/plex/adapter.py`)
  - Extracts ISRC and MusicBrainz IDs from guid objects
  - Extracts bitrate and file format

- **Jellyfin** (`providers/jellyfin/adapter.py`)
  - Extracts ProviderIds (ISRC, MusicBrainz IDs)
  - Extracts audio quality from MediaStreams (sample rate, bit depth)
  - Updated API request to include Fields parameter requesting detailed metadata

- **Navidrome** (`providers/navidrome/adapter.py`)
  - Extracts isrc, mbRecordingID, mbAlbumID
  - Extracts audio quality (bitRate, sampleRate, bitsPerSample)

### 3. **Client Methods** ✅
Added `get_album_tracks_as_soulsync()` methods to:
- `JellyfinClient` - Calls converter on each track
- `NavidromeClient` - Calls converter on each track
- `PlexClient` - Already had this method

These methods are called by `DatabaseUpdateWorker` during full/incremental refresh.

### 4. **Database Insert** ✅
- `insert_or_update_soul_sync_track()` accepts and stores all 24 track fields
- Properly handles JSON serialization for lists (quality_tags, featured_artists)
- Converts boolean to integer for is_compilation
- All execute_write imports fixed

### 5. **Jellyfin API Optimization** ✅
Updated `get_tracks_for_album()` to request all necessary fields via Fields parameter:
```
Fields: Name, Container, Path, RunTimeTicks, Bitrate, 
        ProviderIds, MediaSources, MediaStreams, etc.
```

## Data Flow

```
Plex/Jellyfin/Navidrome API Response
           ↓
    Provider Wrapper (JellyfinTrack, NavidromeTrack, etc.)
           ↓
    Converter Function (convert_jellyfin_track_to_soulsync, etc.)
           ↓
    SoulSyncTrack object (all fields populated)
           ↓
    database.insert_or_update_soul_sync_track()
           ↓
    SQLite tracks table (new columns populated)
```

## Why Fields Might Be Empty

If you run a full or incremental refresh and the new columns are still NULL/empty, it's because:

1. **Server Metadata Not Populated**
   - Plex/Jellyfin/Navidrome don't have ISRC codes (very rare)
   - Plex/Jellyfin/Navidrome don't have MusicBrainz IDs synced
   - Audio files lack proper metadata tags
   - Server hasn't scanned/analyzed files for audio quality

2. **Server Not Configured to Provide Data**
   - Jellyfin: MetadataProvider for MusicBrainz not enabled
   - Navidrome: MusicBrainz metadata sync not enabled
   - Plex: External metadata not enabled

## How to Populate Missing Fields

### For ISRC Codes
- Not commonly provided by most music servers
- Would need to be manually added to metadata tags or through external service
- Plex: Use external metadata plugins/agents
- Jellyfin: Enable MusicBrainz metadata enrichment
- Navidrome: Enable MusicBrainz sync

### For MusicBrainz IDs
- **Plex**: Settings > Library > Music > Enable MusicBrainz metadata agent
- **Jellyfin**: Settings > Plugins > MusicBrainz plugin (must be enabled)
- **Navidrome**: Settings > Metadata > Enable MusicBrainz

### For Audio Quality (Sample Rate, Bit Depth)
- Ensure your audio files are properly encoded
- Rescan library with "Analyze audio" enabled
- Check that your server correctly identifies file properties
- For Jellyfin: Requires MediaInfo library installed on server
- For Navidrome: Requires proper file tagging and audio analysis

## Testing

Run these diagnostic scripts to check what your servers have:

```bash
# Check what metadata fields are available from your servers
python diagnose_metadata.py

# Test the converter functions work correctly
python test_converters.py

# Test the full workflow (converter + database)
python test_full_workflow.py
```

## Code Changes Summary

### Files Modified:
1. **database/music_database.py**
   - Lines 214-245: CREATE TABLE tracks with 26 columns
   - Lines 1345-1415: insert_or_update_soul_sync_track() method

2. **providers/jellyfin/adapter.py**
   - Lines 17-145: convert_jellyfin_track_to_soulsync() function (updated to access wrapper _data)

3. **providers/navidrome/adapter.py**
   - Lines 19-145: convert_navidrome_track_to_soulsync() function (updated to access wrapper _data)

4. **providers/plex/adapter.py**
   - Lines 17-111: convert_plex_track_to_soulsync() function (unchanged, already working)

5. **providers/jellyfin/client.py**
   - Lines 789-823: get_tracks_for_album() updated with Fields parameter
   - Lines 1662-1700: Added get_album_tracks_as_soulsync() method

6. **providers/navidrome/client.py**
   - Lines 960-993: Added get_album_tracks_as_soulsync() method

## Verification

All tests confirm:
- ✅ Converters extract fields when present in source data
- ✅ Database accepts and stores all new fields
- ✅ NULL values handled correctly
- ✅ Client methods properly call converters
- ✅ Database update worker flow is complete

## Next Steps

1. **Run diagnostic**: `python diagnose_metadata.py` to see what fields your servers have
2. **Enable metadata enrichment** on your Plex/Jellyfin/Navidrome servers
3. **Run full refresh** from the SoulSync UI
4. **Verify database**: Check if new fields are now populated with actual values
5. **Investigate metadata gaps**: If fields are still NULL, check server settings/metadata agents

## Conclusion

The infrastructure is complete and working. Fields will be populated IF AND ONLY IF your Plex/Jellyfin/Navidrome servers have that metadata available. This is the correct behavior - the system extracts whatever the server provides and stores it.
