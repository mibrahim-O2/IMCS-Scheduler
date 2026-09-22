"""Encode and decode a timetable to and from a gene array, reading its input
straight from the database instead of a hardcoded Python dict.

One chromosome is a full candidate timetable covering every division passed
to `build_session_requirements`. Each gene is (room, day, start_time) — the
part the GA actually searches over. The course/teacher pairing for that gene
is fixed ahead of time (from DivisionCourse, seeded from real data) and lives
in the parallel `requirements` list at the same index; mutation only ever
re-rolls a gene's room/day/slot, never which course or teacher it is, exactly
as docs/PROJECT_ARCHITECTURE.md §6.1/§6.3 describe and as
scheduler/dev_scripts/phase4-6 proved out. See docs/PROJECT_ARCHITECTURE.md §6.1.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Classroom, ClassroomType, Division, DivisionCourse

DAYS: tuple[str, ...] = ("Mon", "Tue", "Wed", "Thu", "Fri")

# The six 50-minute periods the real timetable runs on (docs/timetable.json), as
# (label, start "HH:MM", end "HH:MM"). Index into this list is what a gene stores,
# rather than repeating the strings — cheaper to compare and to place in a dict key.
TIME_SLOTS: tuple[tuple[str, str, str], ...] = (
    ("08:30-09:20", "08:30", "09:20"),
    ("09:20-10:10", "09:20", "10:10"),
    ("10:10-11:00", "10:10", "11:00"),
    ("11:00-11:50", "11:00", "11:50"),
    ("11:50-12:40", "11:50", "12:40"),
    ("12:40-13:30", "12:40", "13:30"),
)


class Gene(NamedTuple):
    """The variable part of one placed session — what mutation is allowed to change."""

    room_id: int
    day: str
    slot_index: int


@dataclass(frozen=True)
class SessionRequirement:
    """The fixed part of one placed session: which DivisionCourse it fulfils, which
    course/teacher that pins it to, which division(s) it belongs to, and which rooms
    are even valid for it. Built once per generation run from real DivisionCourse rows.
    """

    division_course_id: int
    course_id: int
    teacher_id: int
    division_ids: tuple[int, ...]  # one entry normally, two for a joint PM/PE session
    is_lab: bool
    candidate_rooms: tuple[int, ...]


Chromosome = list[Gene]


@dataclass(frozen=True)
class DivisionInfo:
    """The handful of Division facts the GA needs, cached once per run instead of
    being re-queried on every constraint check."""

    id: int
    label: str
    home_room_id: int | None


def load_divisions(session: Session, division_ids: list[int]) -> dict[int, DivisionInfo]:
    # Pulls the Division rows the run needs into a small in-memory lookup, once.
    rows = session.scalars(select(Division).where(Division.id.in_(division_ids))).all()
    found = {row.id for row in rows}
    missing = set(division_ids) - found
    if missing:
        raise ValueError(f"Division id(s) not found: {sorted(missing)}")
    return {row.id: DivisionInfo(row.id, row.label, row.home_room_id) for row in rows}


def load_lab_room_ids(session: Session) -> tuple[int, ...]:
    # The department's shared lab rooms (Lab A-E). Labs aren't tied to a division: any lab
    # session may use any of them, and the room-clash rule is what keeps two sessions out
    # of the same lab at the same time.
    rows = session.scalars(select(Classroom.id).where(Classroom.type == ClassroomType.LAB).order_by(Classroom.name))
    return tuple(rows)


def build_session_requirements(session: Session, division_ids: list[int]) -> list[SessionRequirement]:
    # Turns every DivisionCourse row owned by one of these divisions into the weekly
    # theory sessions (and lab sessions, where the assignment has one) it needs — this
    # is the real, seeded equivalent of the dev scripts' hand-typed PDF_SESSIONS tuples.
    divisions = load_divisions(session, division_ids)
    lab_room_ids = load_lab_room_ids(session)
    assignments = session.scalars(
        select(DivisionCourse).where(DivisionCourse.division_id.in_(division_ids))
    ).all()

    requirements: list[SessionRequirement] = []
    for assignment in assignments:
        division = divisions[assignment.division_id]

        # A theory session's room: the assignment's own pre-assigned lecture room (set per
        # course through the Phase 9 data-entry dashboard) if there is one, otherwise the
        # division's one fixed room (how every BSCS Part-I to Part-IV assignment from Phase
        # 7-8.1 still works — none of them set lecture_room_id). Either way this is a single
        # room, never a pool: a theory session's room search space is one option, same
        # design as always, just sourced from two possible places now.
        theory_room_id = assignment.lecture_room_id or division.home_room_id
        if theory_room_id is None:
            raise ValueError(
                f"{division.label}: course {assignment.course_id} has no lecture room — set one on the "
                "assignment, or set the division's home_room_id."
            )

        # A joint session (e.g. History-II) belongs to two divisions at once, but only if
        # the other division was actually included in this run — otherwise it is simply a
        # normal single-division session for the one division that was requested.
        division_ids_for_gene = (assignment.division_id,)
        if assignment.joint_division_id is not None and assignment.joint_division_id in divisions:
            division_ids_for_gene = (assignment.division_id, assignment.joint_division_id)

        for _ in range(assignment.weekly_theory_periods):
            requirements.append(
                SessionRequirement(
                    division_course_id=assignment.id,
                    course_id=assignment.course_id,
                    teacher_id=assignment.teacher_id,
                    division_ids=division_ids_for_gene,
                    is_lab=False,
                    candidate_rooms=(theory_room_id,),
                )
            )

        if assignment.has_lab and assignment.lab_teacher_id and assignment.weekly_lab_periods:
            # A pre-assigned lab room (Phase 9) narrows the search to that one lab — a
            # single-element tuple, exactly like a fixed theory room above. Left unset, a lab
            # session may use any of the shared labs, as it always has since Phase 8.1.
            # Either way, mutation and crossover choose among (or copy) only what's in this
            # tuple, so a pre-assigned room can never be reassigned — see operators.py.
            if assignment.lab_room_id is not None:
                lab_candidate_rooms: tuple[int, ...] = (assignment.lab_room_id,)
            elif lab_room_ids:
                lab_candidate_rooms = lab_room_ids
            else:
                raise ValueError(f"{division.label} has a lab course but no lab rooms exist — re-run the seed.")
            for _ in range(assignment.weekly_lab_periods):
                requirements.append(
                    SessionRequirement(
                        division_course_id=assignment.id,
                        course_id=assignment.course_id,
                        teacher_id=assignment.lab_teacher_id,
                        division_ids=(assignment.division_id,),  # labs are never joint in this data
                        is_lab=True,
                        candidate_rooms=lab_candidate_rooms,
                    )
                )

    return requirements


def random_gene(rng: random.Random, requirement: SessionRequirement) -> Gene:
    # A random placement for one required session; course and teacher are already fixed.
    return Gene(
        room_id=rng.choice(requirement.candidate_rooms),
        day=rng.choice(DAYS),
        slot_index=rng.randrange(len(TIME_SLOTS)),
    )


def random_chromosome(rng: random.Random, requirements: list[SessionRequirement]) -> Chromosome:
    # One complete candidate timetable, placed at random, one gene per requirement.
    return [random_gene(rng, requirement) for requirement in requirements]
