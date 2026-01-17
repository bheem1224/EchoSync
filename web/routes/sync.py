from flask import Blueprint, jsonify
from core.tiered_logger import get_logger
from core.provider import ProviderRegistry, get_provider_capabilities, PlaylistSupport

logger = get_logger("sync_route")
bp = Blueprint("sync", __name__, url_prefix="/api/sync")


def _serialize_provider(provider_name):
    """Serialize a provider with capabilities for sync planning."""
    try:
        caps = get_provider_capabilities(provider_name)
        return {
            "name": provider_name,
            "display_name": caps.name.title(),
            "playlist_support": caps.supports_playlists.name,
            "metadata_richness": caps.metadata.name,
            "supports_streaming": caps.supports_streaming,
            "supports_library_scan": caps.supports_library_scan,
            "supports_playlist_write": caps.supports_playlists == PlaylistSupport.READ_WRITE,
            "supports_cover_art": caps.supports_cover_art,
        }
    except KeyError:
        return {
            "name": provider_name,
            "display_name": provider_name.title(),
            "playlist_support": "UNKNOWN",
            "supports_playlist_write": False,
            "metadata_richness": "LOW",
            "supports_streaming": False,
            "supports_library_scan": False,
        }


def build_sync_options():
    """Construct sync source/target options from registered providers."""
    sources = []
    provider_targets = []
    library_targets = []

    for provider_name in ProviderRegistry.list_providers():
        if ProviderRegistry.is_provider_disabled(provider_name):
            continue

        try:
            caps = get_provider_capabilities(provider_name)
            data = _serialize_provider(provider_name)

            # Playlist Provider (Source or Target)
            if caps.supports_playlists in (PlaylistSupport.READ, PlaylistSupport.READ_WRITE):
                sources.append(data)

            if caps.supports_playlists == PlaylistSupport.READ_WRITE:
                provider_targets.append(data)

            # Library Provider (Target)
            if caps.supports_library_scan:
                library_targets.append(data)

        except Exception as e:
            logger.error(f"Error processing provider {provider_name} capabilities: {e}")
            continue

    return {
        "sources": sources,
        "targets": {
            "providers": provider_targets,
            "libraries": library_targets,
        },
        "multi_source_supported": True,
        "multi_target_supported": True,
    }


def build_sync_status():
    """Build a minimal sync status payload."""
    try:
        # Placeholder values until job system endpoints are wired
        last_run = None
        running_jobs = 0
        queued_jobs = 0
        errors = []

        # Count active playlist providers
        active_sync_providers = 0
        for name in ProviderRegistry.list_providers():
            if not ProviderRegistry.is_provider_disabled(name):
                try:
                    caps = get_provider_capabilities(name)
                    if caps.supports_playlists in (PlaylistSupport.READ, PlaylistSupport.READ_WRITE):
                        active_sync_providers += 1
                except:
                    pass

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
    """Return sync source/target options derived from provider registry."""
    options = build_sync_options()
    return jsonify(options)
