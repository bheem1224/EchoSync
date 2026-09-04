# Nexus Sandbox Security & Store Governance

## 1. Zero-Trust Security Philosophy

EchoSync enforces a **Zero-Trust Security Architecture** for third-party plugins. Unprivileged plugins cannot perform direct file I/O, execute raw subprocesses, or access host environment variables directly.

---

## 2. Abstract Syntax Tree (AST) Scanner

When a plugin is loaded, `PluginSecurityScanner` (`core/nexus_framework/plugin_loader.py`) parses all `.py` files and rejects the plugin if forbidden patterns are detected:

### Prohibited Operations

* **Direct Filesystem Mutations:** `open()`, `os.remove`, `os.unlink`, `shutil.move`, `shutil.rmtree`.
* **Subprocess & OS Execution:** `subprocess.Popen`, `os.system`, `sys.exit`.
* **Dynamic Code Execution:** `eval()`, `exec()`, `__import__()`, `globals()`, `locals()`, `__builtins__`.
* **Direct Database Connections:** `sqlite3.connect`, raw SQLAlchemy session creation outside SDK.

---

## 3. Physical File Path Provenance Identity

To prevent identity spoofing, EchoSync verifies plugin identity using physical file path provenance (`inspect.stack()[1].filename`). Unprivileged plugins cannot fake `plugin_id` parameters.

---

## 4. WASM & Native Code Extensions

- **WASM Modules (`.wasm`):** Standard unprivileged plugins can bundle compiled WebAssembly modules executed via `WasmPluginWrapper` (`wasmtime`).
- **Native Binary Extensions (`.so`/`.pyd`):** Native binaries are blocked unless `privileged: true` is set in `manifest.json` and manually approved by the user.

---

## 5. Plugin Store Governance & Audit Tracks

1. **Fast Track (Unprivileged Pure Python / WASM):** Automatically validated by AST scanner and published to the store.
2. **Audit Track (Privileged / Native Code):** Mandatory manual code audit required before official store approval.
