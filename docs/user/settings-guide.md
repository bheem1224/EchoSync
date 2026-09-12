# Settings Lexicon & Configuration Schema

## 1. Overview

EchoSync configuration is managed via encrypted settings in `config.db` and exposed via `/api/v1/system/settings`. This document details the complete configuration lexicon, schema, default values, and operational impacts across all core systems.

---

## 2. Configuration Settings Lexicon

| Key | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `system.library_path` | `string` | `/data/library` | Root path to local physical music library |
| `system.download_path` | `string` | `/data/downloads` | Staging directory for incoming download tasks |
| `system.backup_dir` | `string` | `/config/backups` | Target directory for automated database backups |
| `system.log_level` | `string` | `"INFO"` | Logging verbosity (`"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`) |
| `system.max_workers` | `integer` | `4` | Worker thread pool count for background jobs |
| `metadata.auto_apply_confidence` | `float` | `0.90` | Match score threshold (0.00 to 1.00) required to auto-apply metadata without manual review |
| `metadata.acoustid_enabled` | `boolean` | `true` | Enable Stage 3 AcoustID acoustic fingerprint scans |
| `metadata.acoustid_sample_window` | `integer` | `120` | Rust Symphonia sample window cap in seconds for Chromaprint fingerprint generation |
| `metadata.acoustid_duration_gate` | `float` | `2.0` | Maximum allowed duration delta (seconds) between local track and AcoustID candidate |
| `metadata.musicbrainz_decay_factor` | `float` | `8.0` | Parabolic decay curve parameter for MusicBrainz text matching confidence scoring |
| `metadata.auto_fetch_cover_art` | `boolean` | `true` | Automatically fetch cover art images from Cover Art Archive / Spotify |
| `downloader.active_client` | `string` | `"slskd"` | Active downloader plugin handle (`"slskd"`, etc.) |
| `downloader.auto_download` | `boolean` | `false` | Automatically enqueue slskd downloads for missing library tracks |
| `downloader.max_concurrent_downloads` | `integer` | `3` | Maximum concurrent active download slots |
| `media_server.active_server` | `string` | `"plex"` | Active target media server plugin handle (`"plex"`, `"jellyfin"`, `"navidrome"`) |
| `media_server.auto_sync` | `boolean` | `true` | Automatically trigger media server library refresh on track promotion/ingestion |

---

## 3. Configuration Management Workflows

### Reading System Settings
```bash
curl -X GET "http://localhost:8000/api/v1/system/settings" \
     -H "Accept: application/json"
```

### Updating Settings via API
```bash
curl -X POST "http://localhost:8000/api/v1/system/settings" \
     -H "Content-Type: application/json" \
     -d '{
       "metadata.auto_apply_confidence": 0.88,
       "downloader.max_concurrent_downloads": 5
     }'
```

---

## 4. Troubleshooting Table

| Issue | Root Cause | Remediation |
| :--- | :--- | :--- |
| `400 Bad Request` on settings update | Type mismatch or invalid value range | Check field types in lexicon table (e.g. `auto_apply_confidence` must be between `0.0` and `1.0`) |
| Metadata scans skipping AcoustID | `metadata.acoustid_enabled` set to `false` or missing API key | Ensure `metadata.acoustid_enabled` is `true` and AcoustID provider key is configured |
| System logs too verbose | `system.log_level` set to `"DEBUG"` | Update `system.log_level` to `"INFO"` or `"WARNING"` |
