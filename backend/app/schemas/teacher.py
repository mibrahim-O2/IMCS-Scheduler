"""Request/response schemas for the Teacher endpoints.

See docs/PROJECT_ARCHITECTURE.md §3.4, §4.
"""

from pydantic import BaseModel, ConfigDict, Field

DAY_CHOICES = ("Mon", "Tue", "Wed", "Thu", "Fri")


class TeacherAvailability(BaseModel):
    # Which weekdays this teacher has said they can teach the GA's own input constraint,
    # not something it ever infers or overrides.
    days: list[str] = Field(default_factory=list)


class TeacherCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    designation: str | None = Field(default=None, max_length=100)
    home_program_id: int | None = None
    availability: TeacherAvailability = Field(default_factory=TeacherAvailability)


class TeacherRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    designation: str | None
    home_program_id: int | None
    availability: dict
