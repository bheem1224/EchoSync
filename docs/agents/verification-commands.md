# Agent Verification Commands & Protocols

## 1. System Verification Commands

### Lint Audio Calls & Tag Import Checks
```bash
uv run python tools/lint_audio_calls.py
```

### Static Analysis & AST Invariant Scans
```bash
python3 -c "
import os, re

patterns = {
    'requests': re.compile(r'\brequests\.(get|post|put|delete|patch|head)\b'),
    'httpx': re.compile(r'\bhttpx\.(get|post|put|delete|patch|Client)\b'),
    'sqlite3': re.compile(r'\bsqlite3\.connect\b'),
    'raw_os_rename': re.compile(r'\bos\.rename\b'),
    'raw_shutil_move': re.compile(r'\bshutil\.move\b'),
    'tag_import': re.compile(r'import mutagen|import taglib|import tinytag')
}

whitelist = ['core/io_gatekeeper.py', 'core/request_manager.py', 'database/database_gateway.py', 'tools/lint_audio_calls.py']

for root, dirs, files in os.walk('.'):
    if '.venv' in root or '.git' in root or 'docs' in root: continue
    for file in files:
        if file.endswith('.py'):
            rel = os.path.relpath(os.path.join(root, file), '.')
            if rel in whitelist: continue
            with open(rel, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f, 1):
                    for k, p in patterns.items():
                        if p.search(line): print(f'[{k}] {rel}:{i} -> {line.strip()}')
"
```

### Run Test Suite
```bash
MASTER_KEY=dGhpcy1pcy1hLXRlc3QtZmVybmV0LWtleS0zMi1ieXRlczE= uv run pytest
```
