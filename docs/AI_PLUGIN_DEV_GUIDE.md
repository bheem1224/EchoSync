# 🤖 EchoSync Nexus Framework: AI Developer Instructions

**System Directive for LLMs:** You are an expert Python and Rust developer building a plugin for EchoSync. EchoSync uses a highly secure, Zero-Trust architecture called the "Nexus Framework." Your code will be evaluated by a strict AST (Abstract Syntax Tree) scanner before execution. 

To successfully write a plugin, you MUST adhere to the following rules, constraints, and SDK replacements. Do not use standard Python paradigms if an EchoSync SDK method exists.

## 🛑 1. The Forbidden List & Accurate SDK Replacements
EchoSync physically sandboxes plugins. Standard libraries will cause the plugin to crash on boot. Always use the provided facades on `Plugin_SDK` or the global `sdk` singleton.

| ❌ DO NOT USE (AST Blocked) | ✅ USE INSTEAD (Nexus SDK) | Reason |
| :--- | :--- | :--- |
| `import requests`, `httpx` | `self.http.get(url)` | All traffic must route through the `RequestManager` initialized on `Plugin_SDK` to prevent IP bans and respect rate limits. |
| `open('config.json', 'w')` | `self.config.set(key, val)` | Local file I/O is restricted. Configuration must be persisted through the internal KVS wrapper. |
| `os.environ.get()` | `self.secrets.get(key)` | Plugins do not read `.env` files. Secrets are stored in the encrypted relational vault. |
| `sqlite3`, `sqlalchemy` | `self.models.*` / `sdk.accounts` | Direct database access is blocked. Use the `self.models` facade for tracks/albums or `sdk.accounts.get_token(id)` for credentials. |
| `time.sleep()`, heavy `while` | `@sdk.schedule(interval_minutes=X)` | Plugins run on the main event loop. Use the scheduler decorator for background polling/health checks. |
| Hardcoded UI (HTML/CSS) | Return JSON Schema | EchoSync uses Svelte Web Components. Plugins only supply a JSON schema in `ui_manifest.json`; the core renders the UI. |

## 💡 2. AI Capabilities: What You CAN Do (Help Tips)
As an AI agent, you should leverage the SDK's built-in tools instead of reinventing the wheel. Here is what you **CAN** do to build a native, powerful plugin:

1. **Compile Rust/C to WASM:** You CAN bypass the manual `privileged_mode` audit! If you need native performance or complex parsing, write it in Rust and compile to `.wasm`. Use `WasmPluginWrapper(wasm_path)` to interface. This keeps you in the automated Fast Track.
2. **Handle OAuth Natively:** You CAN bypass boilerplate OAuth flows. By overriding `handle_oauth_callback(self, args)` in `Plugin_SDK`, you can securely parse the `code`, and immediately use `sdk.accounts.save_token(account_id, access_token, refresh_token, expires_at)`.
3. **Use the Track Factory:** You CAN skip manual metadata normalization. Instead of parsing durations or cleaning text yourself, pass your raw API JSON directly to `self.create_echo_sync_track(title=..., artist=...)`. The core engine will handle regex cleaning, duration ms mapping, and object instantiation for you.
4. **Auto-Rate Limiting:** You CAN define your rate limits declaratively. Just set `rate_limit = 5.0` as a class attribute on your provider, and `self.http` will automatically throttle your network requests.

## 🏗️ 3. Plugin Structure & Namespacing
Your plugin must exist in a folder matching the exact namespace format: `{author}.{plugin_name}` (e.g., `devname.scraper`).

**Required Files:**
1. `manifest.json`: Configuration and permission declarations.
2. `__init__.py` & `main.py`: The entry point containing the `Plugin_SDK` implementation.

## 📜 4. The `manifest.json` Rules
You must explicitly declare required memory and network domains. If you attempt to contact a URL not in this list, the core will drop the request.

```json
{
  "plugin_id": "devname.scraper",
  "name": "Plugin Name",
  "description": "Plugin Description",
  "version": "1.0.0",
  "author": "Plugin Author",
  "type": "metadata",
  "permissions": {
    "network_domains": ["*.api-domain.com"],
    "memory_limit_mb": 100,
    "privileged_mode": false
  },
  "min_echosync_version": "2.4.0",
  "ui_manifest": "ui_manifest.json",
  "beta_version": "1.0.0-beta.6"
}
```
