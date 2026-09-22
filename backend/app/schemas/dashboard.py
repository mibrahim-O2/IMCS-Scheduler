"""Response schema for the stats overview.

Counts only not teacher or room availability, which needs generated
timetables. See docs/PROJECT_ARCHITECTURE.md §8.
"""

from datetime import datetime

from pydantic import BaseModel


class ProgramCounts(BaseModel):
    total: int
    schedulable: int
    not_yet_schedulable: int


class SchemeBreakdown(BaseModel):
    scheme_id: int
    program_name: str
    scheme_year: int
    course_count: int
    lab_course_count: int


class CourseCounts(BaseModel):
    total: int
    with_lab: int


class DashboardStats(BaseModel):
    departments: int
    programs: ProgramCounts
    course_schemes: int
    scheme_breakdown: list[SchemeBreakdown]
    courses: CourseCounts
    classrooms: int
    teachers: int
    generated_at: datetime
