# Verification & Testing Protocols for Autonomous Coding Agents

## 1. Environment Preparation

Before executing backend tests or running FastAPI routes, ensure the mandatory encryption key environment variable is set:

```bash
export MASTER_KEY="dGVzdF9tYXN0ZXJfa2V5XzMyX2J5dGVzX2xvbmdfMTI="
```

## 2. Audio Tagging Compliance Verification

Run the architectural linter script to confirm no rogue tagging imports have been introduced:

```bash
uv run python tools/lint_audio_calls.py
```

## 3. Test Execution Protocol

- Execute unit tests using `uv run pytest`:
```bash
MASTER_KEY="dGVzdF9tYXN0ZXJfa2V5XzMyX2J5dGVzX2xvbmdfMTI=" uv run pytest tests/ -v
```
- Verify that no new test regressions or broken imports are introduced.
