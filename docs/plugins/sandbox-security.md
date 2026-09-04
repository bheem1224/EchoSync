# Plugin Sandbox Security & Path Boundaries

## 1. Zero-Trust AST Sandbox Overview

To protect users' host systems and media libraries from malicious or faulty community code, EchoSync executes unprivileged plugins under a **Zero-Trust AST Sandbox**.

Before any Python file within a plugin package is imported or executed, the `PluginSecurityScanner` parses its Abstract Syntax Tree (AST) and evaluates node calls against forbidden function signatures, modules, and attribute accesses.

---

## 2. Blocked Operations & Prohibited Imports

The following operations trigger immediate plugin load rejection:

### Direct Filesystem Mutations
- Prohibited modules: `os`, `shutil`, `pathlib`, `glob`
- Prohibited methods: `open()`, `os.remove()`, `os.unlink()`, `os.rename()`, `shutil.move()`, `shutil.copy()`
- **Remediation:** Plugins must route safe file reads/writes through the `PluginStorageBox` or `LocalFileHandler` provided by `core/plugin_sdk.py`.

### Audio Tagging & Tag Readers
- Prohibited modules: `mutagen`, `tinytag`, `taglib`
- **Remediation:** Audio tagging must strictly invoke `echosync_core` Rust native FFI via `PluginSDK`.

### Direct Database Access
- Prohibited imports: `sqlite3`, `sqlalchemy`, `psycopg2`
- Direct SQL queries against `config.db`, `working.db`, or `library.db` are strictly forbidden.
- **Remediation:** Plugins manage local settings and state strictly via `PluginStorageBox()`.

### Code Reflection & Dynamic Execution
- Prohibited builtins: `eval()`, `exec()`, `__import__()`, `getattr()`, `setattr()`, `globals()`, `locals()`

---

## 3. Path Traversal & Zero-Trust Boundaries

When a plugin requests file access or path translations:
1. `core/io_gatekeeper.py` verifies the plugin's permissions in `manifest.json`.
2. Paths are canonicalized inside native Rust code (`echosync_core`), confirming that resolved realpaths reside strictly within configured host mount points (`/data/library`, `/data/downloads`).
3. Attempts to traverse outside allowed boundaries via symlinks or relative paths (`../`) raise an `IOGatekeeperSecurityViolation`.

---

## 4. Privileged Mode & Native Binaries

If a plugin requires raw system access or native binaries (`.so` / `.pyd` / C++ extensions):
- `manifest.json` must explicitly set `"privileged": true`.
- Privileged plugins bypass the AST scanner but **require manual multi-sig approval** ("Web of Trust" Sentinel audit) before installation from the official Plugin Store.
