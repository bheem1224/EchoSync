---
trigger: always_on
---

### Python Runtime & Environment Management (`uv`)

1. **Virtual Environment Isolation**:
   - Always manage and execute Python through `uv`. Never invoke global/system Python interpreters or package managers (`python`, `python3`, `pip`, `pipenv`, `poetry`).
   - Do NOT run `pip install <package>` or edit `site-packages` directly.

2. **Command Execution Rules**:
   - Run all scripts, test runners, linters, and backend servers using `uv run`:
     - Run scripts: `uv run python -m <module>` or `uv run <script.py>`
     - Run tests: `uv run pytest`
     - Run migrations: `uv run alembic upgrade head`
     - Format/lint: `uv run ruff check .` / `uv run ruff format .`

3. **Dependency Management**:
   - Add new dependencies via CLI only: `uv add <package>` (or `uv add --dev <package>` for dev tools).
   - Sync the workspace environment using `uv sync`.
   - Never manually modify dependency hashes in `uv.lock`. Commit changes made to `pyproject.toml` and `uv.lock` by the CLI.

4. **Interpreter Path Resolution**:
   - When configuring language servers, debuggers, or IDE tools, point exclusively to the local virtual environment binary at `.venv/bin/python` (Unix) or `.venv\Scripts\python.exe` (Windows).
