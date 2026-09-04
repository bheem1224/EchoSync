# Plex Media Server Integration

## 1. Overview

EchoSync integrates with Plex Media Server to synchronize library metadata, scrobble play counts, listen to real-time playback webhooks, and trigger library refreshes upon file import.

---

## 2. Configuration Setup

1. Navigate to **Settings > Integrations > Plex** in the EchoSync UI.
2. Enter your Plex Server URL (e.g., `http://192.168.1.100:32400`).
3. Obtain a **Plex Authentication Token** (`X-Plex-Token`) and paste it into the integration configuration.
4. Select the target Plex Music Library Section ID.

---

## 3. Webhook Configuration

To enable instant scrobbling and playback tracking:

1. Open Plex Web UI -> Account Settings -> Webhooks.
2. Add the EchoSync webhook endpoint URL:
   `http://<echosync-ip>:8000/api/v1/webhooks/plex`
3. EchoSync's `web/routes/webhooks.py` controller parses payload events (`media.play`, `media.pause`, `media.stop`, `media.scrobble`).

---

## 4. Library Sync & Match Resolution

- **Automatic Refresh:** When `Gatekeeper` imports a track into `/data/library`, EchoSync invokes Plex API `/library/sections/{id}/refresh` scoped to the updated folder path.
- **Plex Rating Key Binding:** Remote Plex rating keys are stored in `external_identifiers` table in `library.db` with `provider_id = "plex"`.
