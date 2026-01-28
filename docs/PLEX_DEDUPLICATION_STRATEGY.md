# Provider-Agnostic Track Deduplication & Incremental Update Strategy

> **Note**: This is now integrated into the core bulk import process. No separate script needed.

## Problem Statement

1. **Data Corruption**: Track metadata gets split/corrupted during imports
2. **Duplicate Tracks**: Same provider track (identified by unique ID) exists as multiple database entries
3. **Cross-Provider**: Issue affects Plex (ratingKey), Jellyfin (ID), Navidrome (ID), etc.
4. **Failed Matching**: Corrupted or duplicate entries prevent successful track matching

Examples:
- Plex: "Sweet Dreams (Are Made of This) - 2005 Remaster" stored as multiple rows
- Jellyfin: Same track appears twice with different metadata
- Navidrome: Duplicate entries from rescans

## Solution: Provider-Agnostic Deduplication

### Core Principle

**Each provider has a unique identifier that unambiguously identifies a single track:**

| Provider | Identifier | Type | Uniqueness |
|----------|-----------|------|-----------|
| Plex | `ratingKey` | String | Unique per track in library |
| Jellyfin | Item ID | String/GUID | Unique per track |
| Navidrome | Track ID | String | Unique per track |
| Spotify | Track ID | String | Unique globally |
| Tidal | Track ID | String | Unique globally |

**Strategy**: Check external identifiers FIRST during import. If an identifier already exists in the database, the incoming track IS the same as the existing entry → update, don't duplicate.

### Implementation

**Location**: `database/bulk_operations.py` → `_upsert_track()` method

**Logic** (lines 260-287):

```python
# FIRST: Check for existing external identifiers (provider-agnostic deduplication)
# If same external ID exists, it must be the same track - update instead of duplicate
track = None
if track_data.identifiers:
    for provider_source, provider_item_id in track_data.identifiers.items():
        if provider_source and provider_item_id:
            # Query: Does this (provider, ID) pair already exist?
            ext_id = session.query(ExternalIdentifier).filter(
                ExternalIdentifier.provider_source == provider_source,
                ExternalIdentifier.provider_item_id == str(provider_item_id)
            ).first()
            
            if ext_id and ext_id.track:
                # MATCH! This external ID already linked to a track
                track = ext_id.track
                logger.debug(f"Deduplication: Found existing track with {provider_source} ID '{provider_item_id}'")
                break  # Use first match
```

**Works for**:
- ✅ Plex updates (same ratingKey → update existing)
- ✅ Jellyfin updates (same item ID → update existing)
- ✅ Navidrome updates (same track ID → update existing)
- ✅ Any new provider automatically supported

### Data Flow

```
Incoming track from provider
    ↓
Extract metadata + provider ID
    ↓
Create SoulSyncTrack with identifiers: {provider: ID}
    ↓
Call _upsert_track()
    ↓
├─ Check identifiers table for (provider, ID) match
│  ├─ FOUND → Update existing track (sparse update, preserve enrichments)
│  └─ NOT FOUND → Continue to next step
│
├─ Check other identifier methods (fingerprint, ISRC, etc.)
│  ├─ FOUND → Update existing
│  └─ NOT FOUND → Continue
│
├─ Check metadata (title + artist + duration)
│  ├─ FOUND → Update existing
│  └─ NOT FOUND → Create new track
│
└─ Commit to database
   ├─ New track created OR
   └─ Existing track updated with new/corrected metadata
```

## Benefits

### Prevents Duplicates
- Same Plex track can't create multiple DB entries (unique ratingKey)
- Same Jellyfin track can't create multiple DB entries (unique item ID)
- Applies automatically to all providers

### Fixes Corruption
- Incoming clean metadata from provider overwrites corrupted data
- "Sweet Dreams (Are Made of This) - 2005 Remaster" replaces corrupted "Sweet Dreams - titile"
- Title corrections applied incrementally on each import

### Non-Invasive
- Uses existing sparse update system (only updates non-None fields)
- Preserves enrichments from other sources (metadata, ratings, etc.)
- No data loss

### Automatic
- Integrated into normal bulk import process
- No special scripts or manual operations needed
- Works on incremental updates (sync library button, playlist re-import, etc.)

## Testing

### Scenario 1: Plex Duplicate Prevention

**Setup**:
- Database has corrupted track: "Sweet Dreams - titile" (id=1, plex_id="abc123")
- Plex sends: "Sweet Dreams (Are Made of This) - 2005 Remaster" (ratingKey="abc123")

**Process**:
1. Extract: SoulSyncTrack with `identifiers={'plex': 'abc123'}`
2. Query: `SELECT * FROM external_identifiers WHERE provider_source='plex' AND provider_item_id='abc123'`
3. FOUND: Links to track id=1
4. Update: Track 1 title changed from "Sweet Dreams - titile" → "Sweet Dreams (Are Made of This) - 2005 Remaster"
5. Result: ONE track with corrected title

**Before/After**:
```
BEFORE:
  Track 1: "Sweet Dreams - titile" by WALK THE MOON (plex_id: abc123)

AFTER:
  Track 1: "Sweet Dreams (Are Made of This) - 2005 Remaster" by WALK THE MOON (plex_id: abc123)
```

### Scenario 2: Multiple Provider Sync

**Setup**:
- Plex and Jellyfin both have the same track
- Plex imports first, then Jellyfin

**Process**:
1. Plex import: Creates track with identifier `{plex: 'plex-123'}`
2. Jellyfin import: Has identifier `{jellyfin: 'jf-456'}`
3. Jellyfin's dedup check finds NO match (different provider ID)
4. Metadata check finds match (title + artist + duration)
5. Updates existing track, adds new identifier: `{plex: 'plex-123', jellyfin: 'jf-456'}`
6. Result: Single track with references to both providers

**Before/After**:
```
BEFORE:
  Track 1: "Song" (plex: plex-123)
  Track 2: "Song" (jellyfin: jf-456)

AFTER:
  Track 1: "Song" (plex: plex-123, jellyfin: jf-456)
```

## Configuration

Add to `config.json` for fine-tuning:

```json
{
  "database": {
    "deduplication": {
      "enabled": true,
      "strategy": "identifier_first",
      "preserve_enrichments": true,
      "log_level": "debug"
    }
  }
}
```

- `enabled`: Toggle deduplication (default: true)
- `strategy`: "identifier_first" (check external IDs first) - currently only option
- `preserve_enrichments`: Never overwrite ratings, tags, user metadata (default: true)
- `log_level`: "debug" logs all dedup matches, "info" logs only conflicts

## Architecture Notes

### Why Check External ID First?

**External identifiers are the most reliable match** because:
1. Immutable: Provider never changes a track's ID
2. Unique: No two tracks share same ID within provider
3. Authoritative: Provider is source-of-truth for that data
4. Global: Works across all providers without custom logic

### Why Not Just Check Metadata?

Metadata can be:
- Incomplete (missing artist, album)
- Ambiguous ("Song" by "A" could match 100 tracks)
- Corrupted (as seen in your data)
- Subjective (different normalization rules per provider)

External IDs sidestep all these issues.

### Sparse Updates

When updating existing tracks:
- Only non-None fields from incoming data replace database values
- Missing fields in incoming data don't erase database values
- Preserves enrichments from other sources

Example:
```
Database track: {title: "Song", artist: "A", rating: 5, tags: ["fave"]}
Incoming Plex: {title: "Song", artist: "A", duration: 200}

Result: {title: "Song", artist: "A", duration: 200, rating: 5, tags: ["fave"]}
         ↑ from Plex            ↑ from Plex        ↑ preserved ↑ preserved
```

## Future Enhancements

1. **Conflict detection**: Log when different providers disagree on metadata
2. **Merge strategy**: Configurable rules for combining multi-provider data
3. **Audit trail**: Track all deduplication actions for recovery
4. **Batch cleanup**: Periodic scan for orphaned identifiers
5. **Cross-provider matching**: Resolve Plex→Jellyfin→Navidrome chains

