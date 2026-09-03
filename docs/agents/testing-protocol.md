# Verification & Testing Protocols for Autonomous Coding Agents

## 1. Environment Preparation

Before executing backend tests or running FastAPI routes, ensure the mandatory encryption key environment variable is set:

```bash
export MASTER_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

---

## 2. Command Execution Protocol (`uv run`)

All Python verification scripts, test commands, and lint checks MUST be executed using `uv run`:

```bash
# Correct execution pattern
uv run python tools/lint_audio_calls.py
uv run pytest
```

---

## 3. Required Verification Steps

After making code changes, agents must execute these verification routines:

1. **Audio Tagging Lint Check:**
   ```bash
   uv run python tools/lint_audio_calls.py
   ```
2. **Automated Test Suite:**
   ```bash
   uv run pytest
   ```
3. **File State Verification:**
   Use `read_file` or `list_files` to confirm created/modified files match expected content and formatting.

---

## 4. Benchmarking & Telemetry Rules

- Do NOT write mock scripts, standalone test harnesses, or benchmarking code to prove Big-O performance gains.
- Telemetry state must be tracked using ephemeral thread-safe in-memory singletons backed by `threading.Lock` (`ScanStateManager`), avoiding SQLite for telemetry state.
