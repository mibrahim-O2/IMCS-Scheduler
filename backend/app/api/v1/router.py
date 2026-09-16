"""Aggregates the v1 endpoint routers into one router, mounted by app/main.py.

See docs/PROJECT_ARCHITECTURE.md §4.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import course_schemes, programs

api_router = APIRouter()
api_router.include_router(programs.router, tags=["programs"])
api_router.include_router(course_schemes.router, tags=["course-schemes"])
