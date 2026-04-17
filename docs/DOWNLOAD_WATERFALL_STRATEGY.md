# Download Manager: User-Defined Waterfall Fallback Strategy

## Overview

The DownloadManager now supports a sophisticated **User-Defined Provider Waterfall Fallback Strategy** that allows users to configure their preferred download provider priority. When downloading tracks, the system:

1. Tries each provider in user-defined priority order
2. Searches each provider with multiple strategies (artist+title, album+title, title-only)
3. Uses the Matching Engine to score candidates with a **Perfect Match threshold (≥90 score)**
4. If a perfect match is found, immediately downloads and breaks the waterfall
5. Tracks the best candidate across all providers
6. Downloads the best match found across all providers

## Architecture

### Components Modified

#### 1. Config Database (`database/config_database.py`)

Added two new methods to manage download provider priority:

```python
def get_download_provider_priority() -> List[str]:
    """Get the user-defined download provider priority list.
    Returns list of provider names in priority order (highest first).
    Example: ["slskd", "yt_dlp", "torrent"]
    """

def set_download_provider_priority(provider_list: List[str]) -> bool:
    """Set the user-defined download provider priority list.
    Stores as JSON in service_config table (service_id=NULL for global setting).
    """
```

**Storage:**
- Global setting stored in `service_config` table with `service_id=NULL`
- Key: `download_provider_priority`
- Value: JSON-encoded list of provider names
- Example: `["slskd", "yt_dlp", "torrent"]`

#### 2. Download Manager (`services/download_manager.py`)

**New Methods:**

##### `_get_active_download_providers() -> List[ProviderBase]`
- Fetches all providers from ProviderRegistry with `supports_downloads=True`
- Sorts them by user-defined priority from config database
- Filters out disabled providers
- Returns instantiated provider instances in priority order
- Falls back to registry order if no user priority is configured

##### `_execute_waterfall_search_and_download(download_id, providers)`
Replaces the old `_execute_search_and_download()` method with complete waterfall logic:

1. **Load Track**: Deserializes EchosyncTrack from queue payload (preserves metadata)
2. **Prepare Filters**: Gets quality profile and creates search filters
3. **Generate Strategies**: Creates search strategies (artist+title, album+title, title-only)

4. **Waterfall Loop**: For each provider in priority order:
   - Execute all search strategies
   - Deduplicate candidates
   - Run through quality profile priority tiers
   - Score with Matching Engine
   - If score ≥ 90 (perfect match):
     - Break immediately
     - Mark as winner
   - Otherwise:
     - Track best-so-far score
     - Continue to next provider

5. **Download Best**: 
   - Download using the winning provider
   - Update status to "downloading"

**Updated Method:**

##### `_process_queued_items()`
- Now calls `_get_active_download_providers()`
- Creates search tasks with full provider list
- Tasks use waterfall strategy instead of single provider

##### `_check_active_downloads()`
- Now tries to find provider_id across all active providers
- Handles downloads from multiple concurrent providers
- Continues searching providers until finding the active download

## Waterfall Algorithm Details

```
FOR each provider in user_priority_order:
  | 
  +--> FOR each search strategy (artist+title, album+title, title):
  |      |
  |      +--> GET results from provider
  |      |
  |      +--> Extend candidates list
  |
  +--> Deduplicate candidates
  |
  +--> FOR each quality_priority_tier:
  |      |
  |      +--> Filter candidates by format
  |      |
  |      +--> IF candidates exist:
  |             |
  |             +--> Run Matching Engine
  |             |
  |             +--> Get best candidate (highest score)
  |
  +--> IF best_candidate's score >= 90:
  |      |
  |      +--> MARK AS WINNER
  |      |
  |      +--> BREAK (exit provider loop)
  |
  +--> ELSE IF best_candidate's score > current_best_score:
         |
         +--> UPDATE best_candidate
         |
         +--> CONTINUE (try next provider)

DOWNLOAD best_candidate using winning_provider
```

## Configuration

### User-Defined Priority

Set provider priority via:

```python
from database.config_database import get_config_database

config_db = get_config_database()
priority_list = ["slskd", "yt_dlp", "torrent"]
config_db.set_download_provider_priority(priority_list)
```

Or retrieve current priority:

```python
current_priority = config_db.get_download_provider_priority()
# Returns: ["slskd", "yt_dlp", "torrent"]
# Or empty list if not configured
```

### Default Behavior

If no user-defined priority is configured:
- All active providers are tried in registry order
- Same waterfall logic applies

## Perfect Match Threshold

**Definition**: A match with confidence score ≥ 90%

**Behavior**:
- If any provider yields a score ≥ 90, **immediately** download from that provider
- This prevents unnecessary searching of lower-priority providers
- Speeds up successful downloads

**Scoring Details** (from Matching Engine):
- Metadata confidence: 0-100 points
- Quality bonuses: ±5-20 points for bitrate/peer stats
- Duration matching: Gated before scoring
- Final score used: metadata + quality adjustments

**Example Scenarios**:

| Match | Provider | Score | Action |
|-------|----------|-------|--------|
| Artist/Title perfect with good bitrate | Slskd | 95 | ✓ Download immediately, don't try yt-dlp |
| Album/Title good but not perfect | Slskd | 75 | Try next provider (yt-dlp) |
| Title-only weak match | Yt-dlp | 45 | Try next provider (torrent) |
| Best across all: Title-only | Torrent | 60 | Download best found (60 > 75 > 45) |

## Metadata Preservation

The waterfall strategy **reconstructs** the EchosyncTrack from the database queue payload:

```python
target_track = EchosyncTrack.from_dict(download.echo_sync_track)
```

This ensures **no metadata is lost**:
- ISRC codes ✓
- Album information ✓
- Artist name ✓
- Track duration ✓  
- All custom fields ✓

Therefore, each provider search uses complete metadata, enabling more accurate matching.

## Logging and Monitoring

The waterfall strategy provides detailed logging:

```
DEBUG: Trying search strategy 1/3 [artist+title] via slskd: query='Artist Song'
INFO: Strategy 1 returned 25 candidates
DEBUG: Priority 1: 20 candidates match formats
INFO: Got match on priority 1: score=92.5
INFO: ✓ PERFECT MATCH from slskd (score 92.5 >= 90)
INFO: **PROCEEDING WITH DOWNLOAD**
INFO: Track: Artist - Song
INFO: Provider: slskd
INFO: Match Score: 92.5
```

## Error Handling

The system gracefully handles:

- **Provider instantiation failure**: Continues with other providers
- **Search timeouts**: Logs warning, continues to next strategy
- **Provider-specific errors**: Tries next provider
- **No candidates found**: Falls through waterfall, attempts next provider
- **All providers exhausted**: Marks download as `failed_no_match`

## Performance Considerations

### Concurrency

- Downloads are processed with concurrent tasks (up to 30 queued items)
- Each provider has its own rate limiting and concurrency control
- Slskd: Max 3 concurrent searches (built-in IP ban protection)
- Other providers: Waterfall serializes per-provider but parallelizes strategies

### Status Checking

- `_check_active_downloads()` tries all providers to find active downloads
- Minimizes false "not found" cases when providers have staggered completions
- Handles downloads from multiple concurrent providers

## Future Extensions

The waterfall architecture supports:

1. **Per-Track Priority**: Different priority lists for different track types
2. **Dynamic Switching**: Adjust priority based on provider success rates
3. **Provider Weighting**: Use scores to adjust provider tryout order
4. **Fallback Strategies**: Different strategies for different media types
5. **Smart Caching**: Cache winning providers for similar tracks

## Testing

To test the waterfall strategy:

```python
# 1. Set priority
config_db = get_config_database()
config_db.set_download_provider_priority(["slskd", "yt_dlp"])

# 2. Queue a download
downloader = DownloadManager.get_instance()
track_id = downloader.queue_download(echo_sync_track)

# 3. Monitor logs for waterfall execution
# Logs will show provider tryout order and matching scores
```

## Backward Compatibility

The system is **fully backward compatible**:

- `_get_provider()` still works for legacy single-provider code
- Config database defaults to empty priority list
- Fallsback to first available provider if none configured
- Existing download status tracking unchanged
- No breaking changes to queue or database schema
