#!/usr/bin/env python3
"""Comprehensive test of path configuration"""
import sys
from pathlib import Path
from core.settings import ConfigManager

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("\n=== SoulSync Path Configuration Test ===\n")

config = ConfigManager()
paths = config.get_storage_paths()

print("Storage Paths Summary:")
print("=" * 60)
for key, path in paths.items():
    is_absolute = path.is_absolute()
    exists = path.exists()
    status = "[OK]" if is_absolute else "[ERROR]"
    print(f"{status} {key:15} = {path}")
    if not is_absolute:
        print("    ^ NOT ABSOLUTE!")
    if not exists and key not in ['media_db', 'plugins']:
        print("    (does not exist yet)")

print("\n" + "=" * 60)
print(f"All paths absolute: {all(p.is_absolute() for p in paths.values())}")
print(f"All paths resolved: {all(not str(p).startswith(chr(92) + 'data') for p in paths.values())}")

print("\nGetter Methods Test:")
print("=" * 60)

getters = [
    ("config_dir", config.get_config_dir),
    ("data_dir", config.data_dir),
    ("media_db_path", config.get_media_db_path),
    ("plugins_dir", config.get_plugins_dir),
    ("download_dir", config.get_download_dir),
    ("library_dir", config.get_library_dir),
    ("log_dir", config.get_log_dir),
]

for name, getter in getters:
    try:
        result = getter() if callable(getter) else getter
        print(f"[OK] {name:20} = {result}")
    except Exception as e:
        print(f"[ERROR] {name:20} - {e}")

print("\nDatabase Configuration:")
print("=" * 60)
print(f"config.db location: {config.database_path}")
print(f"music_library.db:   {config.media_db_path}")
print(f"Encryption key:     {config.key_path}")

print("\n=== Test Complete ===\n")
