"""Request/response schemas for the Phase 9 data-entry dashboard: creating a
Division and building up its DivisionCourse assignments before finalizing.

See docs/PROJECT_ARCHITECTURE.md §3.2 and docs/PROJECT_AUDIT.md Phase 9.
"""

from pydantic import BaseModel, ConfigDict, Field


class DivisionCreate(BaseModel):
    program_id: int
    part: int = Field(ge=1, le=4)
    semester: int = Field(ge=1, le=8)
    shift: str = Field(pattern="^(Morning|Evening)$")
    # Null for a program with no PM/PE split (Mathematics — see
    # docs/PROJECT_ARCHITECTURE.md §11.1, still an open question for that program).
    group: str | None = Field(default=None, pattern="^(PM|PE)$")


class DivisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    program_id: int
    part: int
    semester: int | None
    shift: str | None
    group: str | None
    label: str
    home_room_id: int | None
    assignments_locked_at: str | None


class CourseAssignmentCreate(BaseModel):
    course_id: int
    teacher_id: int
    lecture_room_id: int
    # Only meaningful when the course has a lab; the endpoint checks this against the
    # course's own has_lab rather than trusting the client to only send it when appropriate.
    lab_room_id: int | None = None
    # A session shared with another division at once (e.g. History-II) — see
    # docs/CONSTRAINTS.md constraint 5. Optional; most assignments don't need it.
    joint_division_id: int | None = None


class CourseAssignmentUpdate(BaseModel):
    # Every field optional: only what the admin actually changed is sent. The course itself
    # can't be changed this way — remove the row and add a new one instead, which keeps the
    # weekly-periods recompute (tied to the course) simple and unambiguous.
    teacher_id: int | None = None
    lecture_room_id: int | None = None
    lab_room_id: int | None = None
    joint_division_id: int | None = None


class CourseAssignmentRead(BaseModel):
    id: int
    division_id: int
    course_id: int
    course_code: str
    course_name: str
    teacher_id: int
    teacher_name: str
    weekly_theory_periods: int
    has_lab: bool
    lab_teacher_id: int | None
    weekly_lab_periods: int | None
    lecture_room_id: int | None
    lab_room_id: int | None
    joint_division_id: int | None


class TeacherConflictCheck(BaseModel):
    conflict: bool
    message: str | None = None
