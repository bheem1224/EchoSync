# Audit Log: OAuth & Routing Fix

## Step 1: Read-Only Audit & Documentation

### Observations

1.  **`core/nexus_framework/plugin_router.py`**:
    *   Currently, `PluginProxyRouter.mount_router(cls, plugin_id: int, router: Blueprint)` expects an integer `plugin_id`.
    *   It defines `prefix = f"/api/plugins/{plugin_id}"` and applies it: `router.url_prefix = prefix`.
    *   Wait, the prompt says "Modify the Blueprint/router mounting logic in the core framework (e.g., plugin_router.py). Change the url_prefix generation so that instead of using the plugin's folder name or string name (e.g., /api/plugins/Spotify), it strictly uses the stringified CRC32 hash (e.g., /api/plugins/3106502486)."
    *   However, `core/nexus_framework/plugin_loader.py` is where the string `plugin_name` is currently being used to set `url_prefix`.
    *   Line 908 of `core/nexus_framework/plugin_loader.py` is: `blueprint.url_prefix = f"/api/plugins/{plugin_name}"`. I will modify this to use the stringified CRC32 hash (which is `plugin_id`).

2.  **`core/oauth/sidecar.py`**:
    *   The sidecar attempts to route `provider_name` directly:
        `redirect_url = f"http://{lan_ip}:{main_port}/api/plugins/{provider_name}/callback"`
    *   It tries to guess the plugin name via `canonical_name.split('.')[-1]`.
    *   **Change needed**: We should rely on the OAuth `state` parameter or lookup. Since `provider_name` might just be a string name, we can compute the CRC32 hash. `plugin_cls.name` usually contains the canonical name (`{author}.{name}`). If `plugin_cls` is found, we use `generate_plugin_id(plugin_cls.name.lower())` to get the CRC32 hash and use that in the `redirect_url` as `http://127.0.0.1:5000/api/plugins/{crc32_hash}/callback` (the internal proxy target).

3.  **`plugins/EchoSync/spotify/routes.py` and `plugins/EchoSync/tidal/routes.py`**:
    *   They define `@bp.post('/accounts')` and `@bp.put('/<int:account_id>')` routes.
    *   They do things like: `from core.nexus_framework.plugin_SDK import sdk` which relies on stack inspection. Or in Tidal, `sdk.accounts.get_all()` is used without `sdk` being defined.
    *   **Change needed**: Remove `from core.nexus_framework.plugin_SDK import sdk`.
    *   Add:
        ```python
        import zlib
        from core.nexus_framework.plugin_SDK import ProviderStorageBox
        sdk = ProviderStorageBox(plugin_id=zlib.crc32(b'echosync.spotify') & 0xFFFFFFFF)
        ```
    *   Apply this to all routes requiring the SDK.

### Step 2: Enforce Hash-Based API Routing
* Modify `core/nexus_framework/plugin_loader.py` (line ~908) to set `blueprint.url_prefix = f"/api/plugins/{plugin_id}"`.
* Verify `core/nexus_framework/plugin_router.py` does `prefix = f"/api/plugins/{plugin_id}"`.

### Step 3: Fix the OAuth Sidecar Proxy
* Edit `core/oauth/sidecar.py`.
* Remove string manipulation (`canonical_name.split('.')[-1]`).
* Import `generate_plugin_id` and compute the CRC32 hash of the lowercase canonical name.
* Change redirect to `redirect_url = f"http://127.0.0.1:5000/api/plugins/{crc32_hash}/callback"`.

### Step 4: Patch the Undefined SDK in Plugin Routes
* Edit `plugins/EchoSync/spotify/routes.py`.
* Replace `from core.nexus_framework.plugin_SDK import sdk` inside all routes with explicit initialisation using `ProviderStorageBox` and the computed CRC32 hash.
* Edit `plugins/EchoSync/tidal/routes.py` similarly to fix `NameError: name 'sdk' is not defined`.
