# API Reference: System, Jobs & Admin Routes

## 1. System Administration Routes (`web/routes/system.py`)

### `GET /api/v1/system/health`
**Description:** System status and database connectivity check.

#### Response `200 OK`
```json
{
  "status": "healthy",
  "version": "2.5.0",
  "databases": {
    "config_db": "connected",
    "working_db": "connected",
    "library_db": "connected"
  },
  "uptime_seconds": 86400
}
```

---

### `GET /api/v1/system/settings`
**Description:** Retrieve active encrypted application configuration settings.

---

### `POST /api/v1/system/settings`
**Description:** Update application configuration settings in `config.db`.

---

### `POST /api/v1/system/backup`
**Description:** Create an encrypted system backup archive.

---

### `POST /api/v1/system/restore`
**Description:** Restore system state from a backup archive.

---

## 2. Jobs Routes (`web/routes/jobs.py`)

### `GET /api/v1/system/jobs/`
**Description:** List all scheduled background system jobs.

#### Response `200 OK`
```json
{
  "jobs": [
    {
      "job_name": "library_scan",
      "status": "idle",
      "interval_seconds": 3600,
      "last_run": "2026-09-12T08:00:00Z",
      "next_run": "2026-09-12T09:00:00Z"
    }
  ]
}
```

---

### `POST /api/v1/system/jobs/run`
**Description:** Manually trigger immediate execution of a background job.

---

### `POST /api/v1/system/jobs/{job_name}/kill`
**Description:** Force cancel an active running job.

#### Path Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `job_name` | `string` | Yes | Target job identifier |

---

## 3. Auth & Accounts Routes (`web/routes/auth.py`, `web/routes/accounts.py`)

### `POST /api/v1/system/auth/login`
**Description:** Authenticate user credentials and receive session token.

#### Request Body Schema (`LoginRequest`)
```json
{
  "username": "string",
  "password": "string"
}
```

---

### `GET /api/v1/system/accounts/{service_name}`
**Description:** List external provider account configurations.

---

## 4. Webhooks & Plugins API Routes (`web/routes/webhooks.py`, `web/routes/plugins.py`)

### `POST /api/v1/system/webhooks/{plugin}`
**Description:** Generic endpoint for receiving external OAuth callbacks or provider webhooks.

#### Path Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `plugin` | `string` | Yes | Target plugin identifier |

---

### `GET /api/v1/system/plugins`
**Description:** List all installed EchoSync plugins and operational statuses.
