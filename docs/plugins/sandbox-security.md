# Nexus Sandbox Security & Store Governance

## 1. Zero-Trust Security Philosophy

EchoSync enforces a **Zero-Trust Security Architecture** for third-party plugins. Unprivileged plugins cannot perform direct file I/O, execute raw subprocesses, or access host environment variables directly.

## 2. AST Security Sandbox

- **PluginSecurityScanner** (`core/nexus_framework/plugin_loader.py`): Scans plugin Python source AST prior to module import.
- **Prohibited AST Nodes**: Rejects `import os`, `import sys`, `subprocess`, raw `open()`, direct socket connections, and unauthorized `requests`/`httpx` instantiations.
- **Path Traversal Guard**: Physical filesystem operations must route strictly through `Gatekeeper` after permission verification.
