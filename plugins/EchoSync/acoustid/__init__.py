from .client import AcoustIDProvider
from .routes import config_router as _config_bp

ProviderClass = AcoustIDProvider
RouteBlueprint = _config_bp

__all__ = ["AcoustIDProvider", "ProviderClass", "RouteBlueprint"]
