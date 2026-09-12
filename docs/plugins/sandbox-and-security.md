# Plugin Sandbox & Security Architecture

## 1. Zero-Trust Security Paradigm

EchoSync enforces zero-trust security for all third-party plugins. Plugins are never trusted to self-assert identity via string parameters.

---

## 2. Security Invariants

1. **Path Provenance Identity:** Nexus Framework verifies plugin caller identity using physical file path provenance (`inspect.stack()[1].filename`) to securely compute 32-bit CRC32 plugin hashes internally.
2. **Sub-App Namespacing:** REST routes are strictly mounted under `/api/v1/plugins/{plugin_id}/`.
3. **HTTP Rate Limiting:** Outbound HTTP requests from plugins must use `RequestManager` to observe global rate limits. Direct `requests` or `httpx` imports are prohibited.
4. **AST Inspection:** Plugin python source files are scanned during loading for forbidden calls (`os.remove`, `shutil.move`, `sqlite3.connect`).
