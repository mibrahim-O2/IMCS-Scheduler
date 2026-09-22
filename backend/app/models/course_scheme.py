"""CourseScheme model: one row per Program + Part (+ admission scheme year).

The course list lives in a JSONB `content` column so a new scheme year never
needs a migration, and `is_active` soft-deletes schemes that published
timetables still reference. See docs/PROJECT_ARCHITECTURE.md §3.6 and §7.

`applies_to_part` was added in Phase 10: the upload flow moved from one flat
"upload a scheme" button to a 4-slot grid (Part-I..Part-IV) per program, so a
scheme now records which Part slot it fills. It is nullable because the two
schemes the Phase 7-9 GA seeding created for itself (a Phase 7 synthetic
BSCS scheme, and a couple of Phase 9 per-program "manually added subjects"
schemes) were never uploaded through this per-Part flow and don't belong to
one Part see docs/PROJECT_AUDIT.md Phase 10 for the migration that split
the one whole-program BSCS 2024 upload (which covered all 8 semesters, i.e.
all 4 Parts, in a single row) into four per-Part rows to fit this model.
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
    __table_args__ = (
        # Widened from (program_id, scheme_year) in Phase 10: Part-I 2024 and Part-II 2024 for
        # the same program are two different rows now, not a collision. "Only one ACTIVE
        # scheme per Part slot" is enforced in the endpoint instead (like the old active-only
        # check), since a DB-level unique constraint can't exclude soft-deleted history.
        UniqueConstraint("program_id", "applies_to_part", "scheme_year", name="uq_scheme_program_part_year"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int] = mapped_column(
        ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 1-4 (Part-I..Part-IV) which slot in the per-Program upload grid this scheme fills.
    # Null only for schemes created outside that flow (see the module docstring).
    applies_to_part: Mapped[int | None] = mapped_column(Integer, nullable=True)

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
