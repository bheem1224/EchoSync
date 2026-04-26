# EchoSync: Application Overview

Welcome to the EchoSync Master Document. This guide provides a comprehensive overview of the application's architecture and data flow, fully updated for the v2.5.0 Nexus Framework—our decentralized, zero-trust backend and Web Component-driven frontend ecosystem

## Index
1. [The EchoSyncTrack & SyncID Lifecycle](#1-the-echosynctrack--syncid-lifecycle)
2. [Split Database Architecture](#2-split-database-architecture)
3. [The Advanced Matching Engine](#3-the-advanced-matching-engine)
4. [Suggestion Engine & Metadata Enhancer](#4-suggestion-engine--metadata-enhancer)
5. [File I/O, Job Queue, and Media Manager](#5-file-io-job-queue-and-media-manager)
6. [Quality Profiles](#6-quality-profiles)
7. [API Management: Rate Limiter & Request Manager](#7-api-management-rate-limiter--request-manager)
8. [Event Bus & Sync Service](#8-event-bus--sync-service)
9. [The Plugin Architecture (Nexus Framework)](#9-the-plugin-architecture-total-freedom)
10. [Bundled Core Plugins](#10-bundled-core-plugins)
11. [Auto Importer & Healthcheck](#11-auto-importer--healthcheck)

---

## 1. The EchoSyncTrack & SyncID Lifecycle

At the heart of EchoSync is the `EchoSyncTrack` model. Unlike traditional integer-based IDs, EchoSync uses a **Fat Pointer URI** known as the `SyncID` (e.g., `ss:track:meta:{base64}?dur={duration}`).

**The Lifecycle:**
1. **Ingestion:** Tracks are pulled from an external source (like Spotify) and mapped to an `EchoSyncTrack`. The `SyncID` is generated to carry critical metadata right in the identifier.
2. **Evaluation:** The system strictly rejects any ingested track missing a valid `SyncID`.
3. **Database Lookups:** When interacting with core tables, the base identity (stripping URL parameters via `.split('?')[0]`) is used for rapid internal lookups and uniqueness constraints.
4. **Resolution:** If a track is a "Ghost Track" (hard-deleted by the user), the `SyncID` alerts the system to never download it again.

## 2. Split Database Architecture

EchoSync utilizes a strict multi-database architecture. This split ensures security, simplifies backups, and cleanly separates state.

* **`config.db` (Configuration & Secrets):** Stores encrypted provider configurations and AES-encrypted OAuth tokens. Separating this ensures your sensitive credentials are never mixed with easily-shareable media metadata.
* **`music_library.db` (The Physical Media Ledger):** The absolute truth of your library. Contains `Track`, `Album`, `Artist`, and `AudioFingerprint` data.
* **`working.db` (Operational State):** Ephemeral tracking data, such as job queue statuses, `review_tasks` for unmatched files, and user interactions (`user_ratings`).

*(For database engine swap instructions (Postgres/MySQL), see the [Plugin SDK Guide](PLUGIN_SDK_GUIDE.md).)*

## 3. The Advanced Matching Engine

Commercial streaming metadata is messy. The Matching Engine bridges the gap between clean APIs and chaotic local tags using fuzzy logic and gating algorithms.

**How it works conceptually:**
* **Instant Matches:** Uses Global IDs (ISRC, MBID, AcoustID) to immediately hit 100% confidence when available.
* **Fuzzy Text Normalization:** Strips parentheticals, standardizes quotes/dashes, and drops trailing "feat." clauses to align names.
* **Gating Algorithm:** Evaluates title, artist, album, and duration using profiles (like `EXACT_SYNC`). It penalizes version mismatches (e.g., stopping a "Remastered" version from matching a "Live" request if the duration is too far off).
* **Base String Matching:** Aggressively simplifies strings to reduce false negatives.

## 4. Suggestion Engine & Metadata Enhancer

EchoSync doesn't just download files; it intelligently tags and recommends.

* **Metadata Enhancer:** A 5-step "Local-First" pipeline. It first attempts to read local file tags (using libraries like Mutagen to read ID3v2.4/Vorbis comments) before falling back to AcoustID fingerprinting and MusicBrainz text searches. Unmatchable files are pushed to a Review Queue.
* **Suggestion Engine:** Analyzes playback history and user ratings (normalized to a 10-point scale) to generate daily playlists and vibe profiles, feeding data back into your media server.

## 5. File I/O, Job Queue, and Media Manager

* **File I/O:** All file operations (reading, writing, tagging, moving) are centralized through safe handlers (`LocalFileHandler`). Direct file manipulation by plugins is strictly controlled.
* **Job Queue:** A central concurrency manager (`core.job_queue`). Long-running tasks (metadata enhancement, media server scanning) are delegated to background threads with internal locks to prevent overlapping executions.
* **Media Manager:** Orchestrates the library's lifecycle. It handles upgrading track quality when a better version is found and performing library hygiene (like deduplication based on fingerprint hashes).

## 6. Quality Profiles

EchoSync acts as a precise acquisition tool. Quality Profiles define the exact constraints for downloaded media.

A profile defines the acceptable file size, bit rate, bit depth, format, and duration limits. During the download process, the system uses a waterfall strategy: it queries active downloader plugins, evaluating candidates against the Quality Profile, gracefully falling back to lower acceptable tiers if the ideal format isn't found.

## 7. API Management: Rate Limiter & Request Manager

To prevent API bans and ensure stable operations, all external network requests are routed centrally.

* **Request Manager & OAuth Sidecar:** Handles HTTP connections, retries, and session pooling.
* **Rate Limiter:** Enforces strict limits dynamically based on the service (e.g., MusicBrainz 1 req/sec, AcoustID 3 req/sec). It automatically applies exponential backoff when encountering 429 Too Many Requests errors.

## 8. Event Bus & Sync Service

* **The Event Bus:** The nervous system of EchoSync. Uses lightweight dictionary payloads (the "Claim Check Pattern") to broadcast state changes across the application without passing massive Python objects.
* **Sync Service:** The core engine that orchestrates the workflow. It reads source playlists, consults the Matching Engine, dispatches `DOWNLOAD_INTENT` events to the Event Bus, and monitors the Job Queue until tracks are imported.

## 9. The Plugin Architecture (Nexus Framework)

The legacy monolithic structure is gone. EchoSync is now driven by a dynamic plugin architecture.

* **Plugin Loader & AST Sandbox:** Discovers and loads community plugins. To ensure security, it uses a strict Abstract Syntax Tree (AST) scanner to block malicious or destructive Python modules (like `os` or `subprocess`).
* **Hook Manager:** Plugins hook into core application logic. They can listen to events (Event Hooks), modify data in transit (Mutator Hooks), or completely hijack a core process (Skip Hooks).
* **Plugin Store & Alembic:** Plugins are granted isolated database tables (prefixed securely). Database schema changes are handled reliably via three explicit Alembic environments.

*(For detailed developer instructions, see the [Plugin SDK Guide](PLUGIN_SDK_GUIDE.md).)*

## 10. Bundled Core Plugins

To ensure out-of-the-box functionality, EchoSync ships with a suite of bundled core plugins. Rather than hardcoding these fundamental features, they use the exact same hook architecture as community plugins, proving the viability of the "Nexus Framework" SDK:

* **Local Player:** Provides native audio streaming capabilities directly from the server.

* **Local Media Server:** Acts as a lightweight, internal media server (essentially a "mini-Plex" inside EchoSync). It maps your local library via filesystem traversals (e.g., os.walk) and manages active, buffered streaming threads so your music playback never hiccups.

* **Local Metadata:** Responsible for reading embedded file-level metadata (like ID3 and Artist tags). By sitting at Priority 1 in the plugin stack, it allows EchoSync to instantly ingest tagged files without wasting time or rate-limits querying external services like MusicBrainz or AcoustID.

* **Outbound Gateway:** An integration layer allowing external applications to query EchoSync (an External -> EchoSync data flow). Destined to be locked behind an API key in future auth updates, this allows EchoSync to fit perfectly into larger homelab stacks (e.g., exposing endpoints for Prometheus metrics, or allowing applications like Overseerr to talk to it).

These core plugins use the exact same hook architecture as community plugins.

## 11. Auto Importer & Healthcheck

**Auto Importer**
The Auto Importer monitors the download directory using a dual-strategy approach: it utilizes Watchdog for instantaneous filesystem event detection, backed by a Scheduled Polling routine via the Job Queue to ensure nothing is missed. When new files arrive, it routes them to the Metadata Enhancer. Clean matches are automatically tagged and organized into the media library; uncertain matches are pushed to the database Review Queue for manual approval.

**Healthcheck & System Monitoring**
The Healthcheck system is split into two distinct protective layers:

Safe Mode Circuit Breaker: Protects the core application loop. It writes a booting.lock file on startup. If the app crashes and restarts while this lock exists, it reboots in "Safe Mode," temporarily disabling community plugins to ensure the web UI remains accessible for troubleshooting.

Endpoint Monitoring: A simple, built-in registration system for service health. Services and plugins can register an endpoint with the core system; the internal Job Queue will then automatically ping that endpoint every 5 minutes and broadcast an alert if it ever goes offline.