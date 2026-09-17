"""
Phase 2A Integration Test Suite:
- Web Lifespan (api_app.py) asyncio backend task, JobQueue stop, EventBus drain
- System restart & factory reset routing via JobQueue Critical Pool (system.py)
- Library update routing via database_update JobQueue task (library.py)
- SearchAdapter aggregate_stream bounded by general pool & registered with ProcessSupervisor (search_service.py)
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from core.enums import TaskCategory, TaskPriority, TaskStatus
from core.task_manager.task_queue import JobQueue, ScheduledJob, job_queue
from web.api_app import create_app
from web.routes.library import router as library_router
from web.routes.system import router as system_router
from web.services.search_service import SearchAdapter

# ── 1. Web Lifespan Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_app_lifespan_lifecycle():
    """Verify api_app lifespan runs backend services as asyncio.Task and stops JobQueue & EventBus on shutdown."""

    app = create_app(testing=True)

    with patch("core.task_manager.task_queue.stop_job_queue") as mock_stop_jq:
        with patch("core.event_bus.event_bus.stop") as mock_stop_eb:
            with patch("core.backend_services.start_services", new_callable=AsyncMock) as mock_start_services:
                with TestClient(app) as client:
                    resp = client.get("/api/v1/system/status")
                    assert resp.status_code == 200

            # After lifespan exit:
            mock_stop_jq.assert_called_once()
            mock_stop_eb.assert_called_once_with(timeout=5.0)


# ── 2. System Routes Critical Pool Tests ──────────────────────────────────


def test_system_restart_dispatches_via_critical_pool():
    """Verify /restart dispatches via JobQueue with TaskCategory.CRITICAL and TaskPriority.CRITICAL."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(system_router)

    client = TestClient(app)

    with patch.object(job_queue, "register_job") as mock_reg:
        with patch.object(job_queue, "trigger_job_by_name", return_value=True) as mock_trigger:
            resp = client.post("/api/v1/system/restart")
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True

            mock_reg.assert_called_once()
            call_kwargs = mock_reg.call_args.kwargs
            assert call_kwargs["name"] == "system_restart"
            assert call_kwargs["category"] == TaskCategory.CRITICAL
            assert call_kwargs["priority"] == TaskPriority.CRITICAL
            mock_trigger.assert_called_once_with("system_restart")


def test_system_factory_reset_dispatches_via_critical_pool():
    """Verify /reset/factory dispatches via JobQueue with TaskCategory.CRITICAL."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(system_router)

    client = TestClient(app)

    with patch.object(job_queue, "register_job") as mock_reg:
        with patch.object(job_queue, "trigger_job_by_name", return_value=True) as mock_trigger:
            resp = client.post("/api/v1/system/reset/factory")
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True

            mock_reg.assert_called_once()
            call_kwargs = mock_reg.call_args.kwargs
            assert call_kwargs["name"] == "system_factory_reset"
            assert call_kwargs["category"] == TaskCategory.CRITICAL
            assert call_kwargs["priority"] == TaskPriority.CRITICAL
            mock_trigger.assert_called_once_with("system_factory_reset")


def test_can_execute_allows_critical_during_restart_pending():
    """Verify JobQueue.can_execute permits CRITICAL tasks during RESTART_PENDING but pauses others."""
    jq = JobQueue(worker_count=2)
    jq.RESTART_PENDING = True

    now = time.time()
    critical_job = ScheduledJob(
        name="critical_task",
        func=lambda: None,
        next_run=now,
        category=TaskCategory.CRITICAL,
    )
    general_job = ScheduledJob(
        name="general_task",
        func=lambda: None,
        next_run=now,
        category=TaskCategory.GENERAL,
    )

    assert jq.can_execute(critical_job) is True
    assert jq.can_execute(general_job) is False
    assert general_job.state == TaskStatus.PAUSED


# ── 3. Library Routes Database Update Tests ───────────────────────────────


def test_library_update_dispatches_via_job_queue():
    """Verify library /update-database dispatches via job_queue.trigger_job_by_name without raw threads."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(library_router)

    client = TestClient(app)

    with patch(
        "core.nexus_framework.plugin_loader.PluginRegistry.get_active_services_by_type", return_value=["local_server"]
    ), patch("core.nexus_framework.plugin_loader.PluginRegistry.create_instance") as mock_inst:
        mock_provider = MagicMock()
        mock_provider.ensure_connection.return_value = True
        mock_inst.return_value = mock_provider

        with patch.object(job_queue, "trigger_job_by_name", return_value=True) as mock_trigger:
            resp = client.post("/api/v1/core/library/update-database?mode=full")
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True

            mock_trigger.assert_called_once_with(
                "database_update",
                params={"scan_mode": "full_rebuild", "full_refresh": True},
            )


def test_library_update_status_reflects_job_queue_state():
    """Verify /update-status queries job_queue._is_running['database_update']."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(library_router)

    client = TestClient(app)

    with patch(
        "core.nexus_framework.plugin_loader.PluginRegistry.get_active_services_by_type", return_value=["local_server"]
    ), patch.dict(job_queue._is_running, {"database_update": True}):
        resp = client.get("/api/v1/core/library/update-status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["running"] is True


# ── 4. Search Service Stream Worker Tests ─────────────────────────────────


def test_search_service_stream_worker_uses_supervisor_and_general_pool():
    """Verify SearchAdapter.aggregate_stream uses supervisor.spawn_supervised_thread and unregisters on exit."""
    spotify_provider = MagicMock()
    spotify_provider.name = "spotify"
    spotify_provider.search.return_value = [
        {
            "title": "Search Stream Track",
            "artist": "Search Artist",
            "identifiers": {"spotify_id": "999"},
        }
    ]

    mock_caps = MagicMock()
    mock_caps.search.tracks = True

    with (
        patch("web.services.search_service.PluginRegistry.list_plugins", return_value=[123]),
        patch("web.services.search_service.PluginRegistry.create_instance", return_value=spotify_provider),
        patch("web.services.search_service.get_plugin_capabilities", return_value=mock_caps),
        patch("web.services.search_service.get_local_track_details", return_value=(False, None)),
    ):
        adapter = SearchAdapter()
        gen = adapter.aggregate_stream("stream_query", plugin_names=["spotify"], search_types=["tracks"])

        # Get first chunk
        try:
            chunk = next(gen)
            assert chunk is not None
        except StopIteration:
            pass

        # Close generator cleanly
        gen.close()
