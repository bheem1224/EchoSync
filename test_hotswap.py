import os
import sys
from pathlib import Path

# Setup env for database access
os.environ["ECHOSYNC_SAFE_MODE"] = "0"

# Append project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.nexus_framework.plugin_loader import PluginLoader, generate_plugin_id
from database.config_database import get_config_database


def main():
    print("=== Phase 0: Setup ===")
    app = FastAPI()
    app_root = Path(__file__).resolve().parent
    loader = PluginLoader(app_root, main_app=app)
    client = TestClient(app)

    plugin_name = "echo_test"
    plugin_id = generate_plugin_id(plugin_name)
    print(f"Plugin ID: {plugin_id}")

    # Register in DB to ensure reload_plugin works
    db = get_config_database()
    conn = db._open_connection()
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO services (plugin_id, name, absolute_install_path, version, is_active) VALUES (?, ?, ?, ?, ?)",
        (
            plugin_id,
            plugin_name,
            str(app_root / "plugins" / "EchoSync" / plugin_name),
            "1.0.0",
            1,
        ),
    )
    conn.commit()
    conn.close()

    print("=== Phase 1: Load ===")
    # _load_plugin_package performs the actual load
    success = loader._load_plugin_package(plugin_id)
    if not success:
        print("Failed to load plugin!")
        sys.exit(1)

    print(f"Routes mapped: {[r.path for r in app.routes]}")

    response = client.get(f"/api/v1/plugins/{plugin_id}/ping")
    print(f"GET /ping: {response.status_code} {response.text}")
    assert response.status_code == 200
    assert response.json() == {"status": "v1"}

    print("=== Phase 2: Reload (Update routes.py to v2) ===")
    routes_file = app_root / "plugins" / "EchoSync" / plugin_name / "routes.py"
    with open(routes_file, "w") as f:
        f.write(
            'from fastapi import APIRouter\n\nrouter = APIRouter()\n\n@router.get("/ping")\ndef ping():\n    return {"status": "v2"}\n'
        )

    loader.reload_plugin(plugin_id)

    response = client.get(f"/api/v1/plugins/{plugin_id}/ping")
    print(f"GET /ping after reload: {response.status_code} {response.text}")
    assert response.status_code == 200
    assert response.json() == {"status": "v2"}, f"Expected v2, got {response.json()}"

    print("=== Phase 3: Unload ===")
    loader.unload_plugin(plugin_id)

    print(f"Routes mapped after unload: {[r.path for r in app.routes]}")

    response = client.get(f"/api/v1/plugins/{plugin_id}/ping")
    print(
        f"GET /ping after unload: {response.status_code} {response.text if hasattr(response, 'text') else ''}"
    )
    assert response.status_code == 404

    print("ALL TESTS PASSED SUCCESSFULLY.")


if __name__ == "__main__":
    main()
