# EchoSync Plugin Architecture & Hooks [PENDING v2.5.0]

For v2.5.0, EchoSync is introducing a Zero-Trust Plugin Sandbox utilizing an AST (Abstract Syntax Tree) scanner. This ensures that community-developed plugins cannot inadvertently (or maliciously) damage the host environment.

## 🛡️ The AST Sandbox

When a plugin is loaded, the `plugin_loader.py` parses the python file into an AST before execution.

**Strictly Forbidden Imports:**
*   `os`, `sys`, `subprocess` (No shell execution or arbitrary file reading)
*   `sqlite3`, `sqlalchemy` (No direct database manipulation; plugins must use provided DataBrokers)
*   `importlib`, `__import__` (No dynamic bypassing of the AST scanner)

## 🪝 The Hook System

Plugins interact with EchoSync by registering callbacks to specific lifecycle events using the `HookManager`.

There are three types of hooks:

1.  **Pre-Hooks (`pre_`)**: Run *before* the core engine executes a step. These are typically used to mutate or clean the input data. (e.g., `pre_normalize_title`).
2.  **Post-Hooks (`post_`)**: Run *after* the core engine executes a step. These are used to augment the final output or trigger side effects (e.g., sending a Discord notification when a download finishes).
3.  **Skip-Hooks (`skip_`)**: The most powerful hooks. If a plugin registers a Skip-Hook and returns a valid payload, the core engine will **completely bypass** its native logic for that step and use the plugin's payload instead.

*See the individual system documentation files (Matching Engine, Download Manager, etc.) for specific hook implementations.*
