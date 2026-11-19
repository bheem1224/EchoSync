"""Fernet encryption utilities, stdlib/cryptography JWT handling, JWKS verification, and API keys."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

_cipher_instance: Fernet | None = None
_jwt_secret_cache: bytes | None = None

_ALLOWED_ASYMMETRIC_ALGS = {
    "RS256": ("RSA", hashes.SHA256),
    "RS384": ("RSA", hashes.SHA384),
    "RS512": ("RSA", hashes.SHA512),
    "ES256": ("EC", hashes.SHA256),
    "ES384": ("EC", hashes.SHA384),
    "ES512": ("EC", hashes.SHA512),
}

_EC_CURVES = {
    "P-256": ec.SECP256R1,
    "P-384": ec.SECP384R1,
    "P-521": ec.SECP521R1,
}


def _resolve_config_dir() -> Path:
    config_dir_env = os.environ.get("ECHOSYNC_CONFIG_DIR")
    if config_dir_env:
        return Path(config_dir_env)
    return Path(__file__).resolve().parent.parent.parent / "config"


def get_cipher() -> Fernet:
    """Get the Fernet cipher instance for encryption/decryption."""
    global _cipher_instance

    if _cipher_instance is not None:
        return _cipher_instance

    key = os.getenv("MASTER_KEY")
    if key:
        _cipher_instance = Fernet(key.encode())
        return _cipher_instance

    config_dir = _resolve_config_dir()
    key_path = config_dir / ".encryption_key"

    if key_path.exists():
        key_bytes = key_path.read_bytes()
        _cipher_instance = Fernet(key_bytes)
        return _cipher_instance

    key_bytes = Fernet.generate_key()
    config_dir.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(key_bytes)
    key_path.chmod(0o600)

    _cipher_instance = Fernet(key_bytes)
    return _cipher_instance


def encrypt_string(plaintext: str | None) -> str | None:
    """Encrypt a string and return the encrypted payload prefixed with 'enc:'."""
    if plaintext is None:
        return None
    if str(plaintext).startswith("enc:"):
        return str(plaintext)
    cipher = get_cipher()
    encrypted_bytes = cipher.encrypt(str(plaintext).encode("utf-8"))
    return f"enc:{encrypted_bytes.decode('utf-8')}"


def decrypt_string(ciphertext: str | None) -> str | None:
    """Decrypt a string if prefixed with 'enc:', otherwise return as-is."""
    if ciphertext is None:
        return None
    if not str(ciphertext).startswith("enc:"):
        return str(ciphertext)
    cipher = get_cipher()
    try:
        decrypted_bytes = cipher.decrypt(str(ciphertext)[4:].encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except Exception:
        return str(ciphertext)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(encoded: str) -> bytes:
    pad = "=" * ((4 - len(encoded) % 4) % 4)
    return base64.urlsafe_b64decode(encoded + pad)


def _get_jwt_secret() -> bytes:
    global _jwt_secret_cache

    env_secret = os.getenv("ECHOSYNC_JWT_SECRET") or os.getenv("MASTER_KEY")
    if env_secret:
        return env_secret.encode("utf-8")

    config_dir = _resolve_config_dir()
    secret_path = config_dir / ".jwt_secret"
    if secret_path.exists():
        return secret_path.read_bytes().strip()

    if _jwt_secret_cache is None:
        generated = secrets.token_urlsafe(48).encode("utf-8")
        try:
            config_dir.mkdir(parents=True, exist_ok=True)
            secret_path.write_bytes(generated)
            secret_path.chmod(0o600)
        except OSError:
            pass
        _jwt_secret_cache = generated
    return _jwt_secret_cache


def _coerce_numeric_claim(value: Any) -> int | float | None:
    if isinstance(value, datetime):
        return value.timestamp()
    if isinstance(value, (int, float)):
        return value
    return None


def sign_jwt_hs256(payload: dict[str, Any], *, secret: bytes | None = None) -> str:
    """Sign a JWT using HMAC-SHA256 without PyJWT."""
    signing_key = secret or _get_jwt_secret()
    normalized_payload = dict(payload)
    for ts_key in ("exp", "iat", "nbf"):
        if ts_key in normalized_payload and isinstance(normalized_payload[ts_key], datetime):
            normalized_payload[ts_key] = int(normalized_payload[ts_key].timestamp())

    header_b64 = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(
        json.dumps(normalized_payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    sig_b64 = _b64url_encode(hmac.new(signing_key, signing_input, hashlib.sha256).digest())
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def verify_jwt_hs256(
    token: str,
    *,
    secret: bytes | None = None,
    audience: str | None = None,
    issuer: str | None = None,
    leeway_seconds: int = 30,
) -> dict[str, Any] | None:
    """Verify an HS256 JWT token and return its claims, or None on failure."""
    if not isinstance(token, str) or token.count(".") != 2:
        return None
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
        header = json.loads(_b64url_decode(header_b64).decode("utf-8"))
        if not isinstance(header, dict) or header.get("alg") != "HS256":
            return None

        signing_key = secret or _get_jwt_secret()
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = hmac.new(signing_key, signing_input, hashlib.sha256).digest()
        provided_sig = _b64url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, provided_sig):
            return None

        claims = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        if not isinstance(claims, dict):
            return None

        now = time.time()
        exp = _coerce_numeric_claim(claims.get("exp"))
        if exp is not None and now - leeway_seconds > exp:
            return None
        nbf = _coerce_numeric_claim(claims.get("nbf"))
        if nbf is not None and now + leeway_seconds < nbf:
            return None

        if issuer and claims.get("iss") != issuer:
            return None
        if audience:
            aud_claim = claims.get("aud")
            if isinstance(aud_claim, list):
                if audience not in aud_claim:
                    return None
            elif aud_claim != audience:
                return None

        return claims
    except Exception:
        return None


def _jwk_int(b64url_val: str) -> int:
    return int.from_bytes(_b64url_decode(b64url_val), "big")


def _jwk_to_public_key(jwk: dict[str, Any]):
    kty = jwk.get("kty")
    if kty == "RSA":
        n = _jwk_int(jwk["n"])
        e = _jwk_int(jwk["e"])
        return rsa.RSAPublicNumbers(e, n).public_key()
    if kty == "EC":
        crv_name = jwk.get("crv", "P-256")
        curve_cls = _EC_CURVES.get(crv_name)
        if curve_cls is None:
            raise ValueError(f"Unsupported EC curve: {crv_name}")
        x = _jwk_int(jwk["x"])
        y = _jwk_int(jwk["y"])
        return ec.EllipticCurvePublicNumbers(x, y, curve_cls()).public_key()
    raise ValueError(f"Unsupported JWK key type: {kty}")


def _verify_asymmetric_sig(public_key, alg: str, signing_input: bytes, signature: bytes) -> None:
    expected_kty, hash_cls = _ALLOWED_ASYMMETRIC_ALGS[alg]
    if expected_kty == "RSA":
        if not isinstance(public_key, rsa.RSAPublicKey):
            raise ValueError("JWK is not an RSA key.")
        public_key.verify(signature, signing_input, padding.PKCS1v15(), hash_cls())
        return

    if not isinstance(public_key, ec.EllipticCurvePublicKey):
        raise ValueError("JWK is not an EC key.")
    coord_len = (public_key.curve.key_size + 7) // 8
    if len(signature) == 2 * coord_len:
        r = int.from_bytes(signature[:coord_len], "big")
        s = int.from_bytes(signature[coord_len:], "big")
        der_sig = encode_dss_signature(r, s)
    else:
        der_sig = signature
    public_key.verify(der_sig, signing_input, ec.ECDSA(hash_cls()))


def verify_jwt_jwks(
    token: str,
    jwks: dict[str, Any] | list[dict[str, Any]],
    *,
    audience: str | None = None,
    issuer: str | None = None,
    leeway_seconds: int = 60,
) -> dict[str, Any]:
    """Verify an OIDC RS256/ES256 ID token against a JWKS dictionary/key list."""
    if not isinstance(token, str) or token.count(".") != 2:
        raise ValueError("Malformed JWT token.")

    header_b64, payload_b64, sig_b64 = token.split(".")
    header = json.loads(_b64url_decode(header_b64).decode("utf-8"))
    alg = header.get("alg")
    if alg not in _ALLOWED_ASYMMETRIC_ALGS:
        raise ValueError(f"Disallowed or unsupported JWT algorithm: {alg}")

    key_list = jwks.get("keys", []) if isinstance(jwks, dict) else list(jwks)
    if not key_list:
        raise ValueError("JWKS contains no verification keys.")

    expected_kty, _ = _ALLOWED_ASYMMETRIC_ALGS[alg]
    kid = header.get("kid")
    candidate_keys = [
        k
        for k in key_list
        if k.get("kty") == expected_kty and (kid is None or k.get("kid") == kid)
    ]
    if not candidate_keys:
        raise ValueError(f"No matching JWK found for kid={kid!r} and alg={alg}.")

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = _b64url_decode(sig_b64)

    verified = False
    for jwk in candidate_keys:
        try:
            pub_key = _jwk_to_public_key(jwk)
            _verify_asymmetric_sig(pub_key, alg, signing_input, signature)
            verified = True
            break
        except (InvalidSignature, KeyError, ValueError):
            continue

    if not verified:
        raise ValueError("Invalid ID token signature.")

    claims = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    if not isinstance(claims, dict):
        raise ValueError("JWT payload is not a JSON object.")

    now = time.time()
    exp = _coerce_numeric_claim(claims.get("exp"))
    if exp is None or now - leeway_seconds > exp:
        raise ValueError("ID token has expired.")

    nbf = _coerce_numeric_claim(claims.get("nbf"))
    if nbf is not None and now + leeway_seconds < nbf:
        raise ValueError("ID token is not yet valid.")

    if issuer and claims.get("iss") != issuer:
        raise ValueError(f"ID token issuer mismatch: expected {issuer!r}, got {claims.get('iss')!r}.")

    if audience:
        aud_claim = claims.get("aud")
        if isinstance(aud_claim, list):
            if audience not in aud_claim:
                raise ValueError("ID token audience mismatch.")
            if len(aud_claim) > 1 and claims.get("azp") not in (None, audience):
                raise ValueError("ID token authorized party (azp) mismatch.")
        elif aud_claim != audience:
            raise ValueError("ID token audience mismatch.")

    return claims


def create_access_token(
    *,
    user_id: str | None,
    username: str,
    roles: list[str] | tuple[str, ...] = (),
    auth_provider: str = "local",
    csrf: str | None = None,
    ttl_seconds: int = 7 * 86400,
) -> str:
    """Issue an EchoSync HS256 session JWT for cookie or Bearer auth."""
    now = datetime.now(UTC)
    payload = {
        "sub": user_id or username,
        "user": username,
        "roles": list(roles),
        "auth_provider": auth_provider,
        "csrf": csrf or secrets.token_urlsafe(24),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
    }
    return sign_jwt_hs256(payload)


def generate_auth_token(username: str, csrf: str) -> str:
    """Generate an HS256 JWT token for the user with a CSRF claim."""
    return create_access_token(user_id=username, username=username, csrf=csrf)


def verify_auth_token(token: str) -> dict[str, Any] | None:
    """Verify an HS256 JWT token and return the payload."""
    return verify_jwt_hs256(token)


def hash_api_key(raw_key: str) -> str:
    """Compute canonical SHA-256 hex digest for API key storage/lookup."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """Generate a prefixed API key returning `(raw_key, key_prefix, key_hash)`."""
    raw_key = f"es_{secrets.token_urlsafe(32)}"
    key_prefix = raw_key[:11]
    return raw_key, key_prefix, hash_api_key(raw_key)
