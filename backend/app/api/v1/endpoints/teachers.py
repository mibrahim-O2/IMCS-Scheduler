"""Teacher endpoints, including declared availability (docs/PROJECT_ARCHITECTURE.md §3.4, §4).

Real CRUD, added in Phase 9 for the data-entry dashboard before this, the only way to
get a Teacher row into the database was the BSCS timetable seed script. Phase 10 adds a
name search (for the teacher lookup page's type-ahead) and a combined detail view: every
Division assignment plus, when one exists, the teacher's real placed schedule from the
most recently generated Timetable that includes them.
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import or_, select

from app.api.deps import DbSession
from app.models import Classroom, Course, Division, DivisionCourse, Program, Teacher, Timetable, TimetableSession
from app.schemas.teacher import (
    TeacherAssignmentOut,
    TeacherCreate,
    TeacherDetail,
    TeacherRead,
    TeacherScheduleSessionOut,
)

router = APIRouter(prefix="/teachers")


@router.get("", response_model=list[TeacherRead])
def list_teachers(db: DbSession, program_id: int | None = None, search: str | None = None) -> list[TeacherRead]:
    # Every teacher on record, optionally narrowed to one home program (the build-timetable
    # dashboard's teacher dropdown) or by a case-insensitive name substring (the teacher
    # lookup page's search box) either can still show a teacher outside their home program
    # (docs/PROJECT_ARCHITECTURE.md §3.4) neither filter is a hard rule, just a narrowing.
    statement = select(Teacher).order_by(Teacher.full_name)
    if program_id is not None:
        statement = statement.where(Teacher.home_program_id == program_id)
    if search:
        statement = statement.where(Teacher.full_name.ilike(f"%{search}%"))
    return [_to_read(row) for row in db.scalars(statement)]


@router.post("", response_model=TeacherRead, status_code=status.HTTP_201_CREATED)
def create_teacher(payload: TeacherCreate, db: DbSession) -> TeacherRead:
    # Creates one new Teacher row from the dashboard's inline "add new teacher" form. Plain
    # create, no dedup-by-name: unlike the seed script (which merges same-named rows because
    # one real person appears many times across a whole timetable import), an admin typing a
    # name once here is a single deliberate action.
    teacher = Teacher(
        full_name=payload.full_name,
        designation=payload.designation,
        home_program_id=payload.home_program_id,
        availability=payload.availability.model_dump(),
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return _to_read(teacher)


@router.get("/{teacher_id}", response_model=TeacherDetail)
def get_teacher(teacher_id: int, db: DbSession) -> TeacherDetail:
    # The teacher lookup page's main query: this teacher's own record, every Division
    # assignment they hold, and their real weekly schedule if one has ever been generated.
    teacher = db.get(Teacher, teacher_id)
    if teacher is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Teacher {teacher_id} does not exist.")

    assignments = _load_assignments(db, teacher_id)
    schedule, timetable_id, timetable_label = _load_latest_schedule(db, teacher_id)

    return TeacherDetail(
        **_to_read(teacher).model_dump(),
        assignments=assignments,
        schedule=schedule,
        schedule_timetable_id=timetable_id,
        schedule_timetable_label=timetable_label,
    )


def _load_assignments(db: DbSession, teacher_id: int) -> list[TeacherAssignmentOut]:
    # Every DivisionCourse row naming this teacher as either the theory teacher or the lab
    # teacher (Phase 9's data-entry side) one output row per role they actually hold, so a
    # teacher who takes both the theory and the lab for one course gets two rows, each
    # correctly labelled and with that role's own weekly period count.
    rows = db.execute(
        select(DivisionCourse, Division, Course, Program)
        .join(Division, Division.id == DivisionCourse.division_id)
        .join(Course, Course.id == DivisionCourse.course_id)
        .join(Program, Program.id == Division.program_id)
        .where(or_(DivisionCourse.teacher_id == teacher_id, DivisionCourse.lab_teacher_id == teacher_id))
        .order_by(Program.display_name, Division.part, Division.semester)
    ).all()

    out: list[TeacherAssignmentOut] = []
    for assignment, division, course, program in rows:
        base = {
            "division_id": division.id,
            "division_label": division.label,
            "program_name": program.display_name,
            "part": division.part,
            "semester": division.semester,
            "shift": division.shift,
            "group": division.group,
            "course_name": course.name,
        }
        if assignment.teacher_id == teacher_id:
            out.append(TeacherAssignmentOut(**base, is_lab=False, weekly_periods=assignment.weekly_theory_periods))
        if assignment.has_lab and assignment.lab_teacher_id == teacher_id:
            out.append(TeacherAssignmentOut(**base, is_lab=True, weekly_periods=assignment.weekly_lab_periods or 0))
    return out


def _load_latest_schedule(
    db: DbSession, teacher_id: int
) -> tuple[list[TeacherScheduleSessionOut], int | None, str | None]:
    # This teacher's real placed sessions, taken only from the single most recently
    # generated Timetable that includes them multiple regenerations of the same division
    # exist in this database (docs/PROJECT_AUDIT.md's testing history), and showing every
    # one of them at once would look like a self-contradicting schedule.
    latest_timetable_id = db.scalar(
        select(Timetable.id)
        .join(TimetableSession, TimetableSession.timetable_id == Timetable.id)
        .where(TimetableSession.teacher_id == teacher_id)
        .order_by(Timetable.created_at.desc())
        .limit(1)
    )
    if latest_timetable_id is None:
        return [], None, None

    timetable = db.get(Timetable, latest_timetable_id)
    sessions = db.scalars(
        select(TimetableSession)
        .where(TimetableSession.timetable_id == latest_timetable_id, TimetableSession.teacher_id == teacher_id)
        .order_by(TimetableSession.day, TimetableSession.start_time)
    ).all()

    courses = {row.id: row for row in db.scalars(select(Course))}
    rooms = {row.id: row for row in db.scalars(select(Classroom))}
    divisions = {row.id: row for row in db.scalars(select(Division))}

    out = [
        TeacherScheduleSessionOut(
            day=session.day,
            start_time=session.start_time,
            end_time=session.end_time,
            course_name=courses[session.course_id].name,
            room_name=rooms[session.room_id].name,
            division_labels=[divisions[d].label for d in session.division_ids if d in divisions],
            is_lab=session.is_lab,
        )
        for session in sessions
    ]
    return out, timetable.id, timetable.label


def _to_read(teacher: Teacher) -> TeacherRead:
    # Shapes one Teacher row for the API response.
    return TeacherRead(
        id=teacher.id,
        full_name=teacher.full_name,
        designation=teacher.designation,
        home_program_id=teacher.home_program_id,
        availability=teacher.availability,
    )
