from flask import Blueprint, jsonify, request
from web.services.search_service import SearchAdapter

bp = Blueprint("search", __name__, url_prefix="/api/search")

@bp.get("/")
def aggregate_search():
    q = request.args.get("q")
    if not q:
        return jsonify({"error": "missing query"}), 400

    providers_param = request.args.get("providers") or ""
    provider_names = [p for p in providers_param.split(",") if p] or None

    types_param = request.args.get("types") or ""
    search_types = [t for t in types_param.split(",") if t] or None

    adapter = SearchAdapter()
    results = adapter.aggregate(q, provider_names=provider_names, search_types=search_types)
    return jsonify({"query": q, "results": results}), 200


@bp.get("/discovery")
async def federated_discovery():
    q = request.args.get("q")
    if not q:
        return jsonify({"error": "missing query"}), 400

    providers_param = request.args.get("providers") or ""
    provider_names = [p for p in providers_param.split(",") if p] or None

    adapter = SearchAdapter()
    results = await adapter.federated_discovery(q, enabled_providers=provider_names)
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
