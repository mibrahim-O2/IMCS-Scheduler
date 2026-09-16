"""Request/response schemas for Course Scheme upload, review and listing.

See docs/PROJECT_ARCHITECTURE.md §3.6 and §7.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExtractionResponse(BaseModel):
    filename: str
    method: str  # "pdf-text", "ocr" or "word" — the frontend tells the admin which was used
    page_count: int
    character_count: int
    text: str
    warnings: list[str] = []


class CourseIn(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=200)

    # Null means non-credit, written as "NC" in the scheme documents.
    credit_hours: int | None = Field(default=None, ge=0, le=20)

    has_lab: bool = False
    lab_credit_hours: int | None = Field(default=None, ge=0, le=20)
    min_marks: int | None = Field(default=None, ge=0, le=1000)
    max_marks: int | None = Field(default=None, ge=0, le=1000)


class SemesterIn(BaseModel):
    semester: int = Field(ge=1, le=8)
    courses: list[CourseIn]


class SchemeContentIn(BaseModel):
    semesters: list[SemesterIn] = Field(min_length=1)


class SchemeCreate(BaseModel):
    program_id: int
    scheme_year: int = Field(ge=2000, le=2100)
    content: SchemeContentIn

    # The admin-reviewed extracted text, kept alongside the structured rows for audit.
    raw_text: str | None = None


class SchemeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    program_id: int
    program_name: str
    scheme_year: int
    source_filename: str | None
    file_url: str | None
    uploaded_at: datetime
    is_active: bool
    course_count: int


class SchemeDetail(SchemeSummary):
    content: dict[str, Any]
