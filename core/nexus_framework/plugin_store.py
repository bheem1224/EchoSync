import json
import logging
import zipfile
import requests
import re
import os
from pathlib import Path
from packaging import version
from typing import Any, List, Dict, Optional
from core.request_manager import RequestManager
from core.settings import config_manager

logger = logging.getLogger(__name__)

class PrivilegeEscalationError(Exception):
    def __init__(self, escalations):
        self.escalations = escalations
        super().__init__("Privilege escalation detected")

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
                    
                    clean_id = str(plugin_id)
                    # Dynamic split of namespace to build `{author}/{name}`
                    parts = clean_id.split('.')
                    if len(parts) >= 2:
                        author = parts[0]
                        name = ".".join(parts[1:])
                        folder_name = p.get("path") or f"plugins/{author}/{name}"
                    else:
                        folder_name = p.get("path") or clean_id.replace('.', '/')

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
                        
                    clean_id = str(plugin_id)
                    # Dynamic split of namespace to build `{author}/{name}`
                    parts = clean_id.split('.')
                    if len(parts) >= 2:
                        author = parts[0]
                        name = ".".join(parts[1:])
                        folder_name = p.get("path") or f"plugins/{author}/{name}"
                    else:
                        folder_name = p.get("path") or clean_id.replace('.', '/')

                    p["_folder_path"] = f"{subfolder}/{folder_name}" if subfolder else folder_name

                    repo_raw_base = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{p['_folder_path']}"

                    # STEP 1: Update the Scanner (Only fallback if missing)
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

            plugin["_installed"] = False
            plugin["installed_version"] = None
            plugin["installed_channel"] = "stable"
            plugin["beta_opt_in"] = None
            plugin["previous_version_path"] = None
            plugin["int_plugin_id"] = None
            
            absolute_install_path = None
            try:
                from database.config_database import get_config_database
                db = get_config_database()
                db_id = db.get_service_id(plugin_id)
                if db_id:
                    with db._get_connection() as conn:
                        c = conn.cursor()
                        c.execute("SELECT beta_opt_in, previous_version_path, plugin_id, absolute_install_path FROM services WHERE id=?", (db_id,))
                        row = c.fetchone()
                        if row:
                            plugin["beta_opt_in"] = row[0]
                            plugin["previous_version_path"] = row[1]
                            plugin["int_plugin_id"] = row[2]
                            absolute_install_path = row[3]
                            if row[0] == 1:
                                plugin["installed_channel"] = "beta"
            except Exception:
                pass
            
            active_manifest_path = None
            if absolute_install_path:
                comm_dir = Path(absolute_install_path)
                if comm_dir.exists():
                    comm_manifest = comm_dir / "manifest.json"
                    if comm_manifest.exists():
                        plugin["_installed"] = True
                        active_manifest_path = comm_manifest

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
                        # Fallback: Strip non-numeric characters (v, beta, etc) for a safer comparison
                        remote_numeric = re.sub(r'[^0-9.]', '', str(remote_version))
                        local_numeric = re.sub(r'[^0-9.]', '', str(local_version))
                        try:
                            if version.parse(remote_numeric) > version.parse(local_numeric):
                                plugin["update_available"] = True
                        except Exception:
                            # Final fallback: simple inequality
                            if remote_version != local_version:
                                plugin["update_available"] = True
                except Exception as e:
                    logger.debug(f"Error checking local version for {plugin_id}: {e}")
            
            # 2. Check for active Grace Period (Snapshots)
            from database.config_database import get_config_database
            snapshot = get_config_database().get_plugin_snapshot(plugin_id=plugin_id)
            if snapshot:
                # Convert unix timestamp to ISO format for frontend compatibility
                import datetime
                dt = datetime.datetime.fromtimestamp(snapshot['expires_at'], datetime.timezone.utc)
                plugin["archive_expiry_date"] = dt.isoformat()
            
        return all_plugins

    def install_plugin(self, plugin_info: Dict, channel: str = "stable", force_consent: bool = False) -> bool:
        """First-time installation of a plugin."""
        return self.download_plugin(plugin_info, channel, force_consent, is_update=False)

    def update_plugin(self, plugin_id: int, force_consent: bool = False) -> bool:
        """Downloads the update and hot swaps it."""
        from database.config_database import get_config_database
        db = get_config_database()
        with db._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT name, beta_opt_in FROM services WHERE plugin_id=?", (plugin_id,))
            row = c.fetchone()
            if not row:
                logger.error(f"Cannot update plugin: ID {plugin_id} not found in database.")
                return False
                
            plugin_name = row[0]
            local_beta = row[1]
            if local_beta is not None:
                channel = "beta" if local_beta else "stable"
            else:
                channel = "beta" if config_manager.get('ui.beta_plugin_ui', False) else "stable"
            
        store_plugins = self.get_all_store_plugins()
        plugin_info = next((p for p in store_plugins if p.get("id") == plugin_name or p.get("name") == plugin_name), None)
                
        if not plugin_info:
            logger.error(f"Cannot update plugin: {plugin_name} not found in store.")
            return False
            
        return self.download_plugin(plugin_info, channel, force_consent, is_update=True, target_plugin_id=plugin_id)

    def download_plugin(self, plugin_info: Dict, channel: str = "stable", force_consent: bool = False, is_update: bool = True, target_plugin_id: int = None) -> bool:
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

        # STEP 2: Update the Installer Logic (Manifest URL Priority)
        # Primary Route: Check if parsed plugin data contains the explicit URL for that channel
        if channel == "beta":
            download_url = plugin_info.get("beta_url") or plugin_info.get("download_url")
        else:
            download_url = plugin_info.get("download_url")

        # Fallback Route: If explicit URL is completely missing
        if not download_url:
            plugin_id = plugin_info.get("id", plugin_info.get("plugin_id", "unknown_plugin"))
            clean_id = str(plugin_id)
            parts = clean_id.split('.')
            if len(parts) >= 2:
                author = parts[0]
                name = ".".join(parts[1:])
                base_url = f"https://raw.githubusercontent.com/bheem1224/EchoSync/main/plugins/{author}/{name}"
            else:
                base_url = f"https://raw.githubusercontent.com/bheem1224/EchoSync/main/plugins/{clean_id.replace('.', '/')}"

            if channel == "beta":
                download_url = f"{base_url}/beta.zip"
            else:
                v = plugin_info.get("version", "1.0.0")
                download_url = f"{base_url}/releases/v{v}.zip"

        if not download_url:
            logger.error(f"No artifact URL found for plugin {plugin_info.get('id')} on channel {channel}")
            return False

        plugin_id = plugin_info.get("id", plugin_info.get("plugin_id", "unknown_plugin"))
        # Nexus Framework: Resolve nested path (dots to slashes)
        folder_path = plugin_info.get("path")
        if not folder_path:
            clean_id = str(plugin_id)
            folder_path = clean_id.replace('.', '/')
            
        dest_dir = self.plugins_dir / folder_path
        beta_dir = dest_dir / "beta"

        if channel == "beta":
            target_dir = beta_dir
        else:
            target_dir = dest_dir

        tmp_dir = self.plugins_dir / f"tmp_{folder_path.replace('/', '_')}"

        try:
            logger.info(f"Direct downloading {plugin_id} ({channel}) from {download_url}")
            req_mgr = RequestManager(provider="system")
            resp = req_mgr.get(download_url, timeout=30)
            
            if resp.status_code != 200:
                if channel == "beta" and plugin_info.get("download_url") and plugin_info.get("download_url") != download_url:
                    stable_url = plugin_info.get("download_url")
                    logger.warning(
                        f"Beta artifact unavailable for {plugin_id} at {download_url}; falling back to stable artifact {stable_url}"
                    )
                    resp = req_mgr.get(stable_url, timeout=30)
                    download_url = stable_url
                    if resp.status_code != 200:
                        logger.error(
                            f"Fallback stable artifact download also failed with status {resp.status_code}"
                        )
                        return False
                else:
                    logger.error(f"Artifact download failed with status {resp.status_code}")
                    return False

            if tmp_dir.exists(): shutil.rmtree(tmp_dir, ignore_errors=True)
            tmp_dir.mkdir(parents=True, exist_ok=True)

            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                tmp_file.write(resp.content)
                tmp_zip_path = tmp_file.name

            try:
                # Rollback Pathing: Right before extracting a new update
                if is_update and target_plugin_id:
                    try:
                        from database.config_database import get_config_database
                        db = get_config_database()
                        with db._get_connection() as conn:
                            c = conn.cursor()
                            c.execute("SELECT absolute_install_path FROM services WHERE plugin_id=?", (target_plugin_id,))
                            row = c.fetchone()
                            if row and row[0]:
                                c.execute("UPDATE services SET previous_version_path=? WHERE plugin_id=?", (row[0], target_plugin_id))
                                conn.commit()
                    except Exception as e:
                        logger.error(f"Failed to set previous_version_path: {e}")

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

                with open(manifest_file, "r") as f:
                    new_manifest = json.load(f)

                # Strict Manifest Parsing (Task 2)
                required_fields = ["author", "name", "description", "version", "type"]
                missing = [field for field in required_fields if not new_manifest.get(field)]
                if missing:
                    logger.error(f"Manifest validation failed: missing required fields {missing}")
                    return False

                # Store parsed and strict fields for later DB insertion
                manifest_author = new_manifest["author"]
                manifest_name = new_manifest["name"]
                # DO NOT lowercase here to avoid filesystem mismatch with registry
                strict_namespace = f"{manifest_author}.{manifest_name}"
                manifest_desc = new_manifest["description"]
                manifest_version = new_manifest["version"]
                manifest_type = new_manifest["type"]
                
                # Dynamically calculate target directories based on strict_namespace
                dest_dir = self.plugins_dir / manifest_author / manifest_name
                beta_dir = dest_dir / "beta"
                if channel == "beta":
                    target_dir = beta_dir
                else:
                    target_dir = dest_dir

                # Security: Pre-Flight Consent Check for Privilege Escalation
                if not force_consent:
                    # Compare against what is CURRENTLY in target_dir
                    # or fall back to the base directory if target_dir (beta) doesn't exist yet
                    current_path = target_dir if target_dir.exists() else dest_dir
                    current_manifest_file = current_path / "manifest.json"
                    
                    if current_manifest_file.exists():
                        try:
                            with open(current_manifest_file, "r") as f:
                                old_manifest = json.load(f)
                            with open(manifest_file, "r") as f:
                                new_manifest = json.load(f)
                            
                            old_perms = old_manifest.get("permissions", {})
                            new_perms = new_manifest.get("permissions", {})
                            
                            escalations = {}
                            
                            # 1. Check privileged_mode escalation
                            if new_perms.get("privileged_mode") and not old_perms.get("privileged_mode"):
                                escalations["privileged_mode"] = True
                                
                            # 2. Check network_domains expansion
                            old_domains = set(old_perms.get("network_domains", []))
                            new_domains = set(new_perms.get("network_domains", []))
                            added_domains = list(new_domains - old_domains)
                            if added_domains:
                                escalations["new_domains"] = added_domains
                                
                            if escalations:
                                logger.warning(f"Aborting update for {plugin_id}: Privilege escalation detected. Requires user consent.")
                                if tmp_dir.exists(): shutil.rmtree(tmp_dir, ignore_errors=True)
                                raise PrivilegeEscalationError(escalations)
                        except PrivilegeEscalationError:
                            raise
                        except Exception as e:
                            logger.error(f"Error during pre-flight manifest check: {e}")

                # Task 4: Inject Verified Source Block and Enforce Target Version
                try:
                    with open(manifest_file, "r") as f:
                        manifest_data = json.load(f)
                    
                    # This allows official plugins to bypass the AST scanner safely.
                    if plugin_info.get("_source_repo") == self.default_repo:
                        manifest_data["verified_source"] = "official"
                        manifest_data["author"] = "EchoSync"
                    
                    # Stamping correct version into manifest prevents infinite update loops
                    # if the zip artifact has a lagging version string
                    if channel == "beta" and plugin_info.get("beta_version"):
                        manifest_data["version"] = plugin_info.get("beta_version")
                    elif channel in ["stable", "release"] and plugin_info.get("version"):
                        manifest_data["version"] = plugin_info.get("version")
                    
                    with open(manifest_file, "w") as f:
                        json.dump(manifest_data, f, indent=2)
                    logger.info(f"Injected manifest metadata for {plugin_id}")
                except Exception as e:
                    logger.error(f"Failed to inject manifest metadata for {plugin_id}: {e}")

                # Task 3: Atomic Swap
                if channel == "stable" and beta_dir.exists():
                    shutil.rmtree(beta_dir, ignore_errors=True)

                backup_dir = None
                if target_dir.exists():
                    backup_dir = target_dir.parent / f"{target_dir.name}_backup"
                    if backup_dir.exists():
                        shutil.rmtree(backup_dir, ignore_errors=True)
                    try:
                        os.rename(str(target_dir), str(backup_dir))
                        logger.info(f"Backed up target_dir to {backup_dir}")
                    except Exception as backup_err:
                        logger.warning(f"Failed to backup target_dir, falling back to direct removal: {backup_err}")
                        shutil.rmtree(target_dir, ignore_errors=True)
                        backup_dir = None

                try:
                    if not target_dir.parent.exists():
                        target_dir.parent.mkdir(parents=True, exist_ok=True)
                    os.rename(str(tmp_dir), str(target_dir))
                    logger.info(f"Successfully installed {plugin_id} artifact via atomic swap")
                    if backup_dir and backup_dir.exists():
                        shutil.rmtree(backup_dir, ignore_errors=True)
                except Exception as swap_err:
                    logger.error(f"Atomic swap failed, rolling back: {swap_err}")
                    if backup_dir and backup_dir.exists():
                        os.rename(str(backup_dir), str(target_dir))
                    raise swap_err

                # Task 1: Localized Dependency Installation (Micro-Venv)
                requirements_file = target_dir / "requirements.txt"
                if requirements_file.exists():
                    logger.info(f"Found requirements.txt for {plugin_id}, installing into micro-venv")
                    micro_venv_dir = target_dir / "micro-venv"
                    import subprocess
                    try:
                        # Use uv pip install --target to isolate dependencies
                        subprocess.run(
                            ["uv", "pip", "install", "--target", str(micro_venv_dir), "-r", str(requirements_file)],
                            check=True,
                            capture_output=True,
                            text=True
                        )
                        logger.info(f"Successfully installed micro-venv dependencies for {plugin_id}")
                    except subprocess.CalledProcessError as e:
                        logger.error(f"Failed to install micro-venv dependencies for {plugin_id}: {e.stderr}")
                        # Depending on strictness, we could return False here, but we will let it continue
                        # and log the error. Usually a broken requirements.txt means the plugin might fail to load.


                # Task 5: Persist Channel Preference (Nexus normalization)
                clean_id = str(plugin_id)
                config_manager.set(f'plugins.{clean_id}.channel', channel)
                logger.info(f"Persisted channel '{channel}' for plugin {clean_id}")

                # Task 6: Blue/Green Namespace Shifting (Only during updates)
                if is_update:
                    if target_plugin_id:
                        int_plugin_id = target_plugin_id
                    else:
                        from database.config_database import get_config_database
                        db = get_config_database()
                        with db._get_connection() as conn:
                            c = conn.cursor()
                            c.execute("SELECT plugin_id FROM services WHERE LOWER(name)=LOWER(?)", (clean_id,))
                            row = c.fetchone()
                            if not row:
                                raise ValueError(f"Plugin {clean_id} not found in services table")
                            int_plugin_id = row[0]

                    if channel == "beta":
                        try:
                            self._fork_namespace(int_plugin_id)
                            logger.info(f"Forked data namespace for {int_plugin_id} (Blue/Green)")
                        except Exception as e:
                            logger.error(f"Failed to fork namespace for {int_plugin_id}: {e}")
                    elif channel == "stable":
                        try:
                            self._cutover_namespace(int_plugin_id)
                            logger.info(f"Executed data cutover for {int_plugin_id} (Stable Promotion)")
                        except Exception as e:
                            logger.error(f"Failed to cutover namespace for {int_plugin_id}: {e}")




                # State Synchronization: Synchronize with the authoritative SQLite registry
                try:
                    from database.config_database import get_config_database
                    import binascii
                    db = get_config_database()
                    
                    is_official = "raw.githubusercontent.com/bheem1224/EchoSync" in download_url
                    manifest_verified = 1 if (is_official or new_manifest.get("verified_source") == "official") else 0
                    manifest_privileged = 1 if (new_manifest.get("privileged") is True or new_manifest.get("permissions", {}).get("privileged_mode") is True) else 0
                    
                    manifest_permissions = '[]'
                    m_perms = new_manifest.get("permissions")
                    if m_perms is not None:
                        if isinstance(m_perms, list):
                            manifest_permissions = json.dumps(m_perms)
                        elif isinstance(m_perms, str):
                            manifest_permissions = m_perms
                        elif isinstance(m_perms, dict):
                            manifest_permissions = json.dumps(m_perms)
                    
                    computed_plugin_id = target_plugin_id if target_plugin_id else binascii.crc32(strict_namespace.lower().encode('utf-8')) & 0xFFFFFFFF

                    db.register_service(
                        name=manifest_name,
                        service_type=manifest_type,
                        description=manifest_desc,
                        absolute_install_path=str(target_dir.resolve()),
                        plugin_id=computed_plugin_id,
                        version=manifest_version,
                        beta_opt_in=1 if channel == "beta" else 0,
                        verified_source=manifest_verified,
                        privileged_mode=manifest_privileged,
                        permissions=manifest_permissions
                    )
                    
                    logger.info(f"Synchronized database state for plugin {strict_namespace} (CRC32: {computed_plugin_id})")
                except Exception as e:
                    logger.error(f"Failed to synchronize database state for {strict_namespace}: {e}")

                # Hot-Swap Architecture: Perform Zero-Downtime Reload (Only during updates)
                if is_update:
                    try:
                        from core.nexus_framework.plugin_loader import PluginLoader
                        app_root = Path(__file__).parent.parent
                        loader = PluginLoader(app_root)
                        loader.reload_plugin(int_plugin_id)
                        logger.info(f"Live-swap successful for {plugin_id} (int: {int_plugin_id}).")
                    except Exception as e:
                        logger.error(f"Live-swap failed for {plugin_id}: {e}")
                        system_state.restart_pending = True
                        raise RuntimeError(f"Live-swap failed: {e}")
                else:
                    logger.info(f"Fresh installation complete for {plugin_id}. Hot-swap skipped.")
                    try:
                        import binascii
                        plugin_id_int = target_plugin_id if target_plugin_id else binascii.crc32(strict_namespace.lower().encode('utf-8')) & 0xFFFFFFFF
                        from core.nexus_framework.plugin_loader import _sync_ui_components_to_db
                        _sync_ui_components_to_db(plugin_id_int, str(target_dir.resolve()))
                        logger.info(f"Dynamically discovered and registered UI components for fresh installed plugin {strict_namespace}")
                    except Exception as ui_err:
                        logger.error(f"Failed to run UI component discovery for fresh installed plugin {strict_namespace}: {ui_err}")

                return True

            finally:
                if os.path.exists(tmp_zip_path): os.remove(tmp_zip_path)
                if tmp_dir.exists(): shutil.rmtree(tmp_dir, ignore_errors=True)

        except Exception as e:
            logger.error(f"Fatal error during artifact installation: {e}", exc_info=True)
            return False

    def _cleanup_beta_subfolder(self, folder_id: str) -> bool:
        import shutil
        # Convert dots to slashes for nested path support
        path_name = folder_id.replace('.', '/')
        beta_path = self.plugins_dir / path_name / "beta"
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

    def uninstall_plugin(self, plugin_id: int) -> bool:
        import re
        import shutil
        import os
        import sys
        from pathlib import Path
        
        try:
            from database.working_database import get_working_database
            from database.config_database import get_config_database
            db = get_config_database()
            
            # 1. Disable and remove jobs
            try:
                from core.job_queue import job_queue
                job_queue.kill_jobs_by_plugin(plugin_id)
            except Exception as e:
                logger.warning(f"Failed to kill workers for {plugin_id}: {e}")

            # 2. Get install path and modules to purge before deleting services row
            absolute_install_path = None
            modules_to_purge = set()
            clean_id = str(plugin_id)
            
            with db._get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT name, absolute_install_path, loaded_modules FROM services WHERE plugin_id=?", (plugin_id,))
                row = c.fetchone()
                if row:
                    clean_id = row['name']
                    absolute_install_path = row['absolute_install_path']
                    loaded_modules_str = row['loaded_modules']
                    if loaded_modules_str:
                        import json
                        try:
                            modules_to_purge.update(json.loads(loaded_modules_str))
                        except Exception:
                            pass

            # Unregister health checks for the plugin
            try:
                from core.health_check import health_check_registry
                # Try unregistering both full clean_id and short name
                health_check_registry.unregister_check(clean_id)
                short_name = clean_id.split('.')[-1].split('@')[0]
                health_check_registry.unregister_check(short_name)
                
                # Unregister the jobs from job_queue
                from core.job_queue import job_queue
                job_queue.unregister_job(f"health_check_{clean_id}")
                job_queue.unregister_job(f"health_check_{short_name}")
            except Exception as e:
                logger.warning(f"Failed to unregister health check for {clean_id}: {e}")

            # Fallback/Additional check: inspect sys.modules
            if absolute_install_path:
                plugin_path_str = str(Path(absolute_install_path).resolve())
                for mod_name, mod in list(sys.modules.items()):
                    mod_file = getattr(mod, '__file__', None)
                    if mod_file and mod_file.startswith(plugin_path_str):
                        modules_to_purge.add(mod_name)

            for module_name in modules_to_purge:
                if module_name in sys.modules:
                    sys.modules.pop(module_name)
                    logger.debug(f"Hot-unloaded zombie module: {module_name}")

            # 3. Dynamic Database and Config Teardown
            safe_id = re.sub(r'[^a-zA-Z0-9_]', '_', str(plugin_id).replace('.', '_')).lower()
            prefix = f"plugin_{safe_id}_%"
            
            try:
                db_engines = []
                w_db = get_working_database()
                if hasattr(w_db, 'engine'): db_engines.append(w_db.engine)
                c_db = get_config_database()
                if hasattr(c_db, 'engine'): db_engines.append(c_db.engine)

                for db_engine in db_engines:
                    with db_engine.connect() as conn:
                        try:
                            from sqlalchemy import text
                            tables = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE :prefix"), {"prefix": prefix}).fetchall()
                            for (table_name,) in tables:
                                if table_name in ("plugin_state_kvs", "config_kvs"):
                                    continue
                                conn.execute(text(f"DROP TABLE IF EXISTS \"{table_name}\""))
                            conn.commit()
                        except Exception:
                            pass
            except Exception as e:
                logger.warning(f"Failed to teardown dynamic tables for {plugin_id}: {e}")

            # 4. Delete config keys, UI components, and remove from services table
            with db._get_connection() as conn:
                c = conn.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS config_kvs (plugin_id INTEGER, key TEXT, value TEXT, is_sensitive INTEGER, created_at INTEGER, updated_at INTEGER, PRIMARY KEY(plugin_id, key))")
                c.execute("DELETE FROM config_kvs WHERE plugin_id=?", (plugin_id,))
                # Sprint 6: Explicit UI Registry teardown (do NOT rely on FK CASCADE)
                c.execute("DELETE FROM ui_components WHERE plugin_id=?", (plugin_id,))
                logger.info(f"[UIRegistry] Purged UI components for plugin {plugin_id}")
                c.execute("DELETE FROM services WHERE plugin_id=?", (plugin_id,))
                conn.commit()


            # 4b. Delete working state KVS entries to prevent orphaned data
            try:
                from database.working_database import get_working_database
                w_db = get_working_database()
                with w_db.session_scope() as session:
                    from sqlalchemy import text
                    session.execute(text("DELETE FROM plugin_state_kvs WHERE plugin_id = :pid"), {"pid": str(plugin_id)})
            except Exception as e:
                logger.warning(f"Error purging working state KVS for {plugin_id}: {e}")

            # Remove from JSON config if exists
            try:
                from core.settings import config_manager
                all_settings = config_manager.get_settings()
                clean_target = clean_id.replace('EchoSync.', '').replace('core.', '').replace('plugin.', '').lower()
                if 'plugins' in all_settings and clean_target in all_settings['plugins']:
                    del all_settings['plugins'][clean_target]
                    config_manager.save_settings(all_settings)
            except Exception as e:
                logger.warning(f"Error removing from json config: {e}")

            # 5. Delete physical folder
            if absolute_install_path:
                dest_dir = Path(absolute_install_path)
                if dest_dir.exists():
                    shutil.rmtree(dest_dir, ignore_errors=True)
                    logger.info(f"Successfully deleted plugin directory: {dest_dir}")
            else:
                dest_dir = self.plugins_dir / str(plugin_id)
                if dest_dir.exists():
                    shutil.rmtree(dest_dir, ignore_errors=True)

        except Exception as e:
            logger.error(f"Failed during uninstall for {plugin_id}: {e}")
            return False
            
        return True

    def get_plugin_channel(self, plugin_id: int) -> str:
        """Get the active update channel ('stable' or 'beta') for a plugin."""
        try:
            from database.config_database import get_config_database
            db = get_config_database()
            with db._get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT beta_opt_in FROM services WHERE plugin_id=?", (plugin_id,))
                row = c.fetchone()
                if row:
                    local_beta = row[0]
                    if local_beta is not None:
                        return "beta" if local_beta else "stable"
        except Exception:
            pass
        return "beta" if config_manager.get('ui.beta_plugin_ui', False) else "stable"

    def _fork_namespace(self, plugin_id: int):
        """The Fork: Copies current stable DB file and KVS to a @beta side-car."""
        from database.config_database import get_config_database
        from database.working_database import get_working_database
        import os
        import shutil

        beta_id = f"{plugin_id}@beta"

        # 1. Fork Config KVS
        db_config = get_config_database()
        with db_config._get_connection() as conn:
            c = conn.cursor()
            c.execute("CREATE TABLE IF NOT EXISTS config_kvs (plugin_id INTEGER, key TEXT, value TEXT, is_sensitive INTEGER, created_at INTEGER, updated_at INTEGER, PRIMARY KEY(plugin_id, key))")
            c.execute("DELETE FROM config_kvs WHERE plugin_id=?", (beta_id,))
            c.execute("INSERT INTO config_kvs (plugin_id, key, value, is_sensitive) SELECT ?, key, value, is_sensitive FROM config_kvs WHERE plugin_id=?", (beta_id, plugin_id))
            conn.commit()

        # 2. Fork Working State KVS
        db_working = get_working_database()
        with db_working.session_scope() as session:
            from sqlalchemy import text
            session.execute(text("DELETE FROM plugin_state_kvs WHERE plugin_id=:beta"), {"beta": beta_id})
            session.execute(text("INSERT INTO plugin_state_kvs (plugin_id, key, value, is_sensitive) SELECT :beta, key, value, is_sensitive FROM plugin_state_kvs WHERE plugin_id=:orig"), {"beta": beta_id, "orig": plugin_id})

        # 3. Fork File
        stable_db_path = f"/data/plugins/data/{plugin_id}.db"
        beta_db_path = f"/data/plugins/data/{plugin_id}@beta.db"
        if os.path.exists(stable_db_path):
            shutil.copy2(stable_db_path, beta_db_path)

    def _abort_namespace(self, plugin_id: int):
        """The Abort: Physically deletes the @beta side-car file and KVS."""
        from database.config_database import get_config_database
        from database.working_database import get_working_database
        import os

        beta_id = f"{plugin_id}@beta"

        # 1. Abort Config KVS
        db_config = get_config_database()
        with db_config._get_connection() as conn:
            c = conn.cursor()
            c.execute("CREATE TABLE IF NOT EXISTS config_kvs (plugin_id INTEGER, key TEXT, value TEXT, is_sensitive INTEGER, created_at INTEGER, updated_at INTEGER, PRIMARY KEY(plugin_id, key))")
            c.execute("DELETE FROM config_kvs WHERE plugin_id=?", (beta_id,))
            conn.commit()

        # 2. Abort Working State KVS
        db_working = get_working_database()
        with db_working.session_scope() as session:
            from sqlalchemy import text
            session.execute(text("DELETE FROM plugin_state_kvs WHERE plugin_id=:beta"), {"beta": beta_id})

        # 3. Abort File
        beta_db_path = f"/data/plugins/data/{plugin_id}@beta.db"
        if os.path.exists(beta_db_path):
            try:
                os.remove(beta_db_path)
            except OSError:
                pass

    def _cutover_namespace(self, plugin_id: int):
        """The Cutover: Archives current stable and promotes @beta to active."""
        from database.config_database import get_config_database
        from database.working_database import get_working_database
        import os
        import shutil
        
        beta_id = f"{plugin_id}@beta"
        archive_id = f"{plugin_id}@archive"
        
        # 1. Cutover Config KVS
        db_config = get_config_database()
        with db_config._get_connection() as conn:
            c = conn.cursor()
            # Ensure table exists before querying
            c.execute("CREATE TABLE IF NOT EXISTS config_kvs (plugin_id INTEGER, key TEXT, value TEXT, is_sensitive INTEGER, created_at INTEGER, updated_at INTEGER, PRIMARY KEY(plugin_id, key))")
            # Cleanup old archive
            c.execute("DELETE FROM config_kvs WHERE plugin_id=?", (archive_id,))
            
            # Check if beta exists
            c.execute("SELECT 1 FROM config_kvs WHERE plugin_id=? LIMIT 1", (beta_id,))
            has_beta = c.fetchone() is not None
            
            if has_beta:
                # Beta -> Stable: Rename primary to archive, then beta to primary
                c.execute("UPDATE config_kvs SET plugin_id=? WHERE plugin_id=?", (archive_id, plugin_id))
                c.execute("UPDATE config_kvs SET plugin_id=? WHERE plugin_id=?", (plugin_id, beta_id))
            else:
                # Stable -> Stable: Copy primary to archive
                c.execute("""
                    INSERT INTO config_kvs (plugin_id, key, value, is_sensitive)
                    SELECT ?, key, value, is_sensitive FROM config_kvs WHERE plugin_id=?
                """, (archive_id, plugin_id))
            conn.commit()

        # 2. Cutover Working State KVS
        db_working = get_working_database()
        with db_working.session_scope() as session:
            from sqlalchemy import text
            session.execute(text("DELETE FROM plugin_state_kvs WHERE plugin_id=:arch"), {"arch": archive_id})
            
            res = session.execute(text("SELECT 1 FROM plugin_state_kvs WHERE plugin_id=:beta LIMIT 1"), {"beta": beta_id}).fetchone()
            if res:
                session.execute(text("UPDATE plugin_state_kvs SET plugin_id=:arch WHERE plugin_id=:orig"), {"arch": archive_id, "orig": plugin_id})
                session.execute(text("UPDATE plugin_state_kvs SET plugin_id=:orig WHERE plugin_id=:beta"), {"orig": plugin_id, "beta": beta_id})
            else:
                session.execute(text("""
                    INSERT INTO plugin_state_kvs (plugin_id, key, value, is_sensitive)
                    SELECT :arch, key, value, is_sensitive FROM plugin_state_kvs WHERE plugin_id=:orig
                """), {"arch": archive_id, "orig": plugin_id})

        # 3. Cutover Physical Database File
        stable_db_path = f"/data/plugins/data/{plugin_id}.db"
        beta_db_path = f"/data/plugins/data/{plugin_id}@beta.db"
        archive_db_path = f"/data/plugins/data/{plugin_id}@archive.db"
        
        # Ensure directories exist
        os.makedirs(os.path.dirname(stable_db_path), exist_ok=True)

        if os.path.exists(beta_db_path):
            if os.path.exists(stable_db_path):
                # Archive current stable
                try:
                    if os.path.exists(archive_db_path):
                        os.remove(archive_db_path)
                    os.rename(stable_db_path, archive_db_path)
                except OSError:
                    pass
            try:
                os.rename(beta_db_path, stable_db_path)
            except OSError:
                pass
        else:
            # Stable to Stable: copy current to archive
            if os.path.exists(stable_db_path):
                try:
                    if os.path.exists(archive_db_path):
                        os.remove(archive_db_path)
                    shutil.copy2(stable_db_path, archive_db_path)
                except (OSError, IOError):
                    pass

    def rollback_plugin(self, plugin_id: int) -> bool:
        """Restores a plugin to its previous stable version by aborting beta context."""
        import shutil
        import os
        from database.config_database import get_config_database
        
        db = get_config_database()
        with db._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT previous_version_path, absolute_install_path FROM services WHERE plugin_id=?", (plugin_id,))
            row = c.fetchone()
            if not row:
                logger.error(f"Cannot rollback plugin {plugin_id}: Not found in DB.")
                return False
                
            prev_path = row[0]
            curr_path = row[1]
            
            c.execute("UPDATE services SET beta_opt_in=0 WHERE plugin_id=?", (plugin_id,))
            if prev_path:
                c.execute("UPDATE services SET absolute_install_path=? WHERE plugin_id=?", (prev_path, plugin_id))
            conn.commit()

        # 1. Abort side-car data
        try:
            self._abort_namespace(plugin_id)
        except Exception as e:
            logger.error(f"Failed to abort data namespace for {plugin_id}: {e}")

        # 2. Cleanup beta subfolder based on current absolute install path
        if curr_path:
            p = Path(curr_path)
            if p.name == "beta":
                shutil.rmtree(p, ignore_errors=True)
                logger.info(f"Removed beta folder at {p}")
            else:
                beta_path = p / "beta"
                if beta_path.exists():
                    shutil.rmtree(beta_path, ignore_errors=True)
                    logger.info(f"Removed leftover beta folder at {beta_path}")

        from core.state import system_state
        system_state.restart_pending = True
        return True




plugin_store = PluginStore()
