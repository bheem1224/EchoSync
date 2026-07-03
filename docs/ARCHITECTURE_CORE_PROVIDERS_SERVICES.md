# Architecture: Core, Providers, and Services (v2.5.0)

This document outlines the high-level architecture of the EchoSync Nexus Framework (v2.5.0). The system is organized around distinct data boundaries, deterministic identity models, and capability-driven orchestration.

## 1. The Database Shift: Abstract vs. Physical

The v2.5.0 rewrite introduces a strict decoupling between abstract musical metadata and physical file tracking. The legacy base64-encoded, deconstructable hash identifier has been entirely eradicated.

### SyncID
- **Role:** Identifies the abstract `Track` model (the concept of a song).
- **Format:** A globally unique NanoID.
- **Scope:** Used across all metadata tables and external API references to track a logical song entity, regardless of whether a physical file exists locally.

### MediaID
- **Role:** Identifies the physical `LocalMedia` model (the actual file on disk).
- **Format:** A deterministic identifier tied to file provenance.
- **Scope:** Manages file paths, hash verification, and local disk presence.
- **Relationship:** A single `SyncID` (the logical track) maps to a `MediaID` (the physical asset) only when the track is successfully downloaded and ingested.

## 2. The JSON Staging Area

EchoSync employs a strict "Zero-Trust" staging environment to prevent database pollution. Unverified or provisional tracks do not touch the production relational tables (`music.db`).

### Provisional Tracks
- **Storage:** Stored exclusively as raw JSON blobs (`track_data`) within `working.db`.
- **Lifecycle:**
  - External providers stream track data.
  - The framework encapsulates the payload into a JSON staging blob.
  - The blob remains in `working.db` while undergoing matching, scoring, and metadata enhancement.
- **Ingestion:** Only after a track achieves consensus and is fully approved does the system parse the JSON blob, generate a `SyncID`, and commit the normalized entity to the permanent production database.

## 3. The Priority Waterfall Philosophy

EchoSync orchestrates complex background workflows (e.g., metadata enhancement, media downloading) using the "Priority Waterfall" pattern.

### Core Principles
- **Race Condition Prevention:** By avoiding parallel execution of overlapping responsibilities, the system ensures deterministic state mutations.
- **Zero-Trust Fallbacks:** The orchestrator iterates through available plugins sequentially based on their defined authority/priority score. If the primary provider fails, timeouts, or returns malformed data, the system instantly falls back to the next available provider.
- **Capability Routing:** Services do not hardcode dependencies. Instead, they request a capability (e.g., `Capability.FETCH_METADATA`). The system resolves the request by cascading down the priority waterfall of plugins that advertise that capability.
