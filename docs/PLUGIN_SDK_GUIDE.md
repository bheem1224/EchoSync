# EchoSync Developer SDK Guide

Welcome to the EchoSync "Nexus Framework" Plugin SDK. EchoSync v2.4.1+ transitions away from monolithic, hardcoded providers to a dynamic, event-driven plugin architecture.

This is your guide for writing robust, secure, and performant community plugins.

## 1. The Zero-Trust AST Sandbox

To protect users from malicious or poorly written plugins (which could corrupt their media libraries or expose sensitive config data), EchoSync executes all third-party plugins within a strict Abstract Syntax Tree (AST) Sandbox.

### What is Blocked?
The `PluginSecurityScanner` inspects your code before it is allowed to load. It will flatly reject your plugin if it detects the use of:
* Direct filesystem manipulation (`open()`, `os.remove`, `shutil`)
* System/Subprocess calls (`subprocess`, `os.system`, `sys`)
* Dynamic execution and reflection (`eval`, `exec`, `__import__`, `getattr`, `setattr`, `globals`, `locals`, `__builtins__`)
* Core database models or direct SQLite session manipulation (`sqlite3`, `SQLAlchemy` sessions)

**Where to find the exact rules:**
The absolute source of truth for blocked modules, functions, and attributes is the `PluginSecurityScanner` class located in `core/plugin_loader.py`. Review this file to understand the exact AST node visitation rules.

## 2. Safe File I/O

Since standard Python file operations like `open()` and `os.remove()` are blocked by the AST scanner, you must route your file operations through the SDK.

### Using LocalFileHandler
To read, write, tag, or translate paths for media files, plugins must utilize the `LocalFileHandler` interface. This ensures all file operations respect the user's defined path mappings, container boundaries, and permissions.

**Where to find the implementation:**
Explore the `core/file_handling/` directory (specifically `local_file_handler.py` or equivalent files) to see the available methods for safe file operations.

## 3. Database Architecture & Storage

EchoSync uses a strict multi-database setup (`config.db`, `music.db`, `working.db`) managed via Alembic migrations. Plugins cannot execute raw `ALTER TABLE` statements or manipulate core tables directly.

### The `ProviderStorageBox`
Plugins are given their own isolated sandbox for data storage. When you request database access, the system returns a `ProviderStorageBox` object.

* **Table Prefixing:** The `ProviderStorageBox` forcefully prepends `prv_{plugin_id}_` to any table you create. This prevents your plugin from accidentally (or maliciously) overwriting core tables like `tracks` or `users`.
* **Where to find it:** Check `working_database.py` (specifically `get_provider_storage()`) to see how the wrapper is generated.

### Core Write Overrides
If your plugin *absolutely must* write to a core operational table (e.g., updating a `user_ratings` row), you must use the explicit `CORE_WRITE_OVERRIDE` context manager provided by the SDK. This signals intent and bypasses the prefixing mechanism temporarily, subject to core validation.

**Where to find it:** Reference `core/plugin_store.py` or the core database utilities for the implementation details of the override context manager.

## 4. Privileged Mode & Compiled Binaries

We recognize that the AST sandbox is highly restrictive. If you are building a high-performance feature that requires raw system access—such as a C++/Rust audio analyzer, an advanced metadata ripper, or heavy filesystem scanning—you can use the "Escape Hatch."

### Enabling Privileged Mode
You must explicitly declare your need for system access by setting `"privileged": true` in your plugin's `manifest.json`.

*NOTE: Users will be heavily warned in the UI when installing a privileged plugin.*

### The CoreBinaryRunner
Even in privileged mode, avoid using `subprocess` directly. The SDK provides the `CoreBinaryRunner` utility. This wrapper safely executes your compiled binaries, handles standard output/error streams, prevents zombie processes, and respects the core application's shutdown signals.

**Where to find it:** Check the SDK utility files (often located in `core/` or `core/utils/`) for `CoreBinaryRunner`.

## 5. Job Queue & Core Hooks

Plugins should not run infinite `while True: sleep()` loops or spawn rogue `threading.Thread` instances. These will be flagged and killed.

### Registering Background Tasks
To perform background work (e.g., periodic polling, API syncing), you must hook into the core concurrency-limited queue.
Use `register_scheduled_task()` (or the equivalent job registration method in the API) to add your workload to the queue.

**Where to find it:** See `core/job_queue.py` for the API on registering background jobs, intervals, and concurrency locking.

### The Skip Hook Dictionary Contract
The hook system allows you to completely bypass core services (like the Matching Engine or Download Manager). If your plugin intercepts a "Skip Hook", it must return a specific dictionary contract:

```python
{"skip": True, "result": ...}
```

If the core engine receives this payload, it will immediately abort its default logic and use your `result` instead.

**Where to find it:** For a complete list of all currently available hooks (Event, Mutator, and Skip), you should check the event registry in `core/hook_manager.py`.

## 6. HTTP Client & Rate Limiting

All plugins must use the centralized `RequestManager` for HTTP requests. This ensures consistent rate limiting across the entire EchoSync ecosystem and prevents thundering herd problems that could get your IP banned by API providers.

### Using RequestManager in Your Plugin
When your plugin needs to make HTTP requests, instantiate a `RequestManager` with your desired rate limit:

```python
from core.request_manager import RequestManager, RateLimitConfig

class MyPlugin(ProviderBase):
    def __init__(self, config):
        super().__init__(config)
        # Create RequestManager with custom rate limit (optional)
        # Default is 1 RPS if not specified
        self.http = RequestManager(
            provider="my_plugin",
            rate=RateLimitConfig(requests_per_second=2.0)
        )
    
    def search(self, query: str):
        # Use the RequestManager for all HTTP requests:
        response = self.http.get('https://api.example.com/track')
        response = self.http.post('https://api.example.com/search', json={'q': query})
        return response.json()
```

### Default Rate Limit: 1 Request Per Second
By default, all requests are rate-limited to **1 RPS** to protect against API abuse. When you instantiate `RequestManager`, you can override this by passing a `RateLimitConfig`:

```python
# Use default 1 RPS (no rate config needed)
http = RequestManager("my_provider")

# Or customize it:
from core.request_manager import RateLimitConfig
http = RequestManager(
    "my_provider",
    rate=RateLimitConfig(requests_per_second=2.5)
)
```

### Automatic Retry & Backoff
The RequestManager automatically retries failed requests with exponential backoff:
* Retries on network errors (timeouts, connection refused)
* Retries on 429 (Too Many Requests) and 5xx (Server Errors)
* Maximum 3 attempts by default
* Exponential backoff: 0.5s → 1s → 2s → 4s → 8s (capped at 8 seconds)
* Random jitter (+/- 25%) prevents thundering herd

You do not need to implement your own retry logic.

**Where to find it:** See `core/request_manager.py` for the complete implementation and configuration options.

## 7. Database Engine Swaps (PostgreSQL/MySQL)

EchoSync v2.4.1+ officially supports swapping the core database engine from SQLite to PostgreSQL or MySQL for high-scale enterprise deployments.

### How it Works Conceptually
The architecture separates configuration (`config.json`) from data storage. Instead of hardcoded `sqlite:///` connection strings, the application reads the `database_uri` dynamically on boot.

### How to Swap
1. Open your `config.json`.
2. Locate the database connection settings.
3. Replace the SQLite URIs with your target engine URIs:
   ```json
   "database": {
     "music_uri": "postgresql://user:pass@localhost:5432/echosync_music",
     "working_uri": "postgresql://user:pass@localhost:5432/echosync_working"
   }
   ```
   *(Note: `config.db` containing encrypted secrets generally remains SQLite unless explicitly supported).*

**Important Considerations:**
* Existing SQLite data does **not** automatically migrate to Postgres/MySQL. You must start fresh or use a database migration tool (like pgloader) manually.
* Alembic migrations will run automatically on boot against the new target URI.

**Where to see it in action:**
To see exactly where the connection strings are parsed and the database engines are loaded, look at `core/migrations.py` (specifically `run_auto_migrations()`) and the database definition files (`working_database.py`, `music_database.py`).
