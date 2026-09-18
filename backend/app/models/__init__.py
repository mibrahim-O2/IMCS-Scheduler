"""SQLAlchemy ORM models, one module per entity (docs/PROJECT_ARCHITECTURE.md §3).

Every model is imported here so Alembic autogenerate sees all tables through
a single import of this package.
"""

from app.models.classroom import Classroom, ClassroomType
from app.models.course import Course
from app.models.course_scheme import CourseScheme
from app.models.division import Division, DivisionCourse, LabBatch
from app.models.program import Department, Program, ProgramLevel
from app.models.teacher import Teacher
from app.models.timetable import Timetable, TimetableSession, TimetableStatus

__all__ = [
    "Classroom",
    "ClassroomType",
    "Course",
    "CourseScheme",
    "Department",
    "Division",
    "DivisionCourse",
    "LabBatch",
    "Program",
    "ProgramLevel",
    "Teacher",
    "Timetable",
    "TimetableSession",
    "TimetableStatus",
]
