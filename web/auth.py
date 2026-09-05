from fastapi import HTTPException, Request

from core.hook_manager import hook_manager


def require_auth(request: Request):
    # TODO (v2.6.0): Re-enable plugin-based authentication hooks.
    # Temporarily disabled to allow frontend development.
    return True

    # Pass the request through the hook.
    user = hook_manager.apply_filters("AUTHENTICATE_USER", None, request)

    # SOFT AUTH FALLBACK:
    # If a plugin actively rejects auth, it should return False.
    if user is False:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # If user is None (no plugin exists) or Truthy (plugin accepted), proceed.
    return True
