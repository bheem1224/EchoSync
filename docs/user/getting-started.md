# Getting Started with EchoSync

## 1. Overview

EchoSync is a high-performance, self-hosted music management, auto-tagging, metadata enhancement, and acquisition platform. It coordinates local physical music libraries, remote virtual tracks, download providers, and streaming integrations.

## 2. Quick Start & Setup

### Prerequisites
- Docker & Docker Compose or Python 3.12+ with Rust compiler toolchain.
- Standard storage roots configured for media library storage.

### Environment Configuration
Key environment variables:
- `MASTER_KEY`: 32 URL-safe base64-encoded Fernet key for database credential encryption.
- `STORAGE_ROOTS`: JSON list or colon-separated paths to designated media storage directories.

### First Boot Workflow
1. Start the backend server via `run_api.py` or Docker container.
2. Access the SvelteKit 2 SPA interface at `http://localhost:8000`.
3. Complete initial storage root registration in Settings (`settings-lexicon.md`).
4. Configure integrations for Plex (`integrations/plex.md`) or Slskd (`integrations/slskd.md`).
