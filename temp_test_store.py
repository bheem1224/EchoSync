import sys
import os

from core.nexus_framework.plugin_store import plugin_store
plugins = plugin_store.get_all_store_plugins()
for p in plugins:
    print(f"{p.get('id')}: installed={p.get('_installed')}, version={p.get('installed_version')}")
