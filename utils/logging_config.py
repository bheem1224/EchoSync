"""Logging configuration module - backward compatibility stub."""
import logging


def get_logger(name: str) -> logging.Logger:
    """Get or create a logger with the given name."""
    return logging.getLogger(name)
