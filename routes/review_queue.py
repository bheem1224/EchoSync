"""Review queue route aliases and router definitions."""
from fastapi import APIRouter
import web.routes.metadata_review as metadata_review

router = metadata_review.router

__all__ = ["router", "metadata_review"]
