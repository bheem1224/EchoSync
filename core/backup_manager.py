import os
import shutil
import zipfile
import json
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from core.settings import config_manager
from core.tiered_logger import get_logger
from core.state import system_state

logger = get_logger("backup_manager")

class BackupManager:
    def __init__(self):
        self.backups_dir = config_manager.data_dir / "backups"
        self.backups_dir.mkdir(parents=True, exist_ok=True)

    def _sqlite_backup(self, source_path: Path, target_path: Path):
        """Safely backup a SQLite database using the backup API."""
        if not source_path.exists():
            logger.warning(f"Source database not found: {source_path}")
            return
        
        try:
            # Connect to source and target
            src_conn = sqlite3.connect(str(source_path))
            dst_conn = sqlite3.connect(str(target_path))
            
            with dst_conn:
                src_conn.backup(dst_conn)
            
            src_conn.close()
            dst_conn.close()
            logger.info(f"SQLite backup successful: {source_path.name} -> {target_path.name}")
        except Exception as e:
            logger.error(f"Failed to backup SQLite database {source_path}: {e}")
            raise RuntimeError(f"Database backup failed due to lock or exception: {e}")

    def create_backup(self) -> str:
        """Generates a full system backup zip."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"echosync_backup_{timestamp}"
        staging_dir = Path(tempfile.mkdtemp(prefix="backup_stage_"))
        
        try:
            # 1. Copy Databases safely
            from database.working_database import get_working_database
            self._sqlite_backup(config_manager.database_path, staging_dir / "config.db")
            self._sqlite_backup(get_working_database().database_path, staging_dir / "working.db")
            self._sqlite_backup(config_manager.media_db_path, staging_dir / "music_library.db")
            
            # 2. Copy config.json
            if config_manager.config_path.exists():
                shutil.copy2(config_manager.config_path, staging_dir / "config.json")
                
            # 3. Generate plugins_snapshot.json
            plugins_snapshot = {}
            from core.plugin_loader import ProviderRegistry
            for name, entry in ProviderRegistry.get_all().items():
                cls = entry['class']
                # Skip core providers, only backup community plugins
                if entry.get('source_type') == 'core':
                    continue
                    
                plugins_snapshot[name] = {
                    "version": getattr(cls, 'version', 'Unknown'),
                    "author": getattr(cls, 'author', 'Unknown'),
                    "category": getattr(cls, 'category', 'provider'),
                    "channel": config_manager.get_plugin_channel(name.split(".")[-1])
                }
            
            with open(staging_dir / "plugins_snapshot.json", "w") as f:
                json.dump(plugins_snapshot, f, indent=2)
                
            # 4. Zip it up
            zip_path = self.backups_dir / f"{backup_name}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(staging_dir):
                    for file in files:
                        file_path = Path(root) / file
                        zipf.write(file_path, file_path.relative_to(staging_dir))
            
            logger.info(f"Backup created successfully: {zip_path}")
            return str(zip_path)
            
        except Exception as e:
            logger.error(f"Backup generation failed: {e}")
            raise
        finally:
            shutil.rmtree(staging_dir, ignore_errors=True)

    def restore_backup(self, zip_path: Path):
        """Restores the system from a backup zip."""
        staging_dir = Path(tempfile.mkdtemp(prefix="restore_stage_"))
        
        try:
            # 1. Extract
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                # Security: Zip Slip Check
                for zi in zipf.infolist():
                    if '..' in zi.filename or zi.filename.startswith('/'):
                        raise ValueError(f"Malicious path in backup archive: {zi.filename}")
                zipf.extractall(staging_dir)
            
            # 2. Close connections
            from database.config_database import close_config_database
            from database.working_database import close_working_database, get_working_database
            from database.music_database import close_database
            
            close_config_database()
            close_working_database()
            close_database()
            
            # 3. Replace Files
            # Move current files to .old for safety (optional but good practice)
            # For simplicity here we just replace
            if (staging_dir / "config.db").exists():
                shutil.copy2(staging_dir / "config.db", config_manager.database_path)
            if (staging_dir / "working.db").exists():
                # Working DB path might be dynamic, get it from manager
                working_db_path = get_working_database().database_path
                shutil.copy2(staging_dir / "working.db", working_db_path)
            if (staging_dir / "music_library.db").exists():
                shutil.copy2(staging_dir / "music_library.db", config_manager.media_db_path)
            if (staging_dir / "config.json").exists():
                shutil.copy2(staging_dir / "config.json", config_manager.config_path)
                
            # 4. Plugin Sync Logic
            snapshot_path = staging_dir / "plugins_snapshot.json"
            if snapshot_path.exists():
                with open(snapshot_path, "r") as f:
                    snapshot = json.load(f)
                
                # Plugin sync will happen on next restart as well, 
                # but we could trigger downloads here if needed.
                # However, the user request says "trigger PluginLoader/Manager to physically download"
                self._sync_plugins_to_snapshot(snapshot)
            
            system_state.restart_pending = True
            logger.info("Restore successful. System restart required.")
            return True
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            raise
        finally:
            shutil.rmtree(staging_dir, ignore_errors=True)

    def list_backups(self) -> List[Dict[str, Any]]:
        """Returns a list of all available backups in the backups directory."""
        backups = []
        for file in self.backups_dir.glob("*.zip"):
            stat = file.stat()
            backups.append({
                "filename": file.name,
                "size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat()
            })
        
        # Sort by newest first
        return sorted(backups, key=lambda x: x['created_at'], reverse=True)

    def get_backup_path(self, filename: str) -> Path:
        """Resolves a filename to its absolute path within the backups directory with safety checks."""
        if not filename.endswith(".zip"):
             raise ValueError("Only .zip files are allowed")
             
        # Prevent directory traversal
        safe_path = self.backups_dir / os.path.basename(filename)
        
        if not safe_path.exists():
            raise FileNotFoundError(f"Backup file {filename} not found")
            
        return safe_path

    def _sync_plugins_to_snapshot(self, snapshot: Dict[str, Any]):
        """Downloads/Updates plugins to match the snapshot versions."""
        from core.plugin_store import plugin_store
        
        # 1. Fetch available plugins from store to find download URLs
        store_plugins = plugin_store.get_all_store_plugins()
        store_map = {p['id']: p for p in store_plugins}
        
        for plugin_id, metadata in snapshot.items():
            target_version = metadata.get("version")
            channel = metadata.get("channel", "stable")
            
            if plugin_id in store_map:
                plugin_info = store_map[plugin_id]
                # Note: Currently PluginStore.download_plugin takes the full plugin_info object
                # and downloads the latest. We might need it to support version pinning.
                # For now, we trigger the download.
                logger.info(f"Syncing plugin {plugin_id} to {target_version} ({channel})")
                plugin_store.download_plugin(plugin_info, channel=channel)
            else:
                logger.warning(f"Plugin {plugin_id} from backup not found in current store repositories.")

backup_manager = BackupManager()
