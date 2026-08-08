"""Sprint 6 — Central UI Registry API.

Provides a single, lightning-fast endpoint for the Svelte frontend to discover
all registered Web Components, Themes, and Dashboard views without touching disk.

Endpoint:
    GET /api/ui/registry
"""

from fastapi import APIRouter, Depends
from web.auth import require_auth
from core.tiered_logger import get_logger
from contextlib import contextmanager
from typing import Dict, List, Any

logger = get_logger("ui_registry")

router = APIRouter(prefix="/api/v1/system/ui-registry", tags=["UI Registry"])


@contextmanager
def config_db_connection():
    from database.config_database import get_config_database
    db = get_config_database()
    conn = db._open_connection()
    try:
        yield conn
    finally:
        conn.close()


def _query_ui_registry() -> Dict[str, List[Dict[str, Any]]]:
    """Shared query logic — used by both the new and legacy endpoints.

    Performs a single indexed query against ``ui_components`` joined with
    ``services`` (to filter ``is_active = 1``), then groups results by
    ``component_type``.

    Returns a dict of ``{ component_type: [ {tag_name, entry, plugin_id}, ... ] }``.
    """
    registry: Dict[str, List[Dict[str, Any]]] = {}

    try:
        with config_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT
                    uc.tag_name,
                    uc.component_type,
                    uc.entry_path,
                    uc.plugin_id,
                    uc.is_core,
                    s.name AS plugin_name
                FROM ui_components uc
                LEFT JOIN services s ON s.plugin_id = uc.plugin_id
                WHERE uc.is_core = 1
                   OR s.is_active = 1
                ORDER BY uc.component_type, uc.tag_name
            """)
            rows = c.fetchall()

            for row in rows:
                tag_name = row["tag_name"]
                comp_type = row["component_type"]
                entry_path = row["entry_path"]
                plugin_id = row["plugin_id"]
                plugin_name = row["plugin_name"]
                is_core = bool(row["is_core"])

                # If stored as relative path, reconstruct the absolute endpoint URL
                if entry_path and not (entry_path.startswith("/") or entry_path.startswith("http://") or entry_path.startswith("https://")):
                    ident = plugin_name.lower() if plugin_name else str(plugin_id)
                    entry = f"/api/system/plugins/{ident}/{entry_path}"
                else:
                    entry = entry_path

                # Pluralise the type key for the response (card → cards, page → pages)
                type_key = f"{comp_type}s" if not comp_type.endswith("s") else comp_type

                if type_key not in registry:
                    registry[type_key] = []

                registry[type_key].append({
                    "tag_name": tag_name,
                    "entry": entry,
                    "plugin_id": plugin_id,
                    "plugin_name": plugin_name,
                    "is_core": is_core,
                })

    except Exception as exc:
        logger.error(f"[UIRegistry] Failed to query ui_components: {exc}", exc_info=True)

    return registry


@router.get("")
def get_ui_registry(user=Depends(require_auth)):
    """Return all active, registered UI components categorised by type.

    Response shape::

        {
          "cards":    [{"tag_name": "es-spotify-card", "entry": "/plugins/spotify/ui/card.js", ...}],
          "pages":    [...],
          "settings": [...],
          "themes":   [...],
          "views":    [...]
        }
    """
    return _query_ui_registry()
