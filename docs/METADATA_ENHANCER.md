# 🏷️ The Metadata Enhancer

The Metadata Enhancer (`services/metadata_enhancer.py`) is a background worker that continuously monitors and self-heals your local library's metadata.

## The Local-First Pipeline

To respect external API rate limits, the Enhancer strictly follows a 5-step local-first pipeline:

1.  **Path Mapping:** Container volume paths are translated to local paths (`PathMapper`).
2.  **Local Tag Parsing:** The physical file is scanned for existing ID3/Vorbis tags. If `TPE1` (Artist) or MBID/ISRC tags are present, they are extracted.
3.  **Database Fast-Path:** If the track already has a verified AcoustID in `music.db`, the network lookup is skipped.
4.  **Audio Fingerprinting:** `fpcalc` is used to generate an audio fingerprint.
5.  **Text Fallback:** If fingerprinting fails, the system falls back to a text-based lookup.

*Note:* Tracks that cannot be identified are marked with `musicbrainz_id = 'NOT_FOUND'` to prevent infinite reprocessing loops and API abuse.

## Duplicate Hygiene
The Duplicate Hygiene Service (`services/library_hygiene.py`) works alongside the Enhancer, bucketing tracks that share identical AcoustID fingerprint hashes into `auto_resolve` or `manual_review` queues to keep your library clean.

---

## 🪝 Plugin Hooks (v2.5.0)

*   `post_metadata_enhanced`: Triggered after a track has been fully tagged and saved.
*   `skip_acoustid_lookup`: Bypass the `fpcalc` generation and network AcoustID lookup. Useful if a plugin has already determined the exact MBID via another method (e.g., reading an accompanying `.nfo` file).
