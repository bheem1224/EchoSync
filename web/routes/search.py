import asyncio
import json
import threading

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from web.services.search_service import SearchAdapter

router = APIRouter(prefix="/api/v1/core/search", tags=["Search"])


@router.get("/")
async def aggregate_search(request: Request):
    q = request.query_params.get("q")
    if not q:
        raise HTTPException(status_code=400, detail={"error": "missing query"})

    plugins_param = request.query_params.get("plugins") or ""
    plugin_names = [p for p in plugins_param.split(",") if p] or None

    types_param = request.query_params.get("types") or ""
    search_types = [t for t in types_param.split(",") if t] or None

    adapter = SearchAdapter()
    cancel_event = threading.Event()

    async def generate():
        try:
            # We wrap the synchronous generator to avoid blocking the event loop
            for source, results in adapter.aggregate_stream(
                q,
                plugin_names=plugin_names,
                search_types=search_types,
                cancel_event=cancel_event,
            ):
                if await request.is_disconnected():
                    cancel_event.set()
                    break
                yield f"data: {json.dumps({'source': source, 'results': results})}\n\n"
                await asyncio.sleep(0.01)
            yield 'data: {"status": "done"}\n\n'
        except (asyncio.CancelledError, GeneratorExit):
            cancel_event.set()
        except Exception as e:
            from core.tiered_logger import get_logger

            get_logger("search_route").error(
                f"Error in aggregate_search stream generator: {e}"
            )
            cancel_event.set()
        finally:
            cancel_event.set()

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/discovery")
async def federated_discovery(request: Request):
    q = request.query_params.get("q")
    if not q:
        raise HTTPException(status_code=400, detail={"error": "missing query"})

    plugins_param = request.query_params.get("plugins") or ""
    plugin_names = [p for p in plugins_param.split(",") if p] or None

    adapter = SearchAdapter()
    try:
        results = await adapter.federated_discovery(q, enabled_plugins=plugin_names)
    except Exception as e:
        from core.tiered_logger import get_logger

        get_logger("search_route").error(f"Federated discovery error: {e}")
        results = []

    return {"query": q, "results": results}


@router.post("/route")
async def route_search_result(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    item = payload.get("item")
    action = payload.get("action")
    target = payload.get("target")

    adapter = SearchAdapter()
    result = adapter.route_result(item=item, action=action, target=target)

    status = 200 if result.get("accepted") else 400
    return result, status
