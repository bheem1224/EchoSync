from .client import AcoustIDProvider
from .routes import config_bp as _config_bp

ProviderClass = AcoustIDProvider
RouteBlueprint = _config_bp

__all__ = ["AcoustIDProvider", "ProviderClass", "RouteBlueprint"]
