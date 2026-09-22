"""Request/response schemas for the Teacher endpoints.

See docs/PROJECT_ARCHITECTURE.md §3.4, §4.
"""

from datetime import time

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


class TeacherAssignmentOut(BaseModel):
    # One DivisionCourse row this teacher is assigned to, from the data-entry side (Phase 9)
    # not necessarily a generated timetable's actual placement. Phase 10's teacher lookup page.
    division_id: int
    division_label: str
    program_name: str
    part: int
    semester: int | None
    shift: str | None
    group: str | None
    course_name: str
    is_lab: bool
    weekly_periods: int


class TeacherScheduleSessionOut(BaseModel):
    # One real placed session for this teacher, straight from a generated Timetable's
    # TimetableSession rows the GA's actual output, not the assignment list above.
    day: str
    start_time: time
    end_time: time
    course_name: str
    room_name: str
    division_labels: list[str]
    is_lab: bool


class TeacherDetail(TeacherRead):
    assignments: list[TeacherAssignmentOut]
    # Empty when no Timetable has ever been generated for any division this teacher is
    # assigned to the frontend shows that plainly rather than an empty-looking table.
    schedule: list[TeacherScheduleSessionOut]
    schedule_timetable_id: int | None
    schedule_timetable_label: str | None
