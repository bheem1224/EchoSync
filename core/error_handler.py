"""
Centralized Error Handling Module for Echosync

This module provides utilities for managing exceptions, retries, and logging
across the application. It is designed to integrate with the JobQueue,
HealthCheckRegistry, and other core components.
"""

import logging
import traceback
import time
from typing import Callable, Optional, Any
from core.tiered_logger import tiered_logger, get_logger

logger = get_logger(__name__)

class ErrorHandler:
    """
    Centralized error handling utility.
    """

    @staticmethod
    def handle_exception(
        func: Callable,
        retries: int = 0,
        backoff_base: float = 1.0,
        backoff_factor: float = 2.0,
        on_failure: Optional[Callable[[Exception], None]] = None,
        log_tier: str = "normal"  # Specify the logging tier
    ) -> Optional[Any]:
        """
        Execute a function with retry and backoff logic.

        Args:
            func: The function to execute.
            retries: Number of retries on failure.
            backoff_base: Initial backoff time in seconds.
            backoff_factor: Multiplier for exponential backoff.
            on_failure: Optional callback to execute on final failure.
            log_tier: The logging tier to use ("normal", "debug", "verbose").

        Returns:
            The result of the function, or None if all retries fail.
        """
        attempt = 0
        while attempt <= retries:
            try:
                return func()
            except Exception as e:
                # Use tiered logger for specific tier request, or standard logger
                tiered_logger.log(log_tier, logging.ERROR, f"Error in function {func.__name__}: {e}")
                tiered_logger.log(log_tier, logging.DEBUG, traceback.format_exc())

                if attempt == retries:
                    tiered_logger.log(log_tier, logging.ERROR, f"All retries failed for function {func.__name__}")
                    if on_failure:
                        on_failure(e)
                    return None

                backoff_time = backoff_base * (backoff_factor ** attempt)
                tiered_logger.log(log_tier, logging.INFO, f"Retrying {func.__name__} in {backoff_time:.2f} seconds...")
                time.sleep(backoff_time)
                attempt += 1

    @staticmethod
    def log_and_raise(exception: Exception, message: str = ""):
        """
        Log an exception and re-raise it.

        Args:
            exception: The exception to log and raise.
            message: Optional message to log before raising.
        """
        logger.error(message or str(exception))
        logger.debug(traceback.format_exc())
        raise exception

    @staticmethod
    def log_warning(exception: Exception, message: str = ""):
        """
        Log a warning for an exception.

        Args:
            exception: The exception to log.
            message: Optional message to log.
        """
        logger.warning(message or str(exception))
        logger.debug(traceback.format_exc())

# Global instance for convenience
error_handler = ErrorHandler()
