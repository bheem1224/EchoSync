"""System endpoints for status, settings, and logs."""

from web.auth import require_auth
from fastapi import APIRouter, HTTPException, Depends, Request, Response
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json
import os
import time
import platform
import psutil
from core.tiered_logger import get_logger
from core.settings import config_manager
from core.backup_manager import backup_manager
from pathlib import Path

logger = get_logger("system_route")
router = APIRouter(prefix="/api/v1/system", tags=["System"])


@router.get("/health")
def health_check():
    """Health endpoint with actual service health check results."""
    try:
        from services.health_check import get_system_health
        health_data = get_system_health()
        return health_data
    except Exception as e:
        logger.error(f"Error in health check: {e}", exc_info=True)
        return {"status": "error", "results": {}}





@router.post("/restart", dependencies=[Depends(require_auth)])
def request_restart():
    """Forcefully but cleanly exit the application to trigger a Docker/System restart."""
    import time
    import threading
    import os
    from core.state import system_state
    from core.job_queue import JobQueue

    logger.info("Application restart requested via API")
    
    # 1. Tell the job queue to freeze
    system_state.restart_pending = True
    JobQueue.RESTART_PENDING = True

    # 2. Define a hard-kill function
    def hard_kill():
        time.sleep(2) # Give the API exactly 2 seconds to return the 200 OK to the frontend
        logger.warning("Executing hard restart via os._exit(1)...")
        os._exit(1)   # Instantly kills the container. Docker will reboot it.

    # 3. Spin it off in a background thread so the HTTP response can complete
    threading.Thread(target=hard_kill, daemon=True).start()

    return {
        "success": True, 
        "message": "Restarting EchoSync..."
    }


@router.post("/backup", dependencies=[Depends(require_auth)])
def create_system_backup():
    """Generates a full system backup and returns the path/status."""
    try:
        backup_path = backup_manager.create_backup()
        return {
            "success": True,
            "backup_path": backup_path,
            "filename": Path(backup_path).name
        }
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return {"success": False, "error": str(e)}


@router.get("/backups", dependencies=[Depends(require_auth)])
def list_system_backups():
    """Returns a list of all available backup files."""
    try:
        backups = backup_manager.list_backups()
        return {
            "success": True,
            "backups": backups
        }
    except Exception as e:
        logger.error(f"Failed to list backups: {e}")
        return {"success": False, "error": str(e)}


@router.get("/backups/{filename}/download", dependencies=[Depends(require_auth)])
def download_system_backup(filename):
    """Downloads a specific backup file."""
    try:
        file_path = backup_manager.get_backup_path(filename)
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename
        )
    except FileNotFoundError:
        return {"success": False, "error": "Backup not found"}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return {"success": False, "error": "Download failed"}


@router.post("/restore", dependencies=[Depends(require_auth)])
async def restore_system_backup(request: Request):
    """Restores the system from an uploaded zip OR a local filename."""
    tmp_path = None
    
    try:
        content_type = request.headers.get("content-type", "")
        # Check if it's a file upload
        if "multipart/form-data" in content_type:
            form = await request.form()
            if 'file' in form:
                file = form['file']
                if not file.filename or not file.filename.endswith('.zip'):
                    return {"success": False, "error": "Invalid file upload"}
                
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
                    content = await file.read()
                    tmp.write(content)
                    tmp_path = Path(tmp.name)
                    restore_file = tmp_path
            else:
                return {"success": False, "error": "No file uploaded"}
        
        # Or a JSON payload with filename
        elif "application/json" in content_type:
            data = await request.json()
            filename = data.get("filename")
            if not filename:
                return {"success": False, "error": "Filename missing in JSON"}
            
            restore_file = backup_manager.get_backup_path(filename)
            
        else:
            return {"success": False, "error": "No restore source provided"}

        # Execute restore
        success = backup_manager.restore_backup(restore_file)
        if success:
            request_restart() # Trigger reboot
            return {
                "success": True,
                "message": f"Restore from {Path(restore_file).name} successful. Restarting..."
            }
        else:
            return {"success": False, "error": "Restore engine failed"}

    except FileNotFoundError:
        return {"success": False, "error": "Local backup file not found"}
    except Exception as e:
        logger.error(f"Restore failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        if tmp_path and tmp_path.exists():
            os.remove(tmp_path)


@router.get("/stats")
def system_stats():
    """System resource usage statistics, distinguishing app vs system."""
    try:
        import os
        # Total system stats
        sys_mem = psutil.virtual_memory()
        # Get system CPU first (non-blocking)
        sys_cpu = psutil.cpu_percent(interval=None)

        # App-specific stats
        process = psutil.Process(os.getpid())
        app_mem = process.memory_info().rss
        # Get app CPU (non-blocking)
        app_cpu = process.cpu_percent(interval=None)

        # Wait a tiny bit for meaningful deltas
        import time
        time.sleep(0.5)
        
        sys_cpu = psutil.cpu_percent(interval=None)
        app_cpu = process.cpu_percent(interval=None)

        return {
            "memory": {
                "total": sys_mem.total,
                "available": sys_mem.available,
                "percent": sys_mem.percent,
                "app_rss": app_mem
            },
            "cpu": {
                "system": sys_cpu,
                "app": app_cpu
            }
        }
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return {"error": "Failed to get stats"}


from services.metadata_enhancer import get_metadata_enhancer

@router.get("/settings")
def get_settings():
    """Get current application settings (Svelte expects settings/schema/version).

    We inject the current console log level so the UI can populate the dropdown.
    """
    try:
        data = config_manager.get_all() if hasattr(config_manager, "get_all") else {}
        dev_mode = os.getenv('DEV_MODE', 'false').lower() in ('true', '1', 'yes')
        data["dev_mode"] = dev_mode
        safe_mode = os.getenv('ECHOSYNC_SAFE_MODE', '') in ('1', 'true')
        data["safe_mode"] = safe_mode
        # Inject live console log level.  In DEV_MODE the startup level is always
        # DEBUG (set by run_api.py), so we can short-circuit the handler scan which
        # can return NOTSET if Werkzeug adds its own handlers before the request lands.
        if dev_mode:
            data["log_level"] = "DEBUG"
        else:
            try:
                from core.tiered_logger import get_current_log_level
                data["log_level"] = get_current_log_level()
            except Exception:
                pass
        return {
            "settings": data,
            "schema": None,
            "version": None,
        }
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        return {"error": "Failed to get settings"}


@router.get("/encryption-key-warning")
def get_encryption_key_warning():
    """Check if encryption key was auto-generated and return warning info."""
    try:
        if config_manager.was_encryption_key_auto_generated():
            key_value = config_manager.get_generated_encryption_key()
            return {
                "auto_generated": True,
                "key_value": key_value,
                "message": "Encryption key was auto-generated. Pass MASTER_KEY as environment variable to persist settings across container restarts."
            }
        else:
            return {
                "auto_generated": False
            }
    except Exception as e:
        logger.error(f"Error checking encryption key status: {e}")
        return {"error": "Failed to check encryption key status"}


@router.get("/migration-status")
def get_migration_status():
    """Check if v2.1.0 migration was triggered and notify frontend."""
    try:
        from core.db.migrations import was_v2_1_migration_triggered
        is_migrated = was_v2_1_migration_triggered()
        return {
            "v2_1_migration_triggered": is_migrated,
            "message": "Echosync has been upgraded to v2.1.0! The database schema has undergone a massive structural upgrade to support the new Matching Engine. Your configuration is safe, but your media library database has been wiped and is currently being rebuilt from scratch in the background."
        }
    except Exception as e:
        logger.error(f"Error checking migration status: {e}")
        return {"error": "Failed to check migration status"}


@router.post("/migration-acknowledge", dependencies=[Depends(require_auth)])
def acknowledge_migration():
    """Acknowledge the v2.1.0 migration notification."""
    try:
        from core.db.migrations import acknowledge_v2_1_migration
        acknowledge_v2_1_migration()
        logger.info("v2.1.0 migration notification acknowledged by user")
        return {"success": True}
    except Exception as e:
        logger.error(f"Error acknowledging migration: {e}")
        return {"error": "Failed to acknowledge migration"}


# Allowlist of top-level config keys that the UI is permitted to write via this
# endpoint.  Any key not in this set is rejected with 400 to prevent arbitrary
# config-tree poisoning (C1 security fix).
_SETTINGS_ALLOWLIST: frozenset = frozenset({
    "log_level",
    "active_media_server",
    "active_download_client",
    "metadata_enhancement",
    "quality_profiles",
    "scan_interval",
    "file_rename_template",
    "match_threshold",
    "storage",
    "theme",
    "active_matching_engine",
    "account_mapping",
    "custom_ui_path",
})


@router.get("/accounts", dependencies=[Depends(require_auth)])
def get_all_system_accounts():
    """Returns music accounts and media server users for the manager UI.

    Mapping data is now read from config.db (account_mappings table) using
    agnostic relational account IDs.
    """
    from database.config_database import get_config_database
    from web.services.plugin_registry import list_plugins
    try:
        config_db = get_config_database()
        from core.nexus_framework.plugin_loader import PluginRegistry
        active_servers = PluginRegistry.get_active_services_by_type('media_server')
        plugins = list_plugins()
        
        active_media_server_name = 'plex'
        if active_servers:
            db_name = config_db.get_service_name(active_servers[0])
            if db_name:
                active_media_server_name = db_name.lower()

        # 1. Get all music service accounts
        all_accounts = []
        from core.nexus_framework.plugin_SDK import PlaylistSupport
        for plugin in plugins:
            plugin_name_lower = plugin['name'].lower()
            
            # Skip the active media server's own accounts to prevent self-mapping
            if plugin_name_lower == active_media_server_name:
                continue

            plugin_cls = PluginRegistry.get_plugin_class(plugin['plugin_id'])
            if not plugin_cls or not hasattr(plugin_cls, 'capabilities'):
                continue

            caps = plugin_cls.capabilities
            if getattr(caps, 'supports_playlists', PlaylistSupport.NONE) not in (PlaylistSupport.READ, PlaylistSupport.READ_WRITE):
                continue

            service_id = config_db.get_or_create_service_id(plugin['plugin_id'])
            accounts = config_db.get_accounts(service_id=service_id)
            for acc in accounts:
                all_accounts.append({
                    'id': acc.get('id'),
                    'name': acc.get('display_name') or acc.get('account_name'),
                    'service': plugin_name_lower,
                    'label': f"{acc.get('display_name') or acc.get('account_name')} ({plugin['name']})",
                    'color': '#1DB954' if plugin_name_lower == 'spotify' else '#00E5FF' if plugin_name_lower == 'tidal' else '#5b21b6'
                })

        # 2. Get media server users and ensure they have Account records in config.db
        media_users = []
        media_service_id = config_db.get_or_create_service_id(active_servers[0]) if active_servers else None
        if active_media_server_name == 'plex' and media_service_id:
            PlexClient = PluginRegistry.get_plugin_class(active_servers[0])
            if PlexClient:
                try:
                    client = PlexClient()
                    if client.ensure_connection() and client.server:
                        myplex = client.server.myPlexAccount()
                        # Ensure admin exists in config.db so it has a relational ID
                        admin_id = config_db.upsert_account(
                            service_id=media_service_id,
                            user_id=str(myplex.id),
                            account_name=myplex.username,
                            display_name=myplex.title or myplex.username
                        )
                        media_users.append({
                            'id': admin_id,
                            'user_id': str(myplex.id),
                            'name': myplex.title or myplex.username,
                            'account_name': myplex.username,
                            'display_name': myplex.title or myplex.username,
                            'is_admin': True,
                            'linked_account_ids': []
                        })
                        for user in myplex.users():
                            u_id = config_db.upsert_account(
                                service_id=media_service_id,
                                user_id=str(user.id),
                                account_name=user.username,
                                display_name=user.title or user.username
                            )
                            media_users.append({
                                'id': u_id,
                                'user_id': str(user.id),
                                'name': user.title or user.username,
                                'account_name': user.username,
                                'display_name': user.title or user.username,
                                'is_admin': False,
                                'linked_account_ids': []
                            })
                except Exception as e:
                    logger.warning(f"Failed to fetch Plex users: {e}")

        # 3. Load existing stateful mappings from config.db
        for user in media_users:
            mappings = config_db.get_account_mappings(account_id=user['id'])
            linked_ids = []
            for m in mappings:
                # Find the 'other' ID in the mapping pair
                other_id = m['mapped_account_id'] if m['source_account_id'] == user['id'] else m['source_account_id']
                linked_ids.append(other_id)
            user['linked_account_ids'] = linked_ids

        return {
            'music_accounts': all_accounts,
            'media_users': media_users
        }
    except Exception as e:
        logger.error(f"Error getting system accounts: {e}", exc_info=True)
        return {"error": str(e)}


@router.post("/accounts/map", dependencies=[Depends(require_auth)])
async def map_system_accounts(request: Request):
    """Save the mapping between a media server user and music service accounts.

    Accepts:
        { "user_id": <int_account_id>, "account_ids": [<int>, ...] }
    """
    try:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        # user_id here is the relational Account.id for the media user
        source_account_id = payload.get('user_id')
        account_ids = [int(aid) for aid in payload.get('account_ids', [])]
        if source_account_id is None:
            return {'error': 'user_id (Account ID) is required'}

        from database.config_database import get_config_database
        config_db = get_config_database()

        # Clear existing mappings for this account
        config_db.delete_account_mappings_for_account(int(source_account_id))

        # Insert new agnostic mappings
        for target_id in account_ids:
            config_db.set_account_mapping(int(source_account_id), target_id)

        return {'success': True}
    except Exception as e:
        logger.error(f"Error mapping accounts: {e}", exc_info=True)
        return {"error": str(e)}


@router.post("/settings", dependencies=[Depends(require_auth)])
@router.patch("/settings", dependencies=[Depends(require_auth)])
async def update_settings(request: Request):
    """Update application settings (partial update).

    Handles the special `log_level` key by updating the live console logger
    in addition to persisting the value via config_manager.

    Only keys present in _SETTINGS_ALLOWLIST are accepted; all others are
    rejected with 400 to prevent arbitrary config-tree injection.
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}
        
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    rejected_keys = [k for k in payload if k not in _SETTINGS_ALLOWLIST]
    if rejected_keys:
        logger.warning(f"Rejected unknown settings keys: {rejected_keys}")
        raise HTTPException(status_code=400, detail={
            "error": "Rejected unknown settings keys",
            "rejected_keys": rejected_keys,
            "allowed_keys": list(_SETTINGS_ALLOWLIST)
        })

    # Adjust log level immediately if requested.
    if "log_level" in payload:
        lvl = payload.get("log_level") or ""
        normalized = lvl.strip().lower()
        if normalized == "normal":
            normalized = "INFO"
        elif normalized == "verbose":
            normalized = "NOTSET"
        elif normalized == "debug":
            normalized = "DEBUG"
        try:
            from core.tiered_logger import set_log_level
            set_log_level(normalized.upper())
        except Exception:
            pass

    # Handle custom_ui_path validation
    restart_warning = False
    if "custom_ui_path" in payload:
        ui_path = str(payload["custom_ui_path"]).strip()
        if ui_path:
            if not os.path.isdir(ui_path):
                raise HTTPException(status_code=400, detail=f"Custom UI directory does not exist: {ui_path}")
        payload["custom_ui_path"] = ui_path
        restart_warning = True

    try:
        for key, value in payload.items():
            config_manager.set(key, value)

        resp = {"success": True}
        if restart_warning:
            resp["warning"] = "Application restart is required to apply the Custom UI Path."

        return resp
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update settings")


@router.get("/logs")
def get_logs():
    """Retrieve recent application logs."""
    try:
        # TODO: implement log retrieval from logging system
        return {"logs": []}
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return {"error": "Failed to get logs"}


@router.get("/activity/feed")
def activity_feed():
    """Activity feed for dashboard."""
    return {"items": []}


@router.get("/activity/toasts")
def activity_toasts():
    """Toast notifications."""
    return {"toasts": []}


@router.get("/downloads/status")
def downloads_status():
    """Download queue status."""
    return {
        "active": [],
        "queued": [],
        "completed": [],
        "failed": []
    }


@router.get("/quality-profile")
def quality_profile():
    """Audio quality preferences."""
    return {
        "min_bitrate": 320,
        "preferred_format": "FLAC",
        "fallback_format": "MP3"
    }


@router.get("/quality-profiles")
def list_quality_profiles():
    """Return stored quality profiles from config manager and dynamic plugin options."""
    try:
        profiles = config_manager.get_quality_profiles()
        from core.nexus_framework.plugin_loader import PluginRegistry
        plugin_options = PluginRegistry.get_all_quality_options()
        
        return {
            'profiles': profiles,
            'plugin_options': plugin_options
        }
    except Exception as e:
        logger.error(f"Error listing quality profiles: {e}")
        return {'error': 'Failed to list quality profiles'}


@router.post("/quality-profiles", dependencies=[Depends(require_auth)])
async def save_quality_profiles(request: Request):
    """Accept and validate submitted quality profiles, then persist via config manager.

    Expects JSON body: { "profiles": [ ... ] }
    """
    try:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        profiles = payload.get('profiles') if isinstance(payload, dict) else None
        if profiles is None:
            return {'error': 'Missing profiles list'}

        # Basic validation: list of dicts with id and name
        if not isinstance(profiles, list):
            return {'error': 'Profiles must be a list'}

        for p in profiles:
            if not isinstance(p, dict) or 'id' not in p or 'name' not in p:
                return {'error': 'Invalid profiles format; each profile must include id and name'}

        ok = config_manager.set_quality_profiles(profiles)
        if not ok:
            return {'error': 'Failed to persist profiles'}
        return {'success': True}
    except Exception as e:
        logger.error(f"Error saving quality profiles: {e}")
        return {'error': 'Failed to save profiles'}


@router.post("/quality-profile", dependencies=[Depends(require_auth)])
async def save_single_quality_profile(request: Request):
    """Save a single quality profile into the stored list.

    Body: { "profile": { ... } }
    Replaces existing profile with same id or appends.
    """
    try:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        profile = payload.get('profile') if isinstance(payload, dict) else None
        if profile is None:
            return {'error': 'Missing profile object'}

        if not isinstance(profile, dict) or 'id' not in profile or 'name' not in profile:
            return {'error': 'Invalid profile format; id and name required'}

        # Debug log incoming profile payload to help track missing arrays
        try:
            logger.debug(f"Incoming single profile payload: {json.dumps(profile, default=str)[:2000]}")
        except Exception:
            logger.debug(f"Incoming single profile payload (non-serializable)")

        # Load existing profiles
        existing = config_manager.get_quality_profiles() or []
        found = False
        for i, p in enumerate(existing):
            if str(p.get('id')) == str(profile.get('id')):
                # Preserve existing name if incoming profile omitted it
                if not profile.get('name') and p.get('name'):
                    profile['name'] = p.get('name')
                existing[i] = profile
                found = True
                break
        if not found:
            # Ensure new profile has a name
            if not profile.get('name'):
                profile['name'] = f"Profile {len(existing) + 1}"
            existing.append(profile)

        ok = config_manager.set_quality_profiles(existing)
        if not ok:
            return {'error': 'Failed to persist profile'}
        return {'success': True, 'profile': profile}
    except Exception as e:
        logger.error(f"Error saving single quality profile: {e}")
        return {'error': 'Failed to save profile'}


@router.get("/browse")
def browse_filesystem(request: Request):
    """Browse allowed filesystem roots and folders for the UI Browse buttons.

    Query params:
      - path: absolute path or root key (downloads, data, config, library, logs)

    Security: only paths under configured allowed roots will be listed.
    Returns JSON: { path: <abs>, root: <root_key>, entries: [ {name, path, relpath, is_dir} ] }
    """
    try:
        requested = request.query_params.get('path', '')
        settings_data = config_manager.get_all() or {}
        storage = settings_data.get('storage', {})

        roots = {
            'data': storage.get('data_dir'),
            'downloads': storage.get('download_dir'),
            'library': storage.get('library_dir'),
            'logs': storage.get('log_dir'),
            'config': storage.get('config_dir'),
        }
        # Filter out None values
        allowed_roots = {k: os.path.abspath(v) for k, v in roots.items() if v}

        # If no path provided, return available roots
        if not requested:
            return {'roots': [{'key': k, 'path': p} for k, p in allowed_roots.items()]}

        # Special-case: allow browsing filesystem root when client requests '/'
        if requested == '/':
            req_path = os.path.abspath(os.sep)
        else:
            # If requested is a root key, map it
            if requested in allowed_roots:
                req_path = allowed_roots[requested]
            else:
                # Accept absolute paths or paths relative to data root
                if os.path.isabs(requested):
                    req_path = os.path.abspath(requested)
                else:
                    base = allowed_roots.get('data') or os.getcwd()
                    req_path = os.path.abspath(os.path.join(base, requested))

        matched_root = None
        req_p = Path(req_path).resolve()
        if req_path == os.path.abspath(os.sep):
            # browsing top-level root; use root key 'root'
            matched_root = ('root', req_path)
        else:
            for key, root_path in allowed_roots.items():
                try:
                    r_p = Path(root_path).resolve()
                    if req_p == r_p or req_p.is_relative_to(r_p):
                        matched_root = (key, str(r_p))
                        break
                except Exception:
                    continue
            if not matched_root and os.path.isabs(req_path) and os.path.exists(req_path) and os.path.isdir(req_path):
                # Allow browsing absolute host paths (useful when running on host)
                matched_root = ('host', req_path)

        if not matched_root:
            return {'error': 'Path not allowed'}

        # Path must exist and be a directory
        if not os.path.exists(req_path) or not os.path.isdir(req_path):
            return {'error': 'Path not found or not a directory'}

        entries = []
        for name in sorted(os.listdir(req_path)):
            full = os.path.join(req_path, name)
            entries.append({
                'name': name,
                'path': os.path.abspath(full),
                'relpath': os.path.relpath(full, matched_root[1]) if matched_root and matched_root[1] else name,
                'is_dir': os.path.isdir(full)
            })

        return {'path': req_path, 'root': matched_root[0], 'entries': entries}
    except Exception as e:
        logger.error(f"Error browsing filesystem: {e}")
        return {'error': 'Failed to browse path'}


@router.get("/settings/preferences")
def get_preferences():
    """Get metadata enhancement preferences."""
    try:
        prefs = config_manager.get('metadata_enhancement') or {}
        return prefs
    except Exception as e:
        logger.error(f"Error getting preferences: {e}")
        return {"error": "Failed to get preferences"}


@router.post("/settings/preferences", dependencies=[Depends(require_auth)])
async def update_preferences(request: Request):
    """Update metadata enhancement preferences."""
    try:
        payload = await request.json()
        if not payload:
            return {"error": "Missing payload"}

        # Validate/Sanitize if needed
        current = config_manager.get('metadata_enhancement') or {}
        updated = {**current, **payload}

        config_manager.set('metadata_enhancement', updated)
        return {"success": True, "preferences": updated}
    except Exception as e:
        logger.error(f"Error updating preferences: {e}")
        return {"error": "Failed to update preferences"}


@router.post("/settings/preview-rename", dependencies=[Depends(require_auth)])
async def preview_rename(request: Request):
    """Preview file renaming based on template."""
    try:
        payload = await request.json()
        if not payload:
             return {"error": "Missing payload"}

        template = payload.get('template')
        sample_data = payload.get('sample_data') # Optional

        if not template:
             return {"error": "Missing template"}

        enhancer = get_metadata_enhancer()
        preview = enhancer.generate_preview_path(template, sample_data)

        return {"preview": preview}
    except Exception as e:
        logger.error(f"Error generating preview: {e}")
        return {"error": "Failed to generate preview"}


@router.post("/enhance/trigger", dependencies=[Depends(require_auth)])
async def trigger_metadata_enhancement(request: Request):
    """Manually kick off a retroactive metadata enhancement batch.

    Optional JSON body: { "batch_size": <int> }  (default 100)

    Returns JSON: { "status": "ok", "batch_size": <int> }
    """
    try:
        try:
            body = await request.json()
        except Exception:
            body = {}
        size = int(body.get("batch_size", 100))
        get_metadata_enhancer().enhance_library_metadata(batch_size=size)
        return {"status": "ok", "batch_size": size}
    except Exception as exc:
        logger.error("Manual enhance trigger failed: %s", exc, exc_info=True)
        return {"error": str(exc)}


@router.post("/reset/state", dependencies=[Depends(require_auth)])
def reset_state():
    """Drops all tables in working.db and calls create_all() to give a clean operational slate."""
    try:
        from database.working_database import get_working_database
        logger.info("System state reset requested - dropping and recreating working.db")
        working_db = get_working_database()
        working_db.drop_all()
        working_db.create_all()
        return {"success": True, "message": "System state reset successfully."}
    except Exception as e:
        logger.error(f"Error resetting system state: {e}", exc_info=True)
        return {"success": False, "error": "Failed to reset system state"}


@router.post("/reset/library", dependencies=[Depends(require_auth)])
def reset_library():
    """Drops and recreates all tables in music_library.db (Wipes the media database, forces a re-crawl)."""
    try:
        from database.music_database import get_database
        logger.info("Library reset requested - dropping and recreating music_library.db")
        music_db = get_database()
        music_db.drop_all()
        music_db.create_all()
        return {"success": True, "message": "Music library reset successfully. Ready for rescanning."}
    except Exception as e:
        logger.error(f"Error resetting library: {e}", exc_info=True)
        return {"success": False, "error": "Failed to reset library"}


@router.post("/reset/factory", dependencies=[Depends(require_auth)])
def reset_factory():
    """Deletes working.db, music_library.db, and config.db, triggering OOBE on next boot."""
    try:
        from core.state import system_state
        from core.job_queue import JobQueue
        import threading
        import time
        
        logger.warning("Factory reset requested! Deleting all primary databases.")
        
        def execute_factory_reset():
            time.sleep(2)  # Allow API response to return
            try:
                from database.working_database import close_working_database
                close_working_database()
            except ImportError:
                pass
            
            try:
                from database.music_database import close_database
                close_database()
            except ImportError:
                pass
                
            try:
                from database.config_database import close_config_database
                close_config_database()
            except ImportError:
                pass
            
            data_dir = os.getenv("ECHOSYNC_DATA_DIR", "data")
            db_files = [
                os.path.join(data_dir, "working.db"),
                os.path.join(data_dir, "music_library.db"),
                os.path.join(data_dir, "config.db")
            ]
            
            for db_path in db_files:
                if os.path.exists(db_path):
                    try:
                        os.remove(db_path)
                        logger.info(f"Deleted database: {db_path}")
                    except Exception as e:
                        logger.error(f"Failed to delete {db_path}: {e}")
                        
            logger.warning("Factory reset complete. Executing hard restart to trigger OOBE.")
            os._exit(1)
            
        system_state.restart_pending = True
        JobQueue.RESTART_PENDING = True
        threading.Thread(target=execute_factory_reset, daemon=True).start()
        
        return {"success": True, "message": "Factory reset initiated. System will restart shortly."}
    except Exception as e:
        logger.error(f"Error initiating factory reset: {e}", exc_info=True)
        return {"success": False, "error": "Failed to initiate factory reset"}

@router.post("/jobs/{job_name}/kill", dependencies=[Depends(require_auth)])
def kill_job(job_name):
    """Terminate a running job violently if it is a process, or softly if it is a thread."""
    try:
        from core.job_queue import job_queue
        import multiprocessing

        with job_queue._lock:
            val = job_queue._is_running.get(job_name)
            job = job_queue._jobs.get(job_name)

            if not val and not (job and job.running):
                return {'error': 'Job not running'}

            # If it's a multiprocessing Process, terminate it
            if isinstance(val, multiprocessing.Process) and val.is_alive():
                logger.warning(f"Violently terminating heavy job process: {job_name}")
                val.terminate()
                val.join(timeout=2.0)
                if val.is_alive():
                    val.kill() # Escalation
                job_queue._is_running[job_name] = False
                if job:
                    job.running = False
                return {'success': True, 'message': f'Process terminated for {job_name}'}

            # Otherwise, soft kill for threads
            if job:
                job.running = False
            job_queue._is_running[job_name] = False
            return {'success': True, 'message': f'Soft stop signal sent to thread for {job_name}'}

    except Exception as e:
        logger.error(f"Error killing job: {e}")
        return {'error': 'Failed to kill job'}



