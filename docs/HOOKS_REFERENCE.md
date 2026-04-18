# EchoSync Hook Reference

This document serves as a directory of the Core hooks available in the **Plugin Architecture**.

To see the exact payload signatures or return values required by the system, look directly at the `hook_manager.apply_filters('HOOK_NAME', ...)` calls in the referenced source files.

## Infrastructure & Core

| Hook Name | Type | Core Concept / Example Use Case | File Reference |
| :--- | :--- | :--- | :--- |
| `ON_API_STARTUP` | Mutator / Event | Allows plugins to register custom Flask Blueprint routers right before the main application spins up (e.g. mounting an `/api/plugins/my_plugin/` route). | `web/api_app.py` |
| `AUTHENTICATE_USER` | Skip | A plugin can intercept the login request payload, perform external auth (like OIDC/SAML), and bypass the core SQLite password verification entirely if it returns a valid session token. | `web/routes/auth.py` |
| `ON_INBOUND_WEBHOOK` | Skip | Intercepts raw webhook payloads before they are parsed by the media server logic. If a plugin successfully handles a custom event, it can return `"SKIP"` to respond with a 200 OK. | `web/routes/webhooks.py` |

## Job Queue

| Hook Name | Type | Core Concept / Example Use Case | File Reference |
| :--- | :--- | :--- | :--- |
| `ON_JOB_ENQUEUED` | Mutator | Fires when a job is registered. Allows plugins to dynamically alter the interval, max retries, or execution tags of a job before it is stored in the queue heap. | `core/job_queue.py` |
| `ON_JOB_FAILED` | Event | Fires after a job has exhausted all of its `max_retries` attempts. Useful for triggering alerting systems (like Discord/Slack webhooks). | `core/job_queue.py` |

## File Handling & Storage

| Hook Name | Type | Core Concept / Example Use Case | File Reference |
| :--- | :--- | :--- | :--- |
| `RESOLVE_STORAGE_PATH` | Mutator | Runs before any file translation occurs. A plugin can determine and rewrite the final destination directory based on track metadata or external configs. | `core/file_handling/path_mapper.py` |
| `BEFORE_FILE_RENAME` | Mutator | Passes the resolved absolute destination path immediately before the local `shutil.move` is called. Plugins can rename the file on the fly. | `core/file_handling/base_io.py` |
| `CUSTOM_FILE_IO` | Skip | Intercepts the physical move operation. A plugin (like an S3/Cloud Storage adapter) can handle the upload remotely and return `"SKIP"` to prevent the local `shutil.move` from attempting execution. | `core/file_handling/base_io.py` |

## Media Manager & Library Hygiene

| Hook Name | Type | Core Concept / Example Use Case | File Reference |
| :--- | :--- | :--- | :--- |
| `ON_CORRUPTION_DETECTED` | Skip | Fires during deduplication or library sweeps when a file is flagged for deletion. If a plugin quarantines the file instead, returning `"SKIP"` prevents the core deletion logic from running. | `services/library_hygiene.py` |

## Download Manager

| Hook Name | Type | Core Concept / Example Use Case | File Reference |
| :--- | :--- | :--- | :--- |
| `BEFORE_DOWNLOAD_START` | Skip | Fires immediately before the network request to acquire the file begins. A VPN Checker plugin could check interface status and return `"ABORT"` to fail the download gracefully. | `services/download_manager.py` |
| `ON_DOWNLOAD_PROGRESS` | Event | Fired during the download polling loop. Throttle-limited natively (emits events only when progress changes by ~5%). Useful for real-time plugin dashboards. | `services/download_manager.py` |

## Matching Engine

| Hook Name | Type | Core Concept / Example Use Case | File Reference |
| :--- | :--- | :--- | :--- |
| `ON_MATCH_FAILED` | Skip | Fires when the Waterfall Search evaluates all raw candidates and rejects them due to low confidence scores. A plugin (e.g., an Acoustic Fingerprinter) can step in, find a match via external lookup, and return a valid candidate dictionary to override the failure. | `core/matching_engine/matching_engine.py` |

## Suggestion Engine

| Hook Name | Type | Core Concept / Example Use Case | File Reference |
| :--- | :--- | :--- | :--- |
| `PROVIDE_VIBE_PROFILE` | Skip | Intercepts the user playback history aggregation loop. A plugin (e.g., Last.fm AI profiler) can supply the vibe dictionary (tempo, energy, etc.), bypassing the SQLite calculation. | `core/suggestion_engine/vibe_profiler.py` |
| `BEFORE_SUGGESTION_GENERATION` | Mutator | Allows plugins to modify the target user and query parameters right before fetching candidate suggestions from the engine. | `web/routes/suggestions.py` |
| `ON_SUGGESTION_READY` | Mutator | Passes the final array of suggested tracks immediately before they are sent to the client UI, allowing plugins to inject or filter tracks dynamically. | `web/routes/suggestions.py` |

## Playlist Engine

| Hook Name | Type | Core Concept / Example Use Case | File Reference |
| :--- | :--- | :--- | :--- |
| `GENERATE_DYNAMIC_PLAYLIST` | Skip | Intercepts the creation request. If a plugin algorithm generates and returns an array of tracks, the core Daily Mix / Discovery Pool generation logic is bypassed. | `core/personalized_playlists.py` |
| `ON_PLAYLIST_SAVED` | Event | Fires after a dynamic or synced playlist has successfully written its tracks to the provider backend (e.g., Plex/Spotify) and the database transaction completes. | `web/routes/playlists.py` |
