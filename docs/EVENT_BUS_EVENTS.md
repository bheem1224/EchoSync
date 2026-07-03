# Event & Task Orchestration (v2.5.0)

The v2.5.0 Nexus Framework handles cross-plugin communication, background jobs, and system signaling through structured, strict payloads.

## 1. The Priority Waterfall Mechanics

The system no longer relies on chaotic global pub/sub broadcast dicts. Instead, the orchestrator utilizes a "Priority Waterfall."

1. **Capability Query:** When an action is required (e.g., fetching metadata), the orchestrator queries the framework for all plugins declaring `Capability.FETCH_METADATA`.
2. **Sequential Await:** The orchestrator sorts the returned plugins by their configured priority score.
3. **Execution & Fallback:** It dispatches the strict payload to the highest-priority plugin. If the plugin fails, times out, or returns `None`, the orchestrator immediately passes the identical payload down to the next plugin in the waterfall until the capability is fulfilled.

## 2. Core Orchestrator Payloads

The following tables define the strict data contracts for inter-process and inter-plugin task routing.

### `DOWNLOAD_INTENT`

Dispatched to capability-matched media providers when a physical file needs to be acquired.

| Field Name | Data Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `sync_id` | String (NanoID) | Yes | The logical identifier of the target track. |
| `search_query` | String | Yes | The pre-computed fallback search string (e.g., "Artist - Title"). |
| `isrc` | String | No | The International Standard Recording Code for exact matching. |
| `duration_ms` | Integer | Yes | Target duration in milliseconds to prevent incorrect variant downloads. |

### `METADATA_ENHANCEMENT_REQUEST`

Dispatched to capability-matched metadata providers to enrich barebones track information.

| Field Name | Data Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `staging_blob_id` | String | Yes | Identifier to locate the unparsed JSON `track_data` in `working.db`. |
| `artist_hint` | String | Yes | Initial artist name string to guide search. |
| `title_hint` | String | Yes | Initial title string to guide search. |

### `STAGING_TRANSITION_APPROVE`

Internal system event fired when a provisional JSON blob is approved to become a permanent database entity.

| Field Name | Data Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `staging_blob_id` | String | Yes | The identifier of the JSON blob in `working.db`. |
| `assigned_sync_id` | String (NanoID) | Yes | The freshly generated NanoID assigned for the permanent `Track` model. |
| `resolution_strategy` | String | Yes | Indicates the path taken (e.g., "ISRC_FAST_PATH", "HEURISTIC_MATCH"). |
