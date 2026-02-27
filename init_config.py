"""Initialize config with new data_dir structure"""
import sys
import os

# Prevent importing full core package
sys.path.insert(0, '.')
os.environ['SKIP_CORE_IMPORTS'] = '1'

# Import settings module directly without going through core.__init__
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "settings_module",
    Path(__file__).parent / "core" / "settings.py"
)
settings_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(settings_module)

print("\n" + "="*70)
print("INITIALIZING CONFIG WITH DATA_DIR STRUCTURE")
print("="*70 + "\n")

# Get the config_manager instance
cfg = settings_module.config_manager

print("\nStorage configuration generated:")
storage = cfg.get('storage', {})
for key, value in storage.items():
    print(f"  {key}: {value}")

print(f"\nConfig saved to: {cfg.config_path}")
print("\n" + "="*70 + "\n")
