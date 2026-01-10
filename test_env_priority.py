#!/usr/bin/env python3
"""Test that ENV variables properly override config.json"""
import sys
import os
from pathlib import Path
from core.settings import ConfigManager

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("\n=== ENV Variable Priority Test ===\n")
print(f"SOULSYNC_CONFIG_DIR={os.environ.get('SOULSYNC_CONFIG_DIR', 'NOT SET')}")
print(f"SOULSYNC_DATA_DIR={os.environ.get('SOULSYNC_DATA_DIR', 'NOT SET')}")
print(f"SOULSYNC_DOWNLOAD_DIR={os.environ.get('SOULSYNC_DOWNLOAD_DIR', 'NOT SET')}")
print(f"SOULSYNC_LIBRARY_DIR={os.environ.get('SOULSYNC_LIBRARY_DIR', 'NOT SET')}")
print(f"SOULSYNC_LOG_DIR={os.environ.get('SOULSYNC_LOG_DIR', 'NOT SET')}")

print("\n=== ConfigManager Paths ===\n")
config = ConfigManager()

paths = config.get_storage_paths()
print(f"config_dir:    {paths['config_dir']}")
print(f"data_dir:      {paths['data_dir']}")
print(f"download_dir:  {paths['download_dir']}")
print(f"library_dir:   {paths['library_dir']}")
print(f"log_dir:       {paths['log_dir']}")

print(f"\nAll paths are absolute: {all(p.is_absolute() for p in paths.values())}")

# Verify get_library_dir() method exists and works
try:
    lib_dir = config.get_library_dir()
    print(f"\n[OK] get_library_dir() works: {lib_dir}")
except AttributeError:
    print("\n[ERROR] get_library_dir() method not found - check rename was successful")

# Try to access old method to ensure it's gone
try:
    old_method = config.get_transfer_dir()
    print("\n[ERROR] get_transfer_dir() still exists - rename incomplete!")
except AttributeError:
    print("\n[OK] get_transfer_dir() properly removed")

# Verify media_db_path
try:
    media_db = config.get_media_db_path()
    print(f"[OK] get_media_db_path(): {media_db}")
except AttributeError:
    print("\n[ERROR] get_media_db_path() method not found")

# Verify plugins_dir
try:
    plugins_dir = config.get_plugins_dir()
    print(f"[OK] get_plugins_dir(): {plugins_dir}")
except AttributeError:
    print("\n[ERROR] get_plugins_dir() method not found")

print("\n=== Configuration Loaded ===\n")
