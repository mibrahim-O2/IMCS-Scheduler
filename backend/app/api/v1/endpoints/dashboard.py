"""Dashboard endpoints.

GET /api/v1/dashboard/stats returns a stats overview counted from the database.
It is not a teacher/room availability view; that needs generated timetables.
See docs/PROJECT_ARCHITECTURE.md §8.
"""

from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.dashboard import DashboardStats
from app.services.dashboard_service import collect_stats

router = APIRouter(prefix="/dashboard")


@router.get("/stats", response_model=DashboardStats)
def get_stats(db: DbSession) -> DashboardStats:
    # Counts of departments, programs, saved schemes, courses, classrooms and teachers.
    return collect_stats(db)
