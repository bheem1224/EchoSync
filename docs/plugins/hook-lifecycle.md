# Plugin Hook Lifecycle & Execution Matrix

## 1. Overview

EchoSync plugins interact with the core engine through event lifecycle hooks registered via the Nexus Framework.

---

## 2. Supported Hook Matrix

| Hook Name | Input Payload | Return Schema | Description |
| :--- | :--- | :--- | :--- |
| `on_metadata_lookup` | `{"title": str, "artist": str}` | `[CandidateDict]` | Intercepts metadata search and returns candidate matches |
| `on_track_promoted` | `{"sync_id": str, "media_id": str}` | `None` | Fired when a track is promoted to `library.db` |
| `on_download_requested` | `{"track_id": str, "quality": str}` | `{"status": str, "download_id": int}` | Triggered to enqueue a download task |
| `on_sync_triggered` | `{"target": str}` | `{"synced_items": int}` | Triggered during media server synchronization |

---

## 3. Hook Execution Flow

1. **Dispatch:** Core service emits hook request via `PluginRegistry.dispatch_hook(hook_name, payload)`.
2. **Execution:** Active plugins implementing the hook run in parallel or sequence depending on capability type.
3. **Validation:** Returned payloads are validated against Pydantic response models before being consumed by core services.
