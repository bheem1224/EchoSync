#!/usr/bin/env python3
"""Test ENV variable loading"""
import os
from pathlib import Path
from dotenv import load_dotenv
from core.settings import ConfigManager

# Load .env
load_dotenv(Path(__file__).parent / '.env')
config = ConfigManager()

print(f"\nFinal Paths:")
print(f"  config_dir: {config.config_dir}")
print(f"  data_dir:   {config.data_dir}")
print(f"  media_db:   {config.media_db_path}")
print(f"  plugins:    {config.plugins_path}")
