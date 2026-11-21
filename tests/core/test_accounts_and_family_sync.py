"""Tests for Spotify settings/accounts preservation, unified external accounts, and family playlist sync."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.nexus_framework.plugin_SDK import sdk
from core.security import Principal
from core.security.tokens import create_access_token
from core.settings import config_manager
from database.config_database import close_config_database, get_config_database
from database.music_database import close_database
from database.working_database import close_working_database
from plugins.EchoSync.spotify.routes import router as spotify_router
from web.api_app import create_app


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    close_config_database()
    close_working_database()
    close_database()

    data_dir = tmp_path / "data"
    config_dir = tmp_path / "config"
    plugins_dir = tmp_path / "plugins"
    for d in (data_dir, config_dir, plugins_dir):
        d.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("ECHOSYNC_DATA_DIR", str(data_dir))
    monkeypatch.setenv("ECHOSYNC_CONFIG_DIR", str(config_dir))
    monkeypatch.setenv("ECHOSYNC_JWT_SECRET", "accounts-family-sync-test-secret-32b")

    overrides = {
        "database.config_uri": f"sqlite:///{(data_dir / 'config.db').as_posix()}",
        "database.working_uri": f"sqlite:///{(data_dir / 'working.db').as_posix()}",
        "database.music_uri": f"sqlite:///{(data_dir / 'music_library.db').as_posix()}",
    }
    orig_get = config_manager.get
    monkeypatch.setattr(config_manager, "get", lambda k, d=None: overrides.get(k, orig_get(k, d)))
    monkeypatch.setattr(config_manager, "get_plugins_dir", lambda: plugins_dir)
    monkeypatch.setattr(config_manager, "plugins_path", plugins_dir)

    db = get_config_database()
    db._ensure_schema_once()
    app = create_app(testing=True)
    client = TestClient(app)
    yield client, db

    close_config_database()
    close_working_database()
    close_database()


def _auth_headers(user: dict) -> dict[str, str]:
    token = create_access_token(
        user_id=user["id"],
        username=user["username"],
        roles=user["roles"],
        auth_provider=user.get("auth_provider", "local"),
        csrf="test-csrf-token",
    )
    return {"Authorization": f"Bearer {token}", "X-CSRF-Token": "test-csrf-token"}


def test_spotify_settings_save_and_legacy_accounts_preserved(isolated_env):
    _, db = isolated_env

    # Seed legacy Spotify accounts under lowercase 'spotify' service alias
    legacy_svc_id = db.get_or_create_service_id("spotify")
    db.ensure_account(service_id=legacy_svc_id, account_name="abhay_sp", display_name="Abhay's Spotify")
    db.ensure_account(service_id=legacy_svc_id, account_name="simi_sp", display_name="Simi's Spotify")

    sp_app = FastAPI()
    sp_app.include_router(spotify_router)
    sp_client = TestClient(sp_app)

    save_resp = sp_client.post(
        "/settings",
        json={
            "client_id": "cid_123",
            "client_secret": "csec_456",
            "redirect_uri": "https://127.0.0.1:5001/api/oauth/callback/plugins/spotify",
        },
    )
    assert save_resp.status_code == 200
    assert save_resp.json()["success"] is True

    get_resp = sp_client.get("/settings")
    assert get_resp.status_code == 200
    assert get_resp.json()["settings"]["client_id"] == "cid_123"
    assert get_resp.json()["settings"]["client_secret"] == "csec_456"

    accts_resp = sp_client.get("/accounts")
    assert accts_resp.status_code == 200
    names = {a["display_name"] for a in accts_resp.json()["accounts"]}
    assert "Abhay's Spotify" in names
    assert "Simi's Spotify" in names


def test_unified_external_accounts_binding_and_retired_map(isolated_env):
    client, db = isolated_env

    admin = db.create_user("abhay", "correct horse battery staple", roles=["admin"])
    member = db.create_user("simi", "another long passphrase here", roles=["member"])

    # Admin binds both Spotify and Plex accounts to abhay and simi
    r1 = client.post(
        f"/api/v1/auth/users/{admin['id']}/external-accounts",
        json={"provider": "spotify", "external_account_id": "abhay_sp", "display_name": "Abhay's Spotify"},
        headers=_auth_headers(admin),
    )
    assert r1.status_code == 201

    r2 = client.post(
        f"/api/v1/auth/users/{admin['id']}/external-accounts",
        json={"provider": "plex", "external_account_id": "plex_abhay", "display_name": "Abhay"},
        headers=_auth_headers(admin),
    )
    assert r2.status_code == 201

    r3 = client.post(
        f"/api/v1/auth/users/{member['id']}/external-accounts",
        json={"provider": "plex", "external_account_id": "plex_simi", "display_name": "Simi"},
        headers=_auth_headers(admin),
    )
    assert r3.status_code == 201

    # Member can bind their own streaming account
    r4 = client.post(
        f"/api/v1/auth/users/{member['id']}/external-accounts",
        json={"provider": "spotify", "external_account_id": "simi_sp", "display_name": "Simi's Spotify"},
        headers=_auth_headers(member),
    )
    assert r4.status_code == 201
    providers = {a["provider"] for a in r4.json()["external_accounts"]}
    assert providers == {"plex", "spotify"}

    # Member cannot bind a media_server account or bind to another user
    r_deny_media = client.post(
        f"/api/v1/auth/users/{member['id']}/external-accounts",
        json={"provider": "plex", "external_account_id": "plex_other"},
        headers=_auth_headers(member),
    )
    assert r_deny_media.status_code == 403

    r_deny_other = client.post(
        f"/api/v1/auth/users/{admin['id']}/external-accounts",
        json={"provider": "spotify", "external_account_id": "hijack"},
        headers=_auth_headers(member),
    )
    assert r_deny_other.status_code == 403

    # Retired Music-to-Media-Server endpoint returns 410 Gone
    retired_resp = client.post(
        "/api/v1/system/accounts/map",
        json={"user_id": 1, "account_ids": [2]},
        headers=_auth_headers(admin),
    )
    assert retired_resp.status_code == 410


def test_family_target_profiles_and_secrets_denied_for_member(isolated_env):
    client, db = isolated_env

    admin = db.create_user("abhay", "correct horse battery staple", roles=["admin"])
    member = db.create_user("simi", "another long passphrase here", roles=["member"])

    db.bind_external_account(admin["id"], "plex", "plex_abhay", "Abhay")
    db.bind_external_account(member["id"], "plex", "plex_simi", "Simi")

    # Seed a token on an account to ensure secrets are never leaked or accessible to members
    svc_id = db.get_or_create_service_id("spotify")
    acc_id = db.ensure_account(service_id=svc_id, account_name="abhay_sp", display_name="Abhay's Spotify")
    db.save_account_token(acc_id, access_token="secret_tok_123", refresh_token="ref_456", expires_at=9999999999)

    resp = client.get("/api/v1/core/playlists/target-profiles?provider=plex", headers=_auth_headers(member))
    assert resp.status_code == 200
    body = resp.json()
    assert body["default_target_user_id"] == "plex_simi"
    assert [p["external_account_id"] for p in body["my_profiles"]] == ["plex_simi"]
    assert [p["external_account_id"] for p in body["family_profiles"]] == ["plex_abhay"]
    # Ensure no token/secret fields are ever present in family profiles response
    serialized = str(body)
    assert "secret_tok_123" not in serialized
    assert "access_token" not in serialized

    # Verify contract:accounts:secrets remains strictly denied for member principal
    member_principal = Principal(
        user_id=member["id"],
        username=member["username"],
        principal_type="user",
        roles=tuple(member["roles"]),
        scopes=frozenset(member["scopes"]),
    )
    assert member_principal.has_scope("service:playlist_sync:share")
    assert member_principal.has_scope("contract:media_profiles:read:family")
    assert not member_principal.has_scope("contract:accounts:secrets")
    with pytest.raises(PermissionError, match="contract:accounts:secrets"):
        sdk.accounts.get_token(acc_id, principal=member_principal)
