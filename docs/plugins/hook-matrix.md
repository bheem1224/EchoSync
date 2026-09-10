# EchoSync Lifecycle Hook Matrix & Web Component Integration

## 1. Overview & Execution Model

EchoSync uses `HookManager` (`core/hook_manager.py`) to manage hook registration, filter pipeline execution, and UI Web Component extension loading.

## 2. Core Hook Matrix

| Hook Name | Category | Signature | Description |
| :--- | :--- | :--- | :--- |
| `register_metadata_requirements` | Filter | `(reqs: list[str]) -> list[str]` | Registers required metadata keys for enhancement targeting. |
| `post_metadata_enrichment` | Transform | `(track: Track) -> Track` | Intercepts track entity after metadata enrichment prior to DB commit. |
| `scoring_modifier` | Filter | `(candidate: dict) -> dict` | Modifies match confidence scores for candidate track pairs. |
| `ui_component_register` | UI | `() -> list[dict]` | Registers custom element Svelte Web Components for frontend rendering. |
