"""
Health Check System for SoulSync

Allows services to register health checks that can be executed periodically.
Temporary implementation until job queue/task scheduler is added.
"""

import threading
import time
from typing import Dict, Callable, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from utils.logging_config import get_logger

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
    """
    
    def __init__(self):
        self._checks: Dict[str, Callable[[], HealthCheckResult]] = {}
        self._last_results: Dict[str, HealthCheckResult] = {}
        self._scheduler_thread: Optional[threading.Thread] = None
        self._scheduler_running = False
        self._check_interval = 60  # Default: check every 60 seconds
    
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
    
    def start_scheduler(self, interval_seconds: int = 60):
        """
        Start periodic health check execution.
        
        Args:
            interval_seconds: How often to run health checks
        """
        if self._scheduler_running:
            logger.warning("Health check scheduler already running")
            return
        
        self._check_interval = interval_seconds
        self._scheduler_running = True
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        logger.info(f"Started health check scheduler (interval: {interval_seconds}s)")
    
    def stop_scheduler(self):
        """Stop the periodic health check scheduler"""
        if not self._scheduler_running:
            return
        
        self._scheduler_running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        logger.info("Stopped health check scheduler")
    
    def _scheduler_loop(self):
        """Internal scheduler loop that runs health checks periodically"""
        while self._scheduler_running:
            try:
                logger.debug("Running scheduled health checks...")
                self.run_all_checks()
            except Exception as e:
                logger.error(f"Error in health check scheduler: {e}", exc_info=True)
            
            # Sleep in small increments to allow for quick shutdown
            for _ in range(self._check_interval):
                if not self._scheduler_running:
                    break
                time.sleep(1)


# Global health check registry instance
health_check_registry = HealthCheckRegistry()


# Convenience functions
def register_health_check(service_name: str, check_func: Callable[[], HealthCheckResult]):
    """Register a health check function"""
    health_check_registry.register_check(service_name, check_func)


def run_health_check(service_name: str) -> Optional[HealthCheckResult]:
    """Run a specific health check"""
    return health_check_registry.run_check(service_name)


def run_all_health_checks() -> Dict[str, HealthCheckResult]:
    """Run all registered health checks"""
    return health_check_registry.run_all_checks()
