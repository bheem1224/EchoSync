# Media Manager & Matching Engine

## 1. Overview

The Media Manager governs local library organization, audio fingerprinting, metadata enhancement, and recommendation scoring.

## 2. Media Library Management

- **Physical Media Bindings**: Media files on disk are bound to canonical tracks as `LocalMedia` entities in `library.db`.
- **Auto-Tagging & Organization**: Ingested audio files are tagged with canonical metadata via native Rust FFI (`echosync_core`) and renamed according to user format patterns.
- **Review Queue**: Ambiguous track matches with confidence scores below the configured threshold are routed to the Web UI Review Queue (`/review`) for manual approval.
