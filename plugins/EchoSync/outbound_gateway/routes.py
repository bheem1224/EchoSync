from flask import Blueprint, request, abort, Response, current_app

bp = Blueprint('outbound_gateway_routes', __name__)

class ExternalGatewayRegistry:
    _routes = set()

    @classmethod
    def register(cls, plugin_id: str, subpath: str):
        """
        Register a specific plugin's internal route to be exposed externally via the gateway.
        """
        # Clean paths to match easily later
        clean_subpath = subpath.lstrip('/')
        route_key = f"{plugin_id}/{clean_subpath}"
        cls._routes.add(route_key)

    @classmethod
    def is_registered(cls, plugin_id: str, subpath: str) -> bool:
        clean_subpath = subpath.lstrip('/')
        route_key = f"{plugin_id}/{clean_subpath}"
        return route_key in cls._routes

# We want the gateway itself to be mounted at /api/v1/external
# The plugin_loader will automatically pick up `RouteBlueprint` and since we aren't using `mount_router` here,
# we need to make sure `plugin_loader.py` can load this correctly, or we just set the url_prefix.
bp.url_prefix = "/api/v1/external"

def require_api_key():
    """Stubbed auth middleware"""
    # Reject everything currently
    abort(401, description="Unauthorized: API Key invalid or missing (Gateway Auth Not Implemented)")

@bp.before_request
def enforce_gateway_auth():
    require_api_key()

@bp.route('/<plugin_id>/<path:subpath>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def gateway_proxy(plugin_id, subpath):
    """
    Proxy requests to the internal plugin API if registered.
    """
    # Check if the route is exposed
    if not ExternalGatewayRegistry.is_registered(plugin_id, subpath):
        abort(404, description="Route not found or not exposed externally")

    # Normally we would forward the request using requests or test_client here,
    # but the request will be rejected by the require_api_key anyway right now.
    # We will implement the actual proxy here eventually.
    # For now, simply return a 501 Not Implemented
    abort(501, description="Proxy forwarding not implemented yet")
