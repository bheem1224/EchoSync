# Media Manager & Matching Engine

## 1. Overview

The Media Manager manages local library organization, audio fingerprinting, metadata enhancement, and recommendation scoring.

---

## 2. Ingestion Pipeline & AutoImporter

The AutoImporter monitors the download staging directory (`/data/downloads`) for newly completed audio files:

1. **File Detection:** File watcher triggers on new `.flac`, `.mp3`, `.m4a`, `.wav` files.
2. **Audio Tag & Chromaprint Extraction:** Native `echosync_core` extracts ID3/Vorbis tags and generates Chromaprint acoustic fingerprints using `lofty`.
3. **Metadata Matching:** `WeightedMatchingEngine` calculates confidence scores.
4. **Gatekeeper Relocation:** Authorized `Gatekeeper` transfers file from `/data/downloads` to `/data/library`.
5. **Database Binding:** Inserts canonical `Track` and `LocalMedia` records into `library.db`.

---

## 3. Weighted Matching Engine Scoring

Candidate tracks are scored using weighted comparison rules:

| Match Category | Weight % | Matching Logic |
| :--- | :--- | :--- |
| Acoustic Fingerprint | 40% | Chromaprint hash exact/fuzzy match via MusicBrainz FPID. |
| Track Title | 25% | Normalized string edit distance and token sorting. |
| Artist Name | 20% | Normalized primary and featured artist string comparison. |
| Duration Match | 10% | Strict temporal delta (< 2000ms difference). |
| Album Title | 5% | Fuzzy album name string comparison. |

---

## 4. Suggestion & Vibe Engine

The Suggestion Engine analyzes user listening behavior and audio features (tempo, energy, valence) to recommend tracks and automate library maintenance:

- **Content-Based Filtering:** Computes vibe profiles based on listening history.
- **Stale Track Pruning:** Flags tracks with low play counts or corrupt audio for review or quarantine.
- **Dynamic Recommendations:** Surfaces unacquired tracks matching vibe signatures into `working.db` suggestion queue.
