import re
with open("core/plugin_loader.py", "r") as f:
    content = f.read()

# 1. Bubble up the error instead of swallowing it
reload_target = r"""            # Re-load
            self._load_plugin_package(
                clean_id,
                self.plugins_dir.name,
                'community',
                is_beta=(channel == 'beta'),
                is_disabled=is_disabled
            )
            logger.info(f"✅ Successfully live-swapped: {plugin_id}")
        except Exception as e:
            logger.error(f"Live-swap failed for {plugin_id}: {e}", exc_info=True)"""

reload_replacement = r"""            # Re-load
            success = self._load_plugin_package(
                clean_id,
                self.plugins_dir.name,
                'community',
                is_beta=(channel == 'beta'),
                is_disabled=is_disabled
            )
            if success is False:
                logger.error(f"Live-swap failed to load module for {plugin_id}")
                raise Exception(f"Live-swap failed to load module for {plugin_id}")
            logger.info(f"✅ Successfully live-swapped: {plugin_id}")
        except Exception as e:
            logger.error(f"Live-swap failed for {plugin_id}: {e}", exc_info=True)
            raise"""

content = content.replace(reload_target, reload_replacement)

# 2. Return False on import failure and add sys.modules alias for beta imports
load_plugin_target = r"""                module = importlib.import_module(module_path)
            finally:"""

load_plugin_replacement = r"""                try:
                    module = importlib.import_module(module_path)

                    # Task 3: The Dynamic Import Namespace Fix
                    # When a plugin is in the beta channel, it might internally use absolute imports
                    # like `from plugins.EchoSync.slskd.client import ...`. Because the module is actually
                    # loaded from `plugins.EchoSync.slskd.beta`, python's sys.modules won't have the non-beta alias
                    # available, causing an import error for internal files.
                    if is_beta:
                        base_module_path = module_path.replace(".beta", "")
                        if base_module_path not in sys.modules:
                            sys.modules[base_module_path] = sys.modules[module_path]
                            logger.debug(f"Injected alias for {base_module_path} pointing to {module_path}")
                except Exception as import_e:
                    logger.error(f"Failed to dynamically import plugin module {module_path}: {import_e}", exc_info=True)
                    return False
            finally:"""

content = content.replace(load_plugin_target, load_plugin_replacement)

with open("core/plugin_loader.py", "w") as f:
    f.write(content)
