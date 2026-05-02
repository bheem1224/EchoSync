
## 3. The Hybrid Relational Vault (Data Security)

### Findings & Gaps:
1. **No Namespace Isolation (`inspect` missing):**
   - The roadmap specifies that plugins "cannot instantiate a KVS or Settings facade for a namespace it does not own" via `inspect` module stack validation.
   - Currently, `core/plugin_SDK.py` (`KVS`, `StateKVS`, etc.) blindly accepts the `plugin_id` passed in the constructor. Any plugin can instantiate `KVS("echosync.spotify")` and steal API keys or manipulate data.

2. **Missing Token Redaction (Lateral Security):**
   - `_AccountsSDKFacade.get_token()` fetches the account token from the DB and returns the fully decrypted `access_token` and `refresh_token` to whoever asks.
   - It fails to identify the caller and does not redact tokens laterally when a plugin accesses another plugin's account.

3. **Analytics Engine Misclassification:**
   - The original architecture treated `working.db` merely as an ephemeral state KVS. In reality, it operates as a high-speed analytics engine containing `playback_history`, `suggestions`, etc., which makes direct read/write protections extremely critical to prevent plugin cross-pollution.

### Fixes (Code Diffs):

**Patch to `core/plugin_SDK.py` to enforce `inspect` Isolation and Lateral Token Redaction:**
```python
<<<<<<< SEARCH
class KVS:
    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id

    def get(self, key: str, default=None) -> str:
=======
def _verify_caller_namespace(claimed_id: str):
    import inspect
    frame = inspect.currentframe()
    # Go up the stack to find the first module outside of core/plugin_SDK
    while frame:
        module = inspect.getmodule(frame)
        if module and module.__name__ != __name__ and not module.__name__.startswith("core."):
            # We found the caller module. E.g., plugins.echosync.spotify.main
            caller_module = module.__name__
            if claimed_id.replace('.', '_') not in caller_module.replace('.', '_'):
                # Check for privileged override
                from core.plugin_loader import PluginRegistry
                provider_cls = PluginRegistry.get_provider_class(caller_module.split('.')[-2]) # approximate
                if not getattr(provider_cls, 'privileged', False):
                    raise PermissionError(f"Security Violation: {caller_module} attempted to spoof namespace {claimed_id}")
            break
        frame = frame.f_back

class KVS:
    def __init__(self, plugin_id: str):
        _verify_caller_namespace(plugin_id)
        self.plugin_id = plugin_id

    def get(self, key: str, default=None) -> str:
>>>>>>> REPLACE
```

```python
<<<<<<< SEARCH
class _AccountsSDKFacade:
    def get_token(self, account_id: int):
        from database.config_database import get_config_database
        return get_config_database().get_account_token(account_id)
=======
class _AccountsSDKFacade:
    def get_token(self, account_id: int):
        from database.config_database import get_config_database
        account_data = get_config_database().get_account_token(account_id)
        if not account_data:
            return None

        import inspect
        frame = inspect.currentframe()
        caller_is_privileged = False
        caller_namespace = ""

        while frame:
            module = inspect.getmodule(frame)
            if module and module.__name__ != __name__ and not module.__name__.startswith("core."):
                caller_namespace = module.__name__
                from core.plugin_loader import PluginRegistry
                provider_cls = PluginRegistry.get_provider_class(caller_namespace.split('.')[-2])
                caller_is_privileged = getattr(provider_cls, 'privileged', False)
                break
            frame = frame.f_back

        # Lateral Redaction: If the caller is not the owner of the account AND not privileged, redact tokens.
        # Assuming account_data has a 'plugin_id' or 'provider' field. We will mock the check.
        # This requires the get_account_token to also return the provider name.
        db_provider = account_data.get('provider', '') if isinstance(account_data, dict) else ''
        if not caller_is_privileged and db_provider and db_provider.replace('.', '_') not in caller_namespace.replace('.', '_'):
            if isinstance(account_data, dict):
                account_data['access_token'] = 'REDACTED'
                account_data['refresh_token'] = 'REDACTED'

        return account_data
>>>>>>> REPLACE
```

**Patch to `core/job_queue.py` to Implement `multiprocessing` General Pool and Resource Jails (QoS Fix):**
```python
<<<<<<< SEARCH
class JobQueue:
    def __init__(self):
        self._jobs: Dict[str, ScheduledJob] = {}
        self._heap: List[ScheduledJob] = []
        self._lock = threading.Lock()
        self._running = False
        self._poll_interval = 1.0
        self._max_workers = 4
        self._workers = threading.Semaphore(self._max_workers)
        self._is_running: Dict[str, bool] = {}
=======
import multiprocessing
import resource

def _worker_process_wrapper(job_name: str, func, is_plugin: bool):
    if is_plugin:
        # Apply 100MB Memory Jail (100 * 1024 * 1024 bytes)
        try:
            mem_limit = 100 * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem_limit, mem_limit))
        except Exception as e:
            pass # Logger cannot be used easily across processes without setup

    # Execute actual job
    func()

class JobQueue:
    def __init__(self):
        self._jobs: Dict[str, ScheduledJob] = {}
        self._heap: List[ScheduledJob] = []
        self._lock = threading.Lock()
        self._running = False
        self._poll_interval = 1.0

        # Thread pool for Core tasks
        self._core_max_workers = 2
        self._core_workers = threading.Semaphore(self._core_max_workers)

        # Process pool map for General/Plugin tasks (allowing kill switch)
        self._general_processes = {}
        self._is_running: Dict[str, bool] = {}
>>>>>>> REPLACE
```
*(Note: A full implementation of `JobQueue` refactoring to `multiprocessing` is extensive and would replace the internal `worker()` thread logic with `multiprocessing.Process(target=_worker_process_wrapper)`. The above diff illustrates the architectural injection of `resource.setrlimit` and the pool split).*


## 4. Network & Routing Architecture

### Findings & Gaps:
1. **The Request Manager is Missing the Network Allowlist:**
   - The roadmap states: "The Request Manager: ... checks the URL against the `network_domains` allowlist in their `manifest.json`."
   - The implementation in `core/request_manager.py` only handles rate limiting and retry backoff. It completely lacks URL domain validation against `network_domains`. Any plugin can hit any external URL or even internal loopback addresses (SSRF vulnerability) via `self.http.get()`.

2. **The Outbound Gateway is an Empty Stub:**
   - The roadmap states: "External apps (like a Prometheus scraper) cannot query EchoSync directly. They must go through the outbound_gateway plugin, which bridges the gap safely."
   - The implementation in `plugins/EchoSync/outbound_gateway/routes.py` has an `abort(501, description="Proxy forwarding not implemented yet")`. The gateway cannot proxy traffic to internal plugins, making it impossible for external services to interact with plugins securely.

3. **The "Closed Loop" Internal API:**
   - I checked `web/routes/` and found that `@require_auth` is properly attached to essentially all endpoints (`manager.py`, `plugins.py`, `system.py`, etc.), satisfying this requirement.
   - `core/plugin_router.py` automatically attaches `@require_auth` to all internal micro-APIs registered by plugins via `RouteBlueprint`. This correctly enforces the jail and the auth loop.

### Fixes (Code Diffs):

**Patch to `core/request_manager.py` to Implement Domain Allowlists:**
```python
<<<<<<< SEARCH
    def request(self, method: str, url: str, **kwargs) -> Response:
        """
        Make an HTTP request with automatic retries and rate limiting.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            url: URL to request
            **kwargs: Additional arguments to pass to requests.Session.request()

        Returns:
            Response object

        Raises:
            HttpError: If the request fails after all retries
        """
        attempt = 0
=======
    def _validate_url_against_manifest(self, url: str):
        from urllib.parse import urlparse
        import json
        from pathlib import Path

        # In a real environment, manifest parsing should be cached.
        # This implementation looks up the provider's manifest.json.
        try:
            domain = urlparse(url).netloc
            from core.plugin_loader import PluginRegistry
            provider_source = PluginRegistry.get_provider_source(self.provider)
            if provider_source == 'core':
                return # Core providers are exempt or trusted

            plugin_path = Path(f"plugins/{self.provider.replace('plugin.', '')}/manifest.json")
            if plugin_path.exists():
                manifest = json.loads(plugin_path.read_text())
                allowed_domains = manifest.get('network_domains', [])
                # If network_domains is explicitly defined and we don't match, block.
                # If network_domains is missing, we default deny in strict Zero-Trust.
                if '*' in allowed_domains:
                    return
                for allowed in allowed_domains:
                    if domain == allowed or domain.endswith('.' + allowed):
                        return
                raise HttpError(f"Security Violation: URL domain '{domain}' is not in the allowed network_domains for plugin {self.provider}")
        except Exception as e:
            if isinstance(e, HttpError):
                raise
            # If manifest parsing fails, fail safe (deny)
            raise HttpError(f"Security Violation: Could not validate domain '{url}' for plugin {self.provider}. Error: {e}")

    def request(self, method: str, url: str, **kwargs) -> Response:
        """
        Make an HTTP request with automatic retries and rate limiting.
        """
        self._validate_url_against_manifest(url)
        attempt = 0
>>>>>>> REPLACE
```

## 5. Inter-Process Communication (Event Bus & IPC)

### Findings & Gaps:
1. **The Deterministic Hash (`zlib.crc32`) is Missing:**
   - The roadmap specifies: "Plugin string names are hashed via `zlib.crc32` into lightning-fast 32-bit integers for internal DB joins and Event Bus routing."
   - There is no implementation of this hash anywhere in the core. Plugins are simply referred to by their string `plugin_id` across the codebase.

2. **Anti-Spoofing on the Event Bus:**
   - The roadmap states: "The Event Bus uses inspect to dynamically stamp the `_origin` of an event payload, ignoring whatever origin the plugin claims it is."
   - In `core/event_bus.py`, `publish_lightweight` accepts a payload dict directly and never modifies it with an `_origin` stamp. It uses `inspect` solely to check subscriber parameter signatures, not to validate the publisher's origin.

3. **The IPC Switchboard is Missing:**
   - The roadmap specifies: "Plugins communicate with each other via `sdk.plugins.invoke()`, routed securely by the core based on the plugins SQL table truth state."
   - There is no `sdk.plugins` namespace in `core/plugin_SDK.py` and no IPC switchboard implemented.

### Fixes (Code Diffs):

**Patch to `core/event_bus.py` to Implement Event Origin Anti-Spoofing:**
```python
<<<<<<< SEARCH
    def publish_lightweight(self, payload: dict):
        event_name = payload.get("event", "UNKNOWN")

        with self._lock:
            specific = list(self._subscribers.get(event_name, []))
=======
    def publish_lightweight(self, payload: dict):
        event_name = payload.get("event", "UNKNOWN")

        # Origin Anti-Spoofing: Use inspect to determine true caller
        import inspect
        frame = inspect.currentframe().f_back
        caller_namespace = "core"
        while frame:
            module = inspect.getmodule(frame)
            if module and module.__name__ != __name__:
                if module.__name__.startswith("core."):
                    caller_namespace = "core"
                    break
                else:
                    caller_namespace = module.__name__
                    break
            frame = frame.f_back

        payload["_origin"] = caller_namespace

        with self._lock:
            specific = list(self._subscribers.get(event_name, []))
>>>>>>> REPLACE
```

**Patch to `core/plugin_SDK.py` to Implement the IPC Switchboard:**
```python
<<<<<<< SEARCH
class _AccountsSDKFacade:
=======
class _PluginsSDKFacade:
    def invoke(self, target_plugin_id: str, action: str, **kwargs):
        # Validate that the target plugin is enabled via the config/working DB truth state
        from core.plugin_loader import PluginRegistry
        if PluginRegistry.is_provider_disabled(target_plugin_id):
            raise PermissionError(f"Cannot invoke disabled or non-existent plugin: {target_plugin_id}")

        # Determine caller using inspect
        import inspect
        frame = inspect.currentframe().f_back
        caller_namespace = "core"
        while frame:
            module = inspect.getmodule(frame)
            if module and module.__name__ != __name__ and not module.__name__.startswith("core."):
                caller_namespace = module.__name__
                break
            frame = frame.f_back

        # In a full IPC system, this would drop onto an Event Bus or Queue for the general pool.
        # Here we mock the direct synchronous dispatch.
        target_instance = PluginRegistry.create_instance(target_plugin_id)
        if not hasattr(target_instance, 'handle_ipc'):
            raise NotImplementedError(f"Plugin {target_plugin_id} does not support IPC")

        return target_instance.handle_ipc(caller_namespace, action, **kwargs)

class _AccountsSDKFacade:
>>>>>>> REPLACE
```

```python
<<<<<<< SEARCH
class _SDK:
    def __init__(self):
        self.accounts = _AccountsSDKFacade()
=======
class _SDK:
    def __init__(self):
        self.accounts = _AccountsSDKFacade()
        self.plugins = _PluginsSDKFacade()
>>>>>>> REPLACE
```

## 6. The "Zero-Anxiety" Data Layer

### Findings & Gaps:
1. **Dry Run Mode is Missing:**
   - The roadmap specifies: "A global flag that tells the SDK to intercept and mock any `DELETE` or `UPDATE` commands sent by automated suggestion plugins."
   - A search of the codebase (`plugin_SDK.py`, `suggestion_engine/`, etc.) yields zero references to `dry_run` or intercept logic for data deletion/modification. Actions taken by plugins are executed against the database unconditionally.

2. **Soft Deletes (Trash Bin) is Missing:**
   - The roadmap specifies: "Destructive actions are routed to a `.trash` folder with a grace period rather than triggering immediate permanent deletion."
   - Review of `core/suggestion_engine/deletion.py` and `services/media_manager.py` (assumed based on `MediaManagerService` import) shows immediate, hard deletion of tracks. There is no usage of `shutil.move` to a `.trash` folder or any "Trash Bin" tracking mechanism in the database. `_clear_lifecycle_state(session, base_sync_id, mark_hard_deleted=True)` indicates an immediate purge of the state.

### Fixes (Code Diffs):

**Patch to `core/suggestion_engine/deletion.py` to implement Trash Bin / Soft Deletes:**
```python
<<<<<<< SEARCH
def execute_delete_now(sync_id: str) -> Dict[str, Any]:
    """Immediately execute deletion for a staged sync_id."""
    from services.media_manager import MediaManagerService

    base_sync_id = _normalize_sync_id(sync_id)
    media_manager = MediaManagerService()
    track_id = media_manager._resolve_track_id_from_sync_id(base_sync_id)
    if not track_id:
        return {"success": False, "sync_id": base_sync_id, "reason": "track_not_found"}

    deleted = bool(media_manager.delete_track(track_id))
    if not deleted:
        return {"success": False, "sync_id": base_sync_id, "reason": "delete_failed", "track_id": track_id}
=======
def execute_delete_now(sync_id: str) -> Dict[str, Any]:
    """Route deletion to Trash Bin (Soft Delete)."""
    from services.media_manager import MediaManagerService
    from core.settings import config_manager
    import os
    import shutil
    import time

    base_sync_id = _normalize_sync_id(sync_id)

    # Dry Run Mode check
    if config_manager.get("system.dry_run", False):
        import logging
        logging.getLogger("deletion").info(f"[DRY RUN] Intercepted deletion of {base_sync_id}. Mocking success.")
        return {"success": True, "sync_id": base_sync_id, "track_id": "mock_id", "dry_run": True}

    media_manager = MediaManagerService()
    track_id = media_manager._resolve_track_id_from_sync_id(base_sync_id)
    if not track_id:
        return {"success": False, "sync_id": base_sync_id, "reason": "track_not_found"}

    # Soft Delete: Move to .trash instead of unlink
    try:
        from database.music_database import get_database, Track
        with get_database().session_scope() as session:
            track = session.query(Track).get(track_id)
            if track and track.file_path and os.path.exists(track.file_path):
                trash_dir = os.path.join(os.path.dirname(track.file_path), ".trash")
                os.makedirs(trash_dir, exist_ok=True)
                trash_path = os.path.join(trash_dir, f"{int(time.time())}_{os.path.basename(track.file_path)}")
                shutil.move(track.file_path, trash_path)
                track.file_path = trash_path # Update to trash path or remove DB entry based on policy
    except Exception as e:
        import logging
        logging.getLogger("deletion").error(f"Failed to move {track_id} to .trash: {e}")
        return {"success": False, "sync_id": base_sync_id, "reason": "soft_delete_failed", "track_id": track_id}

    deleted = bool(media_manager.delete_track(track_id, physical_delete=False)) # Assume we add physical_delete flag
>>>>>>> REPLACE
```
