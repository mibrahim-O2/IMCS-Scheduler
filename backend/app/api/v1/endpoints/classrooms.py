"""Classroom endpoints (docs/PROJECT_ARCHITECTURE.md §3.3, §4).

Real CRUD, added in Phase 9 for the data-entry dashboard before this, the only way to
get a Classroom row into the database was the BSCS timetable seed script.
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession
from app.models import Classroom, ClassroomType
from app.schemas.classroom import ClassroomCreate, ClassroomRead

router = APIRouter(prefix="/classrooms")


@router.get("", response_model=list[ClassroomRead])
def list_classrooms(db: DbSession, type: str | None = None) -> list[ClassroomRead]:
    # Every classroom on record, optionally narrowed to one type the dashboard uses
    # type="lab" to offer only Lab A-E for a lab room pre-assignment (Part 2), and no
    # filter (or type="lecture") for the lecture room dropdown.
    statement = select(Classroom).order_by(Classroom.name)
    if type is not None:
        statement = statement.where(Classroom.type == ClassroomType(type))
    return [_to_read(row) for row in db.scalars(statement)]


@router.post("", response_model=ClassroomRead, status_code=status.HTTP_201_CREATED)
def create_classroom(payload: ClassroomCreate, db: DbSession) -> ClassroomRead:
    # Creates one new Classroom row. Classroom.name is unique in the schema, so a duplicate
    # name is reported as a clear conflict rather than a raw database error.
    existing = db.scalar(select(Classroom).where(Classroom.name == payload.name))
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"A classroom named '{payload.name}' already exists.")

    classroom = Classroom(name=payload.name, type=ClassroomType(payload.type), capacity=payload.capacity)
    db.add(classroom)
    db.commit()
    db.refresh(classroom)
    return _to_read(classroom)


def _to_read(classroom: Classroom) -> ClassroomRead:
    # Shapes one Classroom row for the API response; .value turns the enum into a plain string.
    return ClassroomRead(id=classroom.id, name=classroom.name, type=classroom.type.value, capacity=classroom.capacity)
