import pytest
from unittest.mock import patch
from web.api_app import create_app
from core.task_manager import supervisor, ProcessOwner, OwnerType, plugin_state_manager, PluginLifecycleState
from api.schemas.system_tasks import (
    TaskQueueSummaryResponse,
    ProcessListResponse,
    ProcessTerminateResponse,
    SystemHealthResponse,
)


@pytest.fixture
def client():
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client


def test_get_task_queue_status_api(client):
    """Test GET /api/v1/tasks/queue endpoint returns 200 OK and valid schema."""
    resp = client.get("/api/v1/tasks/queue")
    assert resp.status_code == 200

    data = resp.get_json()
    model = TaskQueueSummaryResponse.model_validate(data)
    assert "running" in model.stats
    assert "pending" in model.stats
    assert "blocked" in model.stats


def test_get_active_processes_api(client):
    """Test GET /api/v1/tasks/processes endpoint returns active process list."""
    owner = ProcessOwner(
        owner_id="plugin.test_api",
        owner_type=OwnerType.PLUGIN,
        pid=7777,
        task_name="api_test_task"
    )
    reg_id = supervisor.register_process(owner)

    try:
        resp = client.get("/api/v1/tasks/processes")
        assert resp.status_code == 200

        data = resp.get_json()
        model = ProcessListResponse.model_validate(data)
        assert model.total >= 1
        assert any(p.owner_id == "plugin.test_api" for p in model.processes)
    finally:
        supervisor.unregister_process(reg_id)


def test_terminate_process_api_success_and_404(client):
    """Test POST /api/v1/tasks/processes/<registration_id>/terminate endpoint."""
    owner = ProcessOwner(
        owner_id="plugin.terminate_api",
        owner_type=OwnerType.PLUGIN,
        pid=8888,
        task_name="to_be_terminated"
    )
    reg_id = supervisor.register_process(owner)

    with patch("os.kill") as mock_kill:
        # Successful termination
        resp = client.post(f"/api/v1/tasks/processes/{reg_id}/terminate")
        assert resp.status_code == 200
        data = resp.get_json()
        model = ProcessTerminateResponse.model_validate(data)
        assert model.status == "terminated"
        assert model.registration_id == reg_id
        mock_kill.assert_called()

    # 404 for non-existent registration ID
    resp_404 = client.post("/api/v1/tasks/processes/non_existent_id/terminate")
    assert resp_404.status_code == 404
    assert "error" in resp_404.get_json()


def test_get_unified_system_health_api(client):
    """Test GET /api/v1/system/health endpoint returns unified health response."""
    plugin_state_manager.set_state("echosync.health_test", PluginLifecycleState.READY, "All good")

    resp = client.get("/api/v1/system/health")
    assert resp.status_code == 200

    data = resp.get_json()
    model = SystemHealthResponse.model_validate(data)
    assert model.status in ("healthy", "degraded", "error")
    assert "echosync.health_test" in model.plugin_states
    assert model.plugin_states["echosync.health_test"]["state"] == "ready"
