"""CourseScheme model: one row per Program + admission (scheme) year.

The course list lives in a JSONB `content` column so a new scheme year never
needs a migration, and `is_active` soft-deletes schemes that published
timetables still reference. See docs/PROJECT_ARCHITECTURE.md §3.6 and §7.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.program import Program


class CourseScheme(TimestampMixin, Base):
    __tablename__ = "course_schemes"
    __table_args__ = (UniqueConstraint("program_id", "scheme_year", name="uq_scheme_program_year"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int] = mapped_column(
        ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Admission year the scheme applies to, not the calendar year.
    scheme_year: Mapped[int] = mapped_column(Integer, nullable=False)

    # Original upload kept for audit, plus where the stored file lives.
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Source of record for the scheme; Course rows are a queryable projection of it.
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    program: Mapped[Program] = relationship(back_populates="course_schemes")
    courses: Mapped[list["Course"]] = relationship(  # noqa: F821
        back_populates="scheme",
        cascade="all, delete-orphan",
    )
