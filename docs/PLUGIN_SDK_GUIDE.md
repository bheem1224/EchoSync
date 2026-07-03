# Plugin SDK Guide (v2.5.0 Nexus Framework)

This guide defines the integration surface for developing plugins within the EchoSync Nexus Framework. The architecture is designed to be functional, isolated, and capability-driven.

## 1. PluginBase Loosening & Capability Routing

In v2.5.0, the strict object-oriented inheritance model has been deprecated. Plugins are no longer required to implement rigid `@abstractmethod` signatures from `PluginBase`.

### Functional Modules Over Inheritance
- Plugins are evaluated dynamically as functional modules.
- The Nexus loader registers plugins based on the capabilities they export (e.g., `Capability.FETCH_METADATA`, `Capability.DOWNLOAD_MEDIA`), rather than checking strict inheritance chains.
- This design allows developers to write lean plugins that only handle the precise inputs and outputs required by their advertised capabilities.

## 2. Development Modes & Garbage Collection

EchoSync aggressively manages plugin lifecycle state and dependencies to prevent memory leaks and zombie processes during hot reloads. During active plugin development, this strict Garbage Collector (GC) must be bypassed.

### Global Development Mode
- **Flag:** Environment variable `DEV_MODE=true` (or `ECHOSYNC_DEV_MODE=1`).
- **Effect:** Disables global caching layers, disables fast-path ISRC matching mechanisms (forcing deep resolution), and suppresses aggressive application-wide background cleanups to make debugging deterministic.

### Specific Plugin Manifest Override
- **Flag:** Include `"dev_mode": true` in the plugin's `manifest.json`.
- **Effect:** Specifically shields that individual plugin's directory from the Hot Reload Garbage Collector. It allows the developer to modify files, trigger recompilations, or change dependencies without the framework purging the directory under the assumption of a corrupted state.

## 3. Storage and State Mutation Restrictions

Plugins operate in a strict Zero-Trust environment.

### Database Constraints
- Plugins cannot execute raw schema migrations or modify core relational tables in `music.db` directly.
- Plugins are allocated sandboxed KVS (Key-Value Store) capabilities or namespace-jailed relational slices inside `working.db` for state management via the provided SDK facades.
