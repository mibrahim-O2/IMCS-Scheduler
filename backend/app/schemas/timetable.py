"""Request/response schemas for triggering and viewing GA-generated timetables.

See docs/PROJECT_ARCHITECTURE.md §3.7 and §6.
"""

from datetime import datetime, time

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    # None means "every schedulable BSCS division" — the endpoint fills that in.
    division_ids: list[int] | None = None
    seed: int | None = None
    population_size: int = Field(default=120, ge=10, le=1000)
    max_generations: int = Field(default=4000, ge=10, le=20000)


class GenerateResponse(BaseModel):
    timetable_id: int
    label: str
    status: str
    converged: bool
    stagnated: bool
    fitness_score: float
    generation_count: int
    wall_seconds: float
    session_count: int
    conflict_list: list[str]


class TimetableSummary(BaseModel):
    id: int
    label: str
    status: str
    converged: bool
    fitness_score: float | None
    generation_count: int | None
    session_count: int
    division_labels: list[str]
    created_at: datetime


class SessionOut(BaseModel):
    start_time: time
    end_time: time
    course_code: str
    course_name: str
    teacher_name: str
    room_name: str
    is_lab: bool
    division_labels: list[str]


class DayOut(BaseModel):
    day: str
    sessions: list[SessionOut]


class DivisionScheduleOut(BaseModel):
    division_id: int
    division_label: str
    days: list[DayOut]


class TimetableDetail(TimetableSummary):
    generation_params: dict
    conflict_list: list[str]
    divisions: list[DivisionScheduleOut]
