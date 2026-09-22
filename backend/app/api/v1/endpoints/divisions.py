"""Division and DivisionCourse endpoints the Phase 9 data-entry dashboard's backend.

Lets an admin build up a division's course/teacher/room assignments by hand for any
program/shift/part/semester/group, then finalize them into a real GA run the general
tool BSCS Morning no longer needs (it has its own seed script) but BS(AI), Mathematics and
the Evening shift will, once their data exists. See docs/PROJECT_ARCHITECTURE.md §3.2 and
docs/PROJECT_AUDIT.md Phase 9.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import DbSession
from app.api.v1.endpoints.timetables import run_generation
from app.models import Classroom, ClassroomType, Course, Division, DivisionCourse, Program, Teacher
from app.schemas.division import (
    CourseAssignmentCreate,
    CourseAssignmentRead,
    CourseAssignmentUpdate,
    DivisionCreate,
    DivisionRead,
    TeacherConflictCheck,
)
from app.schemas.timetable import GenerateResponse
from app.scheduler.engine import GaSettings

router = APIRouter(prefix="/divisions")

PART_ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV"}
GROUP_LABELS = {"PM": "Pre-Medical", "PE": "Pre-Engineering"}


@router.post("", response_model=DivisionRead, status_code=status.HTTP_201_CREATED)
def create_division(payload: DivisionCreate, db: DbSession) -> DivisionRead:
    # Get-or-create on the natural key (program, part, shift, group, semester) idempotent,
    # like the seed script's own upserts, so re-selecting the same combination in the
    # dashboard never fails with a duplicate-key error, it just returns the same division.
    program = db.get(Program, payload.program_id)
    if program is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Program {payload.program_id} does not exist.")

    existing = db.scalar(
        select(Division).where(
            Division.program_id == payload.program_id,
            Division.part == payload.part,
            Division.shift == payload.shift,
            Division.group == payload.group,
            Division.semester == payload.semester,
        )
    )
    if existing is not None:
        return _to_read(existing)

    division = Division(
        program_id=payload.program_id,
        part=payload.part,
        semester=payload.semester,
        shift=payload.shift,
        group=payload.group,
        label=_build_label(program.display_name, payload.part, payload.shift, payload.group),
    )
    db.add(division)
    db.commit()
    db.refresh(division)
    return _to_read(division)


@router.get("", response_model=list[DivisionRead])
def list_divisions(
    db: DbSession,
    program_id: int | None = None,
    part: int | None = None,
    semester: int | None = None,
    shift: str | None = None,
    group: str | None = None,
) -> list[DivisionRead]:
    # Every division on record, narrowed by whichever filters are given the dashboard uses
    # this to check whether a division already exists for a chosen combination.
    statement = select(Division).order_by(Division.program_id, Division.part, Division.semester)
    for column, value in (
        (Division.program_id, program_id),
        (Division.part, part),
        (Division.semester, semester),
        (Division.shift, shift),
        (Division.group, group),
    ):
        if value is not None:
            statement = statement.where(column == value)
    return [_to_read(row) for row in db.scalars(statement)]


@router.get("/{division_id}", response_model=DivisionRead)
def get_division(division_id: int, db: DbSession) -> DivisionRead:
    # One division's own record status of its assignment lock included, since the
    # dashboard needs to know whether it can still be edited.
    return _to_read(_get_division_or_404(db, division_id))


@router.get("/{division_id}/courses", response_model=list[CourseAssignmentRead])
def list_course_assignments(division_id: int, db: DbSession) -> list[CourseAssignmentRead]:
    # The division's current draft (or finalized) assignment list, course/teacher names
    # joined in so the frontend doesn't need a second round trip to show them.
    _get_division_or_404(db, division_id)
    rows = db.scalars(
        select(DivisionCourse).where(DivisionCourse.division_id == division_id).order_by(DivisionCourse.id)
    ).all()
    return [_to_assignment_read(db, row) for row in rows]


@router.get("/{division_id}/courses/check-teacher", response_model=TeacherConflictCheck)
def check_teacher_conflict(
    division_id: int, teacher_id: int, course_id: int, db: DbSession
) -> TeacherConflictCheck:
    # Live pre-check for the dashboard's teacher dropdown (constraint 9,
    # docs/CONSTRAINTS.md): called as the admin picks a teacher, before they even try to add
    # the row, so the warning is immediate rather than only surfacing at generation time.
    _get_division_or_404(db, division_id)
    conflict_course = _find_teacher_conflict(db, division_id, teacher_id, course_id)
    if conflict_course is None:
        return TeacherConflictCheck(conflict=False)
    teacher = db.get(Teacher, teacher_id)
    teacher_name = teacher.full_name if teacher else f"Teacher {teacher_id}"
    return TeacherConflictCheck(
        conflict=True,
        message=(
            f"{teacher_name} is already assigned {conflict_course} in this division "
            "one subject per teacher per division (constraint 9)."
        ),
    )


@router.post("/{division_id}/courses", response_model=CourseAssignmentRead, status_code=status.HTTP_201_CREATED)
def add_course_assignment(division_id: int, payload: CourseAssignmentCreate, db: DbSession) -> CourseAssignmentRead:
    # Adds one course+teacher+rooms row to the division's draft list. Weekly theory/lab
    # periods are derived from the course's own credit hours here, not trusted from the
    # client "auto-computed, not manually typed" per the dashboard's design.
    division = _get_division_or_404(db, division_id)
    _require_unlocked(division)

    course = db.get(Course, payload.course_id)
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Course {payload.course_id} does not exist.")
    teacher = db.get(Teacher, payload.teacher_id)
    if teacher is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Teacher {payload.teacher_id} does not exist.")
    _validate_rooms(db, course, payload.lecture_room_id, payload.lab_room_id)

    conflict_course = _find_teacher_conflict(db, division_id, payload.teacher_id, payload.course_id)
    if conflict_course is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"{teacher.full_name} is already assigned {conflict_course} in this division "
            "one subject per teacher per division (constraint 9).",
        )

    existing = db.scalar(
        select(DivisionCourse).where(
            DivisionCourse.division_id == division_id, DivisionCourse.course_id == payload.course_id
        )
    )
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"{course.name} is already assigned in this division.")

    # The dashboard's single teacher dropdown covers both theory and lab for a course added
    # this way (Phase 9 keeps the flow to one teacher per course row, unlike the BSCS seed
    # data where a lab can have a different instructor) see docs/PROJECT_AUDIT.md Phase 9.
    assignment = DivisionCourse(
        division_id=division_id,
        course_id=course.id,
        teacher_id=teacher.id,
        weekly_theory_periods=course.credit_hours or 1,
        has_lab=course.has_lab,
        lab_teacher_id=teacher.id if course.has_lab else None,
        weekly_lab_periods=(course.lab_credit_hours or 1) if course.has_lab else None,
        lecture_room_id=payload.lecture_room_id,
        lab_room_id=payload.lab_room_id if course.has_lab else None,
        joint_division_id=payload.joint_division_id,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return _to_assignment_read(db, assignment)


@router.patch("/{division_id}/courses/{assignment_id}", response_model=CourseAssignmentRead)
def update_course_assignment(
    division_id: int, assignment_id: int, payload: CourseAssignmentUpdate, db: DbSession
) -> CourseAssignmentRead:
    # Edits a draft row in place teacher and/or rooms only (see CourseAssignmentUpdate).
    division = _get_division_or_404(db, division_id)
    _require_unlocked(division)
    assignment = _get_assignment_or_404(db, division_id, assignment_id)
    course = db.get(Course, assignment.course_id)

    new_teacher_id = payload.teacher_id if payload.teacher_id is not None else assignment.teacher_id
    if payload.teacher_id is not None:
        teacher = db.get(Teacher, payload.teacher_id)
        if teacher is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Teacher {payload.teacher_id} does not exist.")
        conflict_course = _find_teacher_conflict(
            db, division_id, new_teacher_id, assignment.course_id, exclude_assignment_id=assignment.id
        )
        if conflict_course is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"{teacher.full_name} is already assigned {conflict_course} in this division "
                "one subject per teacher per division (constraint 9).",
            )
        assignment.teacher_id = new_teacher_id
        if assignment.has_lab:
            assignment.lab_teacher_id = new_teacher_id

    lecture_room_id = payload.lecture_room_id if payload.lecture_room_id is not None else assignment.lecture_room_id
    lab_room_id = payload.lab_room_id if payload.lab_room_id is not None else assignment.lab_room_id
    if payload.lecture_room_id is not None or payload.lab_room_id is not None:
        _validate_rooms(db, course, lecture_room_id, lab_room_id if assignment.has_lab else None)
        assignment.lecture_room_id = lecture_room_id
        if assignment.has_lab:
            assignment.lab_room_id = lab_room_id

    if payload.joint_division_id is not None:
        assignment.joint_division_id = payload.joint_division_id

    db.commit()
    db.refresh(assignment)
    return _to_assignment_read(db, assignment)


@router.delete("/{division_id}/courses/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_course_assignment(division_id: int, assignment_id: int, db: DbSession) -> None:
    # Drops one draft row entirely.
    division = _get_division_or_404(db, division_id)
    _require_unlocked(division)
    assignment = _get_assignment_or_404(db, division_id, assignment_id)
    db.delete(assignment)
    db.commit()


@router.post("/{division_id}/finalize", response_model=GenerateResponse, status_code=status.HTTP_201_CREATED)
def finalize_division(division_id: int, db: DbSession) -> GenerateResponse:
    # Locks the assignment list (so it can't be edited out from under a result the admin is
    # about to look at) and runs the real GA for this one division, via the same
    # run_generation() that POST /timetables/generate uses see timetables.py's module
    # docstring for why this isn't a second copy of the save logic. Calling finalize again
    # on an already-locked division is allowed (a fresh generation attempt from the same
    # fixed list); it just doesn't re-lock what's already locked.
    division = _get_division_or_404(db, division_id)
    count = db.scalar(
        select(DivisionCourse.id).where(DivisionCourse.division_id == division_id).limit(1)
    )
    if count is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Add at least one course assignment before finalizing.")

    if division.assignments_locked_at is None:
        division.assignments_locked_at = datetime.now(UTC)
        db.commit()

    return run_generation(db, [division_id], GaSettings(), division.label)


def _build_label(program_name: str, part: int, shift: str, group: str | None) -> str:
    # Human-readable division label, same shape the BSCS seed script builds
    # ("BS Computer Science Part-I (Morning) Pre-Medical"), minus the group suffix for a
    # program with no PM/PE split (Mathematics docs/PROJECT_ARCHITECTURE.md §11.1).
    base = f"{program_name} Part-{PART_ROMAN[part]} ({shift})"
    return f"{base} {GROUP_LABELS[group]}" if group else base


def _get_division_or_404(db: Session, division_id: int) -> Division:
    # Fetches a division or raises the 404 every endpoint above would otherwise repeat.
    division = db.get(Division, division_id)
    if division is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Division {division_id} does not exist.")
    return division


def _get_assignment_or_404(db: Session, division_id: int, assignment_id: int) -> DivisionCourse:
    # Fetches one assignment, confirming it actually belongs to this division.
    assignment = db.get(DivisionCourse, assignment_id)
    if assignment is None or assignment.division_id != division_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Assignment {assignment_id} does not exist in this division.")
    return assignment


def _require_unlocked(division: Division) -> None:
    # The one enforcement point for "finalized means locked" every add/edit/remove
    # endpoint calls this before touching a row.
    if division.assignments_locked_at is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"{division.label}'s assignments were finalized on "
            f"{division.assignments_locked_at:%Y-%m-%d %H:%M} and can no longer be edited.",
        )


def _find_teacher_conflict(
    db: Session, division_id: int, teacher_id: int, course_id: int, exclude_assignment_id: int | None = None
) -> str | None:
    # Constraint 9: is this teacher already assigned a DIFFERENT course in this division, as
    # either the theory or the lab teacher? Returns that other course's name, or None.
    statement = (
        select(Course.name)
        .join(DivisionCourse, DivisionCourse.course_id == Course.id)
        .where(
            DivisionCourse.division_id == division_id,
            DivisionCourse.course_id != course_id,
            or_(DivisionCourse.teacher_id == teacher_id, DivisionCourse.lab_teacher_id == teacher_id),
        )
    )
    if exclude_assignment_id is not None:
        statement = statement.where(DivisionCourse.id != exclude_assignment_id)
    return db.scalar(statement)


def _validate_rooms(db: Session, course: Course, lecture_room_id: int, lab_room_id: int | None) -> None:
    # Confirms the rooms actually exist and, for the lab room, is actually typed as a lab
    # a clear 400 beats a foreign-key error or a silently wrong room type.
    lecture_room = db.get(Classroom, lecture_room_id)
    if lecture_room is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Classroom {lecture_room_id} does not exist.")

    if course.has_lab:
        if lab_room_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{course.name} has a lab choose a lab room.")
        lab_room = db.get(Classroom, lab_room_id)
        if lab_room is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Classroom {lab_room_id} does not exist.")
        if lab_room.type != ClassroomType.LAB:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{lab_room.name} is not a lab room.")
    elif lab_room_id is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{course.name} has no lab remove the lab room.")


def _to_read(division: Division) -> DivisionRead:
    # Shapes one Division row for the API response.
    return DivisionRead(
        id=division.id,
        program_id=division.program_id,
        part=division.part,
        semester=division.semester,
        shift=division.shift,
        group=division.group,
        label=division.label,
        home_room_id=division.home_room_id,
        assignments_locked_at=division.assignments_locked_at.isoformat() if division.assignments_locked_at else None,
    )


def _to_assignment_read(db: Session, assignment: DivisionCourse) -> CourseAssignmentRead:
    # Shapes one DivisionCourse row with its course/teacher names joined in.
    course = db.get(Course, assignment.course_id)
    teacher = db.get(Teacher, assignment.teacher_id)
    return CourseAssignmentRead(
        id=assignment.id,
        division_id=assignment.division_id,
        course_id=assignment.course_id,
        course_code=course.code if course else "?",
        course_name=course.name if course else "?",
        teacher_id=assignment.teacher_id,
        teacher_name=teacher.full_name if teacher else "?",
        weekly_theory_periods=assignment.weekly_theory_periods,
        has_lab=assignment.has_lab,
        lab_teacher_id=assignment.lab_teacher_id,
        weekly_lab_periods=assignment.weekly_lab_periods,
        lecture_room_id=assignment.lecture_room_id,
        lab_room_id=assignment.lab_room_id,
        joint_division_id=assignment.joint_division_id,
    )
