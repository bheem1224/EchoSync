# Slskd Integration & Downloader Guide

## 1. Overview

EchoSync integrates with `slskd` (Soulseek daemon) for automated music search and acquisition.

---

## 2. Shared Volume & File Permissions (Unraid / Docker)

To prevent `Permission denied (os error 13)` during file imports, both containers must mount the same physical download path and share ownership permissions.

### Recommended `slskd.yml` Configuration

Ensure `slskd.yml` sets explicit file and directory permissions:

```yaml
permissions:
  file: "0666"
  directory: "0777"
```

### Docker Volume Mapping Pair

- **slskd container:** `-v /mnt/user/downloads/slskd:/app/downloads`
- **echosync container:** `-v /mnt/user/downloads/slskd:/data/downloads`

---

## 3. EchoSync Integration Setup

1. Open EchoSync UI -> **Settings > Integrations > Slskd**.
2. Set Slskd Host URL: `http://slskd:5030`
3. Enter API Key generated in Slskd Settings.
4. Set Search Timeout (default: 30 seconds) and Max Results per query.

---

## 4. Download Execution Pipeline

1. `DownloadManager` enqueues missing tracks from `working.db`.
2. Queries Slskd REST API `/api/v1/searches`.
3. Filters results against quality profiles (`min_bitrate`, `codec`).
4. Sends download request to `/api/v1/transfers/downloads`.
5. `ON_DOWNLOAD_PROGRESS` hook reports status until completed.
