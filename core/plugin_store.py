import json
import logging
import zipfile
import requests
from core.request_manager import RequestManager
from packaging import version
from typing import List, Dict
from core.settings import config_manager

logger = logging.getLogger(__name__)

class PluginStore:
    def __init__(self):
        self.plugins_dir = config_manager.get_plugins_dir()
        self.default_repo = "https://github.com/bheem1224/EchoSync/tree/main/plugins"

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
        from core.settings import config_manager
        import json

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

                check_url = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{subfolder}/manifest.json".replace("//manifest", "/manifest")

                req_mgr = RequestManager(provider="system")
                etags_file = self.plugins_dir / ".etags.json"
                etags = {}
                if etags_file.exists():
                    try:
                        with open(etags_file, "r") as f:
                            etags = json.load(f)
                    except Exception:
                        pass

                headers = {}
                if check_url in etags:
                    headers["If-None-Match"] = etags[check_url]["etag"]

                try:
                    resp = req_mgr.get(check_url, headers=headers, timeout=10)
                    if resp.status_code == 304:
                        logger.debug(f"Manifest not modified (304) for {check_url}")
                        plugins = etags[check_url].get("plugins", [])
                    elif resp.status_code == 200:
                        manifest_data = resp.json()
                        plugins = manifest_data.get("plugins", [])

                        if "ETag" in resp.headers:
                            etags[check_url] = {"etag": resp.headers["ETag"], "plugins": plugins}
                            with open(etags_file, "w") as f:
                                json.dump(etags, f)
                    else:
                        return []

                    filtered_plugins = []
                    for p in plugins:
                        p["_source_repo"] = repo_url
                        plugin_id = p.get("id", "")
                        if plugin_id:
                            p["_folder_path"] = f"{subfolder}/{plugin_id}" if subfolder else plugin_id

                        # Apply application bounds
                        p["privileged_mode"] = p.get("privileged_mode", False)

                        # Filter by channel
                        channel = config_manager.get_plugin_channel(plugin_id)
                        version_str = p.get("version", "1.0.0")

                        base_dl_path = f"https://github.com/{user}/{repo}/raw/refs/heads/{branch}/{subfolder}"
                        base_dl_path = base_dl_path.replace("//raw", "/raw").rstrip('/')

                        if channel == "beta":
                            p["_download_url"] = f"{base_dl_path}/beta.zip"
                            if p.get("beta_version"):
                                p["version"] = p.get("beta_version")
                        else:
                            p["_download_url"] = f"{base_dl_path}/releases/{version_str}.zip"

                        filtered_plugins.append(p)

                    return filtered_plugins
                except Exception as e:
                    logger.debug(f"Could not fetch {check_url}: {e}")

                return self._scan_github_api(user, repo, branch, subfolder, repo_url)
            except IndexError:
                logger.error(f"Malformed GitHub URL: {repo_url}")
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
                                        plugin_info["_download_url"] = f"https://github.com/{user}/{repo}/archive/refs/heads/{branch}.zip"
                                        plugin_info["_folder_path"] = item.get("path")
                                        plugins.append(plugin_info)
        except Exception as e:
            logger.error(f"Error scanning GitHub API for {user}/{repo}: {e}")

        return plugins


    def get_all_store_plugins(self) -> List[Dict]:
        all_plugins = []
        for repo in self.get_repositories():
            all_plugins.extend(self.scan_repository(repo))
            
        for plugin in all_plugins:
            plugin_id = plugin.get("id", plugin.get("name", "unknown_plugin"))
            plugin_id = plugin_id.split(".")[-1]
            dest_dir = self.plugins_dir / plugin_id
            manifest_file = dest_dir / "manifest.json"
            plugin["_installed"] = dest_dir.exists() and manifest_file.exists()

            plugin["update_available"] = False
            if plugin["_installed"]:
                try:
                    with open(manifest_file, "r") as f:
                        local_manifest = json.load(f)
                    local_version = local_manifest.get("version", "0.0.0")
                    remote_version = plugin.get("version", "0.0.0")
                    if version.parse(remote_version) > version.parse(local_version):
                        plugin["update_available"] = True
                except Exception:
                    pass
            
        return all_plugins

    def download_plugin(self, plugin_info: Dict) -> bool:
        from core.settings import config_manager
        import shutil
        import tempfile
        import os

        download_url = plugin_info.get("download_url") or plugin_info.get("_download_url")
        if not download_url:
            logger.error("No download URL provided for plugin.")
            return False

        try:
            logger.info(f"Downloading plugin {plugin_info.get('name')} from {download_url}")
            req_mgr = RequestManager(provider="system")
            resp = req_mgr.get(download_url, timeout=30)
            resp.raise_for_status()

            plugin_id = plugin_info.get("id", plugin_info.get("name", "unknown_plugin"))
            plugin_id = plugin_id.split(".")[-1]
            channel = config_manager.get_plugin_channel(plugin_id)

            dest_dir = self.plugins_dir / plugin_id
            if channel == "beta":
                dest_dir = dest_dir / "beta"

            # Clear existing plugin folder
            if dest_dir.exists():
                shutil.rmtree(dest_dir, ignore_errors=True)
            dest_dir.mkdir(parents=True, exist_ok=True)

            # Create temp zip file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                tmp_file.write(resp.content)
                tmp_zip_path = tmp_file.name

            try:
                with zipfile.ZipFile(tmp_zip_path, 'r') as z:
                    zip_infos = z.infolist()
                    if not zip_infos:
                        logger.error("Empty zip file")
                        return False

                    extracted_count = 0
                    uncompressed_size = 0
                    for zi in zip_infos:
                        if zi.filename.endswith('/'):
                            continue

                        # Extract directly into dest_dir, stripping any potential root folder in the zip if needed,
                        # but as per instructions: "extract the .zip contents directly into that folder".
                        # However, sometimes zips contain a single root dir. If so, we can strip it, or just extract everything.
                        # Since the instruction is specific: "extract the .zip contents directly into that folder",
                        # we will extract files without stripping unless it creates a nested folder of the plugin id.
                        # Usually, `releases/{version}.zip` contains the plugin files directly or in a folder. Let's just extract all.
                        rel_path = zi.filename
                        # If the zip contains a single root folder with the same name, we can handle it or just extract flat.
                        # Let's extract flat if there's a common prefix, or just extract as is.
                        # I'll extract as is, except to prevent zip slip.
                        if '..' in rel_path or rel_path.startswith('/'):
                            logger.error(f"Malicious path detected in zip: {rel_path}")
                            shutil.rmtree(dest_dir, ignore_errors=True)
                            return False

                        target_file = (dest_dir / rel_path).resolve()
                        if not target_file.is_relative_to(dest_dir.resolve()):
                            logger.error(f"Zip Slip prevented for: {target_file}")
                            shutil.rmtree(dest_dir, ignore_errors=True)
                            raise ValueError("Path traversal attempt detected in zip")

                        target_file.parent.mkdir(parents=True, exist_ok=True)

                        uncompressed_size += zi.file_size
                        if uncompressed_size > 50 * 1024 * 1024:
                            logger.error("Zip bomb detected: uncompressed size exceeds 50MB limit.")
                            shutil.rmtree(dest_dir, ignore_errors=True)
                            return False

                        with target_file.open('wb') as out_f:
                            out_f.write(z.read(zi))
                        extracted_count += 1

                    if extracted_count == 0:
                        logger.error(f"No files extracted for plugin {plugin_id}")
                        return False
            finally:
                os.remove(tmp_zip_path)

            manifest_file = dest_dir / "manifest.json"
            if manifest_file.exists():
                with open(manifest_file, "r") as f:
                    local_manifest = json.load(f)

                if plugin_info.get("_source_repo") == self.default_repo:
                    local_manifest["verified_source"] = "official"
                    with open(manifest_file, "w") as f:
                        json.dump(local_manifest, f, indent=4)
                    logger.info(f"Watermarked {plugin_id} as official.")

            return True
        except Exception as e:
            logger.error(f"Failed to download and extract plugin: {e}")
            return False
    def uninstall_plugin(self, plugin_id: str) -> bool:
        import re
        import shutil
        dest_dir = self.plugins_dir / plugin_id
        if not dest_dir.exists():
            return False
        
        # Drop associated tables
        try:
            from database.working_database import get_working_database
            from database.config_database import get_config_database
            
            safe_id = re.sub(r'[^a-zA-Z0-9_]', '_', plugin_id).lower()
            prefix = f"plugin_{safe_id}_%"
            
            for db_engine in [get_working_database().engine, get_config_database().engine]:
                with db_engine.connect() as conn:
                    try:
                        from sqlalchemy import text
                        tables = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE :prefix"), {"prefix": prefix}).fetchall()
                        for (table_name,) in tables:
                            if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
                                logger.warning(f"Skipping drop table due to invalid name: {table_name}")
                                continue
                            conn.execute(text(f"DROP TABLE IF EXISTS \"{table_name}\""))
                            try:
                                conn.commit()
                            except Exception:
                                pass
                    except ImportError:
                        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ?", (prefix,)).fetchall()
                        for (table_name,) in tables:
                            if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
                                logger.warning(f"Skipping drop table due to invalid name: {table_name}")
                                continue
                            conn.execute(f"DROP TABLE IF EXISTS \"{table_name}\"")
        except Exception as e:
            logger.error(f"Failed to drop tables for {plugin_id}: {e}")
            
        # Delete directory
        shutil.rmtree(dest_dir, ignore_errors=True)
        return True


plugin_store = PluginStore()
