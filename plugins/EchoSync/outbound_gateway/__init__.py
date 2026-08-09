from .client import OutboundGatewayProvider
from .routes import router as RouteBlueprint, ExternalGatewayRegistry

ProviderClass = OutboundGatewayProvider

__all__ = ["ProviderClass", "RouteBlueprint", "ExternalGatewayRegistry"]
