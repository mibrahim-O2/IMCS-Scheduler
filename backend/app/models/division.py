"""Division (section) and LabBatch models, plus DivisionCourse.

A Division is Program + Part + Shift (+ PM/PE group) and is the unit a
timetable is generated for; it exists only for schedulable programs (BS level
today, see §3.1). LabBatch supports one lab running as N parallel sub-batches
with independent teachers and rooms. See docs/PROJECT_ARCHITECTURE.md §3.2.

DivisionCourse is an addition beyond the original §3.2 sketch, added in
Phase 7 once real data (docs/timetable.json) showed why it's needed: which
teacher teaches which subject to which division, and how many periods a
week, is a fact about that specific (division, course) pairing — it isn't
derivable from Division/Course/Teacher alone, and it isn't always symmetric
across PM/PE (e.g. IOT runs 3 periods/week for Part-I PM but only 2 for
Part-I PE in the real timetable). This table is the direct, real, seeded
input the GA reads instead of a hardcoded Python dict.
"""

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.classroom import Classroom
from app.models.course import Course
from app.models.course_scheme import CourseScheme
from app.models.program import Program
from app.models.teacher import Teacher


class Division(TimestampMixin, Base):
    __tablename__ = "divisions"
    __table_args__ = (
        UniqueConstraint("program_id", "part", "shift", "group", name="uq_division_program_part_shift_group"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)

    # 1-4 (Part-I..Part-IV). The original architecture sketch described this field as
    # "1-8 (maps to Part-I..Part-IV per semester pair)", which conflated part and semester
    # into one confusing field. Split cleanly here: part is 1-4, semester below is 1-8.
    part: Mapped[int] = mapped_column(Integer, nullable=False)

    # The actual semester currently running within this part (1-8), where known. Nullable
    # because it's an inference from which semester's subjects the real timetable shows,
    # not a certainty — see docs/PROJECT_ARCHITECTURE.md §11.2 on scheme-vs-real-taught mismatch.
    semester: Mapped[int | None] = mapped_column(Integer, nullable=True)

    shift: Mapped[str | None] = mapped_column(String(20), nullable=True)  # "Morning" | "Evening" | null (Math)
    group: Mapped[str | None] = mapped_column(String(10), nullable=True)  # "PM" | "PE" | null

    # Which CourseScheme this division's subjects were seeded from (nullable: not every
    # division necessarily has one yet).
    course_scheme_id: Mapped[int | None] = mapped_column(
        ForeignKey("course_schemes.id", ondelete="SET NULL"), nullable=True
    )
    student_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Human-readable label ("BS Computer Science Part-I (Morning) - Pre-Medical"), stored
    # rather than recomputed everywhere it's displayed — small convenience, not load-bearing.
    label: Mapped[str] = mapped_column(String(150), nullable=False)

    # This division's own fixed lecture room. Without pinning it, the GA has nothing
    # stopping it from putting a Part-IV lecture in a Part-I room: the room-double-booking
    # constraint only checks for a day/time clash, not "is this actually this division's
    # room". Labs are deliberately NOT pinned here: the department has five physical labs
    # (Lab A-E) that any division may use, so the GA picks a lab per session from that
    # shared pool instead (see scheduler/chromosome.py).
    home_room_id: Mapped[int | None] = mapped_column(ForeignKey("classrooms.id", ondelete="SET NULL"), nullable=True)

    program: Mapped[Program] = relationship()
    course_scheme: Mapped[CourseScheme | None] = relationship()
    home_room: Mapped[Classroom | None] = relationship(foreign_keys=[home_room_id])
    courses: Mapped[list["DivisionCourse"]] = relationship(
        back_populates="division",
        foreign_keys="DivisionCourse.division_id",
        cascade="all, delete-orphan",
    )


class LabBatch(TimestampMixin, Base):
    """One parallel sub-batch of a lab, each with its own teacher and room.

    Not populated for BSCS Part-I to Part-IV in Phase 7 — the real timetable data
    for these divisions has exactly one batch per division per lab (no further
    splitting), so a plain `is_lab=true` TimetableSession row is enough and
    `TimetableSession.lab_batch_id` stays null. This table exists and is ready
    for the "one lab split N ways" case described in §3.2 once that's needed.
    """

    __tablename__ = "lab_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    division_id: Mapped[int] = mapped_column(ForeignKey("divisions.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    batch_label: Mapped[str] = mapped_column(String(50), nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False)
    room_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id", ondelete="RESTRICT"), nullable=False)

    division: Mapped[Division] = relationship()
    course: Mapped[Course] = relationship()
    teacher: Mapped[Teacher] = relationship()
    room: Mapped[Classroom] = relationship()


class DivisionCourse(TimestampMixin, Base):
    """One row = "this division takes this course, taught by this teacher, N
    periods a week" — the real syllabus assignment the GA schedules from.

    `joint_division_id` is set when this same session is shared by another
    division sitting together (e.g. History-II taught to Part-I PM and PE at
    once) — the PM row alone represents the joint session; PE does not get
    its own separate row for it. See docs/CONSTRAINTS.md constraint 5.
    """

    __tablename__ = "division_courses"
    __table_args__ = (UniqueConstraint("division_id", "course_id", name="uq_division_course"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    division_id: Mapped[int] = mapped_column(ForeignKey("divisions.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False)
    weekly_theory_periods: Mapped[int] = mapped_column(Integer, nullable=False)

    has_lab: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lab_teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=True)
    weekly_lab_periods: Mapped[int | None] = mapped_column(Integer, nullable=True)

    joint_division_id: Mapped[int | None] = mapped_column(
        ForeignKey("divisions.id", ondelete="SET NULL"), nullable=True
    )

    division: Mapped[Division] = relationship(back_populates="courses", foreign_keys=[division_id])
    joint_division: Mapped[Division | None] = relationship(foreign_keys=[joint_division_id])
    course: Mapped[Course] = relationship()
    teacher: Mapped[Teacher] = relationship(foreign_keys=[teacher_id])
    lab_teacher: Mapped[Teacher | None] = relationship(foreign_keys=[lab_teacher_id])
