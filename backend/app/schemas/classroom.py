"""Request/response schemas for the Classroom endpoints.

See docs/PROJECT_ARCHITECTURE.md §3.3, §4.
"""

from pydantic import BaseModel, ConfigDict, Field


class ClassroomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    type: str = Field(pattern="^(lecture|lab|hall|multimedia)$")
    capacity: int | None = Field(default=None, ge=0)


class ClassroomRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    capacity: int | None
