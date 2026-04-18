```markdown
# EchoSync: The Advanced Home Lab Guide

Welcome to the deep dive. This guide is intended for sysadmins, data hoarders, and home lab enthusiasts who want to leverage the full power of EchoSync. Here, we cover advanced configurations, metadata enforcement, and exactly how EchoSync interacts with your network and file system.

## 1. Directory Structure & Volume Mounts

EchoSync relies on strict separation of state, configuration, and media. When setting up your Docker container, understand these internal paths:

* `/config`: Stores your `config.json` and the encrypted `config.db` (which holds your API keys, OAuth tokens, and server credentials). **Keep this backed up and secure.**
* `/data`: Stores `working.db` (job queues, review tasks) and `music.db` (your library metadata, sync history, Chromaprint hashes). 
* `/downloads`: The staging ground. This should point to the exact same location your `slskd` container downloads files to. 
* `/library`: Your final, organized library. Your media server (Plex/Jellyfin/Navidrome) should have read access to this exact directory.
* `/logs`: path whare all logs are sotred can be set by ECHOSYNC_LOG_DIR or defaults to /data/logs if not set


## 2. The Auto-Importer & File Organization

EchoSync doesn't just download files; it sanitizes and organizes them. This is controlled by the `file_organization` and `metadata_enhancement` blocks in your `config.json`.

### Organization Templates
You can dynamically format your directory structure using variables. 
```json
"file_organization": {
  "enabled": true,
  "templates": {
    "album_path": "$albumartist/$albumartist - $album/$track - $title",
    "single_path": "$artist/$artist - $title/$title",
    "playlist_path": "$playlist/$artist - $title"
  }
}

The Import Workflow
Detection: The auto_import_scan background job watches /downloads.

Analysis: Files are hashed via Chromaprint and queried against AcoustID/MusicBrainz.

Thresholding: If the match confidence is ≥ 85% (Default EXACT_SYNC profile), the file is tagged (ID3v2.4/Vorbis) and moved to /music.

Review Queue: If confidence is below the threshold, it is parked in the database under review_tasks. You must manually approve or reject these via the Web UI.

3. Quality Profiles (The Soulseek Engine)
EchoSync treats Soulseek as a targeted acquisition engine, not a blind downloader. The quality_profile determines exactly what is accepted.

JSON
"quality_profile": {
  "preset": "balanced",
  "allowed_file_types": ["flac", "mp3_320", "mp3_256"],
  "min_file_size_mb": 0,
  "max_file_size_mb": 150,
  "min_bit_depth": 16,
  "min_bitrate_kbps": 256
}
Waterfall Logic: EchoSync will search slskd prioritizing the top of your allowed_file_types array (e.g., FLAC). If a match isn't found within your timeout window, it cascades down to mp3_320, and so on.

Fake FLAC Detection: The engine verifies bit depth and bitrate. Upscaled MP3s labeled as FLAC are penalized in the scoring engine.

4. Multi-Database Architecture
If you need to query EchoSync manually or perform backups, note the Alembic-managed SQLite split:

config.db: Highly sensitive. AES-encrypted. Contains your Plex tokens, Spotify client secrets, and slskd passwords.

music.db: Your audio metadata truth. Safe to query for Grafana dashboards (e.g., tracking your library size, sync history, or matched track counts).

working.db: Ephemeral state. Holds active background jobs, retries, and rate-limit tracking. Safe to wipe if the system gets totally stuck.

5. Centralized Rate Limiting
To prevent API bans from MusicBrainz or AcoustID, EchoSync routes all outbound requests through a central RequestManager.

MusicBrainz is strictly locked to 1 request/second.

Spotify utilizes adaptive exponential backoff when it encounters 429 Too Many Requests.

You do not need to configure this; the core handles it autonomously.

6. Zero-Trust Plugin Sandbox
EchoSync embraces the **Total Freedom Plugin Architecture**. If you are writing community plugins to manipulate metadata, inject new API routes, or add webhooks via the `core.hook_manager`, be aware of the AST Sandbox.

- Plugins cannot import `os`, `sys`, `subprocess`, or write arbitrarily to the file system outside of the `CUSTOM_FILE_IO` hook.
- Your plugin will automatically be skipped during boot if it throws an unhandled exception, ensuring your core sync jobs never go offline due to a bad community script.
- For a full list of available hooks to interact with the core engine, see `docs/HOOKS_REFERENCE.md`.

7. Troubleshooting & Logs
By default, logs are written to the console and to /data/logs.

Database Locks: If you see database is locked, ensure your database.max_workers in config.json isn't set too high for your storage speed (Default is 2).

Phantom Tracks: If your track count inflates without new files, check your Sync History in the UI. Ensure tracks aren't getting trapped as "orphans" (tracks with database entries but missing physical files or external provider links).