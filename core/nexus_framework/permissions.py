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


def _permissions_to_manifest_dict(permissions: Any) -> dict[str, Any]:
    """Convert stored permissions (dict or scope list) into canonical manifest permissions dict."""
    if isinstance(permissions, dict):
        return dict(permissions)
    if not isinstance(permissions, list):
        return {}
    result: dict[str, Any] = {}
    db_dict: dict[str, bool] = {}
    for item in permissions:
        scope = str(item).strip()
        if not scope:
            continue
        if scope == "privileged_mode":
            result["privileged_mode"] = True
        elif scope.startswith("database."):
            db_dict[scope.split(".", 1)[1]] = True
        elif scope in ("network_domains", "wasm_fs_access"):
            result[scope] = True
        else:
            result[scope] = True
    if db_dict:
        result["database"] = db_dict
    return result


def build_granted_scopes_payload(manifest_data: dict[str, Any]) -> Any:
    """Build canonical granted_scopes snapshot preserving dict permissions & domain/fs lists."""
    perms = manifest_data.get("permissions")
    if isinstance(perms, dict):
        snapshot = dict(perms)
        if "network_domains" in manifest_data and "network_domains" not in snapshot:
            snapshot["network_domains"] = manifest_data["network_domains"]
        if "wasm_fs_access" in manifest_data and "wasm_fs_access" not in snapshot:
            snapshot["wasm_fs_access"] = manifest_data["wasm_fs_access"]
        if manifest_data.get("privileged") or manifest_data.get("privileged_mode"):
            snapshot["privileged_mode"] = True
        return snapshot
    return seed_base_permissions(perms)


def compute_permission_delta(
    current_manifest: dict, new_manifest: dict, filter_safe_scopes: bool = False
) -> list[dict]:
    """Compute newly requested permissions between current_manifest and new_manifest."""
    escalations: list[dict] = []

    current_manifest = current_manifest or {}
    new_manifest = new_manifest or {}

    raw_curr_perms = current_manifest.get("permissions")
    curr_perms = _permissions_to_manifest_dict(raw_curr_perms)
    new_perms = new_manifest.get("permissions") if isinstance(new_manifest.get("permissions"), dict) else {}

    curr_priv = bool(
        current_manifest.get("privileged")
        or current_manifest.get("privileged_mode")
        or curr_perms.get("privileged_mode")
    )
    new_priv = bool(
        new_manifest.get("privileged") or new_manifest.get("privileged_mode") or new_perms.get("privileged_mode")
    )
    if new_priv and not curr_priv:
        escalations.append(
            {
                "scope": "privileged_mode",
                "description": "Requests privileged operating system and subprocess access.",
            }
        )

    curr_domains_raw = current_manifest.get("network_domains")
    if curr_domains_raw is None:
        curr_domains_raw = curr_perms.get("network_domains", [])
    curr_has_any_domains = curr_domains_raw is True
    curr_domains = set(curr_domains_raw if isinstance(curr_domains_raw, list) else [])

    new_domains_raw = new_manifest.get("network_domains")
    if new_domains_raw is None:
        new_domains_raw = new_perms.get("network_domains", [])
    new_domains = set(new_domains_raw if isinstance(new_domains_raw, list) else [])

    added_domains = [] if curr_has_any_domains else sorted(list(new_domains - curr_domains))
    if added_domains:
        escalations.append(
            {
                "scope": "network_domains",
                "added": added_domains,
                "description": f"Requests network egress to new domains: {', '.join(added_domains)}",
            }
        )

    curr_db = curr_perms.get("database") if isinstance(curr_perms.get("database"), dict) else {}
    new_db = new_perms.get("database") if isinstance(new_perms.get("database"), dict) else {}

    db_descriptions = {
        "read_library": "Requests permission to read canonical library data.",
        "mutate_aliases": "Requests permission to write entity aliases to library.",
        "mutate_attributes": "Requests permission to write entity attributes to library.",
        "mutate_working": "Requests permission to modify working database tables.",
    }

    all_db_keys = set(list(db_descriptions.keys()) + list(new_db.keys()))
    for key in sorted(all_db_keys):
        is_curr = bool(curr_db.get(key) or curr_perms.get(f"database.{key}") or curr_perms.get(key))
        is_new = bool(new_db.get(key) or new_perms.get(f"database.{key}") or new_perms.get(key))
        if is_new and not is_curr:
            desc = db_descriptions.get(key, f"Requests permission to access database scope {key}.")
            escalations.append({"scope": f"database.{key}", "description": desc})

    curr_fs_raw = current_manifest.get("wasm_fs_access") or curr_perms.get("wasm_fs_access", [])
    curr_has_any_fs = curr_fs_raw is True
    curr_fs = set(curr_fs_raw if isinstance(curr_fs_raw, list) else [])
    new_fs_raw = new_manifest.get("wasm_fs_access") or new_perms.get("wasm_fs_access", [])
    new_fs = set(new_fs_raw if isinstance(new_fs_raw, list) else [])
    added_fs = [] if curr_has_any_fs else sorted(list(new_fs - curr_fs))
    if added_fs:
        escalations.append(
            {
                "scope": "wasm_fs_access",
                "added": added_fs,
                "description": f"Requests file system access to paths: {', '.join(added_fs)}",
            }
        )

    if filter_safe_scopes:
        escalations = [
            e
            for e in escalations
            if e.get("scope") not in ("database.read_library", "read_library", "metadata.read", "metadata")
        ]

    return escalations


def evaluate_manifest_consent(
    manifest_data: dict[str, Any],
    granted_scopes_raw: Any,
    fallback_permissions_raw: Any = None,
) -> list[dict[str, Any]]:
    """Check whether manifest_data requests scopes exceeding granted_scopes from config.db."""
    import json

    raw = granted_scopes_raw if granted_scopes_raw not in (None, "") else fallback_permissions_raw
    if raw is None:
        return []

    parsed: Any
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {}
    else:
        parsed = raw

    current_manifest: dict[str, Any] = {"permissions": parsed}
    if isinstance(parsed, dict):
        if parsed.get("privileged_mode"):
            current_manifest["privileged_mode"] = True
        if "network_domains" in parsed:
            current_manifest["network_domains"] = parsed["network_domains"]
        if "wasm_fs_access" in parsed:
            current_manifest["wasm_fs_access"] = parsed["wasm_fs_access"]

    return compute_permission_delta(current_manifest, manifest_data, filter_safe_scopes=True)
