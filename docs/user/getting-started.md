# Getting Started with EchoSync

## 1. Overview

EchoSync is a high-performance, self-hosted music management, auto-tagging, metadata enhancement, and acquisition platform. It coordinates local physical music libraries, remote virtual tracks, download providers, and streaming integrations.

---

## 2. Quickstart via Docker Compose

The recommended production setup uses Docker Compose. EchoSync separates configuration, working data, logs, and media storage into distinct volume mounts.

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
      - MASTER_KEY=${MASTER_KEY} # 32-byte url-safe base64 key
      - ECHOSYNC_LOG_DIR=/data/logs
      - ECHOSYNC_ENV=production
    volumes:
      - ./config:/config
      - ./data:/data
      - /mnt/storage/downloads:/data/downloads
      - /mnt/storage/music:/data/library
      - ./plugins:/data/plugins
```

---

## 3. Directory Structure & Volume Mounts

EchoSync enforces strict separation of state, configuration, and media across volume mounts:

- `/config`: Contains `config.json` and encrypted `config.db` (stores settings, service credentials, OAuth tokens).
- `/data`: Holds `working.db` (ephemeral task state, ingestion queues) and `music.db` (`library.db`, canonical entity graph).
- `/data/downloads`: Download staging ground shared with slskd or other downloaders.
- `/data/library`: Organized target music library directory for Plex/Jellyfin/Navidrome.
- `/data/logs`: Operational event and error logs.
- `/data/plugins`: Storage directory for installed plugins.

---

## 4. Master Key Generation

EchoSync requires a master encryption key to encrypt tokens and credentials in `config.db`. Generate a key using Python:

```bash
export MASTER_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

---

## 5. First Boot Verification

Once launched, visit `http://localhost:8000` in your web browser. Confirm the backend health status:

```bash
curl -s http://localhost:8000/api/system/health | jq
```
