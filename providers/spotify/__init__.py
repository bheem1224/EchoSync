from providers.spotify.client import *

# Export provider-level blueprints (if present)
try:
    from providers.spotify.oauth_routes import bp as oauth_bp
except Exception:
    oauth_bp = None

# Export provider-level blueprints (if present)
try:
	from providers.spotify.oauth_routes import bp as oauth_bp
except Exception:
	oauth_bp = None

