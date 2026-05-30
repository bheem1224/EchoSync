import re
with open("core/nexus_framework/plugin_loader.py", "r") as f:
    print(f.read().count('return True\n\n            except Exception as e:\n                logger.error("Plugin loading halted:'))
