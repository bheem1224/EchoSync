import os

def test_spa_catchall(tmp_path, monkeypatch):
    """Ensure non-API requests are served from static folder or fallback to index."""
    from web.api_app import create_app

    # create a fake build directory with index and another asset
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / "index.html").write_text("<html><body>hello</body></html>")
    (build_dir / "foo.js").write_text("console.log('hi');")

    app = create_app()
    # monkeypatch the static_folder so our fake directory is used
    app.static_folder = str(build_dir)

    client = app.test_client()

    # root should serve index.html
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"hello" in resp.data

    # requesting a known asset returns it
    resp = client.get("/foo.js")
    assert resp.status_code == 200
    assert b"console.log" in resp.data

    # API path should still return 404 (content may be standard Flask HTML)
    resp = client.get("/api/notfound")
    assert resp.status_code == 404
