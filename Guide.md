# EchoSync Homelab Guide 🏡

Welcome to the EchoSync Homelab Guide! This document is designed for system administrators and power users deploying EchoSync in a local Docker/Unraid environment.

## 📁 Volume Mounts

EchoSync expects specific directories to function smoothly, especially when interfacing with slskd and your media server.

*   **/app/config (or /config):** Stores your safe mode booting locks and environment variables.
*   **/data:** The lifeblood of the application. Stores `config.db`, `music.db`, and `working.db`. It also holds the cryptographic keys used to encrypt your external API tokens. **BACK THIS FOLDER UP.**
*   **/host/music (or /music):** This must be the root directory where your actual music files live. This is usually the same directory that Plex/Jellyfin/Navidrome sees, AND the directory that slskd downloads into.

## 🔑 Core Environment Variables

EchoSync uses several environment variables for deep configuration:

*   **`ECHOSYNC_ENCRYPTION_KEY`**: A custom 32-byte base64 key used to encrypt API secrets in the database. If not provided, the system auto-generates one and saves it in `/data`.
*   **`ECHOSYNC_DEV_MODE`**: Set to `1` or `true` to enable verbose debug logging and disable caching for rapid development.
*   **`ECHOSYNC_SAFE_MODE`**: Set to `1` to bypass all community plugins. If the app crashes during boot, a lockfile is written to force this mode on the next start to prevent crash loops.
*   **`ECHOSYNC_DATA_DIR`**: Overrides the default `/data` location.
*   **`PUID` & `PGID`**: Sets the Unix user/group permissions for files downloaded and modified by EchoSync (usually 99/100 for Unraid).

## 🌐 The Global HTTPS OAuth Sidecar

EchoSync integrates with commercial APIs like Spotify and Tidal, which strictly require `https://` callback URLs for OAuth authentication. However, EchoSync typically runs on a local network (e.g., `http://192.168.1.100:5000`), which these APIs will reject.

To solve this, EchoSync uses a dedicated OAuth Sidecar Proxy (running on Port `5001`).

**How it works:**
1.  You initiate the login in the UI.
2.  EchoSync redirects you to a central hosted proxy (e.g., `auth.echosync.io`).
3.  The proxy securely receives the tokens over HTTPS from Spotify/Tidal.
4.  The proxy then redirects your browser back to your local IP address (e.g., `http://192.168.1.100:5001/callback`) with the encrypted token payload.
5.  Your local server decrypts the payload and saves the credentials.

*Note: The central proxy never stores your tokens; it strictly acts as an HTTPS bridge.*
