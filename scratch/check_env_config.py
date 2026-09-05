import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import os

from core.settings import config_manager

print("Environment variables:")
for k, v in os.environ.items():
    if "ECHOSYNC" in k or "DATABASE" in k or "DATA" in k:
        print(f"  {k} = {v}")

print("\nConfig Manager Settings:")
for key in [
    "database.music_uri",
    "database.config_uri",
    "database.working_uri",
    "storage.data_dir",
]:
    print(f"  {key} = {config_manager.get(key)}")
