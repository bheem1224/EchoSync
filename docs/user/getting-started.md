# Getting Started with EchoSync

## 1. Introduction

EchoSync is an advanced home lab music synchronization, acquisition, and management server. It automatically organizes audio libraries, enriches metadata, synchronizes with media servers (Plex, Navidrome, Jellyfin), and integrates with download acquisition networks.

---

## 2. Fast Deployment via Docker Compose

The recommended deployment method for EchoSync is Docker Compose.

```yaml
version: '3.8'

services:
  echosync:
    image: echosync/echosync:latest
    container_name: echosync
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - MASTER_KEY=YOUR_32_BYTE_BASE64_FERNET_KEY
      - ECHOSYNC_LOG_DIR=/data/logs
    volumes:
      - ./config:/config
      - ./data:/data
      - /mnt/storage/music:/data/library
      - /mnt/downloads/slskd:/data/downloads
```

---

## 3. Storage Mount Paths

Proper volume mounting is critical for EchoSync file management:

- `/config`: Holds system settings (`config.json`) and `config.db`.
- `/data`: Holds `working.db` and `library.db`.
- `/data/downloads`: Staging folder for acquisition downloads (e.g. Slskd download complete folder).
- `/data/library`: Production organized music library folder where media servers read tracks.

---

## 4. First-Time Setup Wizard

1. Navigate to `http://localhost:8000` in your browser.
2. Complete the initial administrator password setup.
3. Configure your local storage paths (`/data/library` and `/data/downloads`).
4. Enable desired plugins (Plex, Slskd, MusicBrainz, AcoustID) in **Settings > Plugin Store**.
