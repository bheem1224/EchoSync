with open('/app/core/plugin_loader.py', 'r') as f:
    content = f.read()

content = content.replace(
    '    from core.settings import config_manager\nfrom core.binary_runner import CoreBinaryRunner',
    '    from core.settings import config_manager\n    from core.binary_runner import CoreBinaryRunner'
)

with open('/app/core/plugin_loader.py', 'w') as f:
    f.write(content)
