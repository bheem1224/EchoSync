# EchoSync Enterprise API Reference (v2.5.0)

## Architecture Overview & Zero-Trust Plugin Namespacing

EchoSync's v2.5.0 rebuild runs entirely on FastAPI / ASGI, offering high-performance, asynchronous endpoints and auto-validated Pydantic models.

### Zero-Trust Sub-Application Namespacing

All dynamically registered third-party and custom plugin REST endpoints are isolated using FastAPI Sub-Applications. Each plugin's API routes are mounted strictly under the `/api/v1/plugins/{plugin_id}/` hierarchical namespace.

- **Collision Isolation:** The mandatory `{plugin_id}` prefix guarantees that plugins can never collide with core routes or hijack other plugins' endpoints.
- **Context Scope:** Plugins operate strictly within their isolated sub-app context and facade storage boundaries.

---

## API Endpoints Reference

### Accounts

#### `GET` `/api/v1/system/accounts/{service_name}`

**Summary:** List Service Accounts


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `service_name` | path | Yes | `string` |  |


---

#### `POST` `/api/v1/system/accounts/{service_name}`

**Summary:** Create Account


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `service_name` | path | Yes | `string` |  |


**Request Body Schema:** `CreateAccountRequest`


---

#### `PUT` `/api/v1/system/accounts/{service_name}/{account_id}/activate`

**Summary:** Activate Account


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `service_name` | path | Yes | `string` |  |
| `account_id` | path | Yes | `integer` |  |


**Request Body Schema:** `ActivateAccountRequest`


---

#### `DELETE` `/api/v1/system/accounts/{service_name}/{account_id}`

**Summary:** Delete Account


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `service_name` | path | Yes | `string` |  |
| `account_id` | path | Yes | `integer` |  |


---

#### `PUT` `/api/v1/system/accounts/{service_name}/{account_id}/name`

**Summary:** Update Account Name


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `service_name` | path | Yes | `string` |  |
| `account_id` | path | Yes | `integer` |  |


**Request Body Schema:** `UpdateAccountNameRequest`


---

#### `POST` `/api/v1/system/accounts/overrides`

**Summary:** Set Account Overrides


**Request Body Schema:** `AccountOverridesRequest`


---

### Auth

#### `GET` `/api/v1/system/auth/status`

**Summary:** Auth Status


---

#### `POST` `/api/v1/system/auth/login`

**Summary:** Login


**Request Body Schema:** `LoginRequest`


---

### Core: Tracks

#### `GET` `/api/v1/core/tracks/`

**Summary:** List Canonical Tracks


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `detail` | query | No | `boolean` |  |
| `limit` | query | No | `integer` |  |
| `offset` | query | No | `integer` |  |
| `ids` | query | No | `string` |  |


---

#### `GET` `/api/v1/core/tracks/{sync_id}`

**Summary:** Get Canonical Track


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `sync_id` | path | Yes | `string` |  |
| `detail` | query | No | `boolean` |  |


---

#### `PATCH` `/api/v1/core/tracks/{sync_id}`

**Summary:** Patch Canonical Track


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `sync_id` | path | Yes | `string` |  |


---

#### `DELETE` `/api/v1/core/tracks/{sync_id}`

**Summary:** Delete Canonical Track


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `sync_id` | path | Yes | `string` |  |


---

#### `GET` `/api/v1/core/tracks/search`

**Summary:** Search Canonical Tracks


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `title` | query | Yes | `string` |  |
| `artist` | query | No | `string` |  |
| `limit` | query | No | `integer` |  |
| `detail` | query | No | `boolean` |  |


---

### Dashboard

#### `GET` `/api/v1/system/dashboard`

**Summary:** Get Dashboard


---

#### `POST` `/api/v1/system/dashboard`

**Summary:** Update Dashboard


---

#### `GET` `/api/v1/system/dashboard/layout`

**Summary:** Get Dashboard Layout


---

### Downloads

#### `GET` `/api/v1/system/downloads/queue`

**Summary:** Get Queue


---

#### `DELETE` `/api/v1/system/downloads/queue`

**Summary:** Clear Queue


---

#### `POST` `/api/v1/system/downloads/run`

**Summary:** Run Downloads


---

#### `DELETE` `/api/v1/system/downloads/{download_id}`

**Summary:** Delete Download


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `download_id` | path | Yes | `integer` |  |


---

#### `POST` `/api/v1/system/downloads/{download_id}/search`

**Summary:** Search Download


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `download_id` | path | Yes | `integer` |  |


---

#### `DELETE` `/api/v1/system/downloads/batch`

**Summary:** Delete Batch


**Request Body Schema:** `BatchDeleteRequest`


---

### General

#### `GET` `/scan/stream`

**Summary:** Stream Scan Progress


---

### Jobs

#### `POST` `/api/v1/system/jobs/{job_name}/kill`

**Summary:** Kill Job Route


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `job_name` | path | Yes | `string` |  |


---

#### `GET` `/api/v1/system/jobs/`

**Summary:** List Jobs


---

#### `GET` `/api/v1/system/jobs`

**Summary:** List Jobs


---

#### `GET` `/api/v1/system/jobs/active`

**Summary:** List Active Jobs


---

#### `GET` `/api/v1/system/jobs/summary`

**Summary:** Jobs Summary


---

#### `POST` `/api/v1/system/jobs/run`

**Summary:** Run Job


---

#### `GET` `/api/v1/system/jobs/{job_name}`

**Summary:** Get Job


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `job_name` | path | Yes | `string` |  |


---

#### `POST` `/api/v1/system/jobs/{job_name}/interval`

**Summary:** Update Job Interval Route


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `job_name` | path | Yes | `string` |  |


---

#### `POST` `/api/v1/system/jobs/{job_name}/cancel`

**Summary:** Cancel Queue Job


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `job_name` | path | Yes | `string` |  |


---

#### `GET` `/api/v1/system/jobs/stream`

**Summary:** Stream Queue Progress


---

### Local Metadata

#### `GET` `/api/v1/system/local_metadata/library/tracks`

**Summary:** List Tracks


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `page` | query | No | `integer` |  |
| `per_page` | query | No | `integer` |  |
| `artist_id` | query | No | `string` |  |
| `album_id` | query | No | `string` |  |
| `q` | query | No | `string` |  |


---

#### `GET` `/api/v1/system/local_metadata/library/tracks/{track_id}`

**Summary:** Get Track


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `track_id` | path | Yes | `integer` |  |


---

#### `GET` `/api/v1/system/local_metadata/library/artists`

**Summary:** List Artists


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `page` | query | No | `integer` |  |
| `per_page` | query | No | `integer` |  |
| `q` | query | No | `string` |  |


---

#### `GET` `/api/v1/system/local_metadata/library/albums`

**Summary:** List Albums


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `page` | query | No | `integer` |  |
| `per_page` | query | No | `integer` |  |
| `artist_id` | query | No | `string` |  |
| `q` | query | No | `string` |  |


---

### Local Server

#### `GET` `/api/v1/system/local_server/stream`

**Summary:** Stream Audio


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `path` | query | Yes | `string` | Path to the audio file |


---

### Manager

#### `GET` `/api/v1/system/manager/settings`

**Summary:** Manager Settings


**Request Body Schema:** Custom JSON Body


---

#### `POST` `/api/v1/system/manager/settings`

**Summary:** Set Manager Settings


**Request Body Schema:** `ManagerSettingsRequest`


---

#### `GET` `/api/v1/system/manager/ui-beta`

**Summary:** Ui Beta Opt


**Request Body Schema:** Custom JSON Body


---

#### `POST` `/api/v1/system/manager/ui-beta`

**Summary:** Ui Beta Opt


**Request Body Schema:** Custom JSON Body


---

#### `GET` `/api/v1/system/manager/suggestion-candidates`

**Summary:** Get Suggestion Candidates


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `limit` | query | No | `integer` |  |


---

#### `POST` `/api/v1/system/manager/suggestion-candidates/override`

**Summary:** Override Suggestion Candidate


**Request Body Schema:** `OverrideRequest`


---

#### `POST` `/api/v1/system/manager/scan`

**Summary:** Run Manager Scan


---

#### `POST` `/api/v1/system/manager/prune/run`

**Summary:** Run Prune Job


---

#### `GET` `/api/v1/system/manager/duplicates`

**Summary:** Get Duplicates


---

#### `GET` `/api/v1/system/manager/queue/actions`

**Summary:** Get Action Queue


---

#### `POST` `/api/v1/system/manager/track/{track_id}/force_delete`

**Summary:** Force Delete Track


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `track_id` | path | Yes | `integer` |  |


---

#### `POST` `/api/v1/system/manager/track/{track_id}/force_upgrade`

**Summary:** Force Upgrade Track


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `track_id` | path | Yes | `integer` |  |


---

#### `POST` `/api/v1/system/manager/track/{track_id}/fetch_metadata`

**Summary:** Fetch Metadata


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `track_id` | path | Yes | `integer` |  |


---

#### `POST` `/api/v1/system/manager/track/{track_id}/override`

**Summary:** Override Track


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `track_id` | path | Yes | `integer` |  |


**Request Body Schema:** `TrackOverrideRequest`


---

#### `POST` `/api/v1/system/manager/conflicts/resolve`

**Summary:** Resolve Conflict


**Request Body Schema:** `ConflictResolveRequest`


---

#### `GET` `/api/v1/system/manager/trends`

**Summary:** Get Trends


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `user_id` | query | No | `string` |  |
| `account_id` | query | No | `string` |  |


---

#### `GET` `/api/v1/system/manager/search`

**Summary:** Search Library


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `q` | query | No | `string` |  |


---

#### `GET` `/api/v1/system/manager/queue/suggestions`

**Summary:** Get Suggestion Queue


---

#### `POST` `/api/v1/system/manager/veto`

**Summary:** Veto Suggestion


**Request Body Schema:** `VetoRequest`


---

#### `POST` `/api/v1/system/manager/execute`

**Summary:** Execute Pending Action


**Request Body Schema:** `ExecuteRequest`


---

### Media

#### `GET` `/api/v1/core/media/{media_id}`

**Summary:** Get Media


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `media_id` | path | Yes | `string` |  |


---

#### `GET` `/api/v1/core/media/`

**Summary:** Get Media Bulk


---

#### `GET` `/api/v1/core/media/track/{sync_id}`

**Summary:** Get Media For Track


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `sync_id` | path | Yes | `string` |  |


---

### Media Server

#### `GET` `/api/v1/system/media_server/active`

**Summary:** Get Active Server


---

#### `POST` `/api/v1/system/media_server/activate`

**Summary:** Set Active Server


**Request Body Schema:** `ActivateServerRequest`


---

### Metadata

#### `GET` `/api/v1/core/metadata/queue`

**Summary:** Get Queue


---

#### `GET` `/api/v1/core/metadata/queue/{task_id}`

**Summary:** Get Queue Item


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `task_id` | path | Yes | `integer` |  |


---

#### `GET` `/api/v1/core/metadata/queue/{task_id}/audio`

**Summary:** Stream Queue Audio


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `task_id` | path | Yes | `integer` |  |


---

#### `POST` `/api/v1/core/metadata/queue/approve`

**Summary:** Approve Match


**Request Body Schema:** `ApproveMatchRequest`


---

#### `POST` `/api/v1/core/metadata/queue/manual-search`

**Summary:** Manual Search


**Request Body Schema:** `ManualSearchRequest`


---

#### `DELETE` `/api/v1/core/metadata/queue/ignore`

**Summary:** Ignore Task


**Request Body Schema:** `IgnoreTaskRequest`


---

#### `GET` `/api/v1/core/metadata/isrc/{isrc}`

**Summary:** Lookup Isrc


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `isrc` | path | Yes | `string` |  |


---

#### `GET` `/api/v1/core/metadata/cover-art`

**Summary:** Get Cover Art


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `path` | query | Yes | `string` | absolute path to audio file |


---

### Metadata Review

#### `GET` `/api/v1/core/metadata_review`

**Summary:** Get Review Queue


---

#### `PUT` `/api/v1/core/metadata_review/{task_id}`

**Summary:** Update Review Queue Item


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `task_id` | path | Yes | `integer` |  |


**Request Body Schema:** `UpdateReviewQueueRequest`


---

#### `PATCH` `/api/v1/core/metadata_review/{task_id}/save`

**Summary:** Update Review Queue Item


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `task_id` | path | Yes | `integer` |  |


**Request Body Schema:** `UpdateReviewQueueRequest`


---

#### `POST` `/api/v1/core/metadata_review/{task_id}/approve`

**Summary:** Approve Review Queue Item


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `task_id` | path | Yes | `integer` |  |


**Request Body Schema:** `ApproveReviewQueueRequest`


---

#### `GET` `/api/v1/core/metadata_review/{task_id}/stream`

**Summary:** Stream Review Queue Item


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `task_id` | path | Yes | `integer` |  |


---

#### `GET` `/api/v1/core/metadata_review/{task_id}/cover`

**Summary:** Get Review Queue Item Cover


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `task_id` | path | Yes | `integer` |  |


---

#### `POST` `/api/v1/core/metadata_review/{task_id}/lookup/acoustid`

**Summary:** Lookup Review Queue Item Acoustid


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `task_id` | path | Yes | `integer` |  |


---

#### `POST` `/api/v1/core/metadata_review/{task_id}/lookup/musicbrainz`

**Summary:** Lookup Review Queue Item Musicbrainz


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `task_id` | path | Yes | `integer` |  |


**Request Body Schema:** `MusicBrainzLookupRequest`


---

### Playlists

#### `GET` `/api/v1/core/playlists/`

**Summary:** List Playlists


---

#### `POST` `/api/v1/core/playlists/analyze`

**Summary:** Analyze Playlists


**Request Body Schema:** `PlaylistAnalyzeSchema`


---

#### `POST` `/api/v1/core/playlists/analyze/start`

**Summary:** Start Analyze Job


**Request Body Schema:** `PlaylistAnalyzeSchema`


---

#### `GET` `/api/v1/core/playlists/analyze/{job_id}`

**Summary:** Get Analyze Job


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `job_id` | path | Yes | `string` |  |


---

#### `POST` `/api/v1/core/playlists/sync`

**Summary:** Trigger Sync


**Request Body Schema:** `PlaylistSyncSchema`


---

#### `GET` `/api/v1/core/playlists/sync/events`

**Summary:** Sync Events


---

#### `GET` `/api/v1/core/playlists/sync/history`

**Summary:** Sync History Endpoint


---

#### `POST` `/api/v1/core/playlists/download-missing`

**Summary:** Download Missing Tracks


---

#### `GET` `/api/v1/core/playlists/genres`

**Summary:** Get Available Genres


---

#### `GET` `/api/v1/core/playlists/genre/{genre_name}`

**Summary:** Get Genre Playlist


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `genre_name` | path | Yes | `string` |  |


---

#### `GET` `/api/v1/core/playlists/decade/{decade}`

**Summary:** Get Decade Playlist


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `decade` | path | Yes | `string` |  |


---

#### `GET` `/api/v1/core/playlists/popular-picks`

**Summary:** Get Popular Picks


---

#### `GET` `/api/v1/core/playlists/hidden-gems`

**Summary:** Get Hidden Gems


---

#### `GET` `/api/v1/core/playlists/discovery-shuffle`

**Summary:** Get Discovery Shuffle


---

#### `GET` `/api/v1/core/playlists/daily-mixes`

**Summary:** Get All Daily Mixes


---

#### `POST` `/api/v1/core/playlists/sync/schedule`

**Summary:** Schedule Recurring Sync


**Request Body Schema:** `PlaylistSyncScheduleSchema`


---

#### `GET` `/api/v1/core/playlists/sync/scheduled`

**Summary:** List Scheduled Syncs


---

#### `DELETE` `/api/v1/core/playlists/sync/scheduled/{sync_id}`

**Summary:** Delete Scheduled Sync


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `sync_id` | path | Yes | `string` |  |


---

### Plugins

#### `GET` `/api/v1/system/plugins`

**Summary:** List All Plugins


---

#### `GET` `/api/v1/system/plugins/ui-manifest`

**Summary:** Get Ui Manifest


---

#### `POST` `/api/v1/system/plugins/config`

**Summary:** Update Plugin Config


**Request Body Schema:** `UpdateConfigRequest`


---

#### `GET` `/api/v1/system/plugins/repos`

**Summary:** Get Repos


---

#### `POST` `/api/v1/system/plugins/repos`

**Summary:** Add Repo


**Request Body Schema:** `RepoRequest`


---

#### `DELETE` `/api/v1/system/plugins/repos`

**Summary:** Remove Repo


**Request Body Schema:** `RepoRequest`


---

#### `GET` `/api/v1/system/plugins/store`

**Summary:** Get Plugin Store


---

#### `POST` `/api/v1/system/plugins/install`

**Summary:** Install Plugin


**Request Body Schema:** `PluginActionRequest`


---

#### `POST` `/api/v1/system/plugins/update`

**Summary:** Update Plugin


**Request Body Schema:** `PluginActionRequest`


---

#### `POST` `/api/v1/system/plugins/rollback`

**Summary:** Rollback Plugin


**Request Body Schema:** `PluginActionRequest`


---

#### `POST` `/api/v1/system/plugins/{plugin_id}/rollback`

**Summary:** Rollback Plugin


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `plugin_id` | path | Yes | `string` |  |


---

#### `POST` `/api/v1/system/plugins/{plugin_id}/beta-opt`

**Summary:** Set Plugin Beta Opt


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `plugin_id` | path | Yes | `string` |  |


**Request Body Schema:** `BetaOptRequest`


---

#### `POST` `/api/v1/system/plugins/uninstall`

**Summary:** Uninstall Plugin Route


**Request Body Schema:** `UninstallPluginRequest`


---

#### `POST` `/api/v1/system/plugins/{plugin_id}/toggle`

**Summary:** Toggle Plugin


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `plugin_id` | path | Yes | `string` |  |


**Request Body Schema:** `ToggleRequest`


---

#### `GET` `/api/v1/system/plugins/{plugin_id}/{filename}`

**Summary:** Serve Plugin Asset


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `plugin_id` | path | Yes | `string` |  |
| `filename` | path | Yes | `string` |  |


---

#### `GET` `/api/v1/system/plugins/`

**Summary:** List All Plugins


---

#### `GET` `/api/v1/system/plugins/download-clients`

**Summary:** List Download Clients


---

#### `GET` `/api/v1/system/plugins/download-clients/active`

**Summary:** Get Active Download Client


---

#### `POST` `/api/v1/system/plugins/download-clients/activate`

**Summary:** Set Active Download Client


**Request Body Schema:** `ActivateClientRequest`


---

#### `GET` `/api/v1/system/plugins/{plugin_id}/playlists`

**Summary:** Get Plugin Playlists


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `plugin_id` | path | Yes | `string` |  |


---

#### `GET` `/api/v1/system/plugins/{plugin_id}/settings`

**Summary:** Get Plugin Settings


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `plugin_id` | path | Yes | `string` |  |


---

#### `POST` `/api/v1/system/plugins/{plugin_id}/settings`

**Summary:** Update Plugin Settings


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `plugin_id` | path | Yes | `string` |  |


---

#### `GET` `/api/v1/system/plugins/full`

**Summary:** List Plugins Route


---

#### `GET` `/api/v1/system/plugins/by-capability/{capability}`

**Summary:** Get Plugins By Capability


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `capability` | path | Yes | `string` |  |


---

#### `GET` `/api/v1/system/plugins/{plugin_id}`

**Summary:** Get Plugin Details


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `plugin_id` | path | Yes | `string` |  |


---

#### `GET` `/api/v1/system/plugins/{plugin_id}/credentials`

**Summary:** Get Plugin Credentials


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `plugin_id` | path | Yes | `string` |  |


---

#### `POST` `/api/v1/system/plugins/{plugin_id}/credentials`

**Summary:** Set Plugin Credentials


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `plugin_id` | path | Yes | `string` |  |


**Request Body Schema:** `SetCredentialsRequest`


---

### Search

#### `GET` `/api/v1/core/search/`

**Summary:** Aggregate Search


---

#### `GET` `/api/v1/core/search/discovery`

**Summary:** Federated Discovery


---

#### `POST` `/api/v1/core/search/route`

**Summary:** Route Search Result


---

### Suggestions

#### `GET` `/api/v1/core/suggestions/accounts`

**Summary:** Get Suggestion Accounts


---

#### `GET` `/api/v1/core/suggestions/pending/{account_id}`

**Summary:** Get Pending Suggestions


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `account_id` | path | Yes | `integer` |  |


---

#### `POST` `/api/v1/core/suggestions/approve`

**Summary:** Approve Suggestion


**Request Body Schema:** `ApproveSuggestionRequest`


---

#### `GET` `/api/v1/core/suggestions/audit`

**Summary:** Get Suggestion Audit


---

#### `POST` `/api/v1/core/suggestions/toggle-auto`

**Summary:** Toggle Auto Suggestions


**Request Body Schema:** `ToggleAutoRequest`


---

### Sync

#### `GET` `/api/v1/core/sync/status`

**Summary:** Sync Status


---

#### `GET` `/api/v1/core/sync/options`

**Summary:** Sync Options


---

### System

#### `GET` `/api/v1/system/health`

**Summary:** Health Check


---

#### `POST` `/api/v1/system/restart`

**Summary:** Request Restart


---

#### `POST` `/api/v1/system/backup`

**Summary:** Create System Backup


---

#### `GET` `/api/v1/system/backups`

**Summary:** List System Backups


---

#### `GET` `/api/v1/system/backups/{filename}/download`

**Summary:** Download System Backup


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `filename` | path | Yes | `string` |  |


---

#### `POST` `/api/v1/system/restore`

**Summary:** Restore System Backup


---

#### `GET` `/api/v1/system/stats`

**Summary:** System Stats


---

#### `GET` `/api/v1/system/settings`

**Summary:** Get Settings


---

#### `POST` `/api/v1/system/settings`

**Summary:** Update Settings


---

#### `PATCH` `/api/v1/system/settings`

**Summary:** Update Settings


---

#### `GET` `/api/v1/system/encryption-key-warning`

**Summary:** Get Encryption Key Warning


---

#### `GET` `/api/v1/system/migration-status`

**Summary:** Get Migration Status


---

#### `POST` `/api/v1/system/migration-acknowledge`

**Summary:** Acknowledge Migration


---

#### `GET` `/api/v1/system/accounts`

**Summary:** Get All System Accounts


---

#### `POST` `/api/v1/system/accounts/map`

**Summary:** Map System Accounts


---

#### `GET` `/api/v1/system/logs`

**Summary:** Get Logs


---

#### `GET` `/api/v1/system/activity/feed`

**Summary:** Activity Feed


---

#### `GET` `/api/v1/system/activity/toasts`

**Summary:** Activity Toasts


---

#### `GET` `/api/v1/system/downloads/status`

**Summary:** Downloads Status


---

#### `GET` `/api/v1/system/quality-profile`

**Summary:** Quality Profile


---

#### `POST` `/api/v1/system/quality-profile`

**Summary:** Save Single Quality Profile


---

#### `GET` `/api/v1/system/quality-profiles`

**Summary:** List Quality Profiles


---

#### `POST` `/api/v1/system/quality-profiles`

**Summary:** Save Quality Profiles


---

#### `GET` `/api/v1/system/browse`

**Summary:** Browse Filesystem


---

#### `GET` `/api/v1/system/settings/preferences`

**Summary:** Get Preferences


---

#### `POST` `/api/v1/system/settings/preferences`

**Summary:** Update Preferences


---

#### `POST` `/api/v1/system/settings/preview-rename`

**Summary:** Preview Rename


---

#### `POST` `/api/v1/system/enhance/trigger`

**Summary:** Trigger Metadata Enhancement


---

#### `POST` `/api/v1/system/reset/state`

**Summary:** Reset State


---

#### `POST` `/api/v1/system/reset/library`

**Summary:** Reset Library


---

#### `POST` `/api/v1/system/reset/factory`

**Summary:** Reset Factory


---

### System Tasks

#### `GET` `/api/v1/system/tasks/queue`

**Summary:** Get Task Queue Status


---

#### `GET` `/api/v1/system/tasks/processes`

**Summary:** Get Active Processes


---

#### `POST` `/api/v1/system/tasks/processes/{registration_id}/terminate`

**Summary:** Terminate Process


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `registration_id` | path | Yes | `string` |  |


---

#### `GET` `/api/v1/system/tasks/health`

**Summary:** Get Unified System Health


---

### UI Registry

#### `GET` `/api/v1/system/ui-registry`

**Summary:** Get Ui Registry


---

### Webhooks

#### `POST` `/api/v1/system/webhooks/{plugin}`

**Summary:** Handle Plugin Webhook


**Parameters:**

| Name | In | Required | Type | Description |
| --- | --- | --- | --- | --- |
| `plugin` | path | Yes | `string` |  |


---
