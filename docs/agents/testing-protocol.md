# Testing Protocol for Autonomous Coding Agents

## 1. Overview

This document outlines mandatory testing, verification, and linting procedures that autonomous coding agents must execute when making changes to EchoSync.

---

## 2. Environment Verification

Ensure the test environment is initialized with the master encryption key:

```bash
export MASTER_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

---

## 3. Mandatory Pre-Commit Verification Steps

1. **Audio Tagging Lint Check:**
   ```bash
   uv run python tools/lint_audio_calls.py
   ```
   *Expected Result:* `[OK] No rogue tag-reader imports found. Codebase is clean.`

2. **Automated Application Test Suite:**
   ```bash
   uv run pytest
   ```
   Ensure all core orchestration, matching engine, and database repository unit tests pass without failures.

3. **Read-After-Write Verification:**
   After editing or creating any file, verify changes using read tools or directory listing commands prior to plan step completion.
