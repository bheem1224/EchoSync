from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any, Optional
import json
import os
from pathlib import Path
from core.settings import config_manager
from core.nexus_framework.plugin_loader import get_all_plugins
from core.nexus_framework.plugin_store import plugin_store
from core.tiered_logger import get_logger
from contextlib import contextmanager
from web.auth import require_auth
from database.models import Service

logger = get_logger("plugins_route")
router = APIRouter(prefix="/api/v1/system/plugins", tags=['Plugins'])

@contextmanager
def config_db_connection():
    from database.config_database import get_config_database
    db = get_config_database()
    conn = db._open_connection()
    try:
        yield conn
    finally:
        conn.close()

def resolve_case_insensitive_path(path: Path) -> Path:
    if path.exists():
        return path
    parts = path.parts
    if not parts:
        return path
    current = Path(parts[0])
    for part in parts[1:]:
        if (current / part).exists():
            current = current / part
        else:
            found = False
            if current.is_dir():
                try:
                    for child in current.iterdir():
                        if child.name.lower() == part.lower():
                            current = child
                            found = True
                            break
                except Exception:
                    pass
            if not found:
                current = current / part
    return current

class GenericSuccessResponse(BaseModel):
    success: bool
    model_config = ConfigDict(from_attributes=True)

class PluginsListResponse(BaseModel):
    plugins: List[Dict[str, Any]]
    model_config = ConfigDict(from_attributes=True)

@router.get("", response_model=PluginsListResponse, dependencies=[Depends(require_auth)])
def list_plugins():
    plugins = get_all_plugins()
    return PluginsListResponse(plugins=plugins)

class UIPluginComponent(BaseModel):
    element_tag: str
    bundle_url: str

class UIPluginView(BaseModel):
    id: str
    title: str
    icon: Optional[str] = None
    yaml_path: str

class UIPluginManifest(BaseModel):
    id: str
    plugin_id: int
    api_base: str
    components: Dict[str, UIPluginComponent] = {}
    assets: Dict[str, str] = {}
    views: List[UIPluginView] = []
    model_config = ConfigDict(from_attributes=True)

class UIManifestResponse(BaseModel):
    plugins: List[UIPluginManifest]
    model_config = ConfigDict(from_attributes=True)

@router.get("/ui-manifest", response_model=UIManifestResponse, dependencies=[Depends(require_auth)])
def get_ui_manifest(response: Response):
    from web.routes.ui_registry import _query_ui_registry
    registry = _query_ui_registry()
    plugin_map: dict = {}

    for type_key, components in registry.items():
        category = type_key.rstrip("s") if type_key.endswith("s") and type_key != "settings" else type_key
        for comp in components:
            pid = comp.get("plugin_id")
            if pid is None:
                continue
            pname = comp.get("plugin_name") or str(pid)
            if pid not in plugin_map:
                plugin_map[pid] = {
                    "id": pname,
                    "plugin_id": pid,
                    "api_base": f"/api/plugins/{pname}",
                    "components": {},
                    "assets": {},
                    "views": [],
                }
            entry = plugin_map[pid]
            if category == "view":
                entry["views"].append({
                    "id": comp["tag_name"].replace("es-view-", ""),
                    "title": comp["tag_name"],
                    "icon": None,
                    "yaml_path": comp["entry"],
                })
            else:
                entry["assets"]["js"] = comp["entry"]
                entry["components"][category] = {
                    "element_tag": comp["tag_name"],
                    "bundle_url": comp["entry"],
                }

    ui_plugins = list(plugin_map.values())
    response.headers["X-Deprecated"] = "Use /api/ui/registry instead"
    return UIManifestResponse(plugins=ui_plugins)

class UpdateConfigRequest(BaseModel):
    disabled_plugins: Optional[List[str]] = None
    disabled_providers: Optional[List[str]] = None
    active_matching_engine: Optional[str] = None

@router.post("/config", response_model=GenericSuccessResponse, dependencies=[Depends(require_auth)])
def update_plugin_config(data: UpdateConfigRequest):
    disabled_list = data.disabled_plugins or data.disabled_providers
    if disabled_list is not None:
        config_manager.set_disabled_plugins(disabled_list)

    if data.active_matching_engine is not None:
        config_manager.set('settings.active_matching_engine', data.active_matching_engine)

    return GenericSuccessResponse(success=True)

class ReposListResponse(BaseModel):
    repos: List[str]
    model_config = ConfigDict(from_attributes=True)

@router.get("/repos", response_model=ReposListResponse, dependencies=[Depends(require_auth)])
def get_repos():
    repos = plugin_store.get_repositories()
    return ReposListResponse(repos=repos)

class RepoRequest(BaseModel):
    url: str

@router.post("/repos", response_model=GenericSuccessResponse, dependencies=[Depends(require_auth)])
def add_repo(data: RepoRequest):
    if not data.url:
        raise HTTPException(status_code=400, detail="URL required")
    success = plugin_store.add_repository(data.url)
    if success:
        return GenericSuccessResponse(success=True)
    raise HTTPException(status_code=500, detail="Failed to add repository")

@router.delete("/repos", response_model=GenericSuccessResponse, dependencies=[Depends(require_auth)])
def remove_repo(data: RepoRequest):
    if not data.url:
        raise HTTPException(status_code=400, detail="URL required")
    success = plugin_store.remove_repository(data.url)
    if success:
        return GenericSuccessResponse(success=True)
    raise HTTPException(status_code=500, detail="Failed to remove repository")

@router.get("/store", response_model=PluginsListResponse, dependencies=[Depends(require_auth)])
def get_plugin_store():
    try:
        plugins = plugin_store.get_all_store_plugins()
        return PluginsListResponse(plugins=plugins)
    except Exception as e:
        logger.error(f"Error fetching plugin store: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch plugin store")

class PluginActionRequest(BaseModel):
    plugin: Dict[str, Any]
    channel: Optional[str] = None

@router.post("/install", dependencies=[Depends(require_auth)])
def install_plugin(request: Request, data: PluginActionRequest):
    from core.nexus_framework.plugin_store import PrivilegeEscalationError
    plugin_info = data.plugin
    channel = data.channel or plugin_info.get('channel', 'stable')
    if channel == 'release': channel = 'stable'
    force_consent = request.query_params.get('force_consent') == 'true'
    
    if not plugin_info:
        raise HTTPException(status_code=400, detail="Plugin info required")

    try:
        success = plugin_store.install_plugin(plugin_info, channel=channel, force_consent=force_consent)
        if success:
            return {"success": True}
        raise HTTPException(status_code=500, detail=f"Failed to install plugin on channel {channel}")
    except PrivilegeEscalationError as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=403, content={"requires_consent": True, "escalations": e.escalations, "message": "This update requires elevated permissions."})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Install error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to install plugin")

@router.post("/update", dependencies=[Depends(require_auth)])
def update_plugin(request: Request, data: PluginActionRequest):
    from core.nexus_framework.plugin_store import PrivilegeEscalationError
    plugin_info = data.plugin
    force_consent = request.query_params.get('force_consent') == 'true'
    
    if not plugin_info:
        raise HTTPException(status_code=400, detail="Plugin info required")

    try:
        from database.config_database import get_config_database
        db = get_config_database()
        plugin_name = plugin_info.get("id") or plugin_info.get("name")
        
        plugin_id_int = db.get_service_id(plugin_name)
        if not plugin_id_int:
            try:
                plugin_id_int = int(plugin_info.get("plugin_id") or plugin_info.get("id"))
            except (ValueError, TypeError):
                pass
                
        db_plugin_id = None
        if plugin_id_int is not None:
            with config_db_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT plugin_id FROM services WHERE id=? OR plugin_id=?", (plugin_id_int, plugin_id_int))
                row = c.fetchone()
                if row:
                    db_plugin_id = row['plugin_id']
                    
        if not db_plugin_id:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_name} not found in database registry.")

        success = plugin_store.update_plugin(db_plugin_id, force_consent=force_consent)
        if success:
            return {"success": True}
        raise HTTPException(status_code=500, detail=f"Failed to update plugin {plugin_name}")
    except PrivilegeEscalationError as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=403, content={"requires_consent": True, "escalations": e.escalations, "message": "This update requires elevated permissions."})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update plugin")

@router.post("/rollback", response_model=GenericSuccessResponse, dependencies=[Depends(require_auth)])
def rollback_plugin(data: PluginActionRequest):
    plugin_info = data.plugin
    if not plugin_info:
        raise HTTPException(status_code=400, detail="Plugin info required")

    try:
        from database.config_database import get_config_database
        db = get_config_database()
        plugin_name = plugin_info.get("id") or plugin_info.get("name")
        
        plugin_id_int = db.get_service_id(plugin_name)
        if not plugin_id_int:
            try:
                plugin_id_int = int(plugin_info.get("plugin_id") or plugin_info.get("id"))
            except (ValueError, TypeError):
                pass
                
        db_plugin_id = None
        if plugin_id_int is not None:
            with config_db_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT plugin_id FROM services WHERE id=? OR plugin_id=?", (plugin_id_int, plugin_id_int))
                row = c.fetchone()
                if row:
                    db_plugin_id = row['plugin_id']
                    
        if not db_plugin_id:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_name} not found in database registry.")

        success = plugin_store.rollback_plugin(db_plugin_id)
        if success:
            return GenericSuccessResponse(success=True)
        raise HTTPException(status_code=500, detail="Failed to rollback plugin")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rollback error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to rollback plugin")

@router.post("/{plugin_id}/rollback", response_model=GenericSuccessResponse, dependencies=[Depends(require_auth)])
def rollback_plugin_direct(plugin_id: str):
    try:
        from database.config_database import get_config_database
        db = get_config_database()
        
        plugin_id_int = db.get_service_id(plugin_id)
        if not plugin_id_int:
            try:
                plugin_id_int = int(plugin_id)
            except (ValueError, TypeError):
                pass
                
        db_plugin_id = None
        if plugin_id_int is not None:
            with config_db_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT plugin_id FROM services WHERE id=? OR plugin_id=?", (plugin_id_int, plugin_id_int))
                row = c.fetchone()
                if row:
                    db_plugin_id = row['plugin_id']
                    
        if not db_plugin_id:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")
            
        success = plugin_store.rollback_plugin(db_plugin_id)
        if success:
            return GenericSuccessResponse(success=True)
        raise HTTPException(status_code=500, detail="Failed to rollback plugin")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rollback error for {plugin_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to rollback plugin")

class BetaOptRequest(BaseModel):
    beta_opt_in: Optional[bool] = None

@router.post("/{plugin_id}/beta-opt", response_model=GenericSuccessResponse, dependencies=[Depends(require_auth)])
def set_plugin_beta_opt(plugin_id: str, data: BetaOptRequest):
    val = data.beta_opt_in
    db_val = None
    if val is not None:
        db_val = 1 if bool(val) else 0
        
    try:
        from database.config_database import get_config_database
        db = get_config_database()
        
        plugin_id_int = db.get_service_id(plugin_id)
        if not plugin_id_int:
            try:
                plugin_id_int = int(plugin_id)
            except (ValueError, TypeError):
                pass
                
        db_plugin_id = None
        if plugin_id_int is not None:
            with config_db_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT plugin_id FROM services WHERE id=? OR plugin_id=?", (plugin_id_int, plugin_id_int))
                row = c.fetchone()
                if row:
                    db_plugin_id = row['plugin_id']
                    c.execute("UPDATE services SET beta_opt_in=? WHERE plugin_id=?", (db_val, db_plugin_id))
                    conn.commit()
                    
        if not db_plugin_id:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")
            
        try:
            from core.nexus_framework.plugin_loader import PluginLoader
            app_root = Path(__file__).parent.parent.parent
            loader = PluginLoader(app_root)
            loader.reload_plugin(db_plugin_id)
            logger.info(f"Hot-reloaded plugin {db_plugin_id} after beta-opt change")
        except Exception as re:
            logger.warning(f"Failed to hot-reload plugin {db_plugin_id} after beta-opt change: {re}")
            
        return GenericSuccessResponse(success=True)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting beta opt for {plugin_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to set beta opt-in")

class UninstallPluginRequest(BaseModel):
    id: Optional[Any] = None
    name: Optional[str] = None
    author: Optional[str] = None

@router.post("/uninstall", response_model=GenericSuccessResponse, dependencies=[Depends(require_auth)])
def uninstall_plugin_route(data: UninstallPluginRequest):
    import binascii
    plugin_id_raw = data.id
    plugin_name = data.name
    author = data.author

    if not plugin_id_raw and not (plugin_name and author):
        raise HTTPException(status_code=400, detail="Plugin ID required")

    from database.config_database import get_config_database
    db = get_config_database()

    service_id = db.get_service_id(plugin_id_raw)
    if not service_id and author and plugin_name:
        service_id = db.get_service_id(f"{author}.{plugin_name}")

    if service_id:
        with config_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT plugin_id FROM services WHERE id=?", (service_id,))
            row = c.fetchone()
            if row and row['plugin_id'] is not None:
                plugin_id = int(row['plugin_id'])
            else:
                plugin_id = service_id
    else:
        if isinstance(plugin_id_raw, int):
            plugin_id = plugin_id_raw
        elif author and plugin_name:
            plugin_id = binascii.crc32(f"{author}.{plugin_name}".lower().encode('utf-8')) & 0xFFFFFFFF
        else:
            plugin_id = binascii.crc32(str(plugin_id_raw).lower().encode('utf-8')) & 0xFFFFFFFF

    try:
        success = plugin_store.uninstall_plugin(plugin_id)
        if success:
            return GenericSuccessResponse(success=True)
        raise HTTPException(status_code=500, detail="Failed to uninstall plugin")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Uninstall error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to uninstall plugin")


class TogglePluginRequest(BaseModel):
    enabled: Optional[bool] = None

@router.post("/{plugin_id}/toggle", response_model=GenericSuccessResponse, dependencies=[Depends(require_auth)])
def toggle_plugin(plugin_id: str, data: Optional[TogglePluginRequest] = None):
    from core.settings import config_manager
    from core.nexus_framework.plugin_loader import PluginRegistry, PluginLoader
    from core.state import system_state
    from database.config_database import get_config_database
    
    enabled_val = data.enabled if data is not None else None
    
    # 1. Resolve DB records for this plugin
    db = get_config_database()
    db_id = None
    db_name = None
    db_plugin_id = None
    current_is_active = 1
    
    plugin_id_str = str(plugin_id).strip()
    plugin_id_int = int(plugin_id_str) if plugin_id_str.isdigit() else None
    
    with config_db_connection() as conn:
        c = conn.cursor()
        if plugin_id_int is not None:
            c.execute("SELECT id, name, plugin_id, is_active FROM services WHERE id=? OR plugin_id=?", (plugin_id_int, plugin_id_int))
        else:
            c.execute("SELECT id, name, plugin_id, is_active FROM services WHERE lower(name)=lower(?)", (plugin_id_str,))
        row = c.fetchone()
        if row:
            db_id = row['id']
            db_name = row['name']
            db_plugin_id = row['plugin_id']
            current_is_active = row['is_active']
            
    if db_plugin_id is None and plugin_id_int is not None:
        db_plugin_id = plugin_id_int
    if db_name is None and not plugin_id_str.isdigit():
        db_name = plugin_id_str
        
    # Determine target enabled state
    if enabled_val is None:
        target_enabled = not bool(current_is_active)
    else:
        target_enabled = bool(enabled_val)
        
    target_active = 1 if target_enabled else 0
    
    # 2. Update services table in config.db so get_all_plugins() returns correct enabled state
    with config_db_connection() as conn:
        c = conn.cursor()
        if db_id is not None:
            c.execute("UPDATE services SET is_active=? WHERE id=?", (target_active, db_id))
        elif db_plugin_id is not None:
            c.execute("UPDATE services SET is_active=? WHERE plugin_id=?", (target_active, db_plugin_id))
        elif db_name is not None:
            c.execute("UPDATE services SET is_active=? WHERE lower(name)=lower(?)", (target_active, db_name))
        conn.commit()

    # 3. Update config_manager persistent disabled_plugins & in-memory PluginRegistry
    if target_enabled:
        config_manager.enable_plugin(plugin_id_str)
        if db_name:
            config_manager.enable_plugin(db_name)
        if db_plugin_id:
            config_manager.enable_plugin(str(db_plugin_id))
        PluginRegistry.enable_plugin(db_plugin_id or plugin_id_str)
    else:
        config_manager.disable_plugin(db_name or plugin_id_str)
        PluginRegistry.disable_plugin(db_plugin_id or plugin_id_str)
        
    config_manager.save_settings(config_manager.get_settings())

    # 4. Trigger hot reload or update lifecycle state
    try:
        if target_enabled and db_plugin_id:
            app_root = Path(__file__).parent.parent.parent
            loader = PluginLoader(app_root)
            loader.reload_plugin(db_plugin_id)
            logger.info(f"Hot-reloaded plugin {plugin_id} (id: {db_plugin_id}) after enable toggle")
        elif not target_enabled:
            from core.nexus_framework.plugin_state_manager import plugin_state_manager, PluginLifecycleState
            from core.task_manager.supervisor import supervisor
            target_ident = db_name or plugin_id_str
            supervisor.terminate_owner_processes(target_ident)
            if db_plugin_id:
                supervisor.terminate_owner_processes(str(db_plugin_id))
                plugin_state_manager.set_state(str(db_plugin_id), PluginLifecycleState.UNCONFIGURED, "Plugin disabled")
            plugin_state_manager.set_state(target_ident, PluginLifecycleState.UNCONFIGURED, "Plugin disabled")
            logger.info(f"Plugin {plugin_id} disabled and state marked UNCONFIGURED")
    except Exception as e:
        logger.warning(f"Hot-reload/state change failed for {plugin_id}: {e}")
        system_state.restart_pending = True

    return GenericSuccessResponse(success=True)

# --- Merged from plugins_api.py ---



class GenericSuccessResponse(BaseModel):
    success: bool
    model_config = ConfigDict(from_attributes=True)

def _normalize_sensitive_value_for_ui(key, value):
    """Ensure sensitive values returned to UI are plaintext (or empty on failure)."""
    if value is None:
        return value
    sensitive = {'client_secret', 'access_token', 'refresh_token', 'password', 'token', 'api_key'}
    if key in sensitive and isinstance(value, str) and value.startswith('enc:'):
        from core.security import decrypt_string
        decrypted = decrypt_string(value)
        if isinstance(decrypted, str) and decrypted.startswith('enc:'):
            return ''
        return decrypted
    return value


def _normalize_sensitive_value_for_save(key, value):
    """If UI posted an encrypted blob for a sensitive field, decrypt before re-saving."""
    sensitive = {'client_secret', 'access_token', 'refresh_token', 'password', 'token', 'api_key'}
    if key in sensitive and isinstance(value, str) and value.startswith('enc:'):
        from core.security import decrypt_string
        decrypted = decrypt_string(value)
        if isinstance(decrypted, str) and not decrypted.startswith('enc:'):
            return decrypted
    return value


def _build_active_plex_user_map():
    """Build a display-name to Plex user_id map from active config.db accounts."""
    try:
        from database.config_database import get_config_database

        config_db = get_config_database()
        plex_service_id = config_db.get_or_create_service_id('plex')
        accounts = config_db.get_accounts(service_id=plex_service_id, is_active=True)

        mapping = {}
        for account in accounts:
            user_id = account.get('user_id')
            if not user_id:
                continue

            for key in (account.get('display_name'), account.get('account_name')):
                normalized = (key or '').strip().lower()
                if normalized:
                    mapping[normalized] = str(user_id)
        return mapping
    except Exception as e:
        logger.warning(f"Failed to build Plex user map for provider playlists: {e}")
        return {}


def _match_plex_user_for_account(plex_user_map: dict, account_name: str):
    """Return the Plex user_id for a source account name using exact and token-boundary matching."""
    import re
    normalized = (account_name or '').strip().lower()
    if not normalized:
        return None
    if normalized in plex_user_map:
        return plex_user_map[normalized]
    for plex_name, uid in plex_user_map.items():
        if plex_name:
            pattern = r"(?:\b|_)" + re.escape(plex_name) + r"(?:'s|\b|_)"
            if re.search(pattern, normalized, re.IGNORECASE):
                return uid
    return None

@router.get("")
@router.get("/")
def list_all_plugins(request: Request):
    """List all available plugins with their metadata and capabilities."""
    try:
        plugins_list = list_plugins()
        
        content_json = json.dumps(plugins_list, sort_keys=True).encode('utf-8')
        etag = hashlib.md5(content_json).hexdigest()
        
        if request.headers.get('If-None-Match') == etag:
            return Response(status_code=304)
            
        return JSONResponse(
            content=plugins_list, 
            headers={'ETag': etag, 'Cache-Control': 'public, max-age=0, must-revalidate'}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing plugins: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list plugins")

@router.get("/download-clients")
def list_download_clients():
    """List all providers flagged as download clients."""
    try:
        from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry
        from core.settings import config_manager
        
        active_downloads = PluginRegistry.get_active_services_by_type('download')
        active_client = active_downloads[0].split('.')[-1] if active_downloads else None
        download_clients = []
        
        clients = PluginRegistry.get_download_clients()
        
        for plugin_name in clients:
            try:
                plugin_class = PluginRegistry.get_plugin_class(plugin_name)
                if plugin_class:
                    download_clients.append({
                        'name': plugin_name,
                        'display_name': plugin_name.title(),
                        'supports_downloads': True,
                        'description': f'Download music via {plugin_name.title()}',
                        'active': plugin_name == active_client
                    })
            except Exception as e:
                logger.error(f"Error processing plugin {plugin_name} for download clients: {e}")
                continue
        
        return download_clients
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing download clients: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list download clients")

@router.get("/download-clients/active")
def get_active_download_client():
    """Get the currently active download client."""
    try:
        from core.settings import config_manager
        from core.nexus_framework.plugin_loader import PluginRegistry
        active_downloads = PluginRegistry.get_active_services_by_type('download')
        active = active_downloads[0].split('.')[-1] if active_downloads else None
        return {'active_client': active}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting active download client: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get active download client")

class ActivateClientRequest(BaseModel):
    client: Optional[str] = None

@router.post("/download-clients/activate", dependencies=[Depends(require_auth)])
def set_active_download_client(data: ActivateClientRequest):
    """Set the active download client."""
    try:
        from core.settings import config_manager
        from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry

        client_name = data.client

        if not client_name:
            raise HTTPException(status_code=400, detail="Client name is required")

        plugin_class = PluginRegistry.get_plugin_class(client_name)
        if not plugin_class:
            raise HTTPException(status_code=404, detail=f"Plugin {client_name} not found")

        if not getattr(plugin_class, 'supports_downloads', False):
             raise HTTPException(status_code=400, detail=f"Plugin {client_name} does not support downloads")

        config_manager.set_active_download_client(client_name)
        logger.info(f"Active download client set to: {client_name}")

        return {
            'success': True,
            'active_client': client_name
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting active download client: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to set active download client")


@router.post("/{plugin_id}/rollback", dependencies=[Depends(require_auth)])
def rollback_plugin(plugin_id: str):
    """Roll back a plugin to its previous stable version and state."""
    try:
        from core.nexus_framework.plugin_store import plugin_store
        
        success = plugin_store.rollback_plugin(plugin_id)
        
        if success:
            return {'success': True}
        else:
            raise HTTPException(status_code=400, detail="Rollback failed or no snapshot found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rolling back plugin {plugin_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to rollback plugin")


@router.get("/{plugin_id}/accounts")
def get_plugin_accounts(plugin_id: str):
    """Fetch active accounts / profiles for a specific plugin."""
    try:
        from core.nexus_framework.plugin_loader import PluginRegistry
        from database.config_database import get_config_database
        from services.storage_service import get_storage_service

        config_db = get_config_database()
        storage = get_storage_service()

        plugin_cls = PluginRegistry.get_plugin_class(plugin_id)
        short_name = (plugin_cls.name.split('.')[-1].lower() if plugin_cls and hasattr(plugin_cls, 'name') and plugin_cls.name else str(plugin_id)).lower()

        accounts_list = []
        if short_name == 'plex' or 'plex' in str(plugin_id).lower():
            PlexClient = PluginRegistry.get_plugin_class('plex') or plugin_cls
            if PlexClient:
                try:
                    client = PlexClient()
                    if client.ensure_connection() and client.server:
                        myplex = client.server.myPlexAccount()
                        accounts_list.append({
                            'id': str(myplex.id),
                            'user_id': str(myplex.id),
                            'account_name': myplex.username,
                            'display_name': myplex.title or myplex.username,
                            'name': myplex.title or myplex.username,
                            'username': myplex.username,
                            'is_admin': True,
                        })
                        for user in myplex.users():
                            accounts_list.append({
                                'id': str(user.id),
                                'user_id': str(user.id),
                                'account_name': user.username,
                                'display_name': user.title or user.username,
                                'name': user.title or user.username,
                                'username': user.username,
                                'is_admin': False,
                            })
                except Exception as e:
                    logger.warning(f"Error fetching Plex accounts from server: {e}")

        # Fallback to database accounts if empty
        if not accounts_list:
            service_id = config_db.get_or_create_service_id(plugin_id)
            db_accounts = config_db.get_accounts(service_id=service_id, is_active=True)
            for acc in db_accounts:
                accounts_list.append({
                    'id': acc.get('user_id') or str(acc.get('id')),
                    'user_id': acc.get('user_id') or str(acc.get('id')),
                    'account_name': acc.get('account_name'),
                    'display_name': acc.get('display_name') or acc.get('account_name'),
                    'name': acc.get('display_name') or acc.get('account_name'),
                    'username': acc.get('account_name'),
                    'is_admin': False,
                })

        return {
            'plugin': short_name,
            'items': accounts_list,
            'total': len(accounts_list),
        }
    except Exception as e:
        logger.error(f"Error fetching accounts for plugin {plugin_id}: {e}", exc_info=True)
        return {'plugin': str(plugin_id), 'items': [], 'total': 0, 'error': 'Failed to fetch plugin accounts'}


@router.get("/{plugin_id}/playlists")
def get_plugin_playlists(plugin_id: str):
    """Fetch playlists from a specific plugin."""
    try:
        from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry
        
        plugin_cls = PluginRegistry.get_plugin_class(plugin_id)
        if not plugin_cls:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found or not installed")
        
        if PluginRegistry.is_plugin_disabled(plugin_id):
            raise HTTPException(status_code=403, detail=f"Plugin {plugin_id} is disabled")
        
        try:
            plugin = PluginRegistry.create_instance(plugin_id)
        except Exception as e:
            logger.error(f"Error instantiating plugin {plugin_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Plugin {plugin_id} could not be initialized")
        
        if not plugin:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} instance not found")
        
        multi_account_plugins = ['spotify', 'tidal']
        short_name = plugin_cls.name.split('.')[-1].lower() if hasattr(plugin_cls, 'name') and plugin_cls.name else ''
        if short_name in multi_account_plugins:
            try:
                from services.storage_service import get_storage_service
                storage = get_storage_service()
                plex_user_map = _build_active_plex_user_map()

                accounts = storage.list_accounts(str(plugin_id))

                if not accounts:
                    logger.info(f"No accounts found for plugin {plugin_id}")
                    return {
                        'plugin': short_name,
                        'items': [],
                        'total': 0,
                        'status': 'not_configured'
                    }

                all_playlists = []

                for account in accounts:
                    if not account.get('is_active', True):
                        continue
                    try:
                        account_id = account['id']
                        account_name = account.get('display_name') or account.get('account_name') or f"Account {account_id}"

                        if short_name == 'spotify':
                            client = plugin_cls(account_id=account_id)
                        elif short_name == 'tidal':
                            client = plugin_cls(account_id=str(account_id))
                        else:
                            continue

                        if hasattr(client, 'is_configured') and not client.is_configured():
                            continue

                        if hasattr(client, 'get_user_playlists'):
                            playlists = client.get_user_playlists()
                            for p in playlists:
                                if hasattr(p, '__dict__'):
                                    p_dict = p.__dict__.copy()
                                elif isinstance(p, dict):
                                    p_dict = p.copy()
                                else:
                                    continue

                                original_name = p_dict.get('name', 'Unknown')
                                p_dict['name'] = original_name
                                p_dict['source_account_name'] = account_name
                                mapped_user_id = _match_plex_user_for_account(plex_user_map, account_name)
                                if mapped_user_id:
                                    p_dict['target_user_id'] = mapped_user_id
                                p_dict['account_id'] = account_id
                                all_playlists.append(p_dict)

                    except Exception as acc_err:
                        logger.warning(f"Error fetching playlists for account {account.get('id')}: {acc_err}")
                        continue

                return {
                    'plugin': short_name,
                    'items': all_playlists,
                    'total': len(all_playlists)
                }

            except Exception as e:
                logger.error(f"Error handling multi-account logic for {short_name}: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail="Failed to retrieve multi-account playlists")

        if hasattr(plugin, 'is_configured') and not plugin.is_configured():
            logger.info(f"Plugin {plugin_id} is not configured, returning empty list")
            return {
                'plugin': plugin_id,
                'items': [],
                'total': 0,
                'status': 'not_configured'
            }
        
        if not hasattr(plugin, 'get_user_playlists'):
            raise HTTPException(status_code=400, detail=f"Plugin {plugin_id} does not support playlists")
        
        logger.info(f"[ROUTE] Calling get_user_playlists on {plugin_id} plugin")
        playlists = plugin.get_user_playlists()
        
        serialized = []
        for p in playlists:
            if hasattr(p, '__dict__'):
                serialized.append(p.__dict__)
            elif isinstance(p, dict):
                serialized.append(p)
            else:
                try:
                    serialized.append({'id': getattr(p, 'id', ''), 'name': getattr(p, 'name', str(p))})
                except:
                    serialized.append({'name': str(p)})
        
        return {
            'plugin': plugin_id,
            'items': serialized,
            'total': len(serialized)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching playlists for {plugin_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch playlists")


@router.get("/{plugin_id}/settings")
def get_plugin_settings(plugin_id: str):
    """Get settings and schema for a specific plugin."""
    try:
        from database.config_database import get_config_database
        config_db = get_config_database()
        
        from core.nexus_framework.plugin_loader import PluginRegistry
        plugin_cls = PluginRegistry.get_plugin_class(plugin_id)
        if plugin_cls and hasattr(plugin_cls, 'name') and plugin_cls.name:
            normalized_plugin_id = plugin_cls.name
        else:
            normalized_plugin_id = plugin_id

        try:
            service_id = config_db.get_or_create_service_id(normalized_plugin_id)
            if not service_id:
                raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")
        except Exception as e:
            logger.error(f"Error in get_or_create_service_id for {plugin_id}: {e}", exc_info=True)
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")

        keys_of_interest = ['client_id', 'client_secret', 'base_url', 'server_url', 'token', 'api_key', 'username', 'password', 'slskd_url']
        config = {}
        for key in keys_of_interest:
            val = config_db.get_service_config(service_id, key)
            if val is not None:
                config[key] = _normalize_sensitive_value_for_ui(key, val)
        
        from core.network_utils import get_lan_ip
        lan_ip = get_lan_ip()
        callback_id = normalized_plugin_id.split('.')[-1].lower()
        config['redirect_uri'] = f"https://{lan_ip}:5001/api/oauth/callback/plugins/{callback_id}"
        
        schema = _get_mock_schema(callback_id)
        return {
            'plugin': plugin_id,
            'settings': config,
            'schema': schema
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting settings for {plugin_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get plugin settings")

@router.post("/{plugin_id}/settings", dependencies=[Depends(require_auth)])
async def update_plugin_settings(plugin_id: str, request: Request):
    """Update settings for a specific plugin."""
    try:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
            
        logger.info(f"Updating settings for plugin: {plugin_id}")
        from database.config_database import get_config_database
        config_db = get_config_database()
        
        from core.nexus_framework.plugin_loader import PluginRegistry
        plugin_cls = PluginRegistry.get_plugin_class(plugin_id)
        if plugin_cls and hasattr(plugin_cls, 'name') and plugin_cls.name:
            normalized_plugin_id = plugin_cls.name
        else:
            normalized_plugin_id = plugin_id

        service_id = config_db.get_or_create_service_id(normalized_plugin_id)
        if not service_id:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")

        sensitive_keys = {'client_secret', 'token', 'api_key', 'password'}
        for key, val in payload.items():
            if val is not None:
                is_sens = key in sensitive_keys
                config_db.set_service_config(service_id, key, val, is_sensitive=is_sens)

        return {"success": True, "message": f"Settings updated for {plugin_id}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating settings for {plugin_id}: {type(e).__name__} - {e}")
        raise HTTPException(status_code=500, detail="Failed to update settings")

def _get_mock_schema(provider_name):
    """Temporary mock schema until providers declare their own."""
    schemas = {
        'spotify': [
            {'key': 'client_id', 'label': 'Client ID', 'type': 'text', 'sensitive': True},
            {'key': 'client_secret', 'label': 'Client Secret', 'type': 'password', 'sensitive': True},
            {'key': 'redirect_uri', 'label': 'Redirect URI', 'type': 'text', 'default': 'http://127.0.0.1:8008/api/spotify/callback'},
        ],
        'plex': [
            {'key': 'server_url', 'label': 'Server URL', 'type': 'text', 'default': 'http://localhost:32400'},
            {'key': 'token', 'label': 'X-Plex-Token', 'type': 'password', 'sensitive': True},
        ],
        'soulseek': [
            {'key': 'username', 'label': 'Username', 'type': 'text'},
            {'key': 'password', 'label': 'Password', 'type': 'password', 'sensitive': True},
            {'key': 'slskd_url', 'label': 'slskd URL', 'type': 'text', 'default': 'http://localhost:5030'},
            {'key': 'api_key', 'label': 'API Key', 'type': 'password', 'sensitive': True},
        ],
        'slskd': [
            {'key': 'username', 'label': 'Username', 'type': 'text'},
            {'key': 'password', 'label': 'Password', 'type': 'password', 'sensitive': True},
            {'key': 'slskd_url', 'label': 'slskd URL', 'type': 'text', 'default': 'http://localhost:5030'},
            {'key': 'api_key', 'label': 'API Key', 'type': 'password', 'sensitive': True},
        ]
    }
    return schemas.get(provider_name, [])

def _enrich_provider_capabilities(provider_dict, provider_name=None):
    """Enrich a provider dict with capability metadata."""
    try:
        from core.nexus_framework.plugin_loader import get_plugin_capabilities as fetch_capabilities
        name = provider_name or provider_dict.get('name') or provider_dict.get('id')
        
        caps = fetch_capabilities(name)
        provider_dict['metadata_richness'] = caps.metadata.name if hasattr(caps, 'metadata') else 'MEDIUM'
        provider_dict['supports_streaming'] = caps.supports_streaming if hasattr(caps, 'supports_streaming') else False
        provider_dict['supports_downloads'] = caps.supports_downloads if hasattr(caps, 'supports_downloads') else False
        provider_dict['supports_cover_art'] = caps.supports_cover_art if hasattr(caps, 'supports_cover_art') else False
        provider_dict['supports_library_scan'] = caps.supports_library_scan if hasattr(caps, 'supports_library_scan') else False
        provider_dict['playlist_support'] = caps.supports_playlists.name if hasattr(caps, 'supports_playlists') and caps.supports_playlists else 'NONE'
        
        if hasattr(caps, 'search'):
            provider_dict['search_capabilities'] = {
                'tracks': caps.search.tracks if hasattr(caps.search, 'tracks') else False,
                'artists': caps.search.artists if hasattr(caps.search, 'artists') else False,
                'albums': caps.search.albums if hasattr(caps.search, 'albums') else False,
                'playlists': caps.search.playlists if hasattr(caps.search, 'playlists') else False,
            }
    except KeyError:
        provider_dict['metadata_richness'] = 'MEDIUM'
        provider_dict['supports_streaming'] = False
        provider_dict['supports_downloads'] = False
        provider_dict['supports_cover_art'] = False
        provider_dict['supports_library_scan'] = False
        provider_dict['playlist_support'] = 'NONE'
        provider_dict['search_capabilities'] = {
            'tracks': False, 'artists': False, 'albums': False, 'playlists': False
        }
    except Exception:
        pass
    
    return provider_dict

@router.get("/full")
def list_plugins_route():
    """Full plugin metadata for diagnostics."""
    try:
        plugins = list_plugins()
        return {
            'plugins': [p.to_dict() for p in plugins],
            'total': len(plugins)
        }
    except Exception as e:
        logger.error(f"Error listing plugins: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list plugins")

@router.get("/by-capability/{capability}")
def get_plugins_by_capability(capability: str):
    """Get plugins that support a specific capability."""
    try:
        plugins = get_plugins_for_capability(capability)
        return {
            'capability': capability,
            'plugins': [p.to_dict() for p in plugins],
            'total': len(plugins)
        }
    except Exception as e:
        logger.error(f"Error getting plugins for capability {capability}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get plugins for capability")

@router.get("/{plugin_id}")
def get_plugin_details(plugin_id: str):
    """Get full details for a specific plugin."""
    try:
        plugin = get_plugin(plugin_id)
        if not plugin:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")
        
        plugin_dict = plugin.to_dict() if hasattr(plugin, 'to_dict') else plugin
        plugin_dict = _enrich_provider_capabilities(plugin_dict, plugin_id)
        
        return plugin_dict
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting plugin details for {plugin_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get plugin details")

@router.get("/{plugin_id}/credentials", dependencies=[Depends(require_auth)])
def get_plugin_credentials(plugin_id: str):
    """Get credentials/configuration for a specific plugin."""
    try:
        from database.config_database import get_config_database
        config_db = get_config_database()
        from core.nexus_framework.plugin_loader import PluginRegistry
        plugin_cls = PluginRegistry.get_plugin_class(plugin_id)
        if plugin_cls and hasattr(plugin_cls, 'name') and plugin_cls.name:
            normalized_plugin_id = plugin_cls.name
        else:
            normalized_plugin_id = plugin_id
            
        service_id = config_db.get_or_create_service_id(normalized_plugin_id)
        if not service_id:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")

        keys_of_interest = ['client_id', 'client_secret', 'base_url', 'server_url', 'token', 'api_key', 'username', 'password', 'slskd_url']
        credentials = {}
        for key in keys_of_interest:
            val = config_db.get_service_config(service_id, key)
            if val is not None:
                credentials[key] = val
                
        return credentials
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching credentials for {plugin_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch plugin credentials")


@router.get("/{plugin_id}/settings")
def get_plugin_settings(plugin_id: str):
    """Get settings and schema for a specific plugin."""
    try:
        from database.config_database import get_config_database
        config_db = get_config_database()
        
        from core.nexus_framework.plugin_loader import PluginRegistry
        plugin_cls = PluginRegistry.get_plugin_class(plugin_id)
        if plugin_cls and hasattr(plugin_cls, 'name') and plugin_cls.name:
            normalized_plugin_id = plugin_cls.name
        else:
            normalized_plugin_id = plugin_id

        try:
            service_id = config_db.get_or_create_service_id(normalized_plugin_id)
            if not service_id:
                raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")
        except Exception as e:
            logger.error(f"Error in get_or_create_service_id for {plugin_id}: {e}", exc_info=True)
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")

        keys_of_interest = ['client_id', 'client_secret', 'base_url', 'server_url', 'token', 'api_key', 'username', 'password', 'slskd_url']
        config = {}
        for key in keys_of_interest:
            val = config_db.get_service_config(service_id, key)
            if val is not None:
                config[key] = _normalize_sensitive_value_for_ui(key, val)
        
        from core.network_utils import get_lan_ip
        lan_ip = get_lan_ip()
        callback_id = normalized_plugin_id.split('.')[-1].lower()
        config['redirect_uri'] = f"https://{lan_ip}:5001/api/oauth/callback/plugins/{callback_id}"
        
        schema = _get_mock_schema(callback_id)
        return {
            'plugin': plugin_id,
            'settings': config,
            'schema': schema
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting settings for {plugin_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get plugin settings")

@router.post("/{plugin_id}/settings", dependencies=[Depends(require_auth)])
async def update_plugin_settings(plugin_id: str, request: Request):
    """Update settings for a specific plugin."""
    try:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
            
        logger.info(f"Updating settings for plugin: {plugin_id}")
        return {"error": "Need to refactor DI for settings update"}
    except Exception as e:
        logger.error(f"Error updating settings for {plugin_id}: {type(e).__name__}")
        raise HTTPException(status_code=500, detail="Failed to update settings")

def _get_mock_schema(provider_name):
    """Temporary mock schema until providers declare their own."""
    schemas = {
        'spotify': [
            {'key': 'client_id', 'label': 'Client ID', 'type': 'text', 'sensitive': True},
            {'key': 'client_secret', 'label': 'Client Secret', 'type': 'password', 'sensitive': True},
            {'key': 'redirect_uri', 'label': 'Redirect URI', 'type': 'text', 'default': 'http://127.0.0.1:8008/api/spotify/callback'},
        ],
        'plex': [
            {'key': 'server_url', 'label': 'Server URL', 'type': 'text', 'default': 'http://localhost:32400'},
            {'key': 'token', 'label': 'X-Plex-Token', 'type': 'password', 'sensitive': True},
        ],
        'soulseek': [
            {'key': 'username', 'label': 'Username', 'type': 'text'},
            {'key': 'password', 'label': 'Password', 'type': 'password', 'sensitive': True},
            {'key': 'slskd_url', 'label': 'slskd URL', 'type': 'text', 'default': 'http://localhost:5030'},
            {'key': 'api_key', 'label': 'API Key', 'type': 'password', 'sensitive': True},
        ],
        'slskd': [
            {'key': 'username', 'label': 'Username', 'type': 'text'},
            {'key': 'password', 'label': 'Password', 'type': 'password', 'sensitive': True},
            {'key': 'slskd_url', 'label': 'slskd URL', 'type': 'text', 'default': 'http://localhost:5030'},
            {'key': 'api_key', 'label': 'API Key', 'type': 'password', 'sensitive': True},
        ]
    }
    return schemas.get(provider_name, [])

def _enrich_provider_capabilities(provider_dict, provider_name=None):
    """Enrich a provider dict with capability metadata."""
    try:
        from core.nexus_framework.plugin_loader import get_plugin_capabilities as fetch_capabilities
        name = provider_name or provider_dict.get('name') or provider_dict.get('id')
        
        caps = fetch_capabilities(name)
        provider_dict['metadata_richness'] = caps.metadata.name if hasattr(caps, 'metadata') else 'MEDIUM'
        provider_dict['supports_streaming'] = caps.supports_streaming if hasattr(caps, 'supports_streaming') else False
        provider_dict['supports_downloads'] = caps.supports_downloads if hasattr(caps, 'supports_downloads') else False
        provider_dict['supports_cover_art'] = caps.supports_cover_art if hasattr(caps, 'supports_cover_art') else False
        provider_dict['supports_library_scan'] = caps.supports_library_scan if hasattr(caps, 'supports_library_scan') else False
        provider_dict['playlist_support'] = caps.supports_playlists.name if hasattr(caps, 'supports_playlists') and caps.supports_playlists else 'NONE'
        
        if hasattr(caps, 'search'):
            provider_dict['search_capabilities'] = {
                'tracks': caps.search.tracks if hasattr(caps.search, 'tracks') else False,
                'artists': caps.search.artists if hasattr(caps.search, 'artists') else False,
                'albums': caps.search.albums if hasattr(caps.search, 'albums') else False,
                'playlists': caps.search.playlists if hasattr(caps.search, 'playlists') else False,
            }
    except KeyError:
        provider_dict['metadata_richness'] = 'MEDIUM'
        provider_dict['supports_streaming'] = False
        provider_dict['supports_downloads'] = False
        provider_dict['supports_cover_art'] = False
        provider_dict['supports_library_scan'] = False
        provider_dict['playlist_support'] = 'NONE'
        provider_dict['search_capabilities'] = {
            'tracks': False, 'artists': False, 'albums': False, 'playlists': False
        }
    except Exception:
        pass
    
    return provider_dict

@router.get("/full")
def list_plugins_route():
    """Full plugin metadata for diagnostics."""
    try:
        plugins = list_plugins()
        return {
            'plugins': [p.to_dict() for p in plugins],
            'total': len(plugins)
        }
    except Exception as e:
        logger.error(f"Error listing plugins: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list plugins")

@router.get("/by-capability/{capability}")
def get_plugins_by_capability(capability: str):
    """Get plugins that support a specific capability."""
    try:
        plugins = get_plugins_for_capability(capability)
        return {
            'capability': capability,
            'plugins': [p.to_dict() for p in plugins],
            'total': len(plugins)
        }
    except Exception as e:
        logger.error(f"Error getting plugins for capability {capability}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get plugins for capability")

@router.get("/{plugin_id}")
def get_plugin_details(plugin_id: str):
    """Get full details for a specific plugin."""
    try:
        plugin = get_plugin(plugin_id)
        if not plugin:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")
        
        plugin_dict = plugin.to_dict() if hasattr(plugin, 'to_dict') else plugin
        plugin_dict = _enrich_provider_capabilities(plugin_dict, plugin_id)
        
        return plugin_dict
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting plugin details for {plugin_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get plugin details")

@router.get("/{plugin_id}/credentials", dependencies=[Depends(require_auth)])
def get_plugin_credentials(plugin_id: str):
    """Get credentials/configuration for a specific plugin."""
    try:
        from database.config_database import get_config_database
        config_db = get_config_database()
        from core.nexus_framework.plugin_loader import PluginRegistry
        plugin_cls = PluginRegistry.get_plugin_class(plugin_id)
        if plugin_cls and hasattr(plugin_cls, 'name') and plugin_cls.name:
            normalized_plugin_id = plugin_cls.name
        else:
            normalized_plugin_id = plugin_id
            
        service_id = config_db.get_or_create_service_id(normalized_plugin_id)
        if not service_id:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")

        keys_of_interest = ['client_id', 'client_secret', 'base_url', 'server_url', 'token', 'api_key', 'username', 'password', 'slskd_url']
        credentials = {}
        for key in keys_of_interest:
            val = config_db.get_service_config(service_id, key)
            if val is not None:
                credentials[key] = _normalize_sensitive_value_for_ui(key, val)

        from core.network_utils import get_lan_ip
        lan_ip = get_lan_ip()
        callback_id = normalized_plugin_id.split('.')[-1].lower()
        credentials['redirect_uri'] = f"https://{lan_ip}:5001/api/oauth/callback/plugins/{callback_id}"
        
        return {
            'plugin': plugin_id,
            'credentials': credentials
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting credentials for {plugin_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get credentials")

class SetCredentialsRequest(BaseModel):
    credentials: Optional[Dict[str, Any]] = None

@router.post("/{plugin_id}/credentials", dependencies=[Depends(require_auth)])
def set_plugin_credentials(plugin_id: str, data: SetCredentialsRequest):
    """Set credentials/configuration for a specific plugin."""
    try:
        from database.config_database import get_config_database
        
        credentials = data.credentials or {}
        
        if not credentials:
            raise HTTPException(status_code=400, detail="No credentials provided")
        
        config_db = get_config_database()
        from core.nexus_framework.plugin_loader import PluginRegistry
        plugin_cls = PluginRegistry.get_plugin_class(plugin_id)
        if plugin_cls and hasattr(plugin_cls, 'name') and plugin_cls.name:
            normalized_plugin_id = plugin_cls.name
        else:
            normalized_plugin_id = plugin_id
            
        service_id = config_db.get_or_create_service_id(normalized_plugin_id)
        if not service_id:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")
        
        if 'redirect_uri' in credentials:
            del credentials['redirect_uri']

        for key, value in credentials.items():
            is_sensitive = any(sensitive_word in key.lower() for sensitive_word in ['key', 'token', 'password', 'secret'])
            if is_sensitive:
                value = _normalize_sensitive_value_for_save(key, value)
            config_db.set_service_config(service_id, key, value, is_sensitive=is_sensitive)
        
        logger.info(f"Credentials saved for {plugin_id}")
        
        return {
            'success': True,
            'plugin': plugin_id,
            'message': 'Credentials saved successfully'
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting credentials for {plugin_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to set credentials")
@router.get('/{plugin_id}/ui/{filename:path}', dependencies=[Depends(require_auth)])
def serve_plugin_asset(plugin_id: str, filename: str):
    logger.info(f'[serve_plugin_asset] Request received for plugin_id={plugin_id}, filename={filename}')
    install_path = None
    try:
        with config_db_connection() as conn:
            c = conn.cursor()
            if str(plugin_id).isdigit():
                pid_int = int(plugin_id)
                c.execute('SELECT absolute_install_path FROM services WHERE plugin_id = ? OR id = ?', (pid_int, pid_int))
            else:
                c.execute('SELECT absolute_install_path FROM services WHERE LOWER(name) = ?', (str(plugin_id).lower(),))
            row = c.fetchone()
            if row and row[0]:
                install_path = row[0]
            else:
                from database.config_database import get_config_database
                db = get_config_database()
                service_id = db.get_service_id(plugin_id)
                if service_id:
                    c.execute('SELECT absolute_install_path FROM services WHERE id = ?', (service_id,))
                    row = c.fetchone()
                    if row and row[0]:
                        install_path = row[0]
    except Exception as e:
        logger.error(f'Error querying service {plugin_id}: {e}', exc_info=True)
    if install_path:
        resolved_install = Path(install_path).resolve()
        resolved_install = resolve_case_insensitive_path(resolved_install)
        from werkzeug.security import safe_join
        safe_path = safe_join(str(resolved_install), filename)
        if safe_path:
            file_path = Path(safe_path)
            if file_path.exists():
                return FileResponse(path=str(file_path), filename=file_path.name)
        raise HTTPException(status_code=403, detail='Forbidden')
    raise HTTPException(status_code=404, detail='Not Found')


@router.get('/{plugin_id}/static/{filename:path}')
def serve_plugin_static_asset(plugin_id: str, filename: str):
    """Alias for serving assets from the static/ directory."""
    # The underlying safe_join will resolve install_path + 'static/filename'
    return serve_plugin_asset(plugin_id, f"static/{filename}")
