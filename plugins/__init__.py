"""
Plugin system infrastructure for SoulSync.

This package contains the core plugin framework that providers use to integrate
with SoulSync's core functionality.
"""

from plugins.plugin_system import (
    PluginRegistry,
    PluginDeclaration,
    PluginType,
    PluginScope,
    plugin_registry,
    register_plugin,
    get_plugin
)
from plugins.adapter_registry import AdapterRegistry
from plugins.provider_adapter import ProviderAdapter
from plugins.service_registry import ServiceRegistry, service_registry

__all__ = [
    'PluginRegistry',
    'PluginDeclaration',
    'PluginType',
    'PluginScope',
    'plugin_registry',
    'register_plugin',
    'get_plugin',
    'AdapterRegistry',
    'ProviderAdapter',
    'ServiceRegistry',
    'service_registry',
]
