# Event Bus Events

This document summarizes the main `EventBus` event payloads observed in the codebase.

## Event Bus Overview

The core event bus lives in `core/event_bus.py`.

- `EventBus.publish(payload_dict)` is the modern lightweight API.
- `EventBus.publish(event_name, payload_dict)` is a transitional wrapper that also publishes via lightweight handlers.
- `EventBus.publish(channel, event_type, data)` is the legacy channel-based API used for sync job streaming.

Legacy events are stored per-channel in the bus and can be read with `event_bus.get_events(channel, since_id)`.
Lightweight events are dispatched immediately to subscribers registered with `event_bus.subscribe("EVENT_NAME", handler)`.

---

## `DOWNLOAD_INTENT`

Published by `services/sync_service.py` when a missing track is discovered during sync.
This is the payload used by `services/download_manager.py`.

Example payload:

```python
{
    "event": "DOWNLOAD_INTENT",
    "sync_id": spotify_id or spotify_track.identifiers.get('provider_id'),
    "track": full_track,
    "fallback_metadata": full_track,
    "duration_ms": full_track.get("duration_ms"),
    "isrc": full_track.get("isrc"),
    "timestamp": utc_isoformat(utc_now()),
    "source": "playlist_sync"
}
```

Notes:
- `track` contains the full Spotify track dict from `spotify_track.to_dict()`.
- `fallback_metadata` is kept for legacy compatibility.
- This event is consumed by `DownloadManager._on_download_intent()`.

---

## `TRACK_IMPORTED`

Published by `services/library_watcher.py` after a new local track is imported.
Downloaded tracks that match a newly imported file are cancelled by `DownloadManager._on_track_imported()`.

Payload shape:

```python
{
    "event": "TRACK_IMPORTED",
    "track": {
        "title": title,
        "artist_name": artist_name,
        "album_title": album_title,
        "duration_ms": duration_ms,
        "isrc": isrc,
        "file_path": str(path),
        "source": "local_server",
    },
}
```

---

## `TRACK_RATED`

Published by webhook parsers such as `core/webhook_parsers.py` for rating events.
It is consumed by `services/state_listener.py`.

Payload shape:

```python
{
    "event": "TRACK_RATED",
    "sync_id": sync_id,  # may be None
    "data": {
        "rating": rating,
        "user_id": user_id,
        "provider": "plex",
        "provider_item_id": provider_item_id,
    },
}
```

---

## `TRACK_PLAYED`

Published by webhook parsers such as `core/webhook_parsers.py` for scrobble/play events.
It is also subscribed by `services/state_listener.py`.

Payload shape:

```python
{
    "event": "TRACK_PLAYED",
    "sync_id": sync_id,  # may be None
    "data": {
        "user_id": user_id,
        "provider": "plex",
        "provider_item_id": provider_item_id,
    },
}
```

---

## `SUGGESTION_PLAYLIST_REMOVE_INTENT`

Published by `services/state_listener.py` when sponsor rating logic decides a track should be removed from suggestion playlists.
Consumed by `services/media_manager.py`.

Payload shape:

```python
{
    "event": "SUGGESTION_PLAYLIST_REMOVE_INTENT",
    "sync_id": base_sync_id,
    "user_id": user_id,
    "playlist_name": "Suggestions for You",
    "rating_stars": rating_stars,
    "rating_10": stars_to_ten_point(rating_stars),
}
```

---

## `TRACK_DOWNLOADED`

Subscribed by `plugins/spotify/cache_manager.py` to trigger playlist syncs when cached Spotify downloads complete.

Expected payload fields:

```python
{
    "event": "TRACK_DOWNLOADED",
    "sync_id": sync_id,
    ...
}
```

This event is used to trigger `SYNC_PLAYLIST_INTENT` when a downloaded track belongs to a cached playlist.

---

## `SYNC_PLAYLIST_INTENT`

Published by `plugins/spotify/cache_manager.py` when a downloaded track is present in a cached Spotify playlist.

Payload shape:

```python
{
    "event": "SYNC_PLAYLIST_INTENT",
    "playlist_id": playlist_id,
}
```

---

## Lifecycle and feedback intents

These events appear in the suggestion engine lifecycle code.

### `HARD_DELETE_INTENT`

Published by `core/suggestion_engine/deletion.py` when a hard delete is executed immediately.

Payload shape:

```python
{
    "event": "HARD_DELETE_INTENT",
    "sync_id": base_sync_id,
    "scheduled": "IMMEDIATE",
    "reason": "lifecycle_queue_processed",
}
```

### `QUALITY_UPGRADE_INTENT`

Published by `core/suggestion_engine/deletion.py` when an upgrade is queued immediately.

Payload shape:

```python
{
    "event": "QUALITY_UPGRADE_INTENT",
    "sync_id": base_sync_id,
    "scheduled": "IMMEDIATE",
    "reason": "lifecycle_queue_processed",
    "download_id": download_id,
}
```

### `PREFERENCE_MODEL_FEEDBACK`

Published by `core/suggestion_engine/deletion.py` when the suggestion engine decides to keep a track and feed feedback into the model.

Payload shape:

```python
{
    "event": "PREFERENCE_MODEL_FEEDBACK",
    "sync_id": sync_id,
    "score_10": consensus_score,
    "user_ids": user_id_list,
}
```

---

## Legacy sync event stream

These are published using the legacy `event_bus.publish(channel, event_type, data)` signature.
The event objects are stored under a channel and have the shape:

```python
{
    "id": event_id,
    "ts": timestamp,
    "type": event_type,
    "data": payload_dict,
}
```

Common legacy sync event types:

- `sync_started`
- `track_started`
- `track_synced`
- `track_failed`
- `playlist_updated`
- `sync_complete`
- `sync_error`

These are mainly used by `web/routes/playlists.py` and tested in `tests/test_sync_integration.py`.

---

## Notes

- The bus supports wildcard subscription via `event_bus.subscribe(handler)`.
- Lightweight events are dispatched immediately; legacy events are also stored for polling.
- `DOWNLOAD_INTENT` is currently the most important payload for async track queuing.
