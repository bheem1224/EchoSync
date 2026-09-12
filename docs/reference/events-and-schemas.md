# Events & Real-Time Schemas Reference

## 1. EventBus Pub/Sub Engine (`core/event_bus.py`)

EchoSync uses an in-memory pub/sub `EventBus` to decouple background workers, metadata resolution pipelines, database mutations, and frontend streaming feeds.

---

## 2. Standard Event Bus Topics & Schemas

### Ingestion & Scan Events

#### Topic: `scan.started`
- **Trigger:** Initiated local filesystem scan via Rust FFI scanner.
- **Payload Schema:**
  ```json
  {
    "event": "scan.started",
    "timestamp": "2026-09-12T12:00:00Z",
    "root_path": "/data/library"
  }
  ```

#### Topic: `scan.progress`
- **Trigger:** Emitted periodically during multi-threaded scanning batches.
- **Payload Schema:**
  ```json
  {
    "event": "scan.progress",
    "processed_files": 12500,
    "total_files": 50000,
    "current_directory": "/data/library/Daft Punk"
  }
  ```

---

### Track Promotion & File Mutation Events

#### Topic: `track.promoted`
- **Trigger:** A virtual track or staging file is promoted to `library.db` as a physical track.
- **Payload Schema:** Lightweight identifier payload (never serialized track dicts):
  ```json
  {
    "event": "track.promoted",
    "sync_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "media_id": "pm-98712"
  }
  ```

---

## 3. Real-Time Streaming Feeds (SSE / Server-Sent Events)

### Endpoint: `GET /scan/stream`
- **Response Header:** `Content-Type: text/event-stream`
- **Behavior:** Yields real-time JSON events as local library ingestion proceeds. Disconnection triggers safe cancellation via `asyncio.CancelledError`.
