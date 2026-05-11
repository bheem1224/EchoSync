import re
with open("core/plugin_store.py", "r") as f:
    content = f.read()

uninstall_method = """    def uninstall_plugin(self, plugin_id: str) -> bool:
        import re
        import shutil
        import os
        import sys
        # Nexus Framework: Resolve nested path by converting dots to slashes
        clean_id = plugin_id.replace('plugin.', '').replace('core.', '')
        folder_path = clean_id.replace('.', os.sep)
        dest_dir = self.plugins_dir / folder_path

        try:
            from database.working_database import get_working_database
            from web.db.config_db import get_config_database

            # 1. Disable and remove jobs
            try:
                from core.job_queue import job_queue
                job_queue.kill_jobs_by_plugin(plugin_id)
            except Exception as e:
                logger.warning(f"Failed to kill workers for {plugin_id}: {e}")

            # 2. Hot-Unload (Purge from sys.modules)
            ns_parts = clean_id.split('.')
            if len(ns_parts) >= 2:
                author = ns_parts[0]
                plugin_name = ".".join(ns_parts[1:])
            else:
                author = "unknown"
                plugin_name = clean_id

            purge_id = f"{author}/{plugin_name}" if author != "unknown" else clean_id
            module_names = [f"plugins.{purge_id.replace('/', '.')}", f"plugins.{clean_id}"]
            for module_name in module_names:
                if module_name in sys.modules:
                    submodules = [m for m in list(sys.modules.keys()) if m.startswith(module_name + ".")]
                    for m in submodules:
                        sys.modules.pop(m, None)
                    sys.modules.pop(module_name, None)

            # Use clean_id (Author.Name) but replace dots with underscores for DB safety
            safe_id = re.sub(r'[^a-zA-Z0-9_]', '_', clean_id.replace('.', '_')).lower()
            prefix = f"plugin_{safe_id}_%"

            for db_engine in [get_working_database().engine, get_config_database().engine]:
                with db_engine.connect() as conn:
                    try:
                        from sqlalchemy import text
                        tables = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE :prefix"), {"prefix": prefix}).fetchall()
                        for (table_name,) in tables:
                            if table_name in ("plugin_state_kvs", "config_kvs"):
                                continue
                            conn.execute(text(f"DROP TABLE IF EXISTS \\"{table_name}\\""))
                        conn.commit()
                    except Exception:
                        pass

            # 4. Delete config keys
            config = get_config_database()
            with config._get_connection() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM config_kvs WHERE namespace=?", (plugin_id,))
                c.execute("DELETE FROM config_kvs WHERE namespace=?", (f"plugin.{plugin_id}",))
                # 6. Remove from services table
                c.execute("DELETE FROM services WHERE namespace=?", (plugin_id,))
                c.execute("DELETE FROM services WHERE namespace=?", (f"plugin.{plugin_id}",))
                conn.commit()

            # Remove from JSON config if exists
            from core.settings import config_manager
            all_settings = config_manager.get_settings()
            if 'plugins' in all_settings and clean_id in all_settings['plugins']:
                del all_settings['plugins'][clean_id]
                config_manager.save_settings(all_settings)

        except Exception as e:
            logger.error(f"Failed during uninstall for {plugin_id}: {e}")

        # 5. Delete folder
        if dest_dir.exists():
            shutil.rmtree(dest_dir, ignore_errors=True)

        from core.state import system_state
        system_state.restart_pending = True

        return True"""

old_method = re.search(r"    def uninstall_plugin.*?return True", content, re.DOTALL)
if old_method:
    content = content[:old_method.start()] + uninstall_method + content[old_method.end():]
    with open("core/plugin_store.py", "w") as f:
        f.write(content)
else:
    print("Could not find uninstall_plugin method")
