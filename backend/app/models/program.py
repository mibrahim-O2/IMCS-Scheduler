"""Department and Program models.

A Department is one of the three stable top-level groupings; a Program is one
department + level pair. Only BS-level programs are schedulable today, which
`is_schedulable` records. See docs/PROJECT_ARCHITECTURE.md §3.1.
"""

import enum

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class ProgramLevel(str, enum.Enum):
    BS = "BS"
    MASTER = "Master"
    MPHIL = "MPhil"
    MPHIL_BIOINFORMATICS = "MPhilBioinformatics"
    PHD = "PhD"
    MSC_PASS = "MScPass"
    PGD = "PGD"


class Department(TimestampMixin, Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    short_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    programs: Mapped[list["Program"]] = relationship(
        back_populates="department",
        cascade="all, delete-orphan",
        order_by="Program.id",
    )


class Program(TimestampMixin, Base):
    __tablename__ = "programs"
    __table_args__ = (UniqueConstraint("department_id", "level", name="uq_program_department_level"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    level: Mapped[ProgramLevel] = mapped_column(
        Enum(ProgramLevel, name="program_level", values_callable=lambda levels: [x.value for x in levels]),
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(String(150), nullable=False)

    # Only set for levels whose semester structure we actually track (8 for BS).
    total_semesters: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # True only for BS programs right now; decides which programs get Divisions and Timetables.
    is_schedulable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Both splits below are meaningful only while is_schedulable is true.
    has_shift_split: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_pm_pe_split_from_part: Mapped[int | None] = mapped_column(Integer, nullable=True)

    department: Mapped[Department] = relationship(back_populates="programs")
    course_schemes: Mapped[list["CourseScheme"]] = relationship(  # noqa: F821
        back_populates="program",
        cascade="all, delete-orphan",
    )
