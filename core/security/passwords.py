"""NIST SP 800-63B-4 / OWASP password policy, Argon2id PHC hashing, and bcrypt fallback verification."""

from __future__ import annotations

import unicodedata
from typing import Any

from Crypto.Protocol.KDF import bcrypt_check
from cryptography.exceptions import InvalidKey
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id

PASSWORD_MIN_LENGTH = 8
PASSWORD_RECOMMENDED_LENGTH = 15
PASSWORD_MAX_LENGTH = 512

_ARGON2_SALT_BYTES = 16
_ARGON2_HASH_BYTES = 32
_ARGON2_TIME_COST = 3
_ARGON2_LANES = 4
_ARGON2_MEMORY_KIB = 65536


def normalize_password(password: str) -> str:
    """Apply Unicode NFKC normalization per NIST SP 800-63B-4 without stripping spaces."""
    return unicodedata.normalize("NFKC", password)


def validate_password_policy(password: str) -> str:
    """Validate password against NIST SP 800-63B-4 length rules (no composition rules).

    Returns the NFKC-normalized password on success or raises ValueError.
    """
    if not isinstance(password, str):
        raise ValueError("Password must be a string.")
    normalized = normalize_password(password)
    if len(normalized) < PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters long "
            f"(15+ recommended for passphrases)."
        )
    if len(normalized) > PASSWORD_MAX_LENGTH:
        raise ValueError(f"Password must not exceed {PASSWORD_MAX_LENGTH} characters.")
    return normalized


def hash_password(password: str, *, validate_policy: bool = True) -> str:
    """Hash a password using cryptography's Argon2id PHC-encoded format."""
    import os

    normalized = validate_password_policy(password) if validate_policy else normalize_password(password)
    salt = os.urandom(_ARGON2_SALT_BYTES)
    kdf = Argon2id(
        salt=salt,
        length=_ARGON2_HASH_BYTES,
        iterations=_ARGON2_TIME_COST,
        lanes=_ARGON2_LANES,
        memory_cost=_ARGON2_MEMORY_KIB,
    )
    return kdf.derive_phc_encoded(normalized.encode("utf-8"))


def verify_password(password: str, stored_hash: str | None) -> bool:
    """Verify a password against an Argon2id PHC hash or legacy bcrypt hash."""
    if not isinstance(password, str) or not password or not stored_hash:
        return False

    normalized = normalize_password(password)
    pw_bytes = normalized.encode("utf-8")

    if stored_hash.startswith("$argon2id$"):
        try:
            Argon2id.verify_phc_encoded(pw_bytes, stored_hash)
            return True
        except (InvalidKey, ValueError, TypeError):
            return False

    if stored_hash.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            bcrypt_check(pw_bytes, stored_hash.encode("utf-8"))
            return True
        except (ValueError, TypeError):
            return False

    return False


def verify_user_credentials(username: str, password: str) -> dict[str, Any] | None:
    """Authenticate a local user against ConfigDatabase credentials."""
    from database.config_database import get_config_database

    return get_config_database().authenticate_local_user(username, password)
