"""Course model: a queryable projection of CourseScheme.content, rebuilt on upload.

See docs/PROJECT_ARCHITECTURE.md §3.5–§3.6.
"""

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.course_scheme import CourseScheme


class Course(TimestampMixin, Base):
    __tablename__ = "courses"
    __table_args__ = (UniqueConstraint("scheme_id", "code", name="uq_course_scheme_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    scheme_id: Mapped[int] = mapped_column(
        ForeignKey("course_schemes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Null means the course is non-credit ("NC" in the scheme documents).
    credit_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Which semester (1-8) this course belongs to within its scheme, read from
    # CourseScheme.content's semester grouping at materialization time (see
    # course_scheme_service.materialize_courses). Null for courses whose scheme predates
    # this column and hasn't been re-materialized, or for a scheme with no semester
    # grouping at all (e.g. the Phase 7 synthetic timetable-derived scheme) see
    # docs/PROJECT_AUDIT.md Phase 9 for why that one is deliberately left unset.
    semester: Mapped[int | None] = mapped_column(Integer, nullable=True)

    has_lab: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lab_credit_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_marks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_marks: Mapped[int | None] = mapped_column(Integer, nullable=True)

    scheme: Mapped[CourseScheme] = relationship(back_populates="courses")
