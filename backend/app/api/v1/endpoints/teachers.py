"""Teacher endpoints, including declared availability (docs/PROJECT_ARCHITECTURE.md §3.4, §4).

Real CRUD, added in Phase 9 for the data-entry dashboard before this, the only way to
get a Teacher row into the database was the BSCS timetable seed script.
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession
from app.models import Teacher
from app.schemas.teacher import TeacherCreate, TeacherRead

router = APIRouter(prefix="/teachers")


@router.get("", response_model=list[TeacherRead])
def list_teachers(db: DbSession, program_id: int | None = None) -> list[TeacherRead]:
    # Every teacher on record, optionally narrowed to one home program the dashboard's
    # teacher dropdown uses this, but a teacher can still be assigned outside their home
    # program (docs/PROJECT_ARCHITECTURE.md §3.4), so the filter is a convenience, not a rule.
    statement = select(Teacher).order_by(Teacher.full_name)
    if program_id is not None:
        statement = statement.where(Teacher.home_program_id == program_id)
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


@router.get("/{teacher_id}", response_model=TeacherRead)
def get_teacher(teacher_id: int, db: DbSession) -> TeacherRead:
    # One teacher's full record, e.g. for a detail view or a conflict-check message.
    teacher = db.get(Teacher, teacher_id)
    if teacher is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Teacher {teacher_id} does not exist.")
    return _to_read(teacher)


def _to_read(teacher: Teacher) -> TeacherRead:
    # Shapes one Teacher row for the API response.
    return TeacherRead(
        id=teacher.id,
        full_name=teacher.full_name,
        designation=teacher.designation,
        home_program_id=teacher.home_program_id,
        availability=teacher.availability,
    )
