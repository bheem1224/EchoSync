"""Tests for remote path mappings persistence across providers."""

import json
from typing import Any, cast
from flask import Flask
import pytest

from providers.plex import routes as plex_routes
from providers.navidrome import routes as navidrome_routes
from providers.jellyfin import routes as jellyfin_routes


@pytest.mark.parametrize(
    "provider, base_path, module",
    [
        ("plex", "/api/plex", plex_routes),
        ("navidrome", "/api/navidrome", navidrome_routes),
        ("jellyfin", "/api/jellyfin", jellyfin_routes),
    ],
)
def test_path_mappings_roundtrip(
    monkeypatch: Any,
    mock_config_manager: Any,
    provider: str,
    base_path: str,
    module: Any,
):
    """Ensure path_mappings can be saved and then fetched for each provider."""
    # Patch config_manager for both core and provider module
    monkeypatch.setattr("core.settings.config_manager", mock_config_manager, raising=False)
    monkeypatch.setattr(module, "config_manager", mock_config_manager, raising=False)

    app = Flask(__name__)
    app.register_blueprint(module.bp)
    client = app.test_client()

    mappings = [{"remote": "/data/music", "local": "D:/Music"}]

    # Save path mappings
    resp = client.post(f"{base_path}/settings", json={"path_mappings": mappings})
    assert resp.status_code == 200
    set_calls: list[Any] = [
        call
        for call in mock_config_manager.set.call_args_list
        if call.args and call.args[0] == f"{provider}.path_mappings"
    ]
    assert set_calls, f"No path_mappings saved for {provider}"
    saved_payload = cast(str, set_calls[-1].args[1])
    assert json.loads(saved_payload) == mappings

    # Ensure GET returns the saved mappings
    def mock_get(key: str, default: Any = None) -> Any:
        if key == f"{provider}.path_mappings":
            return json.dumps(mappings)
        if key in (f"{provider}.base_url", f"{provider}.token", f"{provider}.server_name"):
            return ""
        if key in (f"{provider}.username", f"{provider}.password"):
            return ""
        if key == "active_media_server":
            return provider
        return default

    mock_config_manager.get.side_effect = mock_get

    resp = client.get(f"{base_path}/settings")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["settings"]["path_mappings"] == mappings
