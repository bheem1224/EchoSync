from .client import MusicBrainzClient, MusicBrainzProvider
from .routes import bp as _routes_bp, config_bp as _config_bp

ProviderClass = MusicBrainzClient
RouteBlueprint = _routes_bp
RouteBlueprint2 = _config_bp

__all__ = ["MusicBrainzClient", "MusicBrainzProvider", "ProviderClass", "RouteBlueprint", "RouteBlueprint2"]
