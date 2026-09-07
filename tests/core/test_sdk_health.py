from core.nexus_framework.plugin_SDK import sdk, _HealthCheckSDKFacade
from core.task_manager.task_queue import job_queue
from core.health_check import HealthCheckResult

def test_sdk_health_dynamic_caller_resolution():
    health_facade = sdk.health
    assert health_facade is not None

    def dummy_health_check():
        return HealthCheckResult(
            service_name='test_service',
            status='healthy',
            message='OK',
        )

    facade = _HealthCheckSDKFacade('EchoSync.test_service')
    facade.register(dummy_health_check, interval_seconds=120)

    job_name = 'health_check_test_service'
    assert job_name in job_queue._jobs
    registered_job = job_queue._jobs[job_name]
    assert registered_job.plugin == 'EchoSync.test_service'
    assert registered_job.interval_seconds == 120

    # Clean up
    job_queue.unregister_job(job_name)
