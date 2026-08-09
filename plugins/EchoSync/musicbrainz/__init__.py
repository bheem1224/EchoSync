from .models import init_db
from .client import MusicBrainzClient, MusicBrainzProvider
from .routes import router as _routes_bp, config_router as _config_bp

ProviderClass = MusicBrainzClient
RouteBlueprint = _routes_bp
RouteBlueprint2 = _config_bp

__all__ = ["MusicBrainzClient", "MusicBrainzProvider", "ProviderClass", "RouteBlueprint", "RouteBlueprint2"]

init_db()
