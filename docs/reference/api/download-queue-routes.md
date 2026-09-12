# API Reference: Downloads Queue Routes

## 1. Overview (`web/routes/downloads.py`)

The Download Queue API allows client applications to monitor active slskd downloads, enqueue missing tracks, clear completed tasks, and manage download priority.

---

## 2. API Endpoints

### `GET /api/v1/system/downloads/queue`
**Description:** Retrieve the complete download task queue including active, queued, and failed downloads.

#### Query Parameters
| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `status` | `string` | No | `None` | Filter by download status (`downloading`, `queued`, `completed`, `failed`) |
| `limit` | `integer` | No | `100` | Maximum number of items to return |

#### Response `200 OK`
```json
{
  "total": 3,
  "queue": [
    {
      "download_id": 42,
      "track_title": "Get Lucky",
      "artist": "Daft Punk",
      "provider": "slskd",
      "status": "downloading",
      "progress_percent": 68.5,
      "speed_bytes_sec": 1250000,
      "eta_seconds": 12,
      "created_at": "2026-09-12T11:55:00Z"
    }
  ]
}
```

---

### `DELETE /api/v1/system/downloads/queue`
**Description:** Clear completed or failed items from the download queue.

#### Response `200 OK`
```json
{
  "status": "success",
  "cleared_count": 5
}
```

---

### `POST /api/v1/system/downloads/run`
**Description:** Force trigger download queue processing worker.

---

### `DELETE /api/v1/system/downloads/{download_id}`
**Description:** Cancel and remove a specific download task by ID.

#### Path Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `download_id` | `integer` | Yes | Download task unique ID |

#### Response `200 OK`
```json
{
  "status": "cancelled",
  "download_id": 42
}
```

#### Error Status Codes
| Code | Trigger Condition | Response Body |
| :--- | :--- | :--- |
| `404` | Download ID not found | `{"detail": "Download task not found"}` |

---

### `POST /api/v1/system/downloads/{download_id}/search`
**Description:** Re-trigger search for an alternative slskd download source for a stuck download task.

#### Path Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `download_id` | `integer` | Yes | Download task unique ID |

---

### `DELETE /api/v1/system/downloads/batch`
**Description:** Batch cancel or delete multiple download tasks.

#### Request Body Schema (`BatchDeleteRequest`)
```json
{
  "download_ids": [42, 43, 44]
}
```

#### Response `200 OK`
```json
{
  "status": "success",
  "deleted_ids": [42, 43, 44]
}
```
