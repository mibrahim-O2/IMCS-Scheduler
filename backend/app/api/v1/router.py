"""Aggregates the v1 endpoint routers into one router, mounted by app/main.py.

See docs/PROJECT_ARCHITECTURE.md §4.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import chat, classrooms, course_schemes, dashboard, divisions, programs, teachers, timetables

api_router = APIRouter()
api_router.include_router(programs.router, tags=["programs"])
api_router.include_router(course_schemes.router, tags=["course-schemes"])
api_router.include_router(course_schemes.courses_router, tags=["courses"])
api_router.include_router(dashboard.router, tags=["dashboard"])
api_router.include_router(timetables.router, tags=["timetables"])
api_router.include_router(teachers.router, tags=["teachers"])
api_router.include_router(classrooms.router, tags=["classrooms"])
api_router.include_router(divisions.router, tags=["divisions"])
api_router.include_router(chat.router, tags=["chat"])
