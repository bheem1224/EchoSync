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
        self.default_repo = "https://github.com/EchoSync/echosync-plugins"

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
            user = parts[-2]
            repo = parts[-1]
            raw_url = f"https://raw.githubusercontent.com/{user}/{repo}/main/store-manifest.json"
            master_raw_url = f"https://raw.githubusercontent.com/{user}/{repo}/master/store-manifest.json"

            for check_url in [raw_url, master_raw_url]:
                try:
                    resp = requests.get(check_url, timeout=10)
                    if resp.status_code == 200:
                        manifest_data = resp.json()
                        plugins = manifest_data.get("plugins", [])
                        for p in plugins:
                            p["_source_repo"] = repo_url
                        return plugins
                except Exception as e:
                    logger.debug(f"Could not fetch {check_url}: {e}")

            return self._scan_github_api(user, repo, repo_url)
        return []

    def _scan_github_api(self, user: str, repo: str, original_repo_url: str) -> List[Dict]:
        api_url = f"https://api.github.com/repos/{user}/{repo}/contents"
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
                                        plugin_info["_download_url"] = f"https://github.com/{user}/{repo}/archive/refs/heads/main.zip"
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

                files_to_extract = []
                for zi in zip_infos:
                    if zi.filename.endswith('/'):
                        continue

                    if folder_path:
                        parts = zi.filename.split('/')
                        if len(parts) > 1 and parts[1] == folder_path:
                            files_to_extract.append(zi)
                    else:
                        files_to_extract.append(zi)

                for zi in files_to_extract:
                    parts = zi.filename.split('/')

                    rel_path = None
                    if folder_path:
                        try:
                            idx = parts.index(folder_path)
                            rel_path = "/".join(parts[idx+1:])
                        except ValueError:
                            continue
                    else:
                        if len(parts) > 1 and not zip_infos[0].filename.endswith('/'):
                            rel_path = zi.filename
                        elif len(parts) > 1:
                            rel_path = "/".join(parts[1:])
                        else:
                            rel_path = zi.filename

                    if rel_path:
                        target_file = dest_dir / rel_path
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        with target_file.open('wb') as f:
                            f.write(z.read(zi))

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
