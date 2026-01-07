# Provider/Plugin Integration Summary

## Overview
Plugins have been folded into the Provider system by adding classification flags and enable/disable functionality. This eliminates duplicate code while maintaining clear separation between bundled providers (stable) and community plugins (potentially unstable).

## Key Changes

### 1. ProviderBase Updates (`core/provider_base.py`)
- **Replaced `type` attribute with `category`**: 
  - `category = 'provider'` (default) = Bundled, stable providers
  - `category = 'plugin'` = Community-made, potentially unstable plugins
- **Added `enabled` flag**: `enabled = True` (default)
  - Allows enable/disable without deleting files
  - Requires app restart to take effect

### 2. ProviderRegistry Enhancements (`core/provider_registry.py`)
- **Added `_disabled_providers` class variable**: Tracks disabled providers at startup
- **New methods**:
  - `get_providers_by_type(provider_type, exclude_disabled=True)`: Filter out disabled providers
  - `create_instance_by_type()`: Now excludes disabled providers with error handling
  - `create_instance()`: Checks if provider is disabled before instantiation
  - `disable_provider(name)`: Disable a provider/plugin
  - `enable_provider(name)`: Re-enable a previously disabled provider/plugin
  - `is_provider_disabled(name)`: Check if a provider is disabled
  - `set_disabled_providers(disabled_list)`: Load disabled list from config (called at startup)
  - `get_disabled_providers()`: Return list of currently disabled providers
- **Updated `get_download_clients()`**: Excludes disabled providers

### 3. Configuration System (`config/settings.py`)
- **Added `disabled_providers` to default config**:
  ```json
  "disabled_providers": []  // List of provider/plugin names to disable
  ```
- **New ConfigManager methods**:
  - `get_disabled_providers()`: Retrieve disabled list from config
  - `set_disabled_providers(disabled_list)`: Update disabled list
  - `disable_provider(name)`: Add provider to disabled list and save
  - `enable_provider(name)`: Remove provider from disabled list and save

### 4. Startup Integration (`web/api_app.py`)
- **Updated `_init_provider_clients()`**:
  - Loads disabled providers from config via `config_manager.get_disabled_providers()`
  - Calls `ProviderRegistry.set_disabled_providers()` before instantiating any providers
  - Ensures disabled providers are skipped during initialization

## Usage Examples

### Disabling a Provider (API)
```python
from config.settings import config_manager
from core.provider_registry import ProviderRegistry

# Disable via config
config_manager.disable_provider('spotify')

# Check if disabled
if ProviderRegistry.is_provider_disabled('spotify'):
    print("Spotify is disabled")

# Get all disabled providers
disabled = ProviderRegistry.get_disabled_providers()
print(f"Disabled: {disabled}")
```

### Configuration File
Edit `config.json` to disable providers:
```json
{
  "disabled_providers": ["spotify", "tidal"]
}
```

When the app restarts, Spotify and TIDAL providers will be skipped.

## Benefits

1. **No Code Duplication**: Plugins and providers use the same base classes and registry
2. **Easy Management**: Simple flag/tag system to distinguish bundled vs community code
3. **Non-Destructive**: Disable without deleting - easy to re-enable later
4. **Configuration-Driven**: Disable list managed in config.json
5. **Performance**: Disabled providers are never instantiated
6. **Flexibility**: Works for both current bundled providers and future community plugins

## File Structure Remains Unchanged

```
providers/
  spotify/
  tidal/
  plex/
  jellyfin/
  navidrome/
  soulseek/

plugins/  (future location for community plugins)
  # (empty until community contributes plugins)
```

## Migration Notes

- **No changes required for existing providers**: They continue to work as-is
- **Plugin system simplified**: `plugin_system.py` concepts are now integrated into provider system
- **Backward compatible**: Existing provider code requires no modifications
- **Future plugins**: Can be placed in `plugins/` folder and loaded the same way as providers

## Testing Disable/Enable

```bash
# Disable Spotify
python -c "from config.settings import config_manager; config_manager.disable_provider('spotify')"

# Restart app - Spotify will be skipped

# Re-enable Spotify
python -c "from config.settings import config_manager; config_manager.enable_provider('spotify')"

# Restart app - Spotify will load normally
```
