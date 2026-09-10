# Configuration Settings Lexicon

## 1. System Settings Reference

EchoSync manages configuration settings via `ConfigManager` backed by `config.db`. Key configuration parameters can be configured through the Web UI or provided as environment variables.

| Setting Name | Environment Variable | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `master_key` | `MASTER_KEY` | None (Required) | 32-byte Fernet key used to encrypt account tokens and service credentials. |
| `storage_roots` | `STORAGE_ROOTS` | `/media/music` | Authorized base directories for media library management. |
| `enable_auto_import` | `ENABLE_AUTO_IMPORT` | `true` | Enables real-time folder monitoring for automatic track ingestion. |
| `matching_min_confidence` | `MATCHING_MIN_CONFIDENCE` | `85.0` | Confidence threshold ($0-100$) for auto-approving metadata matches. |
| `acoustid_api_key` | `ACOUSTID_API_KEY` | None | User key for AcoustID fingerprint web API queries. |
