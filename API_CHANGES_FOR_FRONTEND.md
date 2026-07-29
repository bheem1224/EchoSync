# API Schema Documentation for Svelte Dashboard Component

This document details the real-time Task Manager, Process Supervisor, and Unified System Health REST API endpoints for the Svelte frontend dashboard.

---

## **Base URL**: `/api/v1`

---

### **1. GET `/api/v1/tasks/queue`**

Returns real-time task queue status, including summary counts and lists of running, pending, and blocked jobs.

#### **Response Body Schema (`TaskQueueSummaryResponse`)**:
```json
{
  "stats": {
    "total": 13,
    "running": 1,
    "pending": 11,
    "blocked": 1
  },
  "running_jobs": [
    {
      "name": "media_server_scan",
      "category": "general",
      "state": "running",
      "enabled": true,
      "running": true,
      "next_run": 1785360000.0,
      "interval_seconds": 10800.0,
      "tags": [],
      "plugin": "echosync.local_server",
      "total_successes": 4,
      "total_failures": 0,
      "last_error": null
    }
  ],
  "pending_jobs": [
    {
      "name": "database_update",
      "category": "general",
      "state": "pending",
      "enabled": true,
      "running": false,
      "next_run": 1785367200.0,
      "interval_seconds": 21600.0,
      "tags": [],
      "plugin": null,
      "total_successes": 12,
      "total_failures": 0,
      "last_error": null
    }
  ],
  "blocked_jobs": [
    {
      "name": "stale_track_scan_job",
      "category": "general",
      "state": "pending_blocked",
      "enabled": true,
      "running": false,
      "next_run": 1785360010.0,
      "interval_seconds": 604800.0,
      "tags": [],
      "plugin": "plugin.spotify",
      "total_successes": 0,
      "total_failures": 0,
      "last_error": null
    }
  ]
}
```

---

### **2. GET `/api/v1/tasks/processes`**

Returns all active sub-processes and worker threads registered in the `ProcessSupervisor`.

#### **Response Body Schema (`ProcessListResponse`)**:
```json
{
  "total": 2,
  "processes": [
    {
      "owner_id": "plugin.plex",
      "owner_type": "plugin",
      "pid": 14208,
      "thread_id": 21040,
      "task_name": "library_sync",
      "started_at": "2026-07-29T21:30:00.000000",
      "metadata": {
        "target": "music_library_1"
      }
    },
    {
      "owner_id": "core.binary_runner",
      "owner_type": "core",
      "pid": 19412,
      "thread_id": 11204,
      "task_name": "fpcalc",
      "started_at": "2026-07-29T21:34:00.000000",
      "metadata": {
        "cmd": ["fpcalc", "-json", "sample.flac"]
      }
    }
  ]
}
```

---

### **3. POST `/api/v1/tasks/processes/{registration_id}/terminate`**

Terminates a specific process or worker thread by registration ID.

#### **Response Body Schema (`ProcessTerminateResponse` - 200 OK)**:
```json
{
  "status": "terminated",
  "registration_id": "plugin.plex_a8f9c10d",
  "message": "Successfully terminated process 'plugin.plex_a8f9c10d' (Task: library_sync)"
}
```

#### **Error Response (404 Not Found)**:
```json
{
  "error": "Process registration not found",
  "registration_id": "invalid_id"
}
```

---

### **4. GET `/api/v1/system/health`**

Aggregates overall platform health checks and plugin lifecycle states (`UNCONFIGURED`, `INITIALIZING`, `READY`, `DEGRADED`, `ERROR`).

#### **Response Body Schema (`SystemHealthResponse`)**:
```json
{
  "status": "healthy",
  "timestamp": "2026-07-29T21:35:00.000000+00:00",
  "health_checks": {
    "status": "healthy",
    "summary": {
      "total": 3,
      "operational": 3,
      "degraded": 0,
      "failed": 0
    },
    "results": {
      "core": {
        "service": "core",
        "status": "healthy",
        "message": "Core services operational"
      }
    }
  },
  "plugin_states": {
    "echosync.local_server": {
      "state": "ready",
      "message": "Service operational",
      "last_health_check": "2026-07-29T21:35:00.000000Z"
    },
    "plugin.spotify": {
      "state": "degraded",
      "message": "Rate limit warning",
      "last_health_check": "2026-07-29T21:34:50.000000Z"
    }
  }
}
```
