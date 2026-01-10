#!/usr/bin/env python3
"""Test ENV variable loading"""
import os
from pathlib import Path
from dotenv import load_dotenv
from core.settings import ConfigManager

# Load .env
load_dotenv(Path(__file__).parent / '.env')

print("ENV Variables from .env file:")
print("=" * 60)
env_vars = [
    'SOULSYNC_CONFIG_DIR',
    'SOULSYNC_DATA_DIR', 
    'SOULSYNC_DOWNLOAD_DIR',
    'SOULSYNC_LIBRARY_DIR',
    'SOULSYNC_LOG_DIR',
]

for var in env_vars:
    value = os.environ.get(var)
    if value:
        print(f"[SET] {var} = {value}")
    else:
        print(f"[NOT SET] {var}")

print("\n" + "=" * 60)
print("\nTesting ConfigManager with loaded ENV:\n")

config = ConfigManager()

print("\nFinal Paths:")
print(f"  config_dir: {config.config_dir}")
print(f"  data_dir:   {config.data_dir}")
print(f"  media_db:   {config.media_db_path}")
print(f"  plugins:    {config.plugins_path}")
