# EchoSync Agent Operational Mandate

## 1. Tool & Context Requirement
You are strictly forbidden from using standard OS shell commands (like `grep`, `find`, or `Get-Content`) to search the codebase. EchoSync relies on an architectural knowledge graph.
**Before executing any codebase modification, you MUST use:**
`uv run --env-file .env graphify`

## 2. Rule Ingestion
You must proactively read and adhere to all Markdown rules located in the `.agents/rules/` directory before writing code. Specifically, honor `graphify-reuse-invariant.md`, `separation-of-concerns-invariant.md`, and `core-capabilities-and-ffi-invariants.md`.