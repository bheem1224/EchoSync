# EchoSync: The Advanced Home Lab Guide

Welcome to the deep dive. This guide is intended for sysadmins, data hoarders, and home lab enthusiasts who want to leverage the full power of EchoSync. Here, we cover advanced configurations, metadata enforcement, and exactly how EchoSync interacts with your network and file system.

## 1. Directory Structure & Volume Mounts

EchoSync relies on strict separation of state, configuration, and media. When setting up your Docker container, understand these internal paths:

* `/config`: Stores your `config.json` and the encrypted `config.db` (which holds your API keys, OAuth tokens, and server credentials). **Keep this backed up and secure.**
* `/data`: Stores `working.db` (job queues, review tasks) and `music.db` (your library metadata, sync history, Chromaprint hashes). 
* `/data/downloads`: The staging ground. This should point to the exact same location your `slskd` container downloads files to. 
* `/data/library`: Your final, organized library. Your media server (Plex/Jellyfin/Navidrome) should have read access to this exact directory.
* `/data/logs`: path whare all logs are sotred can be set by ECHOSYNC_LOG_DIR or defaults to /data/logs if not set
* `/data/plugins`: this is whare all downloaded plugins files live 


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
```

### The Import Workflow
1. **Detection:** The auto_import_scan background job watches `/downloads`.
2. **Analysis:** Files are hashed via Chromaprint and queried against AcoustID/MusicBrainz.
3. **Thresholding:** If the match confidence is ≥ 85% (Default EXACT_SYNC profile), the file is tagged (ID3v2.4/Vorbis) and moved to `/library`.
4. **Review Queue:** If confidence is below the threshold, it is parked in the database under `review_tasks`. You must manually approve or reject these via the Web UI.

## 🎛️ Quality Profiles: The Waterfall Engine

In EchoSync, downloading music isn't a blind grab. The Quality Profile acts as a strict set of gatekeepers to ensure you get exactly the file type, bitrate, and size you want from the Slskd network. 

Instead of a simple "Allowed File Types" list, EchoSync uses a **Cascading Waterfall** system based on Priorities. 

### 1. The Priority Waterfall
You can define multiple tiers for a single profile. The engine will relentlessly search the network for a file that matches your **Priority 1** rules. If the search times out without finding a match, it gracefully falls back to **Priority 2**, and so on.

### 2. Defeating "Fake FLACs" with Granular Rules
Because the Slskd network contains upscaled/fake FLAC files, EchoSync lets you create multiple rules for the same file type. 
For example, you can set:
* **Priority 1 (Strict FLAC):** Must be exactly 44.1kHz or 48kHz, minimum 35MB. (Files with strict attributes are rarely faked).
* **Priority 2 (Loose FLAC):** Any FLAC, minimum 20MB. (Fallback if a highly verified FLAC isn't found).
* **Priority 3 (MP3):** Any MP3.

*(Note: You do not need to create multiple MP3 tiers like "320kbps" and "256kbps". EchoSync inherently prefers higher quality files within the same tier!)*

### 3. Tie-Breakers: How it chooses
If EchoSync finds two files on the network that *both* perfectly match your Priority 1 rules (e.g., one is 26MB and one is 30MB), it must decide which one to grab based on your Tie-Breaker Strategy:
* **Max Quality (Largest File):** It will download the larger file, assuming the larger size equates to a slightly better compression ratio or embedded high-res art.
* **Speed (First Match):** It will simply grab the very first file it found that meets the baseline rules, speeding up the overall download process.
* **Save Storage (Smallest File) [Pending v2.5.0 WebUI Update]:** Designed for datahoarders and mobile syncers. If two files meet your strict quality rules, this strategy will actively prefer the *smaller* file to save disk space.

## 4. Multi-Database Architecture
If you need to query EchoSync manually or perform backups, note the Alembic-managed database split:

* **config.db:** Highly sensitive. AES-encrypted. Contains your Plex tokens, Spotify client secrets, and slskd passwords.
* **music.db:** Your audio metadata truth. Safe to query for Grafana dashboards (e.g., tracking your library size, sync history, or matched track counts).
* **working.db:** Ephemeral state. Holds active background jobs, retries, and rate-limit tracking. Safe to wipe if the system gets totally stuck.

## 5. Security & Plugins (The Zero-Trust Sandbox)

EchoSync v2.4.1+ introduces the "Total Freedom" architecture, allowing the community to build powerful plugins. To keep your home lab secure, EchoSync runs a strict security model:

* **The AST Sandbox:** When you install a community plugin, it doesn't just run blindly. EchoSync uses an Abstract Syntax Tree (AST) Scanner to read the plugin's code before it loads. If a plugin attempts to use dangerous Python modules (like `os` to delete files or `subprocess` to run terminal commands), EchoSync instantly blocks the plugin from loading.
* **Safe File Management:** Because raw file access is blocked, plugins must use EchoSync's internal handlers. This guarantees that a community plugin can only modify media within your defined `/library` and `/downloads` folders, preventing it from touching the rest of your server.
* **Privileged Mode:** Sometimes, advanced plugins (like a heavy audio analyzer) actually *need* system access. These plugins must declare `"privileged": true` in their manifest. EchoSync will explicitly warn you in the Web UI before you install them, putting the final security decision in your hands.
* **Safe Mode:** If a plugin crashes the app during boot, the "Circuit Breaker" activates. EchoSync will reboot in Safe Mode, temporarily disabling all community plugins so you can access the Web UI and fix the issue.

## 6. Centralized Rate Limiting
To prevent API bans from MusicBrainz or AcoustID, EchoSync routes all outbound requests through a central RequestManager. The default rate limit is **1 request per second** and can be overridden per provider in `config.json`.
* MusicBrainz is strictly locked to 1 request/second.
* Spotify utilizes adaptive exponential backoff when it encounters 429 Too Many Requests.
You do not need to configure this; the core handles it autonomously.

## 7. Troubleshooting & Logs
By default, logs are written to the console and to `/data/logs`.

* **Database Locks:** If you see database is locked, ensure your database workers aren't set too high for your storage speed.
* **Phantom Tracks:** If your track count inflates without new files, check your Sync History in the UI. Ensure tracks aren't getting trapped as "orphans" (tracks with database entries but missing physical files or external provider links).
