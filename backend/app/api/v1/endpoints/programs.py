"""Department and Program endpoints backing the homepage hierarchy.

Returns all three departments with every program level each one offers;
`is_schedulable` tells the frontend which ones have a real timetable view.
See docs/PROJECT_ARCHITECTURE.md §3.1, §4, §5.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models import Department
from app.schemas.program import DepartmentRead

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/programs", response_model=list[DepartmentRead])
def list_programs(db: DbSession) -> list[Department]:
    # Departments in homepage order (CS -> AI -> Math), each with its program levels nested.
    statement = (
        select(Department)
        .options(selectinload(Department.programs))
        .order_by(Department.display_order)
    )
    return list(db.scalars(statement))
