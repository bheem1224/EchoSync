import re
import os

def fix_file(filepath, replacements):
    if not os.path.exists(filepath):
        return
    with open(filepath, 'r') as f:
        content = f.read()
    for old, new in replacements:
        content = content.replace(old, new)
    with open(filepath, 'w') as f:
        f.write(content)

fix_file('tests/core/test_oauth_sidecar.py', [
    ('from core.nexus_framework.plugin_store import PluginRegistry', 'from core.nexus_framework.plugin_store import PluginRegistry\nfrom database.working_database import PluginDatabaseFactory\n\n')
])
