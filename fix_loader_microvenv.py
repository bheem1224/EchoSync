import re

with open("core/plugin_loader.py", "r") as f:
    content = f.read()

target_str = """                try:
                    module = importlib.import_module(module_path)"""

injection = """                micro_venv_dir = package_dir / "micro-venv"
                micro_venv_str = str(micro_venv_dir)
                added_micro_venv = False
                if micro_venv_dir.exists():
                    sys.path.insert(0, micro_venv_str)
                    added_micro_venv = True
                    logger.debug(f"Injected micro-venv into sys.path for {module_path}")

                try:
                    module = importlib.import_module(module_path)"""

content = content.replace(target_str, injection)

finally_target_str = """            finally:
                if added_to_path and plugins_parent_str in sys.path:
                    sys.path.remove(plugins_parent_str)"""

finally_injection = """            finally:
                if added_micro_venv and micro_venv_str in sys.path:
                    sys.path.remove(micro_venv_str)
                    logger.debug(f"Removed micro-venv from sys.path for {module_path}")
                if added_to_path and plugins_parent_str in sys.path:
                    sys.path.remove(plugins_parent_str)"""

content = content.replace(finally_target_str, finally_injection)

with open("core/plugin_loader.py", "w") as f:
    f.write(content)
