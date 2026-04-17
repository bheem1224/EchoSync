# EchoSync Homelab Guide 🏡

Welcome to the EchoSync Homelab Guide! This document is designed for system administrators and power users deploying EchoSync in a local Docker/Unraid environment.

## 📁 Volume Mounts & Directory Structure

EchoSync automatically resolves its internal paths based on the root data directory, but these can be mapped directly for fine-grained control:

*   **/app/config (or /config):** Stores your core configuration files and the `config.db` database.
*   **/data:** The main application directory. This holds your operational and media databases, as well as the cryptographic keys used to encrypt API tokens. **BACK THIS FOLDER UP.**
*   **/data/library:** The default internal path for your organized music library.
*   **/data/downloads:** The default internal path where active downloads are placed before being processed.
*   **/host/music (or /music):** Typically used to map your existing external media share so EchoSync can scan and enhance it alongside Plex/Jellyfin/Navidrome.

## 🗄️ Database Architecture

EchoSync utilizes a strict multi-database architecture using SQLite (with WAL journaling and enforced foreign keys):

1.  **`config.db` (in `/config`):** Stores provider configurations, OAuth tokens (encrypted via AES), and global application settings.
2.  **`music_library.db` (in `/data`):** The "Physical Media" ledger. It only contains models representing the actual files on your disk: `Track`, `Album`, `Artist`, `AudioFingerprint` (AcoustID), and `ExternalIdentifier`.
3.  **`working.db` (in `/data`):** The "Operational State" ledger. It tracks transient and operational data such as active Downloads, User Ratings, Suggestion algorithms, and Review Queue tasks.

*By keeping physical media separated from operational state, EchoSync ensures that destroying the working database does not corrupt your core library metadata.*

## 🔑 Core Environment Variables

EchoSync uses several environment variables for deep configuration:

*   **`ECHOSYNC_ENCRYPTION_KEY`**: A custom 32-byte base64 key used to encrypt API secrets in `config.db`. If not provided, the system auto-generates one and saves it in `/data`.
*   **`ECHOSYNC_DEV_MODE`**: Set to `1` or `true` (or `0`/`false`) to toggle verbose debug logging and disable caching for rapid development.
*   **`ECHOSYNC_DATA_DIR`**: Overrides the default `/data` root directory location.
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
