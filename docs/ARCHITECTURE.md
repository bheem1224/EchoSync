# SoulSync Architecture Constitution

## 1. Core Principles
* **Central Control:** The `Core` module controls ALL scheduling, database access, and configuration.
* **Dumb Providers:** Providers (Plex, Spotify) are READ-ONLY data fetchers. They DO NOT schedule jobs. They DO NOT write to the DB directly. They only return `SoulSyncTrack` objects.
* **Template Pattern:** All providers must inherit from `ProviderBase` and `Provider{insert Class}Base` and implement `_map_basic_metadata` and `_enrich_ids`.

## 2. Data Models
* **SoulSyncTrack:** The universal object. Providers must map their raw data to this format.
    * Fields: `title`, `artist`, `album`, `isrc`, `external_ids` (dict).
    * Quality: `bit_depth` (int or None), `sample_rate`.

## 3. The Matching Engine
* Located in `core/matching`.
* Uses `ScoringProfile` constants (Strict vs. Fuzzy).
* Handles `pyacoustid` (fingerprinting) internally.

## 4. Current State
* Plex Provider is fetching partial libraries (pagination issue?).
* VS Code is fragile; avoid excessive logging.

## 5. Core Capabilities (MANDATORY USAGE)
**Do not reinvent these wheels in the Providers.**

### A. Network & Rate Limiting (`core.request_manager`)
* **Feature:** Global HTTP client with automatic retries, backoff, and domain-specific rate limiting.
* **Rule:** Providers MUST NOT use `requests.get()` or `aiohttp` directly.
* **Usage:** `self.core.http.get(url, params=...)`
* **Why:** Core handles the "429 Too Many Requests" errors globally.

### B. Central Logging (`core.logger`)
* **Feature:** Unified logging with rotation and level management.
* **Rule:** Do not use `print()` or `logging.getLogger()`.
* **Usage:** `self.logger.info(...)` (Inherited from `ProviderBase`).
* **Why:** Prevents console flooding and ensures logs go to the file for debugging.

### C. Error Handling & Circuit Breaking
* **Feature:** Core wraps provider execution.
* **Rule:** Providers should raise specific exceptions (`ProviderAuthError`, `ProviderNetworkError`) rather than handling generic `Exception`.
* **Why:** Core decides whether to retry the job or disable the provider temporarily.

### D. Configuration (`core.config`)
* **Feature:** Centralized settings management (API Keys, Paths).
* **Rule:** Never hardcode paths or timeouts.
* **Usage:** `self.config.get('plex.timeout')`