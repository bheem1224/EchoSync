from typing import Any
from core.enums import Capability
from core.nexus_framework.plugin_loader import PluginRegistry, generate_plugin_id


def get_acoustid_plugin(provider: Any | None = None) -> Any | None:
    """Resolve the preferred plugin for AcoustID / Chromaprint lookups."""
    if provider is not None:
        return provider

    # Check by plugin id / alias
    plugin = (
        PluginRegistry.get_plugin(generate_plugin_id("EchoSync.acoustid"))
        or PluginRegistry.get_plugin("EchoSync.acoustid")
        or PluginRegistry.get_plugin("acoustid")
    )
    if plugin:
        return plugin

    # Check by capability
    plugins = PluginRegistry.get_plugins_with_capability(Capability.RESOLVE_FINGERPRINT)
    for p in plugins:
        caps = getattr(p, "capabilities", None)
        if caps:
            algos = getattr(caps, "fingerprint_algorithms", []) or []
            if "chromaprint" in algos or getattr(caps, "supports_fingerprinting", False):
                return p
    return plugins[0] if plugins else None


def get_musicbrainz_plugin(provider: Any | None = None) -> Any | None:
    """Resolve the preferred plugin for canonical MusicBrainz metadata lookups."""
    if provider is not None:
        return provider

    # Check by plugin id / alias
    plugin = (
        PluginRegistry.get_plugin(generate_plugin_id("EchoSync.musicbrainz"))
        or PluginRegistry.get_plugin("EchoSync.musicbrainz")
        or PluginRegistry.get_plugin("musicbrainz")
    )
    if plugin:
        return plugin

    # Fallback to general metadata capability
    plugins = PluginRegistry.get_plugins_with_capability(Capability.FETCH_METADATA)
    return plugins[0] if plugins else None
