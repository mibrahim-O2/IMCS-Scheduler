"""SQLAlchemy ORM models, one module per entity (docs/PROJECT_ARCHITECTURE.md §3).

Every model is imported here so Alembic autogenerate sees all tables through
a single import of this package.
"""

from app.models.classroom import Classroom, ClassroomType
from app.models.course import Course
from app.models.course_scheme import CourseScheme
from app.models.program import Department, Program, ProgramLevel
from app.models.teacher import Teacher

__all__ = [
    "Classroom",
    "ClassroomType",
    "Course",
    "CourseScheme",
    "Department",
    "Program",
    "ProgramLevel",
    "Teacher",
]
