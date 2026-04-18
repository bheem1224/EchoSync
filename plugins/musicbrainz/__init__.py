from .client import MusicBrainzClient, MusicBrainzProvider
from .routes import bp as _routes_bp

ProviderClass = MusicBrainzClient
RouteBlueprint = _routes_bp

__all__ = ["MusicBrainzClient", "MusicBrainzProvider", "ProviderClass", "RouteBlueprint"]
