"""
OAuth Sidecar Capability & Zero-Trust Integration Test Suite.

Verifies:
1. Strict unsigned 32-bit integer plugin_id validation across OAuth models and sidecar.
2. High-entropy cryptographic state and PKCE S256 challenge generation.
3. Upstream token exchange execution inside the sidecar process on port 5001.
4. Direct caller return: in-memory resolution via OAuthSessionHandle.
5. Supervised callback dispatch with bound_to_general_pool=False.
6. Zero-Trust EventBus Invariant: tokens are NEVER emitted over EventBus.
7. Error callback dispatch and exception propagation.
"""

from __future__ import annotations

import base64
import hashlib
from unittest.mock import MagicMock, patch

import pytest

from core.event_bus import event_bus
from core.oauth.models import (
    OAuthSession,
    OAuthSessionHandle,
    validate_plugin_id_int,
)
from core.oauth.sidecar import (
    _OAUTH_SESSIONS,
    _SESSIONS_LOCK,
    app,
    register_oauth_session,
)
from core.task_manager.models import OwnerType, ProcessCategory
from core.task_manager.supervisor import supervisor

# ==============================================================================
# 1. Strict Unsigned 32-Bit Integer Plugin ID Validation
# ==============================================================================


def test_validate_plugin_id_int_accepts_valid_integers():
    """Verify that unsigned 32-bit integers are accepted."""
    assert validate_plugin_id_int(0) == 0
    assert validate_plugin_id_int(12345) == 12345
    assert validate_plugin_id_int(0xFFFFFFFF) == 4294967295


def test_validate_plugin_id_int_rejects_strings():
    """Verify that string plugin IDs raise TypeError."""
    with pytest.raises(TypeError) as exc_info:
        validate_plugin_id_int("tidal")
    assert "Plugin ID must be an integer" in str(exc_info.value)


def test_validate_plugin_id_int_rejects_booleans():
    """Verify that boolean values raise TypeError despite bool subclassing int."""
    with pytest.raises(TypeError) as exc_info:
        validate_plugin_id_int(True)
    assert "Plugin ID must be an integer" in str(exc_info.value)


def test_validate_plugin_id_int_rejects_out_of_range():
    """Verify that negative or > 32-bit integers raise ValueError."""
    with pytest.raises(ValueError) as exc_neg:
        validate_plugin_id_int(-1)
    assert "unsigned 32-bit integer" in str(exc_neg.value)

    with pytest.raises(ValueError) as exc_high:
        validate_plugin_id_int(0x100000000)
    assert "unsigned 32-bit integer" in str(exc_high.value)


def test_oauth_session_model_enforces_plugin_id():
    """Verify OAuthSession dataclass enforces unsigned 32-bit integer plugin_id."""
    with pytest.raises(TypeError):
        OAuthSession(
            session_id="test_sess",
            plugin_id="tidal",  # Invalid type
            provider="tidal",
            auth_url="https://auth.example.com",
            token_url="https://token.example.com",
            client_id="cid_123",
            redirect_uri="https://localhost:5001/cb",
        )

    with pytest.raises(ValueError):
        OAuthSession(
            session_id="test_sess",
            plugin_id=-5,  # Invalid range
            provider="tidal",
            auth_url="https://auth.example.com",
            token_url="https://token.example.com",
            client_id="cid_123",
            redirect_uri="https://localhost:5001/cb",
        )


# ==============================================================================
# 2. PKCE Challenge & High-Entropy State Generation
# ==============================================================================


def test_register_oauth_session_pkce_and_state_entropy():
    """Verify register_oauth_session creates S256 PKCE challenges and high-entropy state."""
    test_plugin_id = 3106502486  # CRC32 for Tidal

    handle = register_oauth_session(
        plugin_id=test_plugin_id,
        provider="tidal",
        auth_url="https://login.tidal.com/authorize",
        token_url="https://auth.tidal.com/v1/oauth2/token",
        client_id="test_client_id",
        scopes="user.read playlists.read",
        use_pkce=True,
    )

    assert isinstance(handle, OAuthSessionHandle)
    assert handle.session_id
    assert len(handle.session_id) >= 32  # High entropy state token

    # Check that session is stored in memory
    with _SESSIONS_LOCK:
        session = _OAUTH_SESSIONS.get(handle.session_id)
        assert session is not None
        assert session.plugin_id == test_plugin_id
        assert session.code_verifier is not None
        assert session.code_challenge is not None

        # Verify S256 challenge formula: BASE64URL-ENCODE(SHA256(verifier))
        expected_challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(session.code_verifier.encode("utf-8")).digest())
            .decode("utf-8")
            .rstrip("=")
        )
        assert session.code_challenge == expected_challenge

    # Verify authorization URL includes state, code_challenge, and S256
    assert f"state={handle.session_id}" in handle.auth_url
    assert f"code_challenge={session.code_challenge}" in handle.auth_url
    assert "code_challenge_method=S256" in handle.auth_url


# ==============================================================================
# 3. Direct Caller Return & Supervised Worker Dispatch
# ==============================================================================


def test_centralized_token_broker_direct_caller_return_and_supervision():
    """
    Verify:
    1. Upstream token exchange occurs inside sidecar.
    2. Tokens are returned directly in-memory to on_token callback.
    3. on_token is dispatched via supervisor.spawn_supervised_thread with bound_to_general_pool=False.
    4. ZERO tokens emitted over EventBus.
    """
    test_plugin_id = 3106502486
    received_tokens = []

    def _token_cb(tokens):
        received_tokens.append(tokens)

    # Spy on EventBus to assert zero credential leakage
    event_bus_events = []
    event_bus.subscribe(lambda evt: event_bus_events.append(evt))

    handle = register_oauth_session(
        plugin_id=test_plugin_id,
        provider="tidal",
        auth_url="https://login.tidal.com/authorize",
        token_url="https://auth.tidal.com/v1/oauth2/token",
        client_id="test_client_id",
        client_secret="test_secret",
        use_pkce=True,
        on_token=_token_cb,
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "access_token": "secret_access_token_xyz",
        "refresh_token": "secret_refresh_token_abc",
        "expires_in": 3600,
        "token_type": "Bearer",
    }

    spawn_calls = []

    def _mock_spawn(*args, **kwargs):
        spawn_calls.append(kwargs)
        # Execute target synchronously for test verification
        target = kwargs.get("target")
        t_args = kwargs.get("args", ())
        if target:
            target(*t_args)
        return MagicMock(), "reg_123"

    with patch("requests.post", return_value=mock_resp) as mock_post, patch.object(
        supervisor,
        "spawn_supervised_thread",
        sideeffect=_mock_spawn if hasattr(supervisor, "spawn_supervised_thread") else None,
    ) as mock_spawn_patch:
        # If sideeffect is used
        mock_spawn_patch.side_effect = _mock_spawn

        with app.test_client() as client:
            cb_url = f"/api/oauth/callback/plugins/tidal?code=auth_code_123&state={handle.session_id}"
            resp = client.get(cb_url)

            assert resp.status_code == 200
            assert b"Authentication Successful" in resp.data

    # 1. Upstream POST was made with correct credentials and code_verifier
    assert mock_post.called
    post_args, post_kwargs = mock_post.call_args
    assert post_args[0] == "https://auth.tidal.com/v1/oauth2/token"
    assert post_kwargs["data"]["code"] == "auth_code_123"
    assert post_kwargs["data"]["client_id"] == "test_client_id"
    assert "code_verifier" in post_kwargs["data"]

    # 2. In-memory future resolved
    resolved = handle.wait_for_tokens(timeout=2.0)
    assert resolved["access_token"] == "secret_access_token_xyz"
    assert resolved["refresh_token"] == "secret_refresh_token_abc"

    # 3. Supervised worker dispatch verified
    assert len(spawn_calls) == 1
    call_kwargs = spawn_calls[0]
    assert call_kwargs["owner_id"] == str(test_plugin_id)
    assert call_kwargs["owner_type"] == OwnerType.PLUGIN
    assert call_kwargs["category"] == ProcessCategory.CORE_SYSTEM
    assert call_kwargs["bound_to_general_pool"] is False

    # 4. In-memory callback executed
    assert len(received_tokens) == 1
    assert received_tokens[0]["access_token"] == "secret_access_token_xyz"

    # 5. ZERO-TRUST INVARIANT: Tokens NEVER emitted over EventBus
    for evt in event_bus_events:
        evt_str = str(evt)
        assert "secret_access_token_xyz" not in evt_str
        assert "secret_refresh_token_abc" not in evt_str


# ==============================================================================
# 4. Error Callback & Cancellation Handling
# ==============================================================================


def test_centralized_token_broker_error_handling():
    """Verify provider OAuth error query params trigger on_error and reject future."""
    test_plugin_id = 2391116200  # Spotify
    received_errors = []

    def _err_cb(err_msg):
        received_errors.append(err_msg)

    handle = register_oauth_session(
        plugin_id=test_plugin_id,
        provider="spotify",
        auth_url="https://accounts.spotify.com/authorize",
        token_url="https://accounts.spotify.com/api/token",
        client_id="spotify_client_id",
        use_pkce=False,
        on_error=_err_cb,
    )

    spawn_calls = []

    def _mock_spawn(*args, **kwargs):
        spawn_calls.append(kwargs)
        target = kwargs.get("target")
        t_args = kwargs.get("args", ())
        if target:
            target(*t_args)
        return MagicMock(), "reg_err"

    with patch.object(supervisor, "spawn_supervised_thread", side_effect=_mock_spawn):
        with app.test_client() as client:
            cb_url = f"/api/oauth/callback/plugins/spotify?error=access_denied&error_description=User+denied+access&state={handle.session_id}"
            resp = client.get(cb_url)

            assert resp.status_code == 400
            assert b"Authentication Failed" in resp.data
            assert b"User denied access" in resp.data

    # Verify on_error supervised dispatch
    assert len(spawn_calls) == 1
    assert spawn_calls[0]["bound_to_general_pool"] is False
    assert spawn_calls[0]["owner_id"] == str(test_plugin_id)

    # Verify in-memory callback received error description
    assert len(received_errors) == 1
    assert "User denied access" in received_errors[0]

    # Verify future raised exception
    with pytest.raises(RuntimeError) as exc_info:
        handle.wait_for_tokens(timeout=1.0)
    assert "User denied access" in str(exc_info.value)
