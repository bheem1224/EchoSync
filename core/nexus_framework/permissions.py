"""
Permissions Registry & Normalization for Nexus Framework Plugins.

Authoritative source of permission constants, safe base scopes, and serialization
helpers for plugin security sandboxing.
"""

from typing import Any

SAFE_BASE_SCOPES = [
    "database.read_library",
    "metadata.read",
]

DEFAULT_BASE_PERMISSIONS = list(SAFE_BASE_SCOPES)

# Mutation scopes that require explicit user consent during installation/updates
MUTATION_SCOPES = [
    "database.mutate_aliases",
    "database.mutate_attributes",
    "database.mutate_working",
    "network_domains",
    "privileged_mode",
    "wasm_fs_access",
]


def is_explicitly_denied(permissions: Any, scope: str) -> bool:
    """Checks if a scope is explicitly set to False in a permissions payload."""
    if not isinstance(permissions, dict):
        return False
    if permissions.get(scope) is False:
        return True
    if "." in scope:
        base_cat, sub_key = scope.split(".", 1)
        cat_dict = permissions.get(base_cat)
        if isinstance(cat_dict, dict) and cat_dict.get(sub_key) is False:
            return True
        if permissions.get(sub_key) is False:
            return True
    return False


def normalize_permissions_payload(permissions: Any) -> list[str]:
    """
    Normalizes permissions into a canonical list of scope strings.
    Handles None, lists, and nested dictionary representations.
    """
    if not permissions:
        return []

    if isinstance(permissions, list):
        return [str(p).strip() for p in permissions if p and str(p).strip()]

    if isinstance(permissions, dict):
        normalized = []
        if permissions.get("privileged_mode"):
            normalized.append("privileged_mode")
        db_perms = permissions.get("database", {})
        if isinstance(db_perms, dict):
            for db_key, val in db_perms.items():
                if val:
                    normalized.append(f"database.{db_key}")
        for k, v in permissions.items():
            if k == "database":
                continue
            if isinstance(v, bool) and v:
                normalized.append(k)
            elif isinstance(v, list) and k in ("network_domains", "wasm_fs_access"):
                if v:
                    normalized.append(k)
        return sorted(list(set(normalized)))

    return []


def seed_base_permissions(existing_permissions: Any) -> list[str]:
    """
    Appends SAFE_BASE_SCOPES to existing permissions if missing, preserving
    any already granted scopes and respecting explicit False opt-outs.
    """
    normalized = normalize_permissions_payload(existing_permissions)
    for scope in SAFE_BASE_SCOPES:
        if scope not in normalized and not is_explicitly_denied(existing_permissions, scope):
            normalized.append(scope)
    return sorted(normalized)
