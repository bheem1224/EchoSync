# SoulSync MatchService - Quick Reference Card

## Import Everything You Need

```python
from core import (
    # Data model
    SoulSyncTrack,
    
    # Services
    MatchService,
    TrackParser,
    PostProcessor,
    
    # Contexts
    MatchContext,
    
    # Convenience functions
    get_match_service,
    find_best_match,
    parse_and_match,
)
```

---

## One-Line Examples

### Parse a Filename
```python
track = MatchService().parse_filename("Artist - Song Title (Remix) [FLAC]")
```

### Compare Two Tracks
```python
result = MatchService().compare_tracks(track_a, track_b, context=MatchContext.DOWNLOAD_SEARCH)
print(f"Score: {result.confidence_score}%")
```

### Find Best Match
```python
best = MatchService().find_best_match(source, candidates, context=MatchContext.DOWNLOAD_SEARCH)
print(f"Match: {best.candidate_track.title} ({best.confidence_score}%)")
```

### Find Top 10 Matches
```python
top_10 = MatchService().find_top_matches(source, candidates, top_n=10, min_confidence=70)
```

### Parse + Match in One Call
```python
best = MatchService().parse_and_match("Artist - Song", candidates)
```

### Tag a Music File
```python
PostProcessor().write_tags(Path("song.mp3"), track, cover_art_url="https://...")
```

### Organize Files
```python
PostProcessor().organize_file(
    Path("downloads/song.flac"),
    track,
    pattern="{Artist}/{Year} - {Album}/{TrackNumber}. {Title}{ext}",
    destination_dir=Path("/organized_music")
)
```

---

## Context Selection

| What You're Doing | Context | Threshold |
|-------------------|---------|-----------|
| Syncing watch lists | `EXACT_SYNC` | 85% |
| Downloading from SoulSeek | `DOWNLOAD_SEARCH` | 70% |
| Scanning local library | `LIBRARY_IMPORT` | 65% |

---

## Create a SoulSyncTrack

### Minimal (Just Required)
```python
track = SoulSyncTrack(
    title="Song Title",
    artist="Artist Name",
    duration_ms=180000,
)
```

### Complete (All Fields)
```python
track = SoulSyncTrack(
    title="Song Title",
    artist="Artist Name",
    album="Album Name",
    year=2024,
    duration_ms=180000,
    version="Remix",
    quality_tags=["FLAC", "24bit"],
    is_compilation=False,
    disc_number=1,
    track_number=1,
    track_total=12,
    extra_metadata={"key": "value"},
    external_ids={"spotify": "id123"},
)
```

---

## Result Objects

### MatchResult (from compare_tracks)
```python
result = service.compare_tracks(track_a, track_b)

# Access:
result.confidence_score  # 0-100
result.reasoning         # Why this score?
result.passed_gates      # Which gates? (version, edition, text, etc)
result.failed_gates      # Which gates failed?
```

### MatchCandidate (from find_best_match)
```python
match = service.find_best_match(source, candidates)

# Access:
match.candidate_track      # The SoulSyncTrack object
match.confidence_score     # 0-100
match.result              # Full MatchResult with reasoning
match.rank                # Position in list
```

### TagWriteResult (from write_tags)
```python
result = processor.write_tags(path, track)

# Access:
result.success            # True if all tags written
result.errors             # List of error messages
result.tags_written       # Which tags were set
result.cover_art_embedded # Cover art success?
```

---

## Error Handling Pattern

```python
from core import MatchService, MatchContext

service = MatchService()

try:
    # Do matching
    result = service.compare_tracks(track_a, track_b)
    
    if result.confidence_score < 70:
        print(f"Low confidence: {result.reasoning}")
    else:
        print("Match found!")
        
except ValueError as e:
    print(f"Invalid input: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## Performance Tips

✅ **DO**:
- Cache MatchService instance (don't create new one each time)
- Use `min_confidence` filter in `find_top_matches()`
- Filter candidates before passing to match functions
- Leverage automatic caching for repeated queries

❌ **DON'T**:
- Create new MatchService for every call
- Match against 1000+ candidates without filtering
- Parse same filename multiple times (it's cached)
- Ignore the confidence_score threshold

---

## Pattern Matching Examples

### Find Best Download from Search Results
```python
service = MatchService()

# Parse what user is looking for
target = service.parse_filename("The Weeknd - Blinding Lights")

# Get candidates from SoulSeek
soulseek_results = ...

# Find best download
best_download = service.find_best_match(
    target,
    soulseek_results,
    context=MatchContext.DOWNLOAD_SEARCH
)

if best_download and best_download.confidence_score > 70:
    enqueue_download(best_download.candidate_track)
```

### Sync Watch List Entry
```python
service = MatchService()

# Watch list entry
watch_list_entry = SoulSyncTrack(...)

# Get candidates from TIDAL
tidal_results = ...

# Find exact match
best_sync = service.find_best_match(
    watch_list_entry,
    tidal_results,
    context=MatchContext.EXACT_SYNC
)

if best_sync and best_sync.confidence_score > 85:
    mark_as_synced(watch_list_entry)
```

### Scan and Tag Local Library
```python
service = MatchService()
processor = PostProcessor()

# Local file metadata
local_file = {
    "path": Path("/music/song.flac"),
    "title": "Song Name",
    "artist": "Artist Name",
}

# Get metadata from database
metadata_candidates = database.search_by_title(local_file["title"])

# Find match with fuzzy logic
best_match = service.find_best_match(
    SoulSyncTrack(
        title=local_file["title"],
        artist=local_file["artist"],
    ),
    metadata_candidates,
    context=MatchContext.LIBRARY_IMPORT
)

if best_match:
    # Tag the file
    processor.write_tags(
        local_file["path"],
        best_match.candidate_track,
        cover_art_url=best_match.candidate_track.cover_art_url
    )
```

---

## Debugging

### See What Matched
```python
result = service.compare_tracks(track_a, track_b)
print(f"Score: {result.confidence_score}")
print(f"Reasoning: {result.reasoning}")
print(f"Passed gates: {result.passed_gates}")
print(f"Failed gates: {result.failed_gates}")
```

### See Top Candidates
```python
matches = service.find_top_matches(source, candidates, top_n=5)
for match in matches:
    print(f"#{match.rank}: {match.candidate_track.title} ({match.confidence_score}%)")
    print(f"  Why: {match.result.reasoning}")
```

### Check Parser Output
```python
parsed = service.parse_filename("Artist - Song [FLAC 24bit]")
print(f"Title: {parsed.title}")
print(f"Artist: {parsed.artist}")
print(f"Quality: {parsed.quality_tags}")
print(f"Version: {parsed.version}")
```

---

## Cache Management

### Clear All Caches
```python
from core import clear_cache
clear_cache()
```

### Auto-Cleanup Expired
```python
from core import cleanup_expired_cache
cleanup_expired_cache()  # Runs automatically in background
```

### Get Cache Instance
```python
from core import get_cache
cache = get_cache()
# For advanced cache operations
```

---

## Scoring Formula (Reference)

### EXACT_SYNC (85% Threshold)
```
Title Match: 0-50 points
Duration Match: 0-30 points
Quality Bonus: 0-20 points
Version Penalty: -15 points
Edition Penalty: -10 points
```

### DOWNLOAD_SEARCH (70% Threshold)
```
Title Match: 0-40 points
Duration Match: 0-35 points
Quality Bonus: 0-25 points
Version Penalty: -5 points
Edition Penalty: -5 points
```

### LIBRARY_IMPORT (65% Threshold)
```
Title Match: 0-35 points
Duration Match: 0-45 points (prioritized)
Quality Bonus: 0-20 points
Version Penalty: -3 points
Edition Penalty: -3 points
```

---

## Audio Formats Supported

| Format | Tag Type | Write | Read |
|--------|----------|-------|------|
| MP3 | ID3v2.4 | ✅ | ✅ |
| FLAC | Vorbis | ✅ | ✅ |
| OGG Vorbis | Vorbis | ✅ | ✅ |
| OGG Opus | Vorbis | ✅ | ✅ |
| M4A | iTunes | ✅ | ✅ |
| WAV | - | ❌ | - |
| WMA | - | ❌ | - |

---

## File Organization Pattern

Available substitution tokens:
- `{Artist}` - Artist name
- `{Album}` - Album name
- `{Title}` - Track title
- `{Year}` - Release year
- `{TrackNumber}` - Track number (0-padded to 2 digits)
- `{DiscNumber}` - Disc number
- `{Version}` - Version/remix info
- `{ext}` - File extension

Example patterns:
```python
# Flat
"{Artist} - {Title}{ext}"

# Classic
"{Artist}/{Album}/{TrackNumber}. {Title}{ext}"

# Grouped by Year
"{Artist}/{Year} - {Album}/{TrackNumber}. {Title}{ext}"

# By Disc
"{Artist}/{Album}/Disc{DiscNumber}/{TrackNumber}. {Title}{ext}"
```

---

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Score too low | Lower threshold or use more tolerant context (DOWNLOAD_SEARCH) |
| Parsing failed | Check raw string format, see `test_track_parser.py` for examples |
| No cover art | Pass `cover_art_url=None` to `write_tags()` |
| File already exists | PostProcessor auto-numbers: `song.mp3`, `song (1).mp3`, etc. |
| Permission denied | Check file permissions, might be read-only |
| Tags not written | Check mutagen is installed, fallback to no tags |

---

## Performance Benchmarks

- **Parse filename**: <10ms (cached on repeat)
- **Compare 2 tracks**: <50ms
- **Find best of 100**: <500ms
- **Find best of 1000**: <5 seconds
- **Write tags**: 50-200ms (depending on format)
- **Organize file**: 100-500ms (depends on disk speed)

---

## Troubleshooting Checklist

- [ ] Imported correct classes from `core`?
- [ ] Created SoulSyncTrack with at least `title`, `artist`, `duration_ms`?
- [ ] Specified `MatchContext` (EXACT_SYNC, DOWNLOAD_SEARCH, or LIBRARY_IMPORT)?
- [ ] Checked `confidence_score` against appropriate threshold?
- [ ] Handled `None` return values (empty candidate list)?
- [ ] Caught exceptions for file operations?
- [ ] Verified mutagen installed for tagging?

---

## See Also

- **Full Docs**: [PROJECT_COMPLETION_SUMMARY.md](./PROJECT_COMPLETION_SUMMARY.md)
- **Migration Guide**: [MIGRATION_GUIDE_STEP_17.md](./MIGRATION_GUIDE_STEP_17.md)
- **Status Report**: [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md)
- **Tests**: `tests/test_match_service_e2e.py` (usage examples)
- **Integration**: `tests/test_integration_pipeline.py` (real-world patterns)

---

**Quick Tip**: Start with `MatchService().find_best_match()` and go from there!
