# Legacy Web UI (Flask)

- The old Flask-based web interface (`web_server.py`, templates/static it referenced) is frozen for reference only.
- Current deployments should serve the Svelte-based web UI under `webui/` and expose matching `/api` endpoints from the backend service (see `backend_entry.py`).
- Do not wire legacy Flask routes into new builds; keep these files as historical reference.
