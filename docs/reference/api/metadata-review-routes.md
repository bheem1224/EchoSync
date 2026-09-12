# API Reference: Metadata, Review Queue & Suggestions Routes

## 1. Metadata Queue Routes (`web/routes/metadata.py`)

### `GET /api/v1/core/metadata/queue`
**Description:** Retrieve current pending metadata processing queue items.

#### Query Parameters
| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `limit` | `integer` | No | `50` | Maximum queue items to return |
| `status` | `string` | No | `None` | Filter by task status (`pending`, `review`, `error`) |

#### Response `200 OK`
```json
{
  "total": 12,
  "tasks": [
    {
      "task_id": 104,
      "file_path": "/data/downloads/track01.wav",
      "status": "pending",
      "created_at": "2026-09-12T10:00:00Z"
    }
  ]
}
```

---

### `GET /api/v1/core/metadata/queue/{task_id}`
**Description:** Retrieve detailed status and candidate options for a specific metadata task.

#### Path Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `task_id` | `integer` | Yes | Unique task ID |

---

### `GET /api/v1/core/metadata/queue/{task_id}/audio`
**Description:** Stream raw audio sample for preview during metadata review.

#### Path Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `task_id` | `integer` | Yes | Unique task ID |

---

### `POST /api/v1/core/metadata/queue/approve`
**Description:** Manually approve a metadata match candidate for a task.

#### Request Body Schema (`ApproveMatchRequest`)
```json
{
  "task_id": 104,
  "candidate_mbid": "83b9c108-0131-4824-a740-496e14713437",
  "apply_tags": true
}
```

---

### `DELETE /api/v1/core/metadata/queue/ignore`
**Description:** Dismiss a task from the review queue without applying changes.

#### Request Body Schema (`IgnoreTaskRequest`)
```json
{
  "task_id": 104
}
```

---

### `GET /api/v1/core/metadata/isrc/{isrc}`
**Description:** Direct ISRC catalog lookup across external metadata providers.

#### Path Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `isrc` | `string` | Yes | International Standard Recording Code |

---

## 2. Metadata Review Routes (`web/routes/metadata_review.py`)

### `GET /api/v1/core/metadata_review`
**Description:** List all tasks requiring manual human verification in the review queue.

---

### `POST /api/v1/core/metadata_review/{task_id}/lookup/acoustid`
**Description:** Initiates an isolated Stage 3 AcoustID acoustic scan for a review queue task.

#### Path Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `task_id` | `integer` | Yes | Unique ID of the review queue task |

#### Response `200 OK`
```json
{
  "status": "success",
  "task_id": 104,
  "data": {
    "title": "One More Time",
    "artist": "Daft Punk",
    "album": "Discovery",
    "year": 2001,
    "mbid": "4daeb0a0-e290-449e-8c88-158a452bf9b4",
    "acoustid": "31b6c702-8f12-4217-bf30-5b7218698188",
    "confidence": 0.94
  }
}
```

#### Error Status Codes
| Code | Trigger Condition | Response Body |
| :--- | :--- | :--- |
| `404` | Task ID not found OR AcoustID confidence < 0.60 | `{"detail": "AcoustID found no verified matching recording"}` |
| `500` | Native FFI or Chromaprint decoder failure | `{"detail": "Internal processing error"}` |

---

### `POST /api/v1/core/metadata_review/{task_id}/lookup/musicbrainz`
**Description:** Trigger explicit Stage 5 MusicBrainz text search for candidate recordings.

#### Path Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `task_id` | `integer` | Yes | Unique task ID |

#### Request Body Schema (`MusicBrainzLookupRequest`)
```json
{
  "query_title": "string",
  "query_artist": "string",
  "query_album": "string (optional)"
}
```

---

### `POST /api/v1/core/metadata_review/{task_id}/approve`
**Description:** Approve selected candidate match and trigger atomic IO Gatekeeper promotion.

#### Path Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `task_id` | `integer` | Yes | Unique task ID |

---

## 3. Suggestions Routes (`web/routes/suggestions.py`)

### `GET /api/v1/core/suggestions/accounts`
**Description:** Get configured provider accounts generating automated suggestions.

---

### `GET /api/v1/core/suggestions/pending/{account_id}`
**Description:** Retrieve pending music recommendations generated for a specific account.

#### Path Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `account_id` | `integer` | Yes | Connected provider account ID |

---

### `POST /api/v1/core/suggestions/approve`
**Description:** Approve suggestion item and push to slskd download queue.

#### Request Body Schema (`ApproveSuggestionRequest`)
```json
{
  "suggestion_id": "string",
  "auto_download": true
}
```
