"""API v1 router aggregation.

Route ordering matters here: ``/reference/{key:path}`` is a greedy match, so it
is mounted after the more specific routers.
"""

from fastapi import APIRouter

from app.api.v1.routers import (
    ai,
    auth,
    curriculum,
    execution,
    exercises,
    progress,
    projects,
    reference,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(curriculum.router)
api_router.include_router(exercises.router)
api_router.include_router(execution.router)
api_router.include_router(progress.router)
api_router.include_router(projects.router)
api_router.include_router(ai.router)
api_router.include_router(reference.router)

__all__ = ["api_router"]
