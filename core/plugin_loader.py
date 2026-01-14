"""Dynamic plugin loader for SoulSync providers and plugins."""

import importlib
import importlib.util
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

from flask import Blueprint

from core.provider import ProviderRegistry
from core.provider_base import ProviderBase
from utils.logging_config import get_logger

logger = get_logger("plugin_loader")


class PluginLoader:
    """
    Scans and loads providers from 'providers/' (core) and 'plugins/' (community).
    Registers them with the ProviderRegistry and collects Flask blueprints.
    """

    def __init__(self, app_root: Path):
        self.app_root = app_root
        self.providers_dir = app_root / "providers"
        self.plugins_dir = app_root / "plugins"
        self.loaded_blueprints: List[Blueprint] = []

    def load_all(self):
        """Scan and load all providers and plugins."""
        logger.info("Starting plugin discovery...")

        # 1. Load Core Providers
        self._scan_directory(self.providers_dir, source_type='core')

        # 2. Load Community Plugins (if directory exists)
        if self.plugins_dir.exists():
            self._scan_directory(self.plugins_dir, source_type='community')
        else:
            logger.debug("No plugins/ directory found. Skipping community plugins.")

        logger.info(f"Plugin discovery complete. Loaded {len(self.loaded_blueprints)} blueprints.")

    def _scan_directory(self, directory: Path, source_type: str):
        """
        Scan a directory for provider packages.

        Args:
            directory: The directory to scan (e.g., providers/).
            source_type: 'core' or 'community'.
        """
        if not directory.exists():
            logger.warning(f"Directory not found: {directory}")
            return

        # Ensure the directory is in sys.path so imports work
        str_dir = str(directory.parent)
        if str_dir not in sys.path:
            sys.path.insert(0, str_dir)

        for item in directory.iterdir():
            if not item.is_dir() or item.name.startswith('_'):
                continue

            provider_name = item.name
            init_file = item / "__init__.py"

            if not init_file.exists():
                logger.debug(f"Skipping {provider_name}: no __init__.py found")
                continue

            self._load_provider_package(provider_name, directory.name, source_type)

    def _load_provider_package(self, name: str, parent_dir_name: str, source_type: str):
        """
        Dynamically import a provider package and register its exports.

        Args:
            name: The package name (e.g., 'plex').
            parent_dir_name: The parent directory name (e.g., 'providers' or 'plugins').
            source_type: 'core' or 'community'.
        """
        module_path = f"{parent_dir_name}.{name}"
        try:
            # Dynamic import
            module = importlib.import_module(module_path)

            # 1. Register Provider Class
            provider_class = getattr(module, 'ProviderClass', None)
            if provider_class and issubclass(provider_class, ProviderBase):
                # Check for registry conflicts or disabling logic if needed
                ProviderRegistry.register(provider_class, source_type=source_type)

                # Instantiate immediately to trigger any self-setup if needed
                # (Though strictly speaking, we might want to delay instantiation until needed,
                # existing logic often instantiates them. We will stick to registration for now
                # and let the app instantiate them via registry if needed, OR we can instantiate here
                # if that was the legacy behavior. The legacy behavior was explicit instantiation in _init_provider_clients.
                # BUT, ProviderRegistry.create_instance() is used later.
                # HOWEVER, some providers might need instantiation to set up listeners?
                # Let's check memory: "Instantiate provider clients so they self-register in plugin_registry" was the old way.
                # Now we register the CLASS directly. Instantiation happens when used.
                # BUT, we might want to instantiate them to verify config?
                # For now, just register the class.
                pass
            else:
                # Fallback: Look for any ProviderBase subclass if not explicitly exported
                # (Useful for transition or plugins that don't follow the new spec yet)
                found = False
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and issubclass(attr, ProviderBase) and attr is not ProviderBase:
                        ProviderRegistry.register(attr, source_type=source_type)
                        found = True
                        break
                if not found:
                    logger.debug(f"No ProviderClass found in {module_path}")

            # 2. Collect Route Blueprint
            blueprint = getattr(module, 'RouteBlueprint', None)
            if isinstance(blueprint, Blueprint):
                self.loaded_blueprints.append(blueprint)
                logger.debug(f"Collected blueprint for {name}")
            elif blueprint is not None:
                logger.warning(f"Invalid RouteBlueprint in {name}: expected flask.Blueprint, got {type(blueprint)}")

        except ImportError as e:
            logger.error(f"Failed to import {module_path}: {e}")
            # Graceful failure: Log and continue
        except Exception as e:
            logger.error(f"Unexpected error loading {module_path}: {e}", exc_info=True)

    def get_all_blueprints(self) -> List[Blueprint]:
        return self.loaded_blueprints
