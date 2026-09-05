from .client import MusicBrainzClient, MusicBrainzProvider
from .models import init_db
from .routes import config_router as _config_bp
from .routes import router as _routes_bp

ProviderClass = MusicBrainzClient
RouteBlueprint = _routes_bp
RouteBlueprint2 = _config_bp

__all__ = [
    "MusicBrainzClient",
    "MusicBrainzProvider",
    "ProviderClass",
    "RouteBlueprint",
    "RouteBlueprint2",
]

init_db()
