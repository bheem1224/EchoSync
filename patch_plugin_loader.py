import re

with open('core/plugin_loader.py', 'r') as f:
    content = f.read()

orig_import = 'if alias.name.split(\'.\')[0] in ("os", "subprocess", "sqlite3", "sys", "importlib", "database"):'
patch_import = 'if alias.name.split(\'.\')[0] in ("os", "subprocess", "sqlite3", "sys", "importlib", "database", "inspect", "ctypes"):'

orig_from = 'if node.module and node.module.split(\'.\')[0] in ("os", "subprocess", "sqlite3", "sys", "importlib", "database"):'
patch_from = 'if node.module and node.module.split(\'.\')[0] in ("os", "subprocess", "sqlite3", "sys", "importlib", "database", "inspect", "ctypes"):'

content = content.replace(orig_import, patch_import)
content = content.replace(orig_from, patch_from)

with open('core/plugin_loader.py', 'w') as f:
    f.write(content)
