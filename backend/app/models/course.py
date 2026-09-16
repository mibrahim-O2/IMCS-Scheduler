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

    has_lab: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lab_credit_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_marks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_marks: Mapped[int | None] = mapped_column(Integer, nullable=True)

    scheme: Mapped[CourseScheme] = relationship(back_populates="courses")
