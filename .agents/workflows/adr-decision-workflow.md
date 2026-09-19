# ADR Decision Workflow

> **Scope:** This workflow governs every structural or behavioural change to EchoSync's
> schemas, resolution pipeline, ORM model mappings, plugin contracts, and waterfall stage
> ordering. It is enforced for both human contributors and autonomous coding agents.

---

## 1. When an ADR Is Required

An ADR **must** be authored and approved **before any code is written** when a proposed
change touches any of the following:

| Category | Examples |
|---|---|
| **Schema mutations** | Adding/removing columns in `library.db`, `working.db`, or `config.db`; altering junction tables (`track_artists`, `album_artists`) |
| **Waterfall stage changes** | Reordering, adding, or removing stages 0–6 in `MetadataResolutionEngine._execute_waterfall` |
| **Scoring heuristics** | Modifying parabolic duration curves, studio album bonuses, compilation demotion penalties, or trust-gate thresholds |
| **Plugin capability contracts** | Adding new `Capability` enum values; changing `PluginRegistry` dispatch semantics |
| **ORM model transformations** | Altering how `ResolutionResult` fields map to `Track`, `Artist`, `Album`, or junction rows |
| **Signature semantics** | Any change to when `ECHOSYNC_SIGNATURE` is stamped, verified, or rejected |
| **Core module extraction** | Splitting or merging files under `core/metadata/`, `core/matching_engine/`, or `database/` |

---

## 2. ADR Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│  TRIGGER: Proposed change to schema / waterfall / model mapping │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                   ┌───────────▼───────────┐
                   │  1. DRAFT             │
                   │  Author writes ADR    │
                   │  under docs/agents/   │
                   │  adrs/XXXX-<name>.md  │
                   └───────────┬───────────┘
                               │
                   ┌───────────▼───────────┐
                   │  2. REVIEW            │
                   │  Peer / agent review  │
                   │  Conflicts resolved   │
                   │  Open questions       │
                   │  answered             │
                   └───────────┬───────────┘
                               │
                   ┌───────────▼───────────┐
                   │  3. ACCEPTED          │
                   │  Status set to        │
                   │  "Accepted".          │
                   │  Implementation may   │
                   │  begin.               │
                   └───────────┬───────────┘
                               │
                   ┌───────────▼───────────┐
                   │  4. IMPLEMENTED       │
                   │  Code merged.         │
                   │  Graphify index       │
                   │  updated.             │
                   └───────────┬───────────┘
                               │
                   ┌───────────▼───────────┐
                   │  5. SUPERSEDED /      │
                   │     DEPRECATED        │
                   │  Old ADR updated;     │
                   │  new ADR references   │
                   │  it.                  │
                   └───────────────────────┘
```

---

## 3. ADR Document Format

Every ADR in `docs/agents/adrs/XXXX-<slug>.md` must follow this exact structure:

```markdown
# XXXX — <Title>

**Status:** Draft | Review | Accepted | Implemented | Superseded  
**Date:** YYYY-MM-DD  
**Supersedes:** (ADR number, if applicable)  
**Superseded by:** (ADR number, if applicable)

---

## Context & Problem Statement
<!-- What situation forced this decision? What fails without it? -->

## Decision Drivers
<!-- Non-negotiable constraints: correctness, performance, security, maintainability -->

## Considered Options

### Option A — <Name>
<!-- Description, pros, cons -->

### Option B — <Name>
<!-- Description, pros, cons -->

## Decision Outcome

**Chosen option:** Option X, because …

### Invariants
<!-- Precise, machine-verifiable rules that must hold after this ADR is implemented.
     Write each invariant as a falsifiable statement. -->

- **INV-XXXX-1:** …
- **INV-XXXX-2:** …

## Consequences

### Positive
### Negative / Trade-offs
### Risks & Mitigations
```

---

## 4. Numbering Convention

ADRs are numbered sequentially with four-digit zero-padded identifiers:

```
docs/agents/adrs/
  0001-metadata-resolution-waterfall.md
  0002-reentrant-sqlite-write-lease-and-session-scope.md
  0003-container-aware-native-thread-scaling.md
  0004-plugin-isolation-integer-taint-and-sidecar-contracts.md
  0005-<next-topic>.md
```

The slug must be lowercase-hyphenated, describing the decision topic, not its resolution.

---

## 5. Pre-Implementation Verification (Agents)

Before writing any code in `core/`, `database/`, `plugins/`, or `services/`, an autonomous
agent **must** run:

```powershell
uv run --env-file .env graphify query "<subsystem> architecture invariants"
```

…and confirm that no active ADR invariant contradicts the planned change. If a conflict is
found, the agent must flag it to the user **before** modifying any source file.

---

## 6. Conflict Resolution

| Situation | Rule |
|---|---|
| Active prompt contradicts a historic ADR | Active prompt takes precedence. Update the ADR to reflect the deliberate change. Do **not** introduce undocumented workarounds. |
| Code contradicts an ADR invariant (drift) | Flag to user before writing code. Do not silently widen the invariant. |
| Two ADRs conflict with each other | The higher-numbered ADR supersedes the lower. Update both documents. |

---

## 7. Graphify Sync Obligation

After an ADR reaches **Implemented** status, run:

```powershell
uv run --env-file .env graphify update .
```

This indexes the new decision nodes into the project graph so subsequent queries reflect
the current architectural ground truth.

---

## 8. Anti-Patterns (Prohibited)

- ❌ Writing code in `core/metadata/` without a corresponding Accepted ADR for structural changes.
- ❌ Silently expanding a waterfall stage without updating ADR 0001.
- ❌ Introducing backward-compatibility shim wrappers instead of updating an ADR (violates Rule 6 of `system-invariants.md`).
- ❌ Stamping `ECHOSYNC_SIGNATURE` on a code path not covered by an existing ADR invariant.
- ❌ Running `grep` or recursive file searches in place of `graphify query` as the first investigation step.

