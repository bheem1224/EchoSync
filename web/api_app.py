"""FastAPI app for the Svelte web UI.

Registers all core routers under /api/v1/core. This supersedes the legacy
web_server.py UI and should be used as the backend for the Svelte frontend.
"""

import os
import logging
import threading
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.settings import config_manager
from core.tiered_logger import get_logger

logger = get_logger("api_app")
from core.task_manager import register_all_system_jobs

# Core routers that have been migrated to FastAPI
from web.routes.accounts import router as accounts_bp
from web.routes.auth import router as auth_bp
from web.routes.plugins import router as core_plugins_bp
from web.routes.system import router as system_bp
from web.routes.dashboard import dashboard_bp, dashboards_bp
from web.routes.tracks import router as tracks_bp
from web.routes.library import router as library_bp
from web.routes.media import router as media_bp
from web.routes.search import router as search_bp
from web.routes.jobs import router as jobs_bp

# Batch 3A routers
from web.routes.metadata import router as metadata_bp
from web.routes.metadata_review import router as metadata_review_bp
from web.routes.local_metadata import router as local_metadata_bp
from web.routes.manager import router as manager_bp
from web.routes.system_tasks import router as system_tasks_bp
from web.routes.local_server import router as local_server_bp

# Batch 3B routers
from web.routes.downloads import router as downloads_bp, core_router as core_downloads_bp
from web.routes.suggestions import router as suggestions_bp
from web.routes.media_server import router as media_server_bp
from web.routes.webhooks import router as webhooks_bp
from web.routes.ui_registry import router as ui_registry_bp
from web.routes.sync import router as sync_bp
from web.routes.playlists import router as playlists_bp, api_v1_router as playlists_v1_bp, legacy_router as playlists_legacy_bp, double_v1_router as playlists_double_v1_bp

# Batch 2 routers
# (These will be included once they are migrated, so we import them here but if they fail we can catch it or we'll just migrate them now)
# Wait! If I import them before they are migrated, they'll fail. I will leave the imports out until they are migrated, or I will migrate them first!
# Actually, I should migrate them first. I'll just write the lifespan manager here without importing Batch 2 routers yet.

_backend_started = False
_backend_thread = None
_backend_loop = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for the ASGI application."""
    global _backend_started, _backend_thread, _backend_loop

    logger.info("Initializing application lifespan...")

    # Initialize databases safely inside the ASGI lifecycle
    try:
        from database.config_database import get_config_database
        from core.settings import migrate_legacy_json_to_db, config_manager
        cfg_db = get_config_database()
        if config_manager.config_path.exists():
            migrate_legacy_json_to_db(config_manager.config_path, cfg_db)
        from database.music_database import get_database
        from database.working_database import get_working_database
        get_database()
        get_working_database()
        logger.info("Databases initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize databases: {e}")
        raise

    # Initialize Plugins
    try:
        from core.nexus_framework.plugin_loader import PluginLoader, PluginRegistry
        app_root = Path(__file__).parent.parent
        loader = PluginLoader(app_root, main_app=app)
        disabled_plugins = config_manager.get_disabled_plugins()
        PluginRegistry.set_disabled_plugins(disabled_plugins)
        loader.load_all()
    except Exception as e:
        logger.error(f"Failed to initialize plugins: {e}")

    # Trigger ON_API_STARTUP hook
    try:
        from core.hook_manager import hook_manager
        hook_manager.trigger('ON_API_STARTUP', app)
    except Exception as e:
        logger.warning(f"Failed to trigger ON_API_STARTUP hook: {e}")

    # Load scheduled sync jobs on startup
    try:
        from web.routes.playlists import load_scheduled_syncs_on_startup
        load_scheduled_syncs_on_startup()
    except Exception as e:
        logger.warning(f"Failed to load scheduled syncs: {e}")

    # Start backend services
    dev_mode = os.getenv('DEV_MODE', 'false').lower() in ('true', '1', 'yes')
    testing = getattr(app, "testing", False)
    
    # Uvicorn runs workers, we don't have WERKZEUG_RUN_MAIN anymore.
    # In ASGI, lifespan runs once per worker. If we have multiple workers, they all run it.
    # Uvicorn without workers (reload=False) means 1 worker.
    if not testing and not _backend_started:
        from core.job_queue import start_job_queue
        from core.backend_services import start_services
        
        # Ensure scheduled jobs are registered before starting the queue
        register_all_system_jobs()
        start_job_queue()
        
        def run_backend_services():
            global _backend_loop
            _backend_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_backend_loop)
            try:
                _backend_loop.run_until_complete(start_services())
            except Exception as e:
                logger.error(f"Backend services failed: {e}")
            finally:
                _backend_loop.close()

        _backend_thread = threading.Thread(target=run_backend_services, daemon=True, name="BackendServices")
        _backend_thread.start()
        _backend_started = True
        logger.info("Backend services thread started")

    yield # This yields control back to the application while it runs

    logger.info("Shutting down application lifespan...")
    # Shutdown logic
    if _backend_thread and _backend_loop:
        # We can stop the backend loop gracefully if needed
        pass

def create_app(testing: bool = False) -> FastAPI:
    app = FastAPI(
        title="EchoSync Enterprise API", 
        version="2.5.0", 
        docs_url="/docs", 
        redoc_url="/redoc",
        lifespan=lifespan
    )
    app.testing = testing

    dev_mode = os.getenv('DEV_MODE', 'false').lower() in ('true', '1', 'yes')

    allowed_origins = config_manager.get('cors_origins', [])
    if dev_mode:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    elif allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.middleware("http")
    async def plugin_mount_slash_normalizer(request: Request, call_next):
        path_lower = request.url.path.lower().rstrip('/')
        from core.nexus_framework.plugin_loader import PluginRegistry
        if path_lower in PluginRegistry._mounted_subapps:
            sub_app = PluginRegistry._mounted_subapps[path_lower]
            scope = dict(request.scope)
            scope["path"] = "/"
            scope["raw_path"] = b"/"
            scope["root_path"] = request.url.path
            status_code = 200
            headers = []
            body_chunks = []
            async def send(message):
                nonlocal status_code, headers, body_chunks
                if message["type"] == "http.response.start":
                    status_code = message["status"]
                    headers = message.get("headers", [])
                elif message["type"] == "http.response.body":
                    body_chunks.append(message.get("body", b""))
            await sub_app(scope, request.receive, send)
            res = Response(content=b"".join(body_chunks), status_code=status_code)
            for k, v in headers:
                res.headers[k.decode("latin1")] = v.decode("latin1")
            return res
        return await call_next(request)

    # Mount migrated routers
    app.include_router(accounts_bp)
    app.include_router(auth_bp)
    app.include_router(core_plugins_bp)
    app.include_router(system_bp)
    app.include_router(dashboard_bp)
    app.include_router(dashboards_bp)
    app.include_router(tracks_bp)
    app.include_router(library_bp)
    app.include_router(media_bp)
    app.include_router(search_bp)
    app.include_router(jobs_bp)
    app.include_router(metadata_bp)
    app.include_router(metadata_review_bp)
    app.include_router(local_metadata_bp)
    app.include_router(manager_bp)
    app.include_router(system_tasks_bp)
    app.include_router(local_server_bp)
    
    app.include_router(downloads_bp)
    app.include_router(core_downloads_bp)
    app.include_router(suggestions_bp)
    app.include_router(media_server_bp)
    app.include_router(webhooks_bp)
    app.include_router(ui_registry_bp)
    app.include_router(sync_bp)
    app.include_router(playlists_bp)
    app.include_router(playlists_v1_bp)
    app.include_router(playlists_legacy_bp)
    app.include_router(playlists_double_v1_bp)

    # SPA Support
    custom_ui_path = config_manager.get('custom_ui_path')
    ui_path = os.path.join(os.path.dirname(__file__), '../webui/build')
    if custom_ui_path and os.path.isdir(custom_ui_path) and os.path.exists(os.path.join(custom_ui_path, 'index.html')):
        ui_path = custom_ui_path

    if os.path.exists(ui_path):
        app.mount("/", StaticFiles(directory=ui_path, html=True), name="static")

        from starlette.exceptions import HTTPException as StarletteHTTPException
        @app.exception_handler(404)
        async def spa_fallback(request: Request, exc: StarletteHTTPException):
            if request.url.path.startswith("/api/"):
                return JSONResponse({"detail": "API route not found"}, status_code=404)
            return FileResponse(os.path.join(ui_path, 'index.html'))

    return app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.api_app:create_app", host="0.0.0.0", port=5000, reload=True, factory=True)
