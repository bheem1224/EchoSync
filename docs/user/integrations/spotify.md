# Spotify Plugin Integration Guide

## 1. Overview

The Spotify integration plugin empowers EchoSync to perform metadata enrichment, fetch high-resolution cover art, import user playlists/saved tracks, and resolve virtual media mappings against Spotify's catalog.

---

## 2. Configuration & Authentication

The Spotify plugin requires client credentials configured via OAuth or Developer App API credentials.

### Required Configuration Fields

| Setting | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `client_id` | `string` | Yes | Spotify Developer Application Client ID |
| `client_secret` | `string` | Yes (Encrypted) | Spotify Developer Application Client Secret |
| `redirect_uri` | `string` | Yes | OAuth callback URL (e.g. `http://localhost:8000/api/v1/system/webhooks/spotify`) |

### Setting Credentials via API
```bash
curl -X POST "http://localhost:8000/api/v1/system/plugins/spotify/credentials" \
     -H "Content-Type: application/json" \
     -d '{
       "client_id": "YOUR_SPOTIFY_CLIENT_ID",
       "client_secret": "YOUR_SPOTIFY_CLIENT_SECRET"
     }'
```

---

## 3. Metadata Resolution & Enrichment (Stage 6)

In EchoSync's 6-Stage Metadata Resolution Waterfall, Spotify acts as the final enrichment provider:

1. **ISRC & Catalog Cross-Referencing:** Validates Track ISRCs against Spotify's global track database.
2. **High-Resolution Artwork:** Retrieves original 640x640 album artwork URLs when local cover art is missing or low-resolution.
3. **Genre & Popularity Metrics:** Enriches canonical tracks with Spotify popularity indices and genre tags.

---

## 4. Playlist Ingestion & Synchronization

EchoSync can continuously monitor and mirror Spotify playlists into canonical local playlists.

### Playlist Sync Workflow

1. User provides a Spotify Playlist URI or URL (`spotify:playlist:...`).
2. Spotify plugin fetches track listing and resolves each item against `library.db` (canonical tracks) and `working.db` (virtual tracks).
3. Missing tracks are automatically flagged for acquisition via active downloader plugins (slskd).

---

## 5. Troubleshooting Table

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| `401 Unauthorized` API errors | Expired OAuth refresh token or invalid client secret | Re-authenticate via `/api/v1/system/plugins/spotify/credentials` |
| `429 Too Many Requests` | Exceeded Spotify Web API rate limits | RequestManager automatically handles exponential backoff; lower sync frequency |
| Tracks missing ISRC links | Item in Spotify catalog lacks official ISRC registration | Fallback to text matching or MusicBrainz release lookup |
