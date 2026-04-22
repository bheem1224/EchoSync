# API Migration Log

This log tracks the migration of provider-specific API routes from the monolithic `web/routes/` directory to their respective plugin folders (`plugins/{plugin_id}/routes.py`).

## Batch 1: Plex and Spotify
- **Migrated Route:** `POST /api/accounts/plex/sync_users`
  - **Original File:** `web/routes/accounts.py`
  - **Target File:** `plugins/plex/routes.py`
  - **New Route Path:** `POST /api/plex/sync_users`
  - **Auth Confirmed:** Yes, added `@require_auth`.

*(Note: Most Plex and Spotify routes like `/auth` and `/callback` were already found to be migrated to their plugin folders.)*

## Batch 2: Jellyfin and Navidrome
- **Status:** Skipped
  - **Reason:** No hardcoded API endpoints specific to Jellyfin or Navidrome remained in `web/routes/`. Their configuration and testing routes had already been migrated previously.

## Batch 3: Slskd, Tidal, ListenBrainz, Apple, AcoustID
- **Status:** Skipped
  - **Reason:** Audited the codebase, and no specific API endpoints for these providers remained in the monolithic `web/routes/` directory. All specific provider logic operates via the generic facades or has already been migrated.

## Core Refactoring
- **Bug Fix:** Fixed an issue in `web/routes/metadata_review.py` where three separate methods (`approve_review_queue_item`, `lookup_review_queue_item_acoustid`, and `lookup_review_queue_item_musicbrainz`) erroneously shared the exact same POST path (`/review-queue/<int:task_id>/lookup/acoustid`). Corrected to their proper independent paths.

## Step 4: Pruning
- **Removed Legacy Imports:** None
  - **Reason:** An audit of `web/api_app.py` confirmed that there were no remaining legacy blueprint imports for specific providers (like `from web.routes.plex import bp as plex_bp` or `spotify_bp`). All generic components are retained, and all plugin routes are dynamically mounted via the `PluginRouterRegistry` or `PluginLoader`.
