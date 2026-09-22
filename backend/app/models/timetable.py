"""Timetable and TimetableSession models.

Timetable is a generation RUN the result of one GA call with a status,
fitness score, and whether it actually converged. TimetableSession is one
placed session (one materialized GA gene).

Deviation from the original §3.7 sketch, made deliberately in Phase 7:
the sketch had `Timetable.division_id` (singular) one Timetable per one
Division. Phase 5-6 proved the GA has to schedule several divisions in one
combined chromosome to catch cross-division teacher clashes at all (see
docs/CONSTRAINTS.md constraint 6), and the real data has sessions shared by
two divisions at once (a joint PM/PE class). A single `division_id` column
cannot represent either of those. So a Timetable now represents one
generation run across however many divisions were requested, and each
TimetableSession carries its own `division_ids` (a JSONB array normally
one id, two for a joint session) instead of inheriting one division from its
parent Timetable. This is recorded here and in docs/PROJECT_AUDIT.md so it
isn't mistaken for an oversight.
"""

import enum
from datetime import date, time
from typing import Any

from sqlalchemy import Boolean, Date, Enum, Float, ForeignKey, Integer, String, Time
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.classroom import Classroom
from app.models.course import Course
from app.models.division import LabBatch
from app.models.teacher import Teacher


class TimetableStatus(str, enum.Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Timetable(TimestampMixin, Base):
    __tablename__ = "timetables"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Human-readable name for the run, e.g. "BSCS Part-I to Part-IV Morning".
    label: Mapped[str] = mapped_column(String(150), nullable=False)

    status: Mapped[TimetableStatus] = mapped_column(
        Enum(TimetableStatus, name="timetable_status", values_callable=lambda s: [x.value for x in s]),
        nullable=False,
        default=TimetableStatus.DRAFT,
    )
    algorithm_version: Mapped[str] = mapped_column(String(50), nullable=False)

    # Which divisions were requested, and the GA's own run settings (population, generation
    # cap, mutation rate, etc.) kept for reproducibility, per §3.7.
    generation_params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    fitness_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # True only if the GA actually reached zero hard violations. False means it stopped
    # early (stagnation) or hit the generation cap the caller must not treat that as success.
    converged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    generation_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Remaining violation descriptions if not converged (empty list when converged).
    conflict_list: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    published_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    sessions: Mapped[list["TimetableSession"]] = relationship(
        back_populates="timetable",
        cascade="all, delete-orphan",
        order_by="TimetableSession.day, TimetableSession.start_time",
    )


class TimetableSession(TimestampMixin, Base):
    """One placed session one materialized GA gene."""

    __tablename__ = "timetable_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    timetable_id: Mapped[int] = mapped_column(
        ForeignKey("timetables.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False)
    room_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id", ondelete="RESTRICT"), nullable=False)

    # Which division(s) this session belongs to a list because a joint PM/PE session
    # belongs to two divisions at once. See the module docstring for why this replaces a
    # singular division_id on the parent Timetable.
    division_ids: Mapped[list[int]] = mapped_column(JSONB, nullable=False)

    day: Mapped[str] = mapped_column(String(3), nullable=False)  # "Mon".."Fri"
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_lab: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lab_batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("lab_batches.id", ondelete="SET NULL"), nullable=True
    )

    timetable: Mapped[Timetable] = relationship(back_populates="sessions")
    course: Mapped[Course] = relationship()
    teacher: Mapped[Teacher] = relationship()
    room: Mapped[Classroom] = relationship()
    lab_batch: Mapped[LabBatch | None] = relationship()
