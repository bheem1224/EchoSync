"""Centralized HTTPS OAuth Sidecar & Token Broker for EchoSync.

Terminates TLS on port 5001, manages PKCE challenges, validates cryptographic
state tokens, performs upstream token exchanges, and returns credentials
directly in-memory to calling plugins via supervised worker threads.
"""

from __future__ import annotations

import base64
import hashlib
import html
import json
import secrets
import threading
import urllib.parse
from collections.abc import Callable
from typing import Any

import requests
from flask import Flask, Response, render_template_string, request
from werkzeug.serving import make_server

from core.network_utils import get_lan_ip, get_main_app_port
from core.oauth.cert_manager import ensure_ssl_certs
from core.oauth.models import (
    OAuthSession,
    OAuthSessionHandle,
    validate_plugin_id_int,
)
from core.task_manager.models import OwnerType, ProcessCategory
from core.task_manager.supervisor import supervisor
from core.tiered_logger import get_logger

logger = get_logger("oauth_sidecar")

app = Flask("oauth_sidecar")

_SESSIONS_LOCK = threading.Lock()
_OAUTH_SESSIONS: dict[str, OAuthSession] = {}


_SUCCESS_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Authentication Successful - EchoSync</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .card { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 40px; text-align: center; max-width: 480px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
        .icon { font-size: 48px; margin-bottom: 16px; color: #10b981; }
        h1 { margin: 0 0 12px; font-size: 24px; font-weight: 600; }
        p { color: #94a3b8; font-size: 15px; line-height: 1.5; margin: 0 0 24px; }
        .btn { display: inline-block; background: #10b981; color: white; border: none; padding: 10px 20px; border-radius: 8px; font-weight: 500; cursor: pointer; text-decoration: none; font-size: 14px; }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">&#10003;</div>
        <h1>Authentication Successful</h1>
        <p>Your account has been connected securely. This window can now be closed.</p>
        <button class="btn" onclick="window.close()">Close Window</button>
    </div>
    <script>
        if (window.opener) {
            setTimeout(function() { window.close(); }, 1200);
        } else {
            setTimeout(function() { window.location.href = '/settings/music-services'; }, 2000);
        }
    </script>
</body>
</html>"""

_ERROR_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Authentication Failed - EchoSync</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .card { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 16px; padding: 40px; text-align: center; max-width: 480px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
        .icon { font-size: 48px; margin-bottom: 16px; color: #ef4444; }
        h1 { margin: 0 0 12px; font-size: 24px; font-weight: 600; }
        p { color: #94a3b8; font-size: 15px; line-height: 1.5; margin: 0 0 24px; }
        .error-desc { background: rgba(239, 68, 68, 0.1); color: #fca5a5; padding: 10px 14px; border-radius: 8px; font-family: monospace; font-size: 13px; margin-bottom: 20px; }
        .btn { display: inline-block; background: rgba(255,255,255,0.1); color: white; border: none; padding: 10px 20px; border-radius: 8px; font-weight: 500; cursor: pointer; text-decoration: none; font-size: 14px; }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">&#10005;</div>
        <h1>Authentication Failed</h1>
        <p>An error occurred while connecting your account.</p>
        <div class="error-desc">{{ error_desc }}</div>
        <button class="btn" onclick="window.close()">Close Window</button>
    </div>
</body>
</html>"""


def register_oauth_session(
    plugin_id: int,
    provider: str,
    auth_url: str,
    token_url: str,
    client_id: str,
    client_secret: str | None = None,
    scopes: str | list[str] | None = None,
    use_pkce: bool = True,
    account_id: int | None = None,
    on_token: Callable[[dict[str, Any]], None] | None = None,
    on_error: Callable[[str], None] | None = None,
    extra_auth_params: dict[str, Any] | None = None,
    ttl_seconds: int = 600,
) -> OAuthSessionHandle:
    """
    Register an active OAuth session with the centralized token broker.
    Enforces strict unsigned 32-bit integer plugin_id validation.
    """
    plugin_id = validate_plugin_id_int(plugin_id)
    session_id = secrets.token_urlsafe(32)

    lan_ip = get_lan_ip()
    redirect_uri = f"https://{lan_ip}:5001/api/oauth/callback/plugins/{provider}"

    code_verifier = None
    code_challenge = None
    if use_pkce:
        code_verifier = secrets.token_urlsafe(64)[:128]
        code_challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("utf-8")).digest()).decode("utf-8").rstrip("=")
        )

    params: dict[str, Any] = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": session_id,
    }
    if scopes:
        if isinstance(scopes, (list, tuple, set)):
            params["scope"] = " ".join(scopes)
        else:
            params["scope"] = str(scopes)

    if use_pkce and code_challenge:
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = "S256"

    if extra_auth_params:
        params.update(extra_auth_params)

    delim = "&" if "?" in auth_url else "?"
    full_auth_url = f"{auth_url}{delim}{urllib.parse.urlencode(params)}"

    session = OAuthSession(
        session_id=session_id,
        plugin_id=plugin_id,
        provider=provider,
        auth_url=full_auth_url,
        token_url=token_url,
        client_id=client_id,
        redirect_uri=redirect_uri,
        account_id=account_id,
        client_secret=client_secret,
        code_verifier=code_verifier,
        code_challenge=code_challenge,
        scopes=scopes,
        on_token=on_token,
        on_error=on_error,
        ttl_seconds=ttl_seconds,
    )

    with _SESSIONS_LOCK:
        # Prune expired sessions
        expired_keys = [k for k, v in _OAUTH_SESSIONS.items() if v.is_expired]
        for k in expired_keys:
            _OAUTH_SESSIONS.pop(k, None)
        _OAUTH_SESSIONS[session_id] = session

    logger.info(f"Registered centralized OAuth session {session_id[:8]}... for plugin {plugin_id} ({provider})")
    return OAuthSessionHandle(
        session_id=session_id,
        auth_url=full_auth_url,
        future=session.future,
    )


@app.route("/api/oauth/callback/<provider_name>")
@app.route("/api/oauth/callback/plugins/<provider_name>")
def oauth_callback(provider_name: str):
    """
    Universal callback route for OAuth.
    If matching active session is found in memory, acts as Centralized Token Broker:
    performs upstream token exchange and resolves caller's private session in-memory.
    Otherwise, falls back to legacy 302 redirector for unmigrated providers.
    """
    code = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")
    error_desc = request.args.get("error_description") or error or "OAuth authorization failed"

    # 1. Match session by state token
    matched_session: OAuthSession | None = None
    session_key: str | None = None

    if state:
        with _SESSIONS_LOCK:
            if state in _OAUTH_SESSIONS:
                session_key = state
                matched_session = _OAUTH_SESSIONS.pop(state, None)
            else:
                # Try parsing base64-encoded JSON state (e.g. legacy PKCE payload format)
                try:
                    padded = state + "=" * (-len(state) % 4)
                    data = json.loads(base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8"))
                    candidate = data.get("session_id") or data.get("pkce_id")
                    if candidate and candidate in _OAUTH_SESSIONS:
                        session_key = candidate
                        matched_session = _OAUTH_SESSIONS.pop(candidate, None)
                except Exception:
                    pass

    # 2. If active broker session found: handle directly
    if matched_session and session_key:
        if error:
            logger.error(
                f"OAuth provider returned error for session {session_key[:8]}... (plugin {matched_session.plugin_id}): {error_desc}"
            )
            if matched_session.on_error:
                supervisor.spawn_supervised_thread(
                    target=matched_session.on_error,
                    name=f"oauth_error_{session_key[:8]}",
                    owner_id=str(matched_session.plugin_id),
                    owner_type=OwnerType.PLUGIN,
                    category=ProcessCategory.CORE_SYSTEM,
                    bound_to_general_pool=False,
                    args=(error_desc,),
                )
            if not matched_session.future.done():
                matched_session.future.set_exception(RuntimeError(error_desc))
            return render_template_string(_ERROR_HTML, error_desc=html.escape(error_desc)), 400

        if not code:
            err = "Missing authorization code from OAuth provider"
            logger.error(f"OAuth callback missing code for session {session_key[:8]}")
            if not matched_session.future.done():
                matched_session.future.set_exception(ValueError(err))
            return render_template_string(_ERROR_HTML, error_desc=err), 400

        # Perform upstream token exchange inside sidecar
        token_payload: dict[str, Any] = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": matched_session.redirect_uri,
            "client_id": matched_session.client_id,
        }
        if matched_session.code_verifier:
            token_payload["code_verifier"] = matched_session.code_verifier
        if matched_session.client_secret:
            token_payload["client_secret"] = matched_session.client_secret

        headers = {"Accept": "application/json"}
        auth = None
        if matched_session.client_secret and matched_session.provider.lower() in ("spotify",):
            auth = (matched_session.client_id, matched_session.client_secret)

        try:
            logger.info(
                f"OAuth sidecar exchanging code for tokens with {matched_session.token_url} (plugin {matched_session.plugin_id})"
            )
            resp = requests.post(
                matched_session.token_url,
                data=token_payload,
                headers=headers,
                auth=auth,
                timeout=20,
            )
            if resp.status_code != 200:
                msg = f"Token exchange failed ({resp.status_code}): {resp.text}"
                logger.error(msg)
                if matched_session.on_error:
                    supervisor.spawn_supervised_thread(
                        target=matched_session.on_error,
                        name=f"oauth_error_{session_key[:8]}",
                        owner_id=str(matched_session.plugin_id),
                        owner_type=OwnerType.PLUGIN,
                        category=ProcessCategory.CORE_SYSTEM,
                        bound_to_general_pool=False,
                        args=(msg,),
                    )
                if not matched_session.future.done():
                    matched_session.future.set_exception(RuntimeError(msg))
                return render_template_string(_ERROR_HTML, error_desc=html.escape(msg)), 400

            tokens = resp.json()
            logger.info(
                f"OAuth sidecar successfully received tokens for plugin {matched_session.plugin_id} (session {session_key[:8]})"
            )

            # Direct caller return on supervised burst thread:
            # strictly bound_to_general_pool=False, never emitted over EventBus
            if matched_session.on_token:
                supervisor.spawn_supervised_thread(
                    target=matched_session.on_token,
                    name=f"oauth_token_{session_key[:8]}",
                    owner_id=str(matched_session.plugin_id),
                    owner_type=OwnerType.PLUGIN,
                    category=ProcessCategory.CORE_SYSTEM,
                    bound_to_general_pool=False,
                    args=(tokens,),
                )

            if not matched_session.future.done():
                matched_session.future.set_result(tokens)

            return render_template_string(_SUCCESS_HTML), 200

        except Exception as e:
            logger.error(f"Unexpected error during OAuth token exchange: {e}", exc_info=True)
            if not matched_session.future.done():
                matched_session.future.set_exception(e)
            return render_template_string(_ERROR_HTML, error_desc=html.escape(str(e))), 500

    # 3. Fallback: Legacy 302 redirector for unmigrated providers
    lan_ip = get_lan_ip()
    main_port = get_main_app_port()

    clean_provider = urllib.parse.quote(provider_name.strip())
    if request.path.startswith("/api/oauth/callback/plugins/"):
        try:
            import binascii
            from core.nexus_framework.plugin_loader import PluginRegistry

            plugin_cls = PluginRegistry.get_plugin_class(provider_name)
            if plugin_cls and hasattr(plugin_cls, "name") and plugin_cls.name:
                clean_provider = str(binascii.crc32(plugin_cls.name.lower().encode("utf-8")) & 0xFFFFFFFF)
            else:
                from database.config_database import get_config_database

                db = get_config_database()
                conn = db._open_connection()
                try:
                    c = conn.cursor()
                    c.execute(
                        "SELECT plugin_id FROM services WHERE LOWER(name) LIKE ?",
                        ("%" + clean_provider.lower(),),
                    )
                    row = c.fetchone()
                    if row and row[0]:
                        clean_provider = urllib.parse.quote(str(row[0]))
                finally:
                    conn.close()
        except Exception:
            logger.debug(
                f"Unable to resolve plugin provider '{provider_name}' to canonical plugin ID from DB",
                exc_info=True,
            )

        target_path = f"/api/plugins/{clean_provider}/callback"
    else:
        target_path = f"/api/{clean_provider}/callback"

    query_string = request.query_string.decode("utf-8") if request.query_string else ""
    expected_netloc = f"{lan_ip}:{main_port}"
    expected_prefix = f"http://{expected_netloc}/"
    redirect_url = f"http://{expected_netloc}{target_path}"
    if query_string:
        redirect_url += f"?{query_string}"

    if not redirect_url.startswith(expected_prefix):
        return ("Invalid redirect destination", 400)

    parsed = urllib.parse.urlsplit(redirect_url)
    if parsed.scheme != "http" or parsed.netloc != expected_netloc:
        return ("Invalid redirect destination", 400)

    logger.info(f"OAuth sidecar proxying legacy callback for {clean_provider} to {redirect_url}")
    return Response("", status=302, headers={"Location": redirect_url})


def _serve_sidecar(host: str, port: int, cert_path: str, key_path: str) -> None:
    """Serve Flask app over TLS using WSGI server."""
    try:
        server = make_server(
            host,
            port,
            app,
            threaded=True,
            ssl_context=(cert_path, key_path),
        )
        logger.info(f"OAuth sidecar listening securely on https://{host}:{port}")
        server.serve_forever()
    except OSError as e:
        if e.errno == 98 or getattr(e, "winerror", None) == 10048:
            logger.error(
                f"CRITICAL: OAuth sidecar port {port} is already in use. OAuth redirects will fail. Please kill any lingering processes."
            )
        else:
            logger.error(f"Failed to start OAuth sidecar on port {port}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error starting OAuth sidecar: {e}", exc_info=True)


def start_oauth_sidecar(host: str = "0.0.0.0", port: int = 5001, data_dir: str = "data"):
    """
    Initializes SSL certificates and starts the sidecar Flask app on a managed,
    supervised thread under ProcessSupervisor.
    """
    try:
        cert_path, key_path = ensure_ssl_certs(data_dir)
        thread, reg_id = supervisor.spawn_supervised_thread(
            target=_serve_sidecar,
            name="OAuthSidecarServer",
            owner_id="core.oauth_sidecar",
            owner_type=OwnerType.CORE,
            category=ProcessCategory.CORE_SYSTEM,
            bound_to_general_pool=False,
            args=(host, port, cert_path, key_path),
        )
        return thread, reg_id
    except Exception as e:
        logger.error(f"Could not start OAuth sidecar: {e}", exc_info=True)
        return None, None
