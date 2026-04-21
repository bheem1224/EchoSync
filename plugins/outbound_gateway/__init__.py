from .client import OutboundGatewayProvider
from .routes import bp as RouteBlueprint, ExternalGatewayRegistry

ProviderClass = OutboundGatewayProvider

__all__ = ["ProviderClass", "RouteBlueprint", "ExternalGatewayRegistry"]
