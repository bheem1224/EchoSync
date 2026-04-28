import json
import logging
import zipfile
import requests
from pathlib import Path
from packaging import version
from typing import Any, List, Dict, Optional
from core.request_manager import RequestManager
from core.settings import config_manager

logger = logging.getLogger(__name__)

class PluginStore:
    def __init__(self):
        self.plugins_dir = Path(config_manager.get_plugins_dir())
        self.default_repo = "https://raw.githubusercontent.com/bheem1224/EchoSync/main/plugins/store-manifest.json"

    def get_repositories(self) -> List[str]:
        repos = [self.default_repo]
        try:
            config = config_manager.get_settings()
            custom_repos = config.get("custom_plugin_repos", [])
            if isinstance(custom_repos, list):
                repos.extend(custom_repos)
        except Exception as e:
            logger.error(f"Error reading custom repositories: {e}")
        return repos

    def add_repository(self, url: str) -> bool:
        try:
            config = config_manager.get_settings()
            custom_repos = config.get("custom_plugin_repos", [])
            if url not in custom_repos:
                custom_repos.append(url)
                config["custom_plugin_repos"] = custom_repos
                config_manager.save_settings(config)
            return True
        except Exception as e:
            logger.error(f"Error saving custom repository {url}: {e}")
            return False

    def remove_repository(self, url: str) -> bool:
        try:
            config = config_manager.get_settings()
            custom_repos = config.get("custom_plugin_repos", [])
            if url in custom_repos:
                custom_repos.remove(url)
                config["custom_plugin_repos"] = custom_repos
                config_manager.save_settings(config)
            return True
        except Exception as e:
            logger.error(f"Error removing custom repository {url}: {e}")
            return False



    def scan_repository(self, repo_url: str) -> List[Dict]:
        logger.debug(f"Scanning repository: {repo_url}")
        if not hasattr(self, 'plugins_dir') or self.plugins_dir is None:
            from core.settings import config_manager
            self.plugins_dir = Path(config_manager.get_plugins_dir())
            logger.debug(f"Lazy initialized plugins_dir: {self.plugins_dir}")

        plugins = []
        req_mgr = RequestManager(provider="system")
        etags_file = self.plugins_dir / ".etags.json"
        etags = {}
        if etags_file.exists():
            try:
                with open(etags_file, "r") as f:
                    etags = json.load(f)
            except Exception:
                pass

        # Case 1: Direct JSON URL (New Default)
        if repo_url.endswith(".json"):
            try:
                headers = {}
                if repo_url in etags:
                    headers["If-None-Match"] = etags[repo_url]["etag"]
                
                resp = req_mgr.get(repo_url, headers=headers, timeout=10)
                if resp.status_code == 304:
                    plugins = etags[repo_url].get("plugins", [])
                elif resp.status_code == 200:
                    data = resp.json()
                    plugins = data["plugins"] if isinstance(data, dict) and "plugins" in data else data
                    if not isinstance(plugins, list): plugins = [plugins]
                    
                    if "ETag" in resp.headers:
                        etags[repo_url] = {"etag": resp.headers["ETag"], "plugins": plugins}
                        with open(etags_file, "w") as f:
                            json.dump(etags, f)
                
                # For direct JSON URLs, we need to infer the base paths if possible
                # Default to EchoSync main if it matches
                user, repo, branch = "bheem1224", "EchoSync", "main"
                subfolder = "plugins"
                
                filtered_plugins = []
                for p in plugins:
                    p["_source_repo"] = repo_url
                    plugin_id = p.get("id", "")
                    if not plugin_id: continue
                    
                    folder_name = p.get("path") or plugin_id.split(".")[-1]
                    p["_folder_path"] = f"{subfolder}/{folder_name}" if subfolder else folder_name
                    
                    repo_raw_base = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{p['_folder_path']}"
                    if "download_url" not in p:
                        v = p.get("version", "1.0.0")
                        p["download_url"] = f"{repo_raw_base}/releases/v{v}.zip"
                    if "beta_url" not in p:
                        p["beta_url"] = f"{repo_raw_base}/beta.zip"
                    filtered_plugins.append(p)
                return filtered_plugins
            except Exception as e:
                logger.error(f"Failed to scan direct JSON repo {repo_url}: {e}")
                return []

        # Case 2: GitHub Browser URL (Legacy/Custom)
        parts = repo_url.rstrip('/').split('/')
        if "github.com" in parts:
            try:
                gh_idx = parts.index("github.com")
                user = parts[gh_idx + 1]
                repo = parts[gh_idx + 2]
                
                branch = "main"
                subfolder = ""
                if len(parts) > gh_idx + 3 and parts[gh_idx + 3] == "tree":
                    branch = parts[gh_idx + 4]
                    if len(parts) > gh_idx + 5:
                        subfolder = "/".join(parts[gh_idx + 5:])

                # Try store-manifest.json first, then manifest.json
                manifest_files = ["store-manifest.json", "manifest.json"]
                for m_file in manifest_files:
                    check_url = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{subfolder}/{m_file}".replace(f"//{m_file}", f"/{m_file}")
                    
                    headers = {}
                    if check_url in etags:
                        headers["If-None-Match"] = etags[check_url]["etag"]

                    try:
                        resp = req_mgr.get(check_url, headers=headers, timeout=10)
                        if resp.status_code == 304:
                            plugins = etags[check_url].get("plugins", [])
                            break
                        elif resp.status_code == 200:
                            manifest_data = resp.json()
                            if "plugins" in manifest_data:
                                plugins = manifest_data["plugins"]
                            else:
                                plugins = manifest_data if isinstance(manifest_data, list) else [manifest_data]

                            if "ETag" in resp.headers:
                                etags[check_url] = {"etag": resp.headers["ETag"], "plugins": plugins}
                                with open(etags_file, "w") as f:
                                    json.dump(etags, f)
                            break
                    except Exception as e:
                        logger.debug(f"Could not fetch {check_url}: {e}")
                
                if not plugins:
                    return self._scan_github_api(user, repo, branch, subfolder, repo_url)

                filtered_plugins = []
                for p in plugins:
                    p["_source_repo"] = repo_url
                    plugin_id = p.get("id", "")
                    if not plugin_id: continue
                        
                    folder_name = p.get("path") or plugin_id.split(".")[-1]
                    p["_folder_path"] = f"{subfolder}/{folder_name}" if subfolder else folder_name

                    repo_raw_base = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{p['_folder_path']}"
                    if "download_url" not in p:
                        v = p.get("version", "1.0.0")
                        p["download_url"] = f"{repo_raw_base}/releases/v{v}.zip"
                    if "beta_url" not in p:
                        p["beta_url"] = f"{repo_raw_base}/beta.zip"

                    filtered_plugins.append(p)
                return filtered_plugins
            except Exception as e:
                logger.error(f"Error scanning repository {repo_url}: {e}", exc_info=True)
        return []

    def _scan_github_api(self, user: str, repo: str, branch: str, subfolder: str, original_repo_url: str) -> List[Dict]:
        api_url = f"https://api.github.com/repos/{user}/{repo}/contents"
        if subfolder:
            api_url += f"/{subfolder}"
        api_url += f"?ref={branch}"
        
        plugins = []
        try:
            resp = requests.get(api_url, timeout=10)
            if resp.status_code == 200:
                contents = resp.json()
                for item in contents:
                    if item.get("type") == "dir":
                        dir_url = item.get("url")
                        dir_resp = requests.get(dir_url, timeout=10)
                        if dir_resp.status_code == 200:
                            dir_contents = dir_resp.json()
                            for file_item in dir_contents:
                                if file_item.get("name") == "manifest.json":
                                    manifest_resp = requests.get(file_item.get("download_url"), timeout=10)
                                    if manifest_resp.status_code == 200:
                                        plugin_info = manifest_resp.json()
                                        plugin_info["_source_repo"] = original_repo_url
                                        plugin_id = plugin_info.get("id", item.get("name"))
                                        
                                        # Use the archive for legacy API scan fallback
                                        archive_url = f"https://github.com/{user}/{repo}/archive/refs/heads/{branch}.zip"
                                        plugin_info["download_url"] = archive_url
                                        plugin_info["beta_url"] = archive_url
                                        plugin_info["_folder_path"] = item.get("path")
                                        plugins.append(plugin_info)
        except Exception as e:
            logger.error(f"Error scanning GitHub API for {user}/{repo}: {e}")

        return plugins


    def get_all_store_plugins(self) -> List[Dict]:
        all_plugins = []
        for repo in self.get_repositories():
            all_plugins.extend(self.scan_repository(repo))

        # Deduplicate plugins by ID so the store does not expose duplicate entries
        # when the same plugin appears from multiple repositories or fallback manifests.
        unique_plugins = {}
        for plugin in all_plugins:
            plugin_id = plugin.get("id", plugin.get("name", "unknown_plugin"))
            if plugin_id in unique_plugins:
                existing = unique_plugins[plugin_id]
                # Prefer official source and preserve any populated fields from either entry.
                if plugin.get("verified_source") == "official":
                    existing["verified_source"] = "official"
                if plugin.get("_source_repo") == self.default_repo:
                    existing["_source_repo"] = plugin.get("_source_repo")
                for key in ["beta_url", "download_url", "beta_version", "version", "description", "name"]:
                    if not existing.get(key) and plugin.get(key):
                        existing[key] = plugin.get(key)
                continue
            unique_plugins[plugin_id] = plugin
        all_plugins = list(unique_plugins.values())

        for plugin in all_plugins:
            plugin_id = plugin.get("id", plugin.get("name", "unknown_plugin"))
            
            # 1. Inject Official Status from Source
            if plugin.get("_source_repo") == self.default_repo:
                plugin["verified_source"] = "official"
                plugin["author"] = "EchoSync"

            # Task 1: Resolve Active Version from Core or Community
            # Precedence: Community (/data/plugins) > Core (/app/plugins)
            folder_id = plugin_id.split(".")[-1]
            comm_dir = self.plugins_dir / folder_id
            core_dir = Path(__file__).parent.parent / "plugins" / folder_id
            
            comm_manifest = comm_dir / "manifest.json"
            core_manifest = core_dir / "manifest.json"
            
            plugin["_installed"] = False
            plugin["installed_version"] = None
            plugin["installed_channel"] = config_manager.get_plugin_channel(folder_id)
            
            # Check community first (updates/overrides)
            if comm_dir.exists():
                beta_manifest = comm_dir / "beta" / "manifest.json"
                if plugin["installed_channel"] == "beta" and beta_manifest.exists():
                    plugin["_installed"] = True
                    active_manifest_path = beta_manifest
                elif comm_manifest.exists():
                    plugin["_installed"] = True
                    active_manifest_path = comm_manifest
                else:
                    active_manifest_path = None
            # Check core second (bundled)
            elif core_dir.exists() and core_manifest.exists():
                plugin["_installed"] = True
                active_manifest_path = core_manifest
            else:
                active_manifest_path = None
            plugin["update_available"] = False

            if plugin["_installed"] and active_manifest_path:
                try:
                    with open(active_manifest_path, "r") as f:
                        local_manifest = json.load(f)
                    
                    # Merge local verified status (overrides remote if mismatch)
                    if local_manifest.get("verified_source") == "official":
                        plugin["verified_source"] = "official"

                    local_version = local_manifest.get("version", "0.0.0")
                    plugin["installed_version"] = local_version
                    
                    remote_version = plugin.get("version", "0.0.0")
                    # If on beta track, compare against beta version
                    if plugin["installed_channel"] == "beta" and plugin.get("beta_version"):
                        remote_version = plugin.get("beta_version")

                    try:
                        if version.parse(remote_version) > version.parse(local_version):
                            plugin["update_available"] = True
                    except Exception:
                        if remote_version != local_version:
                            plugin["update_available"] = True
                except Exception as e:
                    logger.debug(f"Error checking local version for {plugin_id}: {e}")
            
        return all_plugins

    def download_plugin(self, plugin_info: Dict, channel: str = "stable") -> bool:
        """
        Direct Artifact Downloader.
        Downloads a cleanly packaged .zip artifact based on the selected channel.
        """
        from core.settings import config_manager
        from core.state import system_state
        from core.event_bus import event_bus
        import shutil
        import tempfile
        import os

        # Task 1: Resolve Direct URL based on Channel
        if channel == "beta":
            download_url = plugin_info.get("beta_url") or plugin_info.get("download_url")
        else:
            download_url = plugin_info.get("download_url")

        if not download_url:
            logger.error(f"No artifact URL found for plugin {plugin_info.get('id')} on channel {channel}")
            return False

        plugin_id = plugin_info.get("id", plugin_info.get("name", "unknown_plugin"))
        folder_id = plugin_id.split(".")[-1]
        dest_dir = self.plugins_dir / folder_id
        beta_dir = dest_dir / "beta"

        if channel == "beta":
            target_dir = beta_dir
        else:
            target_dir = dest_dir

        tmp_dir = self.plugins_dir / f"tmp_{folder_id}"

        try:
            logger.info(f"Direct downloading {plugin_id} ({channel}) from {download_url}")
            req_mgr = RequestManager(provider="system")
            resp = req_mgr.get(download_url, timeout=30)
            
            if resp.status_code != 200:
                logger.error(f"Artifact download failed with status {resp.status_code}")
                return False

            if tmp_dir.exists(): shutil.rmtree(tmp_dir, ignore_errors=True)
            tmp_dir.mkdir(parents=True, exist_ok=True)

            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                tmp_file.write(resp.content)
                tmp_zip_path = tmp_file.name

            try:
                # Task 2: Artifact Extraction (Direct Root Level)
                with zipfile.ZipFile(tmp_zip_path, 'r') as z:
                    # Security: Zip Slip Check
                    for zi in z.infolist():
                        if '..' in zi.filename or zi.filename.startswith('/'):
                            logger.error(f"Malicious path in artifact: {zi.filename}")
                            return False
                    
                    z.extractall(tmp_dir)

                # Validation: Direct check for manifest.json at root
                manifest_file = tmp_dir / "manifest.json"
                if not manifest_file.exists():
                    logger.error(f"Validation failed: Clean artifact missing manifest.json at root for {plugin_id}")
                    # If this happens, we might be downloading a full repo zip by mistake
                    return False

                # Task 4: Inject Verified Source Block if from Official Repo
                # This allows official plugins to bypass the AST scanner safely.
                if plugin_info.get("_source_repo") == self.default_repo:
                    try:
                        with open(manifest_file, "r") as f:
                            manifest_data = json.load(f)
                        
                        manifest_data["verified_source"] = "official"
                        manifest_data["author"] = "EchoSync"
                        
                        with open(manifest_file, "w") as f:
                            json.dump(manifest_data, f, indent=2)
                        logger.info(f"Injected verified_source block for {plugin_id}")
                    except Exception as e:
                        logger.error(f"Failed to inject verified_source for {plugin_id}: {e}")

                # Task 3: Atomic Swap
                if channel == "stable" and beta_dir.exists():
                    shutil.rmtree(beta_dir, ignore_errors=True)

                if target_dir.exists():
                    shutil.rmtree(target_dir, ignore_errors=True)

                if target_dir == beta_dir and not dest_dir.exists():
                    dest_dir.mkdir(parents=True, exist_ok=True)

                os.rename(str(tmp_dir), str(target_dir))
                logger.info(f"Successfully installed {plugin_id} artifact via atomic swap")

                # Task 5: Persist Channel Preference (use folder_id for PluginLoader compatibility)
                config_manager.set(f'plugins.{folder_id}.channel', channel)
                logger.info(f"Persisted channel '{channel}' for plugin {folder_id}")

                # State Updates
                system_state.restart_pending = True
                event_bus.publish("SYSTEM", "PLUGIN_UPDATE_COMPLETE", {
                    "plugin_id": plugin_id,
                    "name": plugin_info.get("name"),
                    "version": plugin_info.get("version"),
                    "channel": channel,
                    "restart_required": True
                })
                
                return True

            finally:
                if os.path.exists(tmp_zip_path): os.remove(tmp_zip_path)
                if tmp_dir.exists(): shutil.rmtree(tmp_dir, ignore_errors=True)

        except Exception as e:
            logger.error(f"Fatal error during artifact installation: {e}", exc_info=True)
            return False

    def _cleanup_beta_subfolder(self, folder_id: str) -> bool:
        import shutil
        beta_path = self.plugins_dir / folder_id / "beta"
        if beta_path.exists():
            shutil.rmtree(beta_path, ignore_errors=True)
            logger.info(f"Removed leftover beta folder for plugin {folder_id}")
            return True
        return False

    def restore_stable_plugins(self) -> Dict[str, Any]:
        """Restore stable plugin artifacts for plugins that still had beta channel config."""
        results = {}
        plugin_settings = config_manager.get('plugins', {}) or {}
        beta_plugin_ids = [pid for pid, data in plugin_settings.items() if isinstance(data, dict) and data.get('channel') == 'beta']
        if not beta_plugin_ids:
            return results

        store_plugins = self.get_all_store_plugins()
        for folder_id in beta_plugin_ids:
            results[folder_id] = {"restored": False, "beta_removed": False, "errors": []}
            if self._cleanup_beta_subfolder(folder_id):
                results[folder_id]["beta_removed"] = True

            plugin_info = next(
                (p for p in store_plugins if p.get('id', '').split('.')[-1] == folder_id or p.get('id', '') == folder_id),
                None,
            )

            config_manager.set(f'plugins.{folder_id}.channel', 'stable')
            if plugin_info and plugin_info.get('download_url'):
                if self.download_plugin(plugin_info, channel='stable'):
                    results[folder_id]["restored"] = True
                else:
                    results[folder_id]["errors"].append('stable_download_failed')
            else:
                if not plugin_info:
                    results[folder_id]["errors"].append('store_info_not_found')
                else:
                    results[folder_id]["errors"].append('stable_download_url_missing')

        config_manager.save_settings(config_manager.get_settings())
        return results

    def uninstall_plugin(self, plugin_id: str) -> bool:
        import re
        import shutil
        folder_id = plugin_id.split(".")[-1]
        dest_dir = self.plugins_dir / folder_id
        if not dest_dir.exists():
            return False
        
        try:
            from database.working_database import get_working_database
            from database.config_database import get_config_database
            
            safe_id = re.sub(r'[^a-zA-Z0-9_]', '_', folder_id).lower()
            prefix = f"plugin_{safe_id}_%"
            
            for db_engine in [get_working_database().engine, get_config_database().engine]:
                with db_engine.connect() as conn:
                    try:
                        from sqlalchemy import text
                        tables = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE :prefix"), {"prefix": prefix}).fetchall()
                        for (table_name,) in tables:
                            conn.execute(text(f"DROP TABLE IF EXISTS \"{table_name}\""))
                        conn.commit()
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"Failed to drop tables for {plugin_id}: {e}")
            
        shutil.rmtree(dest_dir, ignore_errors=True)
        return True


plugin_store = PluginStore()
