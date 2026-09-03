# Configuration Settings Lexicon

## 1. System Settings Reference

EchoSync manages settings through `ConfigManager` backed by `config.db`. Key configuration variables can be passed via environment variables or set via the Web UI.

| Setting Key | Environment Variable | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `master_key` | `MASTER_KEY` | *Required* | 32-byte base64 Fernet key used to encrypt secrets in `config.db`. |
| `storage.library_dir` | `LIBRARY_DIR` | `/data/library` | Root directory for pristine organized music media files. |
| `storage.download_dir` | `DOWNLOAD_DIR` | `/data/downloads` | Staging area for incomplete/completed downloads. |
| `storage.config_dir` | `CONFIG_DIR` | `/config` | Root directory storing `config.json` and `config.db`. |
| `server.port` | `PORT` | `8000` | HTTP listening port for FastAPI / Svelte application. |
| `server.host` | `HOST` | `0.0.0.0` | Bind address for API backend server. |
| `logging.level` | `LOG_LEVEL` | `INFO` | System log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `logging.dir` | `ECHOSYNC_LOG_DIR` | `/data/logs` | Destination directory for rotating log files. |

---

## 2. Quality Profiles Reference

Quality Profiles define mandatory audio quality thresholds and fallback strategies for download acquisition.

| Profile Field | Allowed Values | Description |
| :--- | :--- | :--- |
| `name` | String | Profile label (e.g., `FLAC Only`, `High Quality MP3`). |
| `min_bitrate` | Integer | Minimum acceptable bitrate in kbps (e.g. `320`). |
| `preferred_codec` | `FLAC`, `MP3`, `AAC` | Primary preferred codec format for acquisition. |
| `allow_lossy_fallback` | `true`, `false` | Fallback to lossy formats when lossless download is unavailable. |
| `min_sample_rate` | Integer | Minimum sample rate in Hz (e.g. `44100`, `48000`, `96000`). |

---

## 3. Storage & Path Templates

File renaming and path structure in `data/library` follow configurable templates:

- **Track Template:** `{artist}/{album}/{track_number:02d} - {title}.{ext}`
- **Compilation Template:** `Compilations/{album}/{track_number:02d} - {artist} - {title}.{ext}`
