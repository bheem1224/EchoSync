# EchoSync 🎧
**The ultimate bridge between commercial streaming and your self-hosted audiophile library.**

[![Docker Pulls](https://img.shields.io/docker/pulls/bheem1224/EchoSync.svg)](https://hub.docker.com/r/bheem1224/EchoSync)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

EchoSync is a highly resilient, self-hosted middleware application designed to perfectly mirror your Spotify and Tidal playlists to your local media servers (Plex, Jellyfin, Navidrome). If a track is missing from your local library, EchoSync seamlessly interfaces with Soulseek (via slskd) to acquire it, perfectly tagging and organizing it along the way.

---

## ✨ Core Features & Architectural Pillars

EchoSync is built with an uncompromising focus on database integrity, security, and metadata resilience.

### 🧠 The Advanced Matching Engine
Commercial streaming metadata is notoriously messy. EchoSync features a custom-built fuzzy matching engine designed to conquer bilingual tags and inconsistent formatting:
* **Bilingual Failsafes:** Automatically transliterates Hanzi/Kanji to Pinyin and utilizes space-agnostic token-sort algorithms to match Eastern and Western name flips.
* **The "Double-Lock" Logic:** Safely maps combined artist names (e.g., `Faye 詹雯婷` vs `Faye`) without risking false-positive library corruption.
* **Dynamic Duration Amnesty:** Intelligently widens duration tolerances for unlabelled Extended/Album versions when exact semantic artist/title matches are proven.
* **CJK OST Extraction:** Aggressively scrubs injected lore, character names, and TV drama tags from track titles before scoring.

### 🏛️ Enterprise-Grade Architecture
* **The Database Bedrock:** Powered by strict Alembic migrations across a discrete multi-database environment (`config.db`, `working.db`, `music.db`).
* **Zero-Trust Plugin Sandbox:** Community plugins are executed in a strictly monitored AST (Abstract Syntax Tree) Sandbox that aggressively rejects the import of sensitive or destructive modules (`os`, `sys`, `subprocess`).
* **Self-Healing Metadata:** The background enhancer continuously sweeps your library, automatically fixing legacy "Various Artists" tagging errors by physically reading and prioritizing `TPE1` file tags.
* **Safe Mode Circuit Breaker:** Prevents fatal boot-loops by automatically bypassing community plugins if a crash is detected during the initialization sequence.

---

## 🔌 Supported Integrations

**Streaming Sources:**
* Spotify (Supports Multiple Accounts)

**Local Media Servers:**
* Plex
* Jellyfin
* Navidrome

**Acquisition & Metadata:**
* Soulseek (via slskd integration)
* MusicBrainz / ListenBrainz
* AcoustID (fpcalc audio fingerprinting)
* LRCLIB (Synchronized Lyrics)

---

## 🚀 Quick Start (Docker)

The easiest way to run EchoSync is via Docker Compose. 

```yaml
version: '3.8'
services:
  EchoSync:
    image: bheem1224/EchoSync:latest
    container_name: EchoSync
    ports:
      - "8080:8080"
    volumes:
      - ./config:/app/config
      - ./data:/app/data
      - /path/to/your/music:/music
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=America/New_York

🛠️ Tech Stack
Backend: Python 3.11+, Alembic, SQLite, FastAPI/Flask.

Frontend: Svelte, TailwindCSS, Vite.

Security: AES-encrypted credential storage (No plaintext API keys).

🤝 Contributing
Because EchoSync utilizes strict database migrations and an AST-sandboxed plugin architecture, please refer to our CONTRIBUTING.md and ARCHITECTURE_CORE.md before submitting PRs involving database models or plugin hooks.

📜 Origin & Acknowledgement
EchoSync began as a fork of Nezreka's Echosync. As we introduced Svelte, Alembic migrations, encrypted storage, and the Zero-Trust Sandbox, the codebase became a 100% structural rewrite. To respect the original author's namespace while reflecting the new architecture, the project was rebranded in v2.5.0. We thank Nezreka for the original inspiration!