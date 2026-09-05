"""Review queue route aliases and router definitions."""

from web.routes import metadata_review

router = metadata_review.router

__all__ = ["metadata_review", "router"]
