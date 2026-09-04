# System Settings Lexicon & Configuration Reference

## 1. Overview

EchoSync system configuration is stored in `/config/config.json` and mirrored in `config.db`.

---

## 2. Global Core Settings

| Setting Key | Data Type | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `SERVER_PORT` | `integer` | `8000` | Port for the FastAPI web server and REST API. |
| `LOG_LEVEL` | `string` | `"INFO"` | System logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `MASTER_KEY` | `string` | `""` | 32-byte Fernet secret key used to encrypt plugin tokens and passwords. |
| `AUTO_IMPORTER_ENABLED` | `boolean` | `true` | Toggles real-time background monitoring of `/data/downloads`. |
| `AUTO_IMPORTER_INTERVAL` | `integer` | `300` | Automated file scan interval in seconds. |
| `MATCHING_THRESHOLD` | `integer` | `85` | Tier 1 metadata confidence score required to auto-bind media. |
| `FINGERPRINTING_ENABLED` | `boolean` | `true` | Enables Chromaprint audio fingerprinting via `echosync_core`. |

---

## 3. Storage Configuration

| Setting Key | Data Type | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `LIBRARY_PATH` | `string` | `"/data/library"` | Target destination path for organized media files. |
| `DOWNLOADS_PATH` | `string` | `"/data/downloads"` | Staging directory where download clients save completed files. |
| `FILE_STRUCTURE_PATTERN` | `string` | `"{artist}/{album}/{track_number} - {title}"` | Naming convention for organized library files. |
