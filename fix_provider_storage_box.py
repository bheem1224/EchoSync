import glob
import re

for filepath in glob.glob('plugins/EchoSync/**/*.py', recursive=True):
    with open(filepath, 'r') as f:
        content = f.read()

    if 'PluginStorageBox' in content:
        # replace `from core.nexus_framework.plugin_SDK import PluginStorageBox`
        # with `from core.nexus_framework.plugin_SDK import sdk`
        # and remove the instantiation line `sdk = PluginStorageBox(...)`
        content = re.sub(r'from core\.nexus_framework\.plugin_SDK import PluginStorageBox\s*sdk = PluginStorageBox\(plugin_id=zlib\.crc32\(b[\'"](.*?)[\'"]\) \& 0xFFFFFFFF\)',
                         r'from core.nexus_framework.plugin_SDK import sdk', content)

        with open(filepath, 'w') as f:
            f.write(content)
