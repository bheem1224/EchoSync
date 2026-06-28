from flask import Blueprint, jsonify, request, Response, stream_with_context
import json
from web.services.search_service import SearchAdapter

bp = Blueprint("search", __name__, url_prefix="/api/search")

@bp.get("/")
def aggregate_search():
    q = request.args.get("q")
    if not q:
        return jsonify({"error": "missing query"}), 400

    plugins_param = request.args.get("plugins") or ""
    plugin_names = [p for p in plugins_param.split(",") if p] or None

    types_param = request.args.get("types") or ""
    search_types = [t for t in types_param.split(",") if t] or None

    adapter = SearchAdapter()

    def generate():
        try:
            for source, results in adapter.aggregate_stream(q, plugin_names=plugin_names, search_types=search_types):
                yield f"data: {json.dumps({'source': source, 'results': results})}\n\n"
        except Exception as e:
            from core.tiered_logger import get_logger
            get_logger("search_route").error(f"Error in aggregate_search stream generator: {e}")
        finally:
            yield "data: {\"status\": \"done\"}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@bp.get("/discovery")
def federated_discovery():
    import asyncio
    q = request.args.get("q")
    if not q:
        return jsonify({"error": "missing query"}), 400

    plugins_param = request.args.get("plugins") or ""
    plugin_names = [p for p in plugins_param.split(",") if p] or None

    adapter = SearchAdapter()
    # Run the async federated discovery in a sync context to avoid Flask [async] extra requirement
    try:
        results = asyncio.run(adapter.federated_discovery(q, enabled_plugins=plugin_names))
    except Exception as e:
        from core.tiered_logger import get_logger
        get_logger("search_route").error(f"Federated discovery error: {e}")
        results = []

    return jsonify({"query": q, "results": results}), 200


@bp.post("/route")
def route_search_result():
    payload = request.get_json(silent=True) or {}
    item = payload.get("item")
    action = payload.get("action")
    target = payload.get("target")

    adapter = SearchAdapter()
    result = adapter.route_result(item=item, action=action, target=target)

    status = 202 if result.get("accepted") else 400
    return jsonify(result), status
