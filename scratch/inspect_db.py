import sys
import os
sys.path.append(os.getcwd())

from core.settings import config_manager

print("Plugins dir:", config_manager.get_plugins_dir())
print("Plugins path settings:", config_manager.get("plugins_dir"))
print("Current dir contents of plugins dir:", os.listdir(config_manager.get_plugins_dir()) if os.path.exists(config_manager.get_plugins_dir()) else "Does not exist")
