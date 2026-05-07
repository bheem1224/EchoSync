from core.plugin_SDK import PluginBase as ProviderBase

# Legacy compatibility shim for the Nexus Plugin Framework.
# Built-in providers have been migrated to core.plugin_SDK.PluginBase.
# This file exists solely to prevent ModuleNotFoundError crashes in 
# community plugins that have not yet updated their imports.
