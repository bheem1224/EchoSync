from flask import Blueprint, jsonify
from utils.logging_config import get_logger
from plugins.plugin_system import plugin_registry, PluginScope, PluginType
from core.provider_capabilities import get_provider_capabilities

logger = get_logger("sync_route")
bp = Blueprint("sync", __name__, url_prefix="/api/sync")


def _serialize_plugin(plugin):
    """Serialize a plugin with optional capability enrichment for sync planning."""
    data = plugin.to_dict()
    try:
        caps = get_provider_capabilities(plugin.name)
        data.update({
            "playlist_support": caps.supports_playlists.name,
            "metadata_richness": caps.metadata.name,
            "supports_streaming": caps.supports_streaming,
            "supports_library_scan": caps.supports_library_scan,
        })
        data["supports_playlist_write"] = caps.supports_playlists.name == "READ_WRITE"
    except KeyError:
        data.setdefault("playlist_support", "UNKNOWN")
        data["supports_playlist_write"] = "playlist.write" in (data.get("provides") or [])
    return data


def _dedup_by_name(items):
    seen = set()
    deduped = []
    for item in items:
        name = item.get("name")
        if name in seen:
            continue
        seen.add(name)
        deduped.append(item)
    return deduped


def build_sync_options():
    """Construct sync source/target options from registered plugins."""
    sources = []
    provider_targets = []
    library_targets = []

    for plugin in plugin_registry.list_all():
        if not getattr(plugin, "enabled", True):
            continue

        data = _serialize_plugin(plugin)
        scopes = set(plugin.scope or [])

        is_playlist_provider = (
            plugin.plugin_type == PluginType.PLAYLIST_PROVIDER or
            PluginScope.SYNC in scopes
        )
        is_library_provider = (
            plugin.plugin_type == PluginType.LIBRARY_PROVIDER or
            PluginScope.LIBRARY in scopes
        )

        if is_playlist_provider:
            sources.append(data)
            provider_targets.append(data)
        if is_library_provider:
            library_targets.append(data)

    return {
        "sources": _dedup_by_name(sources),
        "targets": {
            "providers": _dedup_by_name(provider_targets),
            "libraries": _dedup_by_name(library_targets),
        },
        # UI is allowed to pick multiple sources/targets simultaneously
        "multi_source_supported": True,
        "multi_target_supported": True,
    }


def build_sync_status():
    """Build a minimal sync status payload.

    Returns:
        dict: status with last_run, running_jobs, queued_jobs, errors, active_sync_providers
    """
    try:
        # Placeholder values until job system endpoints are wired
        last_run = None  # could be ISO timestamp in future
        running_jobs = 0
        queued_jobs = 0
        errors = []

        # Count providers that operate in SYNC scope (playlist providers)
        sync_providers = plugin_registry.get_plugins_by_scope(PluginScope.SYNC)
        active_sync_providers = len([p for p in sync_providers if p.enabled])

        return {
            "last_run": last_run,
            "running_jobs": running_jobs,
            "queued_jobs": queued_jobs,
            "errors": errors,
            "active_sync_providers": active_sync_providers,
        }
    except Exception as e:
        logger.error(f"Error building sync status: {e}")
        return {
            "last_run": None,
            "running_jobs": 0,
            "queued_jobs": 0,
            "errors": ["Failed to compute sync status"],
            "active_sync_providers": 0,
        }


@bp.get("/status")
def sync_status():
    """Return minimal sync status for dashboard widget."""
    status = build_sync_status()
    return jsonify(status)


@bp.get("/options")
def sync_options():
    """Return sync source/target options derived from plugin registry."""
    options = build_sync_options()
    return jsonify(options)
