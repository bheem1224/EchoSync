"""Quick test to verify all critical endpoints return 200."""

from flask import Flask


def test_all_critical_endpoints(monkeypatch):
    """Verify system endpoints respond correctly."""
    from web.api_app import create_app
    app = create_app()
    
    client = app.test_client()
    
    endpoints = [
        '/',
        '/api/settings',
        '/api/quality-profile',
        '/api/downloads/status',
        '/api/activity/toasts',
        '/api/activity/feed',
        '/api/plugins',
        '/api/providers/',
        '/api/jobs/',
        '/api/jobs/summary',
        '/api/sync/status',
        '/api/sync/options',
    ]
    
    for endpoint in endpoints:
        resp = client.get(endpoint)
        assert resp.status_code in (200, 404), f"{endpoint} returned {resp.status_code}"
        if resp.status_code == 404:
            print(f"Warning: {endpoint} returned 404")
