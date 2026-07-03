# AI SYSTEM PROMPT: EchoSync Plugin Generation (v2.5.0)

CONTEXT: You are writing plugins for the EchoSync v2.5.0 Nexus Framework. You must adhere strictly to these structural boundaries.

## 1. Identity & Database Contract
- ABORT legacy SyncID concepts (Base64 hashes).
- `SyncID` = Abstract Track logical identity (NanoID).
- `MediaID` = Physical file identity.
- Plugins NEVER touch `music.db` directly. All provisional track data manipulated by plugins must interact exclusively with the JSON `track_data` blob inside `working.db`.
- Database interaction occurs ONLY via SDK jail facades.

## 2. Capability Architecture
- ABORT strict `PluginBase` inheritance or `@abstractmethod` implementations.
- Write functional python modules.
- Plugins are loaded and routed strictly by declared Enums (e.g., `Capability.FETCH_METADATA`, `Capability.DOWNLOAD_MEDIA`).
- Rely on the Orchestrator's "Priority Waterfall". Expect your plugin's entry point to receive payloads and return strict dictionary structures. If you fail, return `None` immediately so the orchestrator can route to the fallback provider.

## 3. Development Workflow
- Expect hot-reloading aggressive Garbage Collection (GC).
- When bootstrapping a plugin directory, mandate the inclusion of `"dev_mode": true` in the plugin `manifest.json` to shield the local directory from the Nexus GC during iteration.

## 4. Expected I/O
- Input payloads match strict dictionaries (refer to `EVENT_BUS_EVENTS.md` for schemas like `DOWNLOAD_INTENT`).
- Output returns must be lean, JSON-serializable dictionaries. Do not return complex Python objects or SQLAlchemy models. The framework serializes outputs immediately.
