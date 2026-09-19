# Feature Discovery & Execution Workflow

**Trigger:** Any task requiring new business logic, utility functions, string manipulation, logging, file handling, orchestration, or architectural modifications.

## Step 1: The Discovery Gate (Graph Query)
Before writing any code, you must query the knowledge graph to map existing capabilities.
- Run: `uv run --env-file .env graphify query "<core_concept>"`
- *Example:* `uv run --env-file .env graphify query "string normalization"`

## Step 2: Signature Verification (Native File Read)
Once Graphify identifies a relevant target module or class, use native IDE read tools to inspect the file and verify the exact function signatures and data contracts. Do not guess the parameters based on the graph summary alone.

## Step 3: Reuse or Halt
Evaluate the existing component against your current task requirements:
- **If Sufficient:** Reuse the component immediately in your implementation.
- **If Insufficient:** Stop writing code. Output an upgrade plan explaining how the centralized component should be extended, and ask the user for authorization to proceed.

## Step 4: Graph Synchronization
If you are authorized to make architectural changes, create new modules, or significantly alter function signatures, you must synchronize the graph once tests pass.
- Run: `uv run --env-file .env graphify update .`