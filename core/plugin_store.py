import json
import logging
import zipfile
import io
import requests
from pathlib import Path
from typing import List, Dict, Optional
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
        parts = repo_url.rstrip('/').split('/')
        if "github.com" in parts:
            try:
                gh_idx = parts.index("github.com")
                user = parts[gh_idx + 1]
                repo = parts[gh_idx + 2]
                
                branch = "main"
                subfolder = ""
                if len(parts) > gh_idx + 4 and parts[gh_idx + 3] == "tree":
                    branch = parts[gh_idx + 4]
                    subfolder = "/".join(parts[gh_idx + 5:])
                
                if subfolder:
                    raw_urls = [f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{subfolder}/store-manifest.json"]
                else:
                    raw_urls = [
                        f"https://raw.githubusercontent.com/{user}/{repo}/main/store-manifest.json",
                        f"https://raw.githubusercontent.com/{user}/{repo}/master/store-manifest.json"
                    ]

                for check_url in raw_urls:
                    try:
                        resp = requests.get(check_url, timeout=10)
                        if resp.status_code == 200:
                            manifest_data = resp.json()
                            plugins = manifest_data.get("plugins", [])
                            for p in plugins:
                                p["_source_repo"] = repo_url
                                if "download_url" not in p and "_download_url" not in p:
                                    p["_download_url"] = f"https://github.com/{user}/{repo}/archive/refs/heads/{branch}.zip"
                                    plugin_id = p.get("id", "")
                                    if plugin_id:
                                        p["_folder_path"] = f"{subfolder}/{plugin_id}" if subfolder else plugin_id
                            return plugins
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
        return all_plugins

    def download_plugin(self, plugin_info: Dict) -> bool:
        download_url = plugin_info.get("download_url") or plugin_info.get("_download_url")
        if not download_url:
            logger.error("No download URL provided for plugin.")
            return False

        try:
            logger.info(f"Downloading plugin {plugin_info.get('name')} from {download_url}")
            resp = requests.get(download_url, timeout=30)
            resp.raise_for_status()

            with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                plugin_id = plugin_info.get("id", plugin_info.get("name", "unknown_plugin"))
                plugin_id = plugin_id.split(".")[-1]

                dest_dir = self.plugins_dir / plugin_id
                dest_dir.mkdir(parents=True, exist_ok=True)

                folder_path = plugin_info.get("_folder_path")

                zip_infos = z.infolist()
                
                if not zip_infos:
                    logger.error("Empty zip file")
                    return False
                    
                root_dir = zip_infos[0].filename.split('/')[0]

                target_prefix = f"{root_dir}/{folder_path}/" if folder_path else f"{root_dir}/"
                
                if folder_path:
                    prefix_exists = any(zi.filename.startswith(target_prefix) for zi in zip_infos)
                    if not prefix_exists:
                        for zi in zip_infos:
                            if zi.filename.endswith('/manifest.json'):
                                dir_path = zi.filename[:-14]
                                if dir_path.endswith(f"/{plugin_id}"):
                                    target_prefix = dir_path + "/"
                                    break

                extracted_count = 0
                for zi in zip_infos:
                    if zi.filename.endswith('/'):
                        continue
                        
                    if zi.filename.startswith(target_prefix):
                        rel_path = zi.filename[len(target_prefix):]
                        if rel_path:
                            target_file = dest_dir / rel_path
                            target_file.parent.mkdir(parents=True, exist_ok=True)
                            with target_file.open('wb') as f:
                                f.write(z.read(zi))
                            extracted_count += 1
                
                if extracted_count == 0:
                    logger.error(f"No files extracted for plugin {plugin_id} with prefix {target_prefix}")
                    return False

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

plugin_store = PluginStore()
