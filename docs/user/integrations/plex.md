# Plex Media Server Integration

## 1. Overview

The **Plex Plugin** (`EchoSync.Plex`) enables bi-directional synchronization between EchoSync and Plex Media Server:
- Reports library updates to Plex upon file ingestion.
- Listens for Plex webhook playback events to update EchoSync user vibe profiles.

---

## 2. Setup & Configuration

1. Install the Plex plugin from **Settings > Plugin Store**.
2. Enter your Plex Server URL (`http://192.168.1.50:32400`) and Plex Authentication Token.
3. Select the target Plex Music Library section.

---

## 3. Webhook Integration

Configure Plex Webhooks to point to `http://<echosync-host>:8000/api/webhooks/plex`. When playback starts or finishes, EchoSync parses the event via `PlexWebhookParser` in `core/webhook_parsers.py`.
