---
trigger: always_on
description: Mandatory ADR consultation via Graphify and decision logging for system architecture changes.
---

## Architecture Decision Record (ADR) Protocol

1. **Pre-Implementation Verification:**
   - Before introducing, modifying, or refactoring core infrastructure (`core/`, `database/`, `plugins/`), query Graphify:
     `uv run --env-file .env graphify query "<Subsystem> architecture invariants"`
   - Adhere strictly to the active architectural patterns defined in `docs/agents/system-invariants.md` and `docs/agents/adrs/`.

2. **Conflict Resolution & Prompt Primacy:**
   - Active user prompts take absolute precedence over historic ADRs.
   - If an instruction deliberately changes a historical design, update the relevant ADR and do not introduce undocumented workarounds.
   - If an architectural discrepancy is discovered between active code and documentation, flag it explicitly to the user before writing code.

3. **ADR Indexing:**
   - Major system decisions must be committed under `docs/agents/adrs/XXXX-<name>.md` using the standard format:
     - **Context & Problem Statement**
     - **Decision Drivers**
     - **Considered Options & Trade-offs**
     - **Decision Outcome & Invariants**
   - Run `uv run --env-file .env graphify update .` to index the new ADR into the project graph.