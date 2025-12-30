# Developer Guide: Adding Providers & Plugins

## Overview

Providers and plugins share identical architecture:
- **Bundled Providers** (official, released with app): `providers/`
- **Plugins** (community, user-developed): `plugins/`

Both use the same structure: `client.py` (logic) + `adapter.py` (HTTP routes). The registry auto-discovers them.

---

## Structure: Client + Adapter Pattern

```
providers/my_service/
├── __init__.py
├── client.py       # Service client logic
└── adapter.py      # HTTP API routes (optional)

plugins/my_custom_service/
├── __init__.py
├── client.py       # Service client logic
└── adapter.py      # HTTP API routes (optional)
```

---

## Step 1: Implement the Client

**File:** `providers/my_service/client.py` (or `plugins/my_custom_service/client.py`)

```python
from core.provider_base import ProviderBase

class MyServiceClient(ProviderBase):
    """
    Service client for MyService.
    
    Inherits from ProviderBase which provides:
    - name: str (e.g., 'my_service')
    - config: dict (from config_manager)
    - capabilities: dict (search, playlists, library, etc.)
    """
    
    name = 'my_service'
    
    def __init__(self):
        super().__init__()
        self.api_key = self.config.get('api_key')
    
    def search_tracks(self, query: str, limit: int = 10):
        """Search for tracks matching query."""
        # Implementation...
        return [...]
    
    def get_playlists(self):
        """Fetch user's playlists."""
        # Implementation...
        return [...]
    
    def is_connected(self) -> bool:
        """Check if service is reachable."""
        # Implementation...
        return True
```

**Key Points:**
- Class must inherit from `core.provider_base.ProviderBase`.
- Define a `name` attribute (lowercase, unique).
- Implement capability methods (search_tracks, get_playlists, etc.).
- Access config via `self.config` (populated from config.json).

---

## Step 2: Implement the HTTP Adapter (Optional)

**File:** `providers/my_service/adapter.py` (or `plugins/my_custom_service/adapter.py`)

```python
from flask import Blueprint, jsonify, request
from providers.my_service.client import MyServiceClient

bp = Blueprint('my_service', __name__, url_prefix='/api/my_service')
client = MyServiceClient()

@bp.post('/search')
def search():
    """POST /api/my_service/search"""
    query = request.json.get('q')
    results = client.search_tracks(query)
    return jsonify({'results': results}), 200

@bp.get('/playlists')
def get_playlists():
    """GET /api/my_service/playlists"""
    playlists = client.get_playlists()
    return jsonify({'items': playlists}), 200
```

**Key Points:**
- Define a Flask Blueprint with unique `url_prefix` (e.g., `/api/my_service`).
- Use the client class from the same package.
- Return JSON responses.
- If no custom routes needed, you can omit this file.

**Note:** Standard routes (settings GET/POST, playlists list) are handled by `web/routes/providers.py` automatically.

---

## Step 3: Register the Adapter (Optional, If Using Custom Routes)

**File:** `web/api_app.py`

If you added custom routes, register the adapter blueprint:

```python
from providers.my_service.adapter import bp as my_service_bp

def create_app() -> Flask:
    app = Flask(__name__)
    # ... existing blueprints ...
    app.register_blueprint(my_service_bp)
    return app
```

**Note:** If your plugin only uses standard settings/playlists routes, this step is optional.

---

## Step 4: Create __init__.py

**File:** `providers/my_service/__init__.py` (or `plugins/my_custom_service/__init__.py`)

```python
from providers.my_service.client import MyServiceClient
from providers.my_service.adapter import bp

__all__ = ['MyServiceClient', 'bp']
```

**Note:** The adapter import is optional if no custom routes.

---

## Installation

### For Bundled Providers:
1. Add to `providers/my_service/` with `client.py` and optionally `adapter.py`.
2. Update `providers/__init__.py` to include `'my_service'` in `__all__`.
3. Restart the app.

### For Community Plugins:
1. Add to `plugins/my_custom_service/` with `client.py` and optionally `adapter.py`.
2. Restart the app.
3. System auto-discovers via `core/provider_registry.py`.

---

## Capabilities Declaration

Define what your provider supports in `client.py`:

```python
from core.provider_base import ProviderBase

class MyServiceClient(ProviderBase):
    name = 'my_service'
    
    # Declare capabilities
    supports_search = True
    supports_playlists = True  # READ, READ_WRITE, or NONE
    supports_library_scan = False
    supports_streaming = True
    
    # Custom capability metadata
    capabilities = {
        'search': {'tracks': True, 'albums': True, 'artists': False},
        'metadata': {'richness': 'high'},
    }
```

The registry and API automatically expose these via `/api/providers/<name>`.

---

## Config Storage

Access configuration in your client:

```python
class MyServiceClient(ProviderBase):
    def __init__(self):
        super().__init__()
        self.api_key = self.config.get('api_key')
        self.api_url = self.config.get('api_url', 'https://api.myservice.com')
```

User settings are persisted via:
- **POST** `/api/providers/my_service/settings` { api_key, api_url, ... }
- Config stored in `config.json` and `config.db`.

---

## Testing Your Provider

```python
import pytest
from providers.my_service.client import MyServiceClient

def test_search():
    client = MyServiceClient()
    results = client.search_tracks('test')
    assert len(results) > 0

def test_is_connected():
    client = MyServiceClient()
    assert client.is_connected() is True
```

Run tests:
```bash
pytest tests/test_providers.py -v
```

---

## Removal

**To remove a provider or plugin:**

```bash
rm -rf providers/my_service
# or
rm -rf plugins/my_custom_service
```

Restart the app. No code changes needed; the registry skips deleted providers.

---

## Example: Minimal Provider

```python
# providers/example/client.py
from core.provider_base import ProviderBase

class ExampleClient(ProviderBase):
    name = 'example'
    
    def search_tracks(self, query: str, limit: int = 10):
        return [
            {'id': '1', 'title': 'Example Track', 'artist': 'Example Artist'}
        ]
    
    def is_connected(self) -> bool:
        return True
```

That's it. Drop it in, restart, and it's available at `/api/providers/example`.

---

## Troubleshooting

**Provider not showing up in `/api/providers`:**
- Verify `name` attribute is defined in client class.
- Check that `client.py` is importable (no syntax errors).
- Restart the app (registry scans on startup only).

**Custom routes not working:**
- Verify adapter blueprint is registered in `web/api_app.py`.
- Check that `url_prefix` is unique.
- Restart the app.

**Settings not persisting:**
- Use `config_manager.set_service_credentials('provider_name', {...})` in your adapter.
- Verify `config.json` is writable (mounted volume in Docker).

---

## References

- [Backend Architecture](BACKEND_ARCHITECTURE.md)
- [ProviderBase](core/provider_base.py)
- [Provider Registry](core/provider_registry.py)
- [Example Provider: Spotify](providers/spotify/client.py)
