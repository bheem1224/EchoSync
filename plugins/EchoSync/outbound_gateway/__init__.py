from .client import OutboundGatewayProvider
from .routes import ExternalGatewayRegistry
from .routes import router as RouteBlueprint

ProviderClass = OutboundGatewayProvider

__all__ = ["ExternalGatewayRegistry", "ProviderClass", "RouteBlueprint"]
