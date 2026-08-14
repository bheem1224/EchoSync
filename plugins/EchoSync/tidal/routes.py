"""Tidal provider routes."""
import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from core.tiered_logger import get_logger
from core.nexus_framework.plugin_SDK import sdk

logger = get_logger("tidal_routes")
router = APIRouter()


@router.get('')
@router.get('/')
def list_accounts():
    """List all Tidal accounts."""
    try:
        from core.network_utils import get_lan_ip
        redirect_uri = f"https://{get_lan_ip()}:5001/api/oauth/callback/plugins/tidal"

        db_accounts = sdk.accounts.get_all()
        accounts = []
        
        client_id = sdk.config.get('client_id', '') or ''
        client_secret_present = bool(sdk.secrets.get('client_secret'))
        
        # Fallback to DB service_config if not in SDK namespace
        if not client_id or not client_secret_present:
            from database.config_database import get_config_database
            db = get_config_database()
            svc_id = db.get_service_id(3106502486) or db.get_service_id('EchoSync.Tidal') or db.get_service_id('tidal')
            if svc_id:
                client_id = client_id or db.get_service_config(svc_id, 'client_id') or ''
                client_secret_present = client_secret_present or bool(db.get_service_config(svc_id, 'client_secret'))

        for a in db_accounts:
            normalized = {
                'id': a.get('id'),
                'account_name': a.get('account_name') or a.get('display_name') or 'Unnamed',
                'display_name': a.get('display_name') or a.get('account_name') or 'Unnamed',
                'user_id': a.get('user_id'),
                'is_active': bool(a.get('is_active')),
                'is_authenticated': bool(a.get('is_authenticated')),
                'client_id': client_id,
                'client_secret_configured': client_secret_present
            }
            accounts.append(normalized)
        
        return JSONResponse(content={
            'accounts': accounts,
            'redirect_uri': redirect_uri
        })
    except Exception as e:
        logger.error(f"Error getting Tidal accounts: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}, status_code=500)


@router.post('')
@router.post('/')
async def create_account(request: Request):
    """
    Create a new Tidal account with credentials.
    Body: { account_name, client_id, client_secret }
    """
    try:
        payload = await request.json() or {}
        account_name = (payload.get('account_name') or '').strip()
        client_id = (payload.get('client_id') or '').strip()
        client_secret = (payload.get('client_secret') or '').strip()
        
        if not account_name:
            return JSONResponse(content={'error': 'account_name is required'}, status_code=400)
        if not client_id or not client_secret:
            return JSONResponse(content={'error': 'client_id and client_secret are required'}, status_code=400)
        
        # Create account via SDK
        account_id = sdk.accounts.ensure_account(account_name=account_name, display_name=account_name)
        if not account_id:
            return JSONResponse(content={'error': 'Failed to create account'}, status_code=500)
        
        sdk.config.set('client_id', client_id)
        sdk.secrets.set('client_secret', client_secret)
        
        # Also mirror to database service_config
        from database.config_database import get_config_database
        db = get_config_database()
        svc_id = db.get_service_id(3106502486) or db.get_service_id('EchoSync.Tidal') or db.get_service_id('tidal')
        if svc_id:
            db.set_service_config(svc_id, 'client_id', client_id, is_sensitive=False)
            db.set_service_config(svc_id, 'client_secret', client_secret, is_sensitive=True)

        logger.info(f"Created Tidal account {account_id} with credentials")
        
        return JSONResponse(content={
            'account': {
                'id': account_id,
                'account_name': account_name,
                'display_name': account_name,
                'is_active': False,
                'is_authenticated': False,
                'client_id': client_id,
                'client_secret_configured': True
            }
        }, status_code=201)
    except Exception as e:
        logger.error(f"Error creating Tidal account: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}, status_code=500)


@router.get('/{account_id}')
def get_account(account_id: int):
    """Get a specific Tidal account with credentials."""
    try:
        accounts = sdk.accounts.get_all()
        account = next((a for a in accounts if a.get('id') == account_id), None)
        
        if not account:
            return JSONResponse(content={'error': 'Account not found'}, status_code=404)
        
        client_id = sdk.config.get('client_id', '') or ''
        client_secret = sdk.secrets.get('client_secret', '') or ''
        
        return JSONResponse(content={
            'account': {
                'id': account.get('id'),
                'account_name': account.get('account_name') or account.get('display_name') or 'Unnamed',
                'display_name': account.get('display_name') or account.get('account_name') or 'Unnamed',
                'user_id': account.get('user_id'),
                'is_active': bool(account.get('is_active')),
                'is_authenticated': bool(account.get('is_authenticated')),
                'client_id': client_id,
                'client_secret': client_secret
            }
        })
    except Exception as e:
        logger.error(f"Error getting Tidal account: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}, status_code=500)


@router.put('/{account_id}')
async def update_account(account_id: int, request: Request):
    """
    Update Tidal account name and/or credentials.
    Body: { account_name?, client_id?, client_secret? }
    """
    try:
        accounts = sdk.accounts.get_all()
        account = next((a for a in accounts if a.get('id') == account_id), None)
        
        if not account:
            return JSONResponse(content={'error': 'Account not found'}, status_code=404)
        
        payload = await request.json() or {}
        
        if payload.get('account_name'):
            new_name = payload.get('account_name').strip()
            if new_name:
                sdk.accounts.update_account_name(account_id, new_name)
        
        if 'client_id' in payload and payload.get('client_id'):
            client_id_value = payload.get('client_id').strip()
            sdk.config.set('client_id', client_id_value)
            
        if 'client_secret' in payload and payload.get('client_secret'):
            client_secret_value = payload.get('client_secret').strip()
            sdk.secrets.set('client_secret', client_secret_value)
        
        accounts = sdk.accounts.get_all()
        account = next((a for a in accounts if a.get('id') == account_id), None)
        
        return JSONResponse(content={
            'account': {
                'id': account.get('id'),
                'account_name': account.get('account_name') or account.get('display_name') or 'Unnamed',
                'display_name': account.get('display_name') or account.get('account_name') or 'Unnamed',
                'user_id': account.get('user_id'),
                'is_active': bool(account.get('is_active')),
                'is_authenticated': bool(account.get('is_authenticated')),
                'client_id': sdk.config.get('client_id', '') or '',
                'client_secret_configured': bool(sdk.secrets.get('client_secret'))
            }
        })
    except Exception as e:
        logger.error(f"Error updating Tidal account: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}, status_code=500)


@router.put('/{account_id}/activate')
@router.post('/{account_id}/activate')
async def activate_account(account_id: int, request: Request):
    """Activate a Tidal account."""
    try:
        accounts = sdk.accounts.get_all()
        account = next((a for a in accounts if a.get('id') == account_id), None)
        
        if not account:
            return JSONResponse(content={'error': 'Account not found'}, status_code=404)
        
        payload = await request.json() or {}
        is_active = payload.get('is_active', True)
        sdk.accounts.toggle_account_active(account_id, is_active)
        
        return JSONResponse(content={'status': 'ok', 'is_active': is_active})
    except Exception as e:
        logger.error(f"Error activating Tidal account: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}, status_code=500)


@router.delete('/{account_id}')
def delete_account(account_id: int):
    """Delete a Tidal account."""
    try:
        deleted = sdk.accounts.delete_account(account_id)
        if not deleted:
            return JSONResponse(content={'error': 'Account not found'}, status_code=404)
        
        logger.info(f"Deleted Tidal account {account_id}")
        return JSONResponse(content={'status': 'ok', 'message': 'Account deleted'})
    except Exception as e:
        logger.error(f"Error deleting Tidal account: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}, status_code=500)


@router.post('/redirect-uri')
async def set_redirect_uri(request: Request):
    """
    Set global redirect URI for all Tidal accounts.
    Body: { redirect_uri }
    """
    try:
        payload = await request.json() or {}
        redirect_uri = payload.get('redirect_uri', '').strip()
        
        if not redirect_uri:
            return JSONResponse(content={'error': 'redirect_uri is required'}, status_code=400)
        
        sdk.config.set('redirect_uri', redirect_uri)
        return JSONResponse(content={'status': 'ok', 'redirect_uri': redirect_uri})
    except Exception as e:
        logger.error(f"Error setting redirect URI: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}, status_code=500)


@router.get('/auth')
async def begin_auth(request: Request):
    """Initiate Tidal OAuth device-code flow for the given account_id.
    Query params: account_id (required)
    Returns: { auth_url } to open in a new tab, or { device_code_url } for device flow.
    """
    try:
        account_id = request.query_params.get('account_id')
        if not account_id:
            return JSONResponse(content={'error': 'account_id parameter is required'}, status_code=400)

        client_id = sdk.config.get('client_id')
        if not client_id:
            from database.config_database import get_config_database
            db = get_config_database()
            svc_id = db.get_service_id(3106502486) or db.get_service_id('EchoSync.Tidal') or db.get_service_id('tidal')
            if svc_id:
                client_id = db.get_service_config(svc_id, 'client_id')

        if not client_id:
            return JSONResponse(content={'error': 'Tidal client_id not configured'}, status_code=400)

        from core.network_utils import get_lan_ip
        redirect_uri = f"https://{get_lan_ip()}:5001/api/oauth/callback/plugins/tidal"
        auth_url = f"https://login.tidal.com/oauth2/authorization?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope=r_usr+w_usr"

        try:
            from .client import TidalClient
            tc = TidalClient(account_id=int(account_id))
            if hasattr(tc, 'get_auth_url'):
                auth_url = tc.get_auth_url()
        except Exception:
            pass

        logger.info(f"Generated Tidal auth URL for account {account_id}")
        return JSONResponse(content={'auth_url': auth_url}, status_code=200)
    except Exception as e:
        logger.error(f"Error generating Tidal auth URL: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error"}, status_code=500)
