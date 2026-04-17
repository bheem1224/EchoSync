# EchoSync 🎧
**The ultimate bridge between commercial streaming and your self-hosted audiophile library.**

[![Docker Pulls](https://img.shields.io/docker/pulls/bheem1224/EchoSync.svg)](https://hub.docker.com/r/bheem1224/EchoSync)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

EchoSync is a highly resilient, self-hosted middleware application designed to perfectly mirror your Spotify and Tidal playlists to your local media servers (Plex, Jellyfin, Navidrome). If a track is missing from your local library, EchoSync seamlessly interfaces with Soulseek (via slskd) to acquire it, perfectly tagging and organizing it along the way.

---

## ✨ Core Features & Architectural Pillars

EchoSync is built with an uncompromising focus on database integrity, security, and metadata resilience.

### 🧠 The Advanced Matching Engine
Commercial streaming metadata is notoriously inconsistent. EchoSync features a custom-built, multi-tiered matching engine designed to bridge the gap between structured API data (Spotify/Tidal) and messy local metadata:
* **Global ID Utilization:** Instant 100% match execution using ISRC, MBID (MusicBrainz), and Audio Fingerprinting when available.
* **Tiered Fallback Strategies:** Utilizes an `EXACT_SYNC` profile for strict, high-precision text and duration matching, gracefully falling back to a Tier-2 (Title + strict Duration) search when artist tags are wildly inaccurate.
* **Fuzzy Logic & Gating:** A 5-step gating algorithm evaluates title, artist, album, and duration, applying penalties for version mismatches (e.g., rejecting a "Remix" when the "Original" is requested).
* **Text Normalization:** Built-in metadata cleanup that standardizes apostrophes/dashes, extracts edition info (e.g., "Deluxe", "Remastered"), and strips trailing "feat." clauses to normalize comparisons.
* **Artist Subset Rescue:** Intelligently maps tracks when compilation or featured artists cause low fuzzy scores (e.g., recognizing that "Macklemore" is a valid subset of "Macklemore & Ryan Lewis" if the duration is tight).
* **Extensible Plugin Hooks:** The scoring engine allows community plugins to dynamically inject score boosts, override duration tolerances, or normalize text (e.g., the CJK Language Pack plugin).


### 🏛️ Enterprise-Grade Architecture
* **The Database Bedrock:** Powered by strict Alembic migrations across a discrete multi-database environment (`config.db`, `working.db`, `music.db`).
* **Zero-Trust Plugin Sandbox:** Community plugins are executed in a strictly monitored AST (Abstract Syntax Tree) Sandbox that aggressively rejects the import of sensitive or destructive modules (`os`, `sys`, `subprocess`).
* **Self-Healing Metadata:** The background enhancer continuously sweeps your library, automatically fixing legacy "Various Artists" tagging errors by physically reading and prioritizing `TPE1` file tags.
* **Safe Mode Circuit Breaker:** Prevents fatal boot-loops by automatically bypassing community plugins if a crash is detected during the initialization sequence.

---

## 🔌 Supported Integrations

**Streaming Sources:**
* Spotify (Supports Multiple Accounts)
* Tidal (up coming)
* YouTube Music (up coming)
**Local Media Servers:**
* Plex
* Jellyfin
* Navidrome (up coming)

**Acquisition & Metadata:**
* Soulseek (via slskd integration)
* MusicBrainz / ListenBrainz
* AcoustID (fpcalc audio fingerprinting)
* LRCLIB (Synchronized Lyrics)

---

## 🚀 Quick Start

### ⚠️ CRITICAL: The Master Encryption Key
EchoSync AES-encrypts your sensitive provider credentials (Spotify, Tidal, Slskd) inside `config.db`. **You must provide a `MASTER_KEY` environment variable.** * **Option A (Pre-generate):** Generate a random base64 string and add it to your compose file *before* your first boot.
* **Option B (Auto-generate):** If you boot without one, EchoSync will auto-generate a base64 key and print it to your Docker logs. **You must copy this key and add it to your compose file immediately.** If you reboot the container without setting the `MASTER_KEY` environment variable, EchoSync will not be able to decrypt `config.db`, effectively resetting your configuration.

### Standard Docker (Recommended)
EchoSync provides a pre-configured `docker-compose.yml` file in the root of the repository. 

1. Download the docker-compose.yml file.
2. Ensure your mounts (specifically `/data`, `/config`, and your `/downloads`/`/library` paths) are correctly mapped in the `docker-compose.yml`.
3. Run the Docker Compose command:
```bash
docker compose up -d


🛠️ Tech Stack
Backend: Python 3.11+, Alembic, SQLite, FastAPI/Flask.

Frontend: Svelte, TailwindCSS, Vite.

Security: AES-encrypted credential storage (No plaintext API keys).

🤝 Contributing
Because EchoSync utilizes strict database migrations and an AST-sandboxed plugin architecture, please refer to our CONTRIBUTING.md and ARCHITECTURE_CORE.md before submitting PRs involving database models or plugin hooks.

📜 Origin & Acknowledgement
EchoSync began as a fork of Nezreka's SoulSync. As we introduced Svelte, Alembic migrations, encrypted storage, and the Zero-Trust Sandbox, the codebase became a 100% structural rewrite. To respect the original author's namespace while reflecting the new architecture, the project was rebranded in v2.5.0. We thank Nezreka for the original inspiration!