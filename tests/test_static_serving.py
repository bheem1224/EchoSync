from fastapi.testclient import TestClient
from core.settings import config_manager


def test_spa_catchall(tmp_path, monkeypatch):
    """Ensure non-API requests are served from static folder or fallback to index."""
    # create a fake build directory with index and another asset
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / "index.html").write_text("<html><body>hello</body></html>")
    (build_dir / "foo.js").write_text("console.log('hi');")

    monkeypatch.setattr(config_manager, "get", lambda key, default=None: str(build_dir) if key == "custom_ui_path" else default)

    from web.api_app import create_app

    app = create_app(testing=True)

    client = TestClient(app)

    # root should serve index.html
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"hello" in resp.content

    # requesting a known asset returns it
    resp = client.get("/foo.js")
    assert resp.status_code == 200
    assert b"console.log" in resp.content

    # API path should still return 404 (content may be standard JSON detail)
    resp = client.get("/api/notfound")
    assert resp.status_code == 404
