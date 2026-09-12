# API Reference: Library, Tracks, Search & Local Metadata Routes

## 1. Core Tracks Routes (`web/routes/tracks.py`)

### `GET /api/v1/core/tracks/`
**Description:** List canonical tracks in the library with optional pagination and filtering.

#### Path Parameters
*None*

#### Query Parameters
| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `detail` | `boolean` | No | `false` | Include expanded physical and virtual media details |
| `limit` | `integer` | No | `50` | Maximum number of records to return |
| `offset` | `integer` | No | `0` | Number of records to skip |
| `ids` | `string` | No | `None` | Comma-separated list of track sync UUIDs |

#### Request Body Schema
*None*

#### Response `200 OK`
```json
{
  "total": 1200,
  "limit": 50,
  "offset": 0,
  "tracks": [
    {
      "sync_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "title": "Get Lucky",
      "artist": "Daft Punk",
      "album": "Random Access Memories",
      "duration": 248,
      "isrc": "USCR11300001",
      "year": 2013,
      "created_at": "2026-01-15T10:00:00Z"
    }
  ]
}
```

#### Error Status Codes
| Code | Trigger Condition | Response Body |
| :--- | :--- | :--- |
| `400` | Invalid pagination parameters or malformed limit/offset | `{"detail": "Invalid pagination parameters"}` |
| `500` | Internal database connection error | `{"detail": "Internal server error"}` |

---

### `GET /api/v1/core/tracks/{sync_id}`
**Description:** Retrieve a single canonical track by its UUID.

#### Path Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `sync_id` | `string` | Yes | Unique track sync UUID |

#### Query Parameters
| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `detail` | `boolean` | No | `true` | Include physical file paths and remote streaming links |

#### Request Body Schema
*None*

#### Response `200 OK`
```json
{
  "sync_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "title": "Get Lucky",
  "artist": "Daft Punk",
  "album": "Random Access Memories",
  "duration": 248,
  "physical_media": [
    {
      "media_id": "pm-98712",
      "file_path": "/data/library/Daft Punk/Random Access Memories/01 - Get Lucky.flac",
      "format": "FLAC",
      "bitrate": 1042000,
      "sample_rate": 44100
    }
  ],
  "virtual_media": [
    {
      "provider_id": "spotify",
      "external_uri": "spotify:track:60nZcImufyMA1MKQL3P190"
    }
  ]
}
```

#### Error Status Codes
| Code | Trigger Condition | Response Body |
| :--- | :--- | :--- |
| `404` | Canonical track sync_id not found | `{"detail": "Track not found"}` |

---

### `PATCH /api/v1/core/tracks/{sync_id}`
**Description:** Update canonical metadata attributes for a specific track.

#### Path Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `sync_id` | `string` | Yes | Unique track sync UUID |

#### Query Parameters
*None*

#### Request Body Schema
```json
{
  "title": "Get Lucky (Radio Edit)",
  "artist": "Daft Punk",
  "album": "Random Access Memories",
  "year": 2013,
  "track_number": 1
}
```

#### Response `200 OK`
```json
{
  "status": "success",
  "sync_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "updated_fields": ["title", "year"]
}
```

#### Error Status Codes
| Code | Trigger Condition | Response Body |
| :--- | :--- | :--- |
| `400` | Malformed request body | `{"detail": "Invalid payload format"}` |
| `404` | Track sync_id not found | `{"detail": "Track not found"}` |

---

### `DELETE /api/v1/core/tracks/{sync_id}`
**Description:** Remove canonical track entity from `library.db`.

#### Path Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `sync_id` | `string` | Yes | Unique track sync UUID |

#### Query Parameters
*None*

#### Request Body Schema
*None*

#### Response `200 OK`
```json
{
  "status": "deleted",
  "sync_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

#### Error Status Codes
| Code | Trigger Condition | Response Body |
| :--- | :--- | :--- |
| `404` | Track sync_id not found | `{"detail": "Track not found"}` |

---

### `GET /api/v1/core/tracks/search`
**Description:** Search canonical tracks by title and optional artist.

#### Path Parameters
*None*

#### Query Parameters
| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `title` | `string` | Yes | *None* | Track title search term |
| `artist` | `string` | No | `None` | Track artist search term |
| `limit` | `integer` | No | `20` | Max results |
| `detail` | `boolean` | No | `false` | Include expanded media details |

#### Request Body Schema
*None*

#### Response `200 OK`
```json
{
  "results": [
    {
      "sync_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "title": "Get Lucky",
      "artist": "Daft Punk",
      "album": "Random Access Memories"
    }
  ]
}
```

#### Error Status Codes
| Code | Trigger Condition | Response Body |
| :--- | :--- | :--- |
| `400` | Missing required query parameter `title` | `{"detail": "Field required"}` |

---

## 2. Core Media Routes (`web/routes/media.py`)

### `GET /api/v1/core/media/{media_id}`
**Description:** Retrieve physical or virtual media metadata details by media ID.

#### Path Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `media_id` | `string` | Yes | Media unique ID |

#### Query Parameters
*None*

#### Request Body Schema
*None*

#### Response `200 OK`
```json
{
  "media_id": "pm-98712",
  "sync_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "type": "physical",
  "file_path": "/data/library/Daft Punk/Random Access Memories/01 - Get Lucky.flac",
  "bitrate": 1042000,
  "sample_rate": 44100
}
```

#### Error Status Codes
| Code | Trigger Condition | Response Body |
| :--- | :--- | :--- |
| `404` | Media record not found | `{"detail": "Media record not found"}` |

---

### `GET /api/v1/core/media/`
**Description:** Bulk retrieve media records by IDs.

#### Path Parameters
*None*

#### Query Parameters
| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `ids` | `string` | Yes | *None* | Comma-separated list of media IDs |

#### Request Body Schema
*None*

#### Response `200 OK`
```json
{
  "media": [
    {
      "media_id": "pm-98712",
      "sync_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    }
  ]
}
```

---

### `GET /api/v1/core/media/track/{sync_id}`
**Description:** Retrieve all media instances associated with a canonical track sync_id.

#### Path Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `sync_id` | `string` | Yes | Track sync UUID |

#### Query Parameters
*None*

#### Request Body Schema
*None*

#### Response `200 OK`
```json
{
  "sync_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "physical": [
    {
      "media_id": "pm-98712",
      "file_path": "/data/library/Daft Punk/Random Access Memories/01 - Get Lucky.flac"
    }
  ],
  "virtual": [
    {
      "media_id": "vm-1204",
      "provider_id": "spotify"
    }
  ]
}
```

---

## 3. Playlists Routes (`web/routes/playlists.py`)

### `GET /api/v1/core/playlists/`
**Description:** List all canonical and smart playlists.

#### Path Parameters
*None*

#### Query Parameters
*None*

#### Request Body Schema
*None*

#### Response `200 OK`
```json
{
  "playlists": [
    {
      "playlist_id": "pl-001",
      "name": "Synthwave Essentials",
      "track_count": 45,
      "provider": "local"
    }
  ]
}
```

---

### `POST /api/v1/core/playlists/analyze`
**Description:** Analyze playlists for missing physical media.

#### Path Parameters
*None*

#### Query Parameters
*None*

#### Request Body Schema (`PlaylistAnalyzeSchema`)
```json
{
  "playlist_ids": ["pl-001", "pl-002"]
}
```

#### Response `200 OK`
```json
{
  "status": "completed",
  "analyzed_count": 2,
  "missing_tracks": [
    {
      "title": "Midnight City",
      "artist": "M83",
      "playlist_id": "pl-001"
    }
  ]
}
```

---

### `POST /api/v1/core/playlists/sync`
**Description:** Trigger sync across connected remote providers (Plex, Spotify, Navidrome).

#### Path Parameters
*None*

#### Query Parameters
*None*

#### Request Body Schema (`PlaylistSyncSchema`)
```json
{
  "provider_id": "spotify",
  "playlist_id": "spotify:playlist:37i9dQZF1DXdLENR2yR211"
}
```

#### Response `200 OK`
```json
{
  "status": "sync_initiated",
  "job_id": "job-sync-9912"
}
```

---

## 4. Search & Discovery Routes (`web/routes/search.py`)

### `GET /api/v1/core/search/`
**Description:** Unified aggregate search across local library, virtual tracks, and connected providers.

#### Path Parameters
*None*

#### Query Parameters
| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `q` | `string` | Yes | *None* | Search query string |
| `limit` | `integer` | No | `20` | Max results count |

#### Request Body Schema
*None*

#### Response `200 OK`
```json
{
  "query": "Daft Punk",
  "tracks": [
    {
      "sync_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "title": "Get Lucky",
      "artist": "Daft Punk"
    }
  ],
  "albums": [
    {
      "album_id": "alb-102",
      "title": "Random Access Memories",
      "artist": "Daft Punk"
    }
  ],
  "artists": [
    {
      "artist_id": "art-55",
      "name": "Daft Punk"
    }
  ]
}
```

---

### `GET /api/v1/core/search/discovery`
**Description:** Federated discovery across active remote plugin metadata providers.

#### Query Parameters
| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `q` | `string` | Yes | *None* | Discovery search query |

---

## 5. Local Metadata Routes (`web/routes/local_metadata.py`)

### `GET /api/v1/system/local_metadata/library/tracks`
**Description:** List local metadata library tracks with pagination and artist/album filtering.

#### Path Parameters
*None*

#### Query Parameters
| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `page` | `integer` | No | `1` | Page number |
| `per_page` | `integer` | No | `50` | Results per page |
| `artist_id` | `string` | No | `None` | Filter by artist ID |
| `album_id` | `string` | No | `None` | Filter by album ID |
| `q` | `string` | No | `None` | Title/Artist query term |

#### Response `200 OK`
```json
{
  "page": 1,
  "per_page": 50,
  "total": 350,
  "items": [
    {
      "track_id": 12,
      "title": "Get Lucky",
      "artist_name": "Daft Punk",
      "album_title": "Random Access Memories"
    }
  ]
}
```

---

### `GET /api/v1/system/local_metadata/library/tracks/{track_id}`
**Description:** Get detailed track metadata record from local database.

#### Path Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `track_id` | `integer` | Yes | Local track ID |

---

### `GET /api/v1/system/local_metadata/library/artists`
**Description:** List local library artists with pagination.

#### Query Parameters
| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `page` | `integer` | No | `1` | Page number |
| `per_page` | `integer` | No | `50` | Results per page |
| `q` | `string` | No | `None` | Search filter |

---

### `GET /api/v1/system/local_metadata/library/albums`
**Description:** List local library albums with pagination and artist filtering.

#### Query Parameters
| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `page` | `integer` | No | `1` | Page number |
| `per_page` | `integer` | No | `50` | Results per page |
| `artist_id` | `string` | No | `None` | Filter by artist ID |
| `q` | `string` | No | `None` | Search filter |
