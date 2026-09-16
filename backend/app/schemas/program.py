"""Response schemas for the departments/programs endpoint.

See docs/PROJECT_ARCHITECTURE.md §3.1 and §5.
"""

from pydantic import BaseModel, ConfigDict

from app.models.program import ProgramLevel


class ProgramRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    level: ProgramLevel
    display_name: str
    total_semesters: int | None
    is_schedulable: bool
    has_shift_split: bool
    has_pm_pe_split_from_part: int | None


class DepartmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    short_code: str
    display_order: int
    programs: list[ProgramRead]
