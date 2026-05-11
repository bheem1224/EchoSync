import re

with open("core/plugin_loader.py", "r") as f:
    content = f.read()

# We need to replace the sys.modules alias injection block we added earlier
# and ensure the __path__ bridging is correctly implemented.
# Looking at line 536-554, there is already some __path__ bridging, but it
# might not be sufficient or correct according to the mission.

# Let's see the current __path__ bridging logic
path_bridge_target = """                # If we are loading plugins.EchoSync.tidal.beta, we want plugins.EchoSync.tidal.client
                # to look inside the beta folder too.
                if is_beta:
                    parent_module_name = f"{parent_dir_name}.{clean_name}"
                    try:
                        # Ensure parent module exists in sys.modules
                        importlib.import_module(parent_module_name)
                        parent_module = sys.modules.get(parent_module_name)
                        if parent_module and hasattr(parent_module, '__path__'):
                            beta_path = str(self.plugins_dir / path_name / "beta")
                            if beta_path not in parent_module.__path__:
                                logger.debug(f"Bridging {parent_module_name} __path__ to include {beta_path}")
                                parent_module.__path__.insert(0, beta_path)
                    except Exception as bridge_err:
                        logger.debug(f"Could not bridge parent module path: {bridge_err}")"""

path_bridge_replacement = """                # Task: Dynamic Import Pathing Patch (Namespace Injection)
                # When a plugin executes an absolute import (e.g., from plugins.EchoSync.slskd.client import SlskdProvider)
                # python resolves the file from disk if the submodule is not loaded.
                # We need to ensure the active channel's directory is the first entry in the base module's __path__.
                base_module_name = f"{parent_dir_name}.{clean_name}"
                try:
                    # 1. Implicitly load the base namespace package
                    base_module = importlib.import_module(base_module_name)

                    # 2. Inject the active channel folder into the base module's search path
                    channel_dir = str(package_dir) # This handles both stable and beta paths since package_dir already includes "/beta" if is_beta is True
                    if hasattr(base_module, '__path__'):
                        if channel_dir not in base_module.__path__:
                            base_module.__path__.insert(0, channel_dir)
                            logger.debug(f"Injected {channel_dir} into {base_module_name} __path__")
                except Exception as bridge_err:
                    logger.debug(f"Could not bridge base module path: {bridge_err}")"""

content = content.replace(path_bridge_target, path_bridge_replacement)

# Remove the sys.modules injection we added in TASK 3 before
sys_modules_injection = """                    # Task 3: The Dynamic Import Namespace Fix
                    # When a plugin is in the beta channel, it might internally use absolute imports
                    # like `from plugins.EchoSync.slskd.client import ...`. Because the module is actually
                    # loaded from `plugins.EchoSync.slskd.beta`, python's sys.modules won't have the non-beta alias
                    # available, causing an import error for internal files.
                    if is_beta:
                        base_module_path = module_path.replace(".beta", "")
                        if base_module_path not in sys.modules:
                            sys.modules[base_module_path] = sys.modules[module_path]
                            logger.debug(f"Injected alias for {base_module_path} pointing to {module_path}")"""

content = content.replace(sys_modules_injection, "")

with open("core/plugin_loader.py", "w") as f:
    f.write(content)
