# Slskd Integration

## 1. Overview

The **Slskd Plugin** (`EchoSync.Slskd`) integrates EchoSync with Slskd (Soulseek daemon) to handle automated track acquisition for missing media or quality upgrades.

---

## 2. Configuration

1. In **Settings > Download Clients**, enable Slskd.
2. Set API Base URL (`http://slskd:5030`) and API Key.
3. Ensure `/data/downloads` in EchoSync mounts the exact same directory as Slskd's completed downloads directory.

---

## 3. Download Lifecycle

1. EventBus publishes `DOWNLOAD_INTENT`.
2. Slskd plugin searches Soulseek network for track candidates matching format/bitrate parameters.
3. Slskd enqueues download. Upon completion, `AutoImporter` scans staging directory and moves track to `/data/library`.
