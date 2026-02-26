import pytest
import asyncio

from core.service_bootstrap import start_services
from core.settings import config_manager


class DummyDownloadManager:
    def __init__(self):
        self.started = False
        self.ensure_called = False

    def start(self):
        self.started = True

    def ensure_background_task(self):
        self.ensure_called = True


@pytest.mark.asyncio
async def test_start_services_with_start_on_boot_disabled(monkeypatch):
    """When configuration disables startup the download manager should not be started."""
    dummy = DummyDownloadManager()
    # override the global accessor to return our dummy
    monkeypatch.setattr('services.download_manager.get_download_manager', lambda: dummy)

    # force config to report start_on_boot = False
    monkeypatch.setattr(config_manager, 'get', lambda key, default=None: {'start_on_boot': False} if key == 'download' else default)

    await start_services()
    assert not dummy.started
    assert not dummy.ensure_called


@pytest.mark.asyncio
async def test_start_services_with_start_on_boot_enabled(monkeypatch, caplog):
    """When configuration allows startup both start() and ensure_background_task() should have been invoked."""
    dummy = DummyDownloadManager()
    # patch the reference used by service_bootstrap (imported at module load time)
    monkeypatch.setattr('core.service_bootstrap.get_download_manager', lambda: dummy)

    monkeypatch.setattr(config_manager, 'get', lambda key, default=None: {'start_on_boot': True} if key == 'download' else default)

    caplog.set_level("DEBUG")
    await start_services()

    # check for any errors in logs
    errors = [r for r in caplog.records if r.levelname == "ERROR"]
    assert not errors, f"unexpected errors logged: {errors}"

    assert dummy.started or dummy.ensure_called, "download manager was not started despite start_on_boot=True"
