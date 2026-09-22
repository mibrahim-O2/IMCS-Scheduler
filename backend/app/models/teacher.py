"""Teacher model, resolved by full name never by initials, which collide.

Cross-program load is derived from timetable sessions later, so nothing here
restricts a teacher to their home program. See docs/PROJECT_ARCHITECTURE.md §3.4.
"""

from typing import Any

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.program import Program


class Teacher(TimestampMixin, Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    designation: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Primary affiliation only; a teacher can still be scheduled in other programs.
    home_program_id: Mapped[int | None] = mapped_column(
        ForeignKey("programs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    max_hours_per_week: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Teacher-declared availability windows per day; an input constraint for the GA.
    availability: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    home_program: Mapped[Program | None] = relationship()
