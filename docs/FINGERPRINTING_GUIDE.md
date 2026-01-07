# Chromaprint Fingerprinting Integration

## Overview

SoulSync now supports **Chromaprint** audio fingerprinting for high-accuracy track matching. Fingerprints are particularly useful for library imports where filenames or tags may be unreliable, but the audio itself is trustworthy.

## Key Features

### 1. Automatic Fingerprint Generation
The `TrackParser` can automatically generate fingerprints from audio files:

```python
from core.track_parser import parse_file

# Parse a file and generate its Chromaprint fingerprint
track = parse_file("path/to/song.flac", generate_fingerprint=True)
print(track.fingerprint)  # Chromaprint string
```

### 2. Fingerprint-Based Matching
The `WeightedMatchingEngine` prioritizes fingerprint matching when available:

- If fingerprints match exactly → **immediate 100% confidence** (other checks skipped)
- If no fingerprints → falls back to text/duration matching
- Configurable fingerprint weight in scoring profiles

### 3. Smart Profile Fallback (LIBRARY_IMPORT)

For library imports, SoulSync uses context-aware profile selection:

| Scenario | Profile Used | Weights |
|----------|-------------|---------|
| **With fingerprints** | Profile 3 (Primary) | 60% fingerprint, 30% duration, 10% text |
| **Without fingerprints** | Profile 2 (Fallback) | 40% text, 20% duration, 25% quality bonus |

This ensures maximum accuracy when fingerprints are available, but still works gracefully when they're not.

### 4. Fingerprint Caching

Fingerprints are cached in `music_library.db` to avoid regenerating them:

```python
from core.fingerprinting import FingerprintCache

cache = FingerprintCache("data/music_library.db")

# Get cached fingerprint
fp = cache.get("path/to/song.flac")

# Cache a new fingerprint
cache.set("path/to/song.flac", fingerprint_string)

# Clear old fingerprints
cache.clear_expired(days=30)
```

## Installation

Chromaprint support requires `pyacoustid`:

```bash
pip install pyacoustid
```

### Optional: Chromaprint Library

For full fingerprinting (not just AcousticID lookup), install Chromaprint:
- **Windows**: `choco install chromaprint`
- **macOS**: `brew install chromaprint`
- **Linux**: `apt-get install chromaprint-fpcalc`

Without the Chromaprint library, fingerprinting will use AcousticID API for fingerprint submission.

## Configuration

### Matching Profiles

Three scoring profiles are configurable in `config/config.json`:

```json
{
  "matching_profiles": {
    "EXACT_SYNC": {
      "description": "Strict matching for Spotify→Tidal syncing",
      "text_weight": 0.35,
      "duration_weight": 0.20,
      "fingerprint_weight": 0.25,
      "quality_bonus": 0.10,
      "version_mismatch_penalty": 50,
      "edition_mismatch_penalty": 40,
      "fuzzy_match_threshold": 0.85
    },
    "DOWNLOAD_SEARCH": {
      "description": "Tolerant matching for P2P sources (Soulseek)",
      "text_weight": 0.40,
      "duration_weight": 0.20,
      "fingerprint_weight": 0.15,
      "quality_bonus": 0.25,
      "version_mismatch_penalty": 50,
      "edition_mismatch_penalty": 30,
      "fuzzy_match_threshold": 0.65
    },
    "LIBRARY_IMPORT": {
      "primary_profile_with_fingerprint": {
        "text_weight": 0.10,
        "duration_weight": 0.30,
        "fingerprint_weight": 0.60,
        "quality_bonus": 0.0,
        "version_mismatch_penalty": 20,
        "edition_mismatch_penalty": 20,
        "fuzzy_match_threshold": 0.5
      },
      "fallback_profile_no_fingerprint": {
        "text_weight": 0.40,
        "duration_weight": 0.20,
        "fingerprint_weight": 0.0,
        "quality_bonus": 0.25,
        "version_mismatch_penalty": 50,
        "edition_mismatch_penalty": 30,
        "fuzzy_match_threshold": 0.65
      }
    }
  }
}
```

**For advanced users**: Edit these weights directly in `config.json` to customize matching behavior. No WebUI changes needed - the system reads from config on startup.

## Usage Examples

### Example 1: Parse and Match with Fingerprint

```python
from core.match_service import MatchService, MatchContext
from core.track_parser import parse_file
from core.models import SoulSyncTrack

service = MatchService()

# Parse local file with fingerprint
local_track = parse_file("C:/Music/song.flac", generate_fingerprint=True)

# Create candidate from metadata API
candidate = SoulSyncTrack(
    title="Song Title",
    artist="Artist Name",
    album="Album",
    duration_ms=180000,
    fingerprint="AcQd-E..."  # From MusicBrainz AcousticID
)

# Find match (will use fingerprint first if available)
result = service.find_best_match(
    local_track,
    [candidate],
    context=MatchContext.LIBRARY_IMPORT
)

print(f"Match: {result.candidate_track.title} ({result.confidence_score}%)")
```

### Example 2: Batch Library Import with Fingerprinting

```python
from pathlib import Path
from core.track_parser import parse_file
from core.match_service import get_match_service, MatchContext

service = get_match_service()

# Parse all local files
local_files = list(Path("C:/Music").glob("**/*.flac"))
local_tracks = [
    parse_file(str(f), generate_fingerprint=True) 
    for f in local_files
]

# Get candidates from metadata provider (your provider)
candidates = your_metadata_provider.search(local_tracks)

# Match with fingerprint-first profile
for track, candidate_list in zip(local_tracks, candidates):
    best_match = service.find_best_match(
        track,
        candidate_list,
        context=MatchContext.LIBRARY_IMPORT
    )
    if best_match:
        print(f"{track.title} → {best_match.candidate_track.title}")
```

### Example 3: Fallback Behavior

```python
# Track with fingerprint - uses LIBRARY_IMPORT Profile 3
track_with_fp = SoulSyncTrack(
    title="Unknown", 
    artist="Unknown",
    fingerprint="AcQd-E..."  # Has fingerprint
)

# Track without fingerprint - automatically falls back to DOWNLOAD_SEARCH logic
track_no_fp = SoulSyncTrack(
    title="Track Name",
    artist="Artist Name"
    # No fingerprint
)

# Both will work, but with different strategies:
service.find_best_match(track_with_fp, candidates, MatchContext.LIBRARY_IMPORT)    # Fingerprint-first
service.find_best_match(track_no_fp, candidates, MatchContext.LIBRARY_IMPORT)      # Falls back to text/duration
```

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Fingerprint generation | 5-15 sec | First run; depends on file codec |
| Fingerprint lookup (cached) | <1 ms | Database query |
| Fingerprint comparison | <1 ms | Chromaprint comparison |
| Text match (no fingerprint) | 1-2 ms | Standard fuzzy matching |

**Caching Impact**: 10,000 track library with fingerprints cached reduces matching time from hours to seconds.

## Troubleshooting

### "pyacoustid not installed" Warning

```bash
# Install the dependency
pip install pyacoustid
```

### Fingerprint Generation Fails

Check that:
1. File format is supported (MP3, FLAC, M4A, OGG, WAV, etc.)
2. File is not corrupted
3. Chromaprint library is installed (optional but improves compatibility)

```python
from core.fingerprinting import FingerprintGenerator

# Check if file can be fingerprinted
if FingerprintGenerator.can_fingerprint("path/to/file.flac"):
    fp = FingerprintGenerator.generate("path/to/file.flac")
    print(f"Generated: {fp}")
```

### Profile Not Loading from Config

1. Ensure `config/config.json` exists in the project root
2. Check that `matching_profiles` section exists
3. Verify JSON syntax is valid
4. Check application logs for load errors

```python
from core.scoring.scoring_profile import ProfileFactory

# Check which profiles loaded
config_profiles = ProfileFactory._load_config_profiles()
print("Loaded profiles:", config_profiles.keys())
```

## Technical Details

### Fingerprint Fields

`SoulSyncTrack` now includes:
- `fingerprint: Optional[str]` - Chromaprint fingerprint string
- `fingerprint_confidence: Optional[float]` - Confidence of generation (0-1)

### Matching Engine Behavior

**With Fingerprints:**
1. Compare fingerprints → if match, return 100% (authoritative)
2. If no fingerprint match, fail gracefully

**Without Fingerprints:**
1. Check version compatibility
2. Check edition/track_total match
3. Fuzzy text matching (title, artist, album)
4. Duration matching with tolerance
5. Quality tie-breaker

### Database Schema

Fingerprint cache table:

```sql
CREATE TABLE fingerprint_cache (
    file_path TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    cached_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

## Best Practices

1. **Always cache fingerprints** - Set `fingerprint_cache` path when initializing `TrackParser`
2. **Use LIBRARY_IMPORT context** - For local files, use `MatchContext.LIBRARY_IMPORT` 
3. **Validate with duration** - Fingerprint should be confirmed with duration check
4. **Monitor fallbacks** - Check logs when LIBRARY_IMPORT falls back to DOWNLOAD_SEARCH (missing fingerprints)
5. **Update config carefully** - Test with a small batch before applying to large library

## See Also

- [MatchService API Documentation](IMPLEMENTATION_STATUS.md)
- [Weighted Matching Engine Details](BACKEND_ARCHITECTURE.md)
- [Configuration Reference](../config/config.example.json)
