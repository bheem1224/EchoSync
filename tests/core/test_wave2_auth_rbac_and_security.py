"""Wave 2 unit tests: NIST SP 800-63B-4 passwords, Argon2id/bcrypt, JWT/JWKS, OIDC PKCE+JIT, RBAC, and plugin sandbox."""

from __future__ import annotations

import base64
import hashlib
import json
import time
import urllib.parse

import httpx
import pytest
from Crypto.Protocol.KDF import bcrypt as pycrypto_bcrypt
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from fastapi.testclient import TestClient

from core.nexus_framework.plugin_SDK import sdk
from core.nexus_framework.plugin_loader import (
    PluginLoader,
    PluginRegistry,
    _is_allowlisted_core_plugin,
    compute_plugin_crc32,
)
from core.security import (
    ADMIN_ROLE_PERMISSIONS,
    MEMBER_ROLE_PERMISSIONS,
    PASSWORD_MIN_LENGTH,
    PASSWORD_RECOMMENDED_LENGTH,
    Principal,
    decrypt_string,
    encrypt_string,
    enforce_contract_scope,
    generate_auth_token,
    hash_password,
    is_privileged_or_verified,
    normalize_password,
    oidc_manager,
    verify_auth_token,
    verify_jwt_hs256,
    verify_jwt_jwks,
    verify_password,
    sign_jwt_hs256,
)
from core.settings import config_manager
from core.task_manager import PluginLifecycleState, plugin_state_manager
from database.config_database import close_config_database, get_config_database
from database.music_database import close_database
from database.working_database import close_working_database
from web.api_app import create_app


def _b64u_int(value: int, length: int | None = None) -> str:
    raw = value.to_bytes(length or max(1, (value.bit_length() + 7) // 8), "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64u_bytes(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


@pytest.fixture
def isolated_auth_env(tmp_path, monkeypatch):
    """Fully isolated temporary config/working/music DBs and FastAPI TestClient."""
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
    monkeypatch.setenv("ECHOSYNC_JWT_SECRET", "wave2-test-jwt-secret-key-material-32bytes")

    config_uri = f"sqlite:///{(data_dir / 'config.db').as_posix()}"
    working_uri = f"sqlite:///{(data_dir / 'working.db').as_posix()}"
    music_uri = f"sqlite:///{(data_dir / 'music_library.db').as_posix()}"

    overrides: dict[str, object] = {
        "database.config_uri": config_uri,
        "database.working_uri": working_uri,
        "database.music_uri": music_uri,
    }
    original_get = config_manager.get

    def mock_get(key, default=None):
        if key in overrides:
            return overrides[key]
        return original_get(key, default)

    monkeypatch.setattr(config_manager, "get", mock_get)
    monkeypatch.setattr(config_manager, "get_plugins_dir", lambda: plugins_dir)
    monkeypatch.setattr(config_manager, "plugins_path", plugins_dir)

    config_db = get_config_database()
    app = create_app()
    client = TestClient(app)

    prev_plugins = dict(PluginRegistry._plugins)
    prev_sources = dict(PluginRegistry._plugin_sources)
    prev_disabled = set(PluginRegistry._disabled_plugins)
    prev_quality = dict(PluginRegistry._quality_options)
    prev_mounted = dict(PluginRegistry._mounted_subapps)

    try:
        yield {
            "tmp_path": tmp_path,
            "data_dir": data_dir,
            "plugins_dir": plugins_dir,
            "config_db": config_db,
            "app": app,
            "client": client,
            "overrides": overrides,
            "monkeypatch": monkeypatch,
        }
    finally:
        PluginRegistry._plugins.clear()
        PluginRegistry._plugins.update(prev_plugins)
        PluginRegistry._plugin_sources.clear()
        PluginRegistry._plugin_sources.update(prev_sources)
        PluginRegistry._disabled_plugins.clear()
        PluginRegistry._disabled_plugins.update(prev_disabled)
        PluginRegistry._quality_options.clear()
        PluginRegistry._quality_options.update(prev_quality)
        PluginRegistry._mounted_subapps.clear()
        PluginRegistry._mounted_subapps.update(prev_mounted)
        close_config_database()
        close_working_database()
        close_database()


def test_nist_password_policy_argon2id_unicode_long_passphrase_and_bcrypt_fallback():
    assert PASSWORD_MIN_LENGTH == 8
    assert PASSWORD_RECOMMENDED_LENGTH == 15

    # Short passwords rejected
    with pytest.raises(ValueError, match="at least 8"):
        hash_password("short7")

    # Zero composition rules: pure lowercase passphrase with spaces succeeds
    passphrase = "correct horse battery staple"
    encoded = hash_password(passphrase)
    assert encoded.startswith("$argon2id$")
    assert verify_password(passphrase, encoded) is True
    assert verify_password("wrong passphrase", encoded) is False

    # NFKC normalization matches visually equivalent full-width Unicode input
    nfkc_raw = "\uff21\uff22\uff23defgh123"
    assert normalize_password(nfkc_raw) == "ABCdefgh123"
    unicode_hash = hash_password(nfkc_raw)
    assert verify_password("ABCdefgh123", unicode_hash) is True

    # 64+ character passphrases preserve full entropy beyond bcrypt's 72-byte cutoff
    long_a = "x" * 75 + "alpha"
    long_b = "x" * 75 + "bravo"
    hash_a = hash_password(long_a)
    assert verify_password(long_a, hash_a) is True
    assert verify_password(long_b, hash_a) is False

    # Legacy bcrypt fallback verification
    legacy_hash = pycrypto_bcrypt("legacy-secret-pw", 6).decode("utf-8")
    assert verify_password("legacy-secret-pw", legacy_hash) is True
    assert verify_password("wrong-legacy-pw", legacy_hash) is False

    # Preserved legacy security exports
    token = generate_auth_token("alice", "csrf-123")
    claims = verify_auth_token(token)
    assert claims is not None and claims["user"] == "alice" and claims["csrf"] == "csrf-123"
    cipher_val = encrypt_string("sensitive-token")
    assert cipher_val and cipher_val.startswith("enc:")
    assert decrypt_string(cipher_val) == "sensitive-token"


def test_jwt_hs256_and_jwks_rs256_es256_verification():
    # HS256 roundtrip + expiry + tamper
    secret = b"unit-test-hs256-secret-32-bytes-minimum"
    valid_jwt = sign_jwt_hs256({"sub": "u1", "exp": int(time.time()) + 120}, secret=secret)
    decoded = verify_jwt_hs256(valid_jwt, secret=secret)
    assert decoded is not None and decoded["sub"] == "u1"
    assert verify_jwt_hs256(valid_jwt + "x", secret=secret) is None

    expired_jwt = sign_jwt_hs256({"sub": "u1", "exp": int(time.time()) - 120}, secret=secret)
    assert verify_jwt_hs256(expired_jwt, secret=secret) is None

    # RS256 JWKS verification + alg-confusion rejection
    rsa_priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    rsa_nums = rsa_priv.public_key().public_numbers()
    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "kid": "rsa-key-1",
                "alg": "RS256",
                "n": _b64u_int(rsa_nums.n),
                "e": _b64u_int(rsa_nums.e),
            }
        ]
    }
    now = int(time.time())
    hdr = _b64u_bytes(json.dumps({"alg": "RS256", "kid": "rsa-key-1", "typ": "JWT"}).encode())
    pld = _b64u_bytes(
        json.dumps({"sub": "oidc-1", "iss": "https://idp.test", "aud": "echo-client", "exp": now + 300}).encode()
    )
    sig = rsa_priv.sign(f"{hdr}.{pld}".encode("ascii"), padding.PKCS1v15(), hashes.SHA256())
    rs_token = f"{hdr}.{pld}.{_b64u_bytes(sig)}"

    claims = verify_jwt_jwks(rs_token, jwks, audience="echo-client", issuer="https://idp.test")
    assert claims["sub"] == "oidc-1"

    with pytest.raises(ValueError, match="Disallowed"):
        confused = sign_jwt_hs256({"sub": "oidc-1", "exp": now + 300}, secret=b"evil")
        verify_jwt_jwks(confused, jwks, audience="echo-client", issuer="https://idp.test")

    # ES256 P-256 JWKS verification
    ec_priv = ec.generate_private_key(ec.SECP256R1())
    ec_nums = ec_priv.public_key().public_numbers()
    ec_jwks = [
        {
            "kty": "EC",
            "crv": "P-256",
            "kid": "ec-1",
            "x": _b64u_int(ec_nums.x, 32),
            "y": _b64u_int(ec_nums.y, 32),
        }
    ]
    ec_hdr = _b64u_bytes(json.dumps({"alg": "ES256", "kid": "ec-1"}).encode())
    der_sig = ec_priv.sign(f"{ec_hdr}.{pld}".encode("ascii"), ec.ECDSA(hashes.SHA256()))
    r_val, s_val = decode_dss_signature(der_sig)
    raw_sig = r_val.to_bytes(32, "big") + s_val.to_bytes(32, "big")
    es_token = f"{ec_hdr}.{pld}.{_b64u_bytes(raw_sig)}"
    ec_claims = verify_jwt_jwks(es_token, ec_jwks, audience="echo-client", issuer="https://idp.test")
    assert ec_claims["sub"] == "oidc-1"


def test_first_boot_setup_login_rbac_api_keys_and_managed_accounts(isolated_auth_env):
    client = isolated_auth_env["client"]
    config_db = isolated_auth_env["config_db"]

    # Seeded roles exist cleanly
    roles_by_name = {r["name"]: r for r in config_db.list_roles()}
    assert roles_by_name["admin"]["permissions"] == list(ADMIN_ROLE_PERMISSIONS)
    assert set(roles_by_name["member"]["permissions"]) == set(MEMBER_ROLE_PERMISSIONS)

    # 1. Pre-setup status
    st0 = client.get("/api/v1/auth/status")
    assert st0.status_code == 200
    assert st0.json()["setup_required"] is True
    assert st0.json()["authenticated"] is False

    # 2. First-boot setup creates initial admin + cookies, repeats return 409
    setup_resp = client.post(
        "/api/v1/auth/setup",
        json={"username": "admin_one", "password": "correct horse battery staple"},
    )
    assert setup_resp.status_code == 201
    admin_user = setup_resp.json()["user"]
    assert "admin" in admin_user["roles"]
    assert "echo_auth" in setup_resp.cookies

    repeat_setup = client.post(
        "/api/v1/auth/setup",
        json={"username": "admin_two", "password": "another passphrase 123"},
    )
    assert repeat_setup.status_code == 409

    # 3. Unauthenticated request blocked once users exist
    anon_client = TestClient(isolated_auth_env["app"])
    assert anon_client.get("/api/v1/auth/me").status_code == 401
    assert anon_client.get("/api/v1/auth/users").status_code == 401

    # 4. Logout + legacy alias login
    assert client.post("/api/v1/auth/logout").status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401

    login_resp = client.post(
        "/api/v1/system/auth/login",
        json={"username": "admin_one", "password": "correct horse battery staple"},
    )
    assert login_resp.status_code == 200
    assert client.get("/api/v1/system/auth/me").status_code == 200

    # 5. Admin provisions member user + assigns managed account
    create_member = client.post(
        "/api/v1/auth/users",
        json={"username": "member_one", "password": "long member passphrase", "roles": ["member"]},
    )
    assert create_member.status_code == 201
    member_id = create_member.json()["user"]["id"]

    assert (
        client.post(
            f"/api/v1/auth/users/{member_id}/managed-accounts",
            json={"server_plugin_id": 12345, "managed_account_id": "plex-home-1"},
        ).status_code
        == 201
    )

    # 6. Member session enforces two-tier RBAC (:own vs :any + admin routes) and API key ceiling
    member_client = TestClient(isolated_auth_env["app"])
    m_login = member_client.post(
        "/api/v1/auth/login",
        json={"username": "member_one", "password": "long member passphrase"},
    )
    assert m_login.status_code == 200

    assert member_client.post("/api/v1/auth/users", json={"username": "x", "password": "pw"}).status_code == 403
    assert member_client.get(f"/api/v1/auth/users/{admin_user['id']}/managed-accounts").status_code == 403
    own_ma = member_client.get(f"/api/v1/auth/users/{member_id}/managed-accounts")
    assert own_ma.status_code == 200
    assert own_ma.json()["managed_accounts"][0]["managed_account_id"] == "plex-home-1"

    # API key scope escalation rejected (403); allowed scope succeeds (201)
    assert (
        member_client.post(
            "/api/v1/auth/api-keys",
            json={"name": "esc-key", "scopes": ["service:accounts:edit"]},
        ).status_code
        == 403
    )
    key_resp = member_client.post(
        "/api/v1/auth/api-keys",
        json={"name": "reader-key", "scopes": ["contract:accounts:read:own"]},
    )
    assert key_resp.status_code == 201
    raw_key = key_resp.json()["api_key"]
    key_id = key_resp.json()["id"]

    api_client = TestClient(isolated_auth_env["app"])
    assert (
        api_client.get(
            f"/api/v1/auth/users/{member_id}/managed-accounts",
            headers={"X-API-Key": raw_key},
        ).status_code
        == 200
    )
    assert (
        api_client.get(
            f"/api/v1/auth/users/{member_id}/managed-accounts",
            headers={"Authorization": f"Bearer {raw_key}"},
        ).status_code
        == 200
    )
    assert member_client.delete(f"/api/v1/auth/api-keys/{key_id}").status_code == 200
    assert (
        api_client.get(
            f"/api/v1/auth/users/{member_id}/managed-accounts",
            headers={"X-API-Key": raw_key},
        ).status_code
        == 401
    )


def test_oidc_pkce_jwks_and_jit_group_role_mapping(isolated_auth_env):
    client = isolated_auth_env["client"]
    overrides = isolated_auth_env["overrides"]
    monkeypatch = isolated_auth_env["monkeypatch"]

    rsa_priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    rsa_nums = rsa_priv.public_key().public_numbers()
    jwks_doc = {
        "keys": [
            {
                "kty": "RSA",
                "kid": "idp-key-1",
                "alg": "RS256",
                "n": _b64u_int(rsa_nums.n),
                "e": _b64u_int(rsa_nums.e),
            }
        ]
    }
    issuer = "https://sso.echosync.test"
    discovery_doc = {
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/authorize",
        "token_endpoint": f"{issuer}/token",
        "jwks_uri": f"{issuer}/jwks.json",
    }

    overrides.update(
        {
            "security.oidc.enabled": True,
            "security.oidc.issuer_url": issuer,
            "security.oidc.client_id": "echosync-web",
            "security.oidc.redirect_uri": "http://testserver/api/v1/auth/oidc/callback",
            "security.oidc.group_role_map": {"music-admins": "admin"},
        }
    )

    monkeypatch.setattr(oidc_manager, "fetch_discovery", lambda *_a, **_kw: discovery_doc)
    monkeypatch.setattr(oidc_manager, "fetch_jwks", lambda *_a, **_kw: jwks_doc)

    login_init = client.get("/api/v1/auth/oidc/login?mode=json")
    assert login_init.status_code == 200
    auth_url = login_init.json()["authorization_url"]
    parsed_qs = urllib.parse.parse_qs(urllib.parse.urlparse(auth_url).query)
    state = parsed_qs["state"][0]
    challenge = parsed_qs["code_challenge"][0]
    assert parsed_qs["code_challenge_method"] == ["S256"]

    # Retrieve ephemeral nonce & verify PKCE verifier matches challenge
    state_entry = oidc_manager._pending_states[state]
    expected_challenge = _b64u_bytes(hashlib.sha256(state_entry["code_verifier"].encode("ascii")).digest())
    assert challenge == expected_challenge

    now = int(time.time())
    hdr = _b64u_bytes(json.dumps({"alg": "RS256", "kid": "idp-key-1", "typ": "JWT"}).encode())
    pld = _b64u_bytes(
        json.dumps(
            {
                "sub": "oidc-sub-999",
                "preferred_username": "sso_admin",
                "nonce": state_entry["nonce"],
                "groups": ["music-admins"],
                "iss": issuer,
                "aud": "echosync-web",
                "exp": now + 300,
            }
        ).encode()
    )
    sig = rsa_priv.sign(f"{hdr}.{pld}".encode("ascii"), padding.PKCS1v15(), hashes.SHA256())
    id_token = f"{hdr}.{pld}.{_b64u_bytes(sig)}"

    def fake_httpx_post(url, data=None, timeout=15.0):
        assert url == discovery_doc["token_endpoint"]
        assert data["code_verifier"] == state_entry["code_verifier"]
        return httpx.Response(200, json={"id_token": id_token}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_httpx_post)

    cb_resp = client.get(f"/api/v1/auth/oidc/callback?code=authcode-1&state={state}")
    assert cb_resp.status_code == 200
    cb_user = cb_resp.json()["user"]
    assert cb_user["username"] == "sso_admin"
    assert cb_user["oidc_subject"] == "oidc-sub-999"
    assert cb_user["roles"] == ["admin"]
    assert "echo_auth" in cb_resp.cookies


def test_principal_secrets_isolation_forged_official_bypass_and_consent_freeze(isolated_auth_env):
    config_db = isolated_auth_env["config_db"]
    plugins_dir = isolated_auth_env["plugins_dir"]
    tmp_path = isolated_auth_env["tmp_path"]

    # 1. Principal.require enforces scope string
    reader = Principal(user_id="u1", username="bob", principal_type="user", roles=("member",), scopes=frozenset({"contract:tracks:read"}))
    with pytest.raises(PermissionError, match="Missing required capability scope: service:accounts:edit"):
        reader.require("service:accounts:edit")

    # 2. Plugins are explicitly denied contract:accounts:secrets even with "*"
    wildcard_plugin = Principal(
        user_id=None,
        username="plugin:evil",
        principal_type="plugin",
        roles=(),
        scopes=frozenset({"*"}),
        plugin_id=999,
    )
    with pytest.raises(PermissionError, match="contract:accounts:secrets"):
        enforce_contract_scope(wildcard_plugin, "contract:accounts:secrets")
    with pytest.raises(PermissionError, match="contract:accounts:secrets"):
        sdk.accounts.get_token(1, principal=wildcard_plugin)

    # 3. Manifest cannot self-assert verified_source == "official" and unlisted plugins fail core allowlist
    forged_manifest = {"id": "Evil.rogue", "verified_source": "official", "privileged_mode": True}
    assert is_privileged_or_verified(forged_manifest) is False
    assert is_privileged_or_verified({"id": "EchoSync.core"}, trusted_core_path=True) is True
    assert _is_allowlisted_core_plugin(tmp_path / "plugins" / "EchoSync" / "rogue_unlisted", {"id": "EchoSync.rogue_unlisted", "author": "EchoSync", "verified_source": "official"}) is False

    # 4. PluginLoader does not let forged official plugin bypass PluginSecurityScanner
    evil_dir = plugins_dir / "Evil" / "rogue"
    evil_dir.mkdir(parents=True, exist_ok=True)
    (evil_dir / "manifest.json").write_text(
        json.dumps(
            {
                "id": "Evil.rogue",
                "name": "rogue",
                "author": "Evil",
                "version": "1.0.0",
                "type": "metadata",
                "verified_source": "official",
                "privileged": True,
            }
        ),
        encoding="utf-8",
    )
    (evil_dir / "__init__.py").write_text(
        "import subprocess\nclass RoguePlugin:\n    pass\n",
        encoding="utf-8",
    )
    evil_pid = compute_plugin_crc32("evil.rogue")
    loader = PluginLoader(tmp_path)
    loader.reconcile_services()
    loader.load_all()
    assert PluginRegistry.get_plugin(evil_pid) is None

    # 5. Escalating scopes during plugin reload freezes plugin in AWAITING_CONSENT
    esc_dir = plugins_dir / "ThirdParty" / "sample"
    esc_dir.mkdir(parents=True, exist_ok=True)
    (esc_dir / "manifest.json").write_text(
        json.dumps(
            {
                "id": "ThirdParty.sample",
                "name": "sample",
                "author": "ThirdParty",
                "version": "1.1.0",
                "type": "metadata",
                "permissions": {"database": {"mutate_aliases": True}},
            }
        ),
        encoding="utf-8",
    )
    (esc_dir / "__init__.py").write_text("# clean plugin\n", encoding="utf-8")
    esc_pid = compute_plugin_crc32("thirdparty.sample")
    config_db.register_service(
        name="ThirdParty.sample",
        service_type="metadata",
        description="Sample",
        absolute_install_path=str(esc_dir.resolve()),
        plugin_id=esc_pid,
        version="1.0.0",
    )

    result = loader.reload_plugin(esc_pid)
    assert result is False
    status = plugin_state_manager.get_state("ThirdParty.sample")
    assert status.state == PluginLifecycleState.AWAITING_CONSENT
