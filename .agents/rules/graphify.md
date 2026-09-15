---
trigger: always_on
description: Mandatory architectural navigation via Graphify knowledge graph at graphify-out/. Enforces graph-first queries and project-scoped environment loading.
---

## Graphify Architecture & Navigation Invariants

This repository maintains an active Graphify architectural knowledge graph under `graphify-out/`.

### 1. Mandatory Gatekeeper Protocol (Zero-Search Rule)
For **any** inquiry involving architecture, symbol discovery, function calls, class relationships, dependency tracing, or cross-module boundaries:
* **PROHIBITION:** You are strictly forbidden from running `grep`, regex searches, or recursive directory scans across raw source files before querying the graph.
* **MANDATORY FIRST ACTION:** Always query `graphify-out/graph.json` first using the CLI runner.
* **EXPLORATION SEQUENCE:**
  1. Targeted Query: `uv run --env-file .env graphify query "<question>"`
  2. Relationship Path: `uv run --env-file .env graphify path "<SymbolA>" "<SymbolB>"`
  3. Concept Summary: `uv run --env-file .env graphify explain "<SymbolOrModule>"`
  4. Impact Analysis: `uv run --env-file .env graphify affected "<Symbol>"`
* If `graphify-out/wiki/index.md` exists, consult it before opening raw implementation files.
* Only open and read source files *after* Graphify has pinpointed the exact target nodes and call sites.

### 2. Environment & LLM Access Invariant
* **MANDATORY FLAG:** Every invocation of `graphify` **MUST** be executed through `uv run --env-file .env graphify <command>`.
* **RATIONALE:** Bare invocations (`graphify ...` or `uv run graphify ...`) lack the project-scoped API keys (e.g., `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, or `OPENAI_API_KEY`) stored in `.env`.
* **FAILURE IMPACT:** Without `--env-file .env`, Pass 3 semantic analysis, LLM community labeling (`label`), and semantic re-extraction fail silently or drop down to placeholder communities (`Community N`), degrading the graph's query fidelity.

### 3. Graph Synchronization Protocol
* Whenever you add, refactor, or delete backend or core modules (`core/`, `services/`, `plugins/`, `database/`), update the graph at the end of the session:
  ```powershell
  uv run --env-file .env graphify update .

