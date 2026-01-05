from providers.tidal.client import *
from providers.tidal.adapter import *

# Import and expose OAuth blueprint for Flask registration
try:
    from providers.tidal.oauth_routes import bp as oauth_bp
except ImportError:
    oauth_bp = None

