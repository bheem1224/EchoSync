from functools import wraps
from flask import request, abort
from core.hook_manager import hook_manager

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Pass the request through the hook.
        user = hook_manager.apply_filters('AUTHENTICATE_USER', None, request)

        # SOFT AUTH FALLBACK:
        # If a plugin actively rejects auth, it should return False.
        if user is False:
            abort(401, description="Unauthorized")

        # If user is None (no plugin exists) or Truthy (plugin accepted), proceed.
        return f(*args, **kwargs)
    return decorated_function
