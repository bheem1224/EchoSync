"""
Health Check System for SoulSync

Allows services to register health checks that are scheduled via job_queue.
Each health check is registered as a job with a configurable interval.
"""

import time
from typing import Dict, Callable, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from core.tiered_logger import get_logger

logger = get_logger("health_check")


@dataclass
class HealthCheckResult:
    """Result of a health check execution"""
    service_name: str
    status: str  # "healthy", "degraded", "unhealthy"
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    response_time_ms: float = 0.0


class HealthCheckRegistry:
    """
    Registry for service health checks.
    Services register their health check functions and the registry
    can execute them on demand or periodically.
    Scheduling is delegated to job_queue for centralized job management.
    """
    
    def __init__(self):
        self._checks: Dict[str, Callable[[], HealthCheckResult]] = {}
        self._last_results: Dict[str, HealthCheckResult] = {}
    
    def register_check(self, service_name: str, check_func: Callable[[], HealthCheckResult]):
        """
        Register a health check function for a service.
        
        Args:
            service_name: Unique identifier for the service
            check_func: Function that returns a HealthCheckResult
        """
        self._checks[service_name] = check_func
        logger.info(f"Registered health check for service: {service_name}")
    
    def unregister_check(self, service_name: str):
        """Remove a health check from the registry"""
        if service_name in self._checks:
            del self._checks[service_name]
            logger.info(f"Unregistered health check for service: {service_name}")
    
    def run_check(self, service_name: str) -> Optional[HealthCheckResult]:
        """
        Execute a health check for a specific service.
        
        Args:
            service_name: Name of the service to check
            
        Returns:
            HealthCheckResult or None if service not registered
        """
        if service_name not in self._checks:
            logger.warning(f"No health check registered for service: {service_name}")
            return None
        
        try:
            start_time = time.time()
            result = self._checks[service_name]()
            result.response_time_ms = (time.time() - start_time) * 1000
            result.timestamp = datetime.now()
            
            # Cache the result
            self._last_results[service_name] = result
            
            if result.status != "healthy":
                logger.warning(f"Health check failed for {service_name}: {result.message}")
            
            return result
        except Exception as e:
            logger.error(f"Health check exception for {service_name}: {e}", exc_info=True)
            result = HealthCheckResult(
                service_name=service_name,
                status="unhealthy",
                message=f"Health check exception: {str(e)}",
                timestamp=datetime.now()
            )
            self._last_results[service_name] = result
            return result
    
    def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """
        Execute all registered health checks.
        
        Returns:
            Dictionary mapping service names to their health check results
        """
        results = {}
        for service_name in self._checks.keys():
            result = self.run_check(service_name)
            if result:
                results[service_name] = result
        return results
    
    def get_last_result(self, service_name: str) -> Optional[HealthCheckResult]:
        """Get the last cached health check result for a service"""
        return self._last_results.get(service_name)
    
    def get_all_last_results(self) -> Dict[str, HealthCheckResult]:
        """Get all cached health check results"""
        return self._last_results.copy()
    
    def register_check_with_job(
        self, 
        service_name: str, 
        check_func: Callable[[], HealthCheckResult],
        interval_seconds: float = 60.0,
        max_retries: int = 3
    ):
        """
        Register a health check and schedule it as a periodic job in job_queue.
        
        Args:
            service_name: Unique identifier for the service
            check_func: Function that returns a HealthCheckResult
            interval_seconds: How often to run the check (default: 60 seconds)
            max_retries: Number of retries on failure (default: 3)
        """
        # Register the check function
        self.register_check(service_name, check_func)
        
        # Import here to avoid circular imports
        from core.job_queue import job_queue
        
        # Create a wrapper that calls the check and handles results
        def health_check_job():
            self.run_check(service_name)
        
        # Register as a periodic job in job_queue
        job_queue.register_job(
            name=f"health_check_{service_name}",
            func=health_check_job,
            interval_seconds=interval_seconds,
            start_after=interval_seconds,  # Wait for interval before first run
            max_retries=max_retries,
            tags=["health_check"]
        )
        
        logger.info(f"Registered health check job for {service_name} (interval: {interval_seconds}s)")


# Global health check registry instance
health_check_registry = HealthCheckRegistry()


# Convenience functions
def register_health_check(service_name: str, check_func: Callable[[], HealthCheckResult]):
    """Register a health check function (one-time, manual execution only)"""
    health_check_registry.register_check(service_name, check_func)


def register_health_check_job(
    service_name: str, 
    check_func: Callable[[], HealthCheckResult],
    interval_seconds: float = 60.0,
    max_retries: int = 3
):
    """
    Register a health check and schedule it as a periodic job.
    
    Args:
        service_name: Unique identifier for the service
        check_func: Function that returns a HealthCheckResult
        interval_seconds: How often to run the check (default: 60 seconds). Override for debug mode or custom schedules.
        max_retries: Number of retries on failure (default: 3)
    """
    health_check_registry.register_check_with_job(
        service_name, 
        check_func, 
        interval_seconds=interval_seconds,
        max_retries=max_retries
    )


def run_health_check(service_name: str) -> Optional[HealthCheckResult]:
    """Run a specific health check"""
    return health_check_registry.run_check(service_name)


def run_all_health_checks() -> Dict[str, HealthCheckResult]:
    """Run all registered health checks"""
    return health_check_registry.run_all_checks()
