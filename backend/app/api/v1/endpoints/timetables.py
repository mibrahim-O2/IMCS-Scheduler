"""Timetable endpoints: trigger a real GA generation, list, view detail, and export.

Calls scheduler/engine.py and contains no scheduling logic of its own this
file's job is turning a request into a call into the engine, and turning the
engine's result into database rows and a response
(docs/PROJECT_ARCHITECTURE.md §4, §6, §9).

`run_generation()` is the one place that actually calls the engine and saves its result
both this file's own POST /generate and the Phase 9 data-entry dashboard's
POST /divisions/{id}/finalize (app/api/v1/endpoints/divisions.py) call it, so there is one
save path, not two copies of the same logic.
"""

import io
from collections import defaultdict

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import DbSession
from app.models import (
    Classroom,
    Course,
    Division,
    Program,
    Teacher,
    Timetable,
    TimetableSession,
    TimetableStatus,
)
from app.schemas.timetable import (
    DayOut,
    DivisionScheduleOut,
    GenerateRequest,
    GenerateResponse,
    SessionOut,
    TimetableDetail,
    TimetableSummary,
)
from app.scheduler.chromosome import DAYS, TIME_SLOTS
from app.scheduler.constraints.hard import describe
from app.scheduler.engine import GaSettings, generate_timetable
from app.services import export_service

router = APIRouter(prefix="/timetables")


def bscs_division_ids(db: DbSession) -> list[int]:
    # Every Division belonging to BS Computer Science specifically (not just any BS
    # program) the actual scope this phase seeds and schedules.
    return list(
        db.scalars(
            select(Division.id)
            .join(Program, Program.id == Division.program_id)
            .where(Program.display_name == "BS Computer Science")
            .order_by(Division.id)
        )
    )


def run_generation(db: Session, division_ids: list[int], settings: GaSettings, label: str) -> GenerateResponse:
    # The one place that calls the real GA and saves its result as a draft Timetable +
    # TimetableSession rows draft, not published, because a human should review it first
    # (docs/PROJECT_ARCHITECTURE.md §3.7). Both POST /generate below and the Phase 9
    # per-division "Finalize" flow (divisions.py) call this instead of each doing their own
    # engine call and save, so there is exactly one save path to keep correct.
    try:
        result = generate_timetable(db, division_ids, settings)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    conflict_list = [
        describe(violation) for found in result.final_violations.values() for violation in found
    ]

    timetable = Timetable(
        label=label,
        status=TimetableStatus.DRAFT,
        algorithm_version=settings.as_dict()["algorithm_version"],
        generation_params={**settings.as_dict(), "division_ids": division_ids},
        fitness_score=result.fitness,
        converged=result.converged,
        generation_count=result.generation_count,
        conflict_list=conflict_list,
    )
    db.add(timetable)
    db.flush()

    for gene, requirement in zip(result.chromosome, result.requirements, strict=True):
        _, start, end = TIME_SLOTS[gene.slot_index]
        db.add(
            TimetableSession(
                timetable_id=timetable.id,
                course_id=requirement.course_id,
                teacher_id=requirement.teacher_id,
                room_id=gene.room_id,
                division_ids=list(requirement.division_ids),
                day=gene.day,
                start_time=start,
                end_time=end,
                is_lab=requirement.is_lab,
            )
        )
    db.commit()
    db.refresh(timetable)

    return GenerateResponse(
        timetable_id=timetable.id,
        label=timetable.label,
        status=timetable.status.value,
        converged=timetable.converged,
        stagnated=result.stagnated,
        fitness_score=timetable.fitness_score,
        generation_count=timetable.generation_count,
        wall_seconds=result.wall_seconds,
        session_count=len(result.chromosome),
        conflict_list=conflict_list,
    )


@router.post("/generate", response_model=GenerateResponse, status_code=status.HTTP_201_CREATED)
def generate(payload: GenerateRequest, db: DbSession) -> GenerateResponse:
    # Runs the real GA against real database data, defaulting to every BSCS division when
    # none are named see run_generation() above for the actual engine call and save.
    division_ids = payload.division_ids or bscs_division_ids(db)
    if not division_ids:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No BSCS divisions found run the seed scripts first.")

    settings = GaSettings(
        seed=payload.seed, population_size=payload.population_size, max_generations=payload.max_generations
    )
    default_label = "BSCS Part-I to Part-IV (Morning)"
    label = default_label if payload.division_ids is None else f"BSCS ({len(division_ids)} divisions)"
    return run_generation(db, division_ids, settings, label)


@router.get("", response_model=list[TimetableSummary])
def list_timetables(db: DbSession) -> list[TimetableSummary]:
    # Every generated timetable, newest first, with a quick sense of what's in it.
    timetables = db.scalars(select(Timetable).order_by(Timetable.created_at.desc())).all()
    return [_to_summary(db, timetable) for timetable in timetables]


@router.get("/{timetable_id}", response_model=TimetableDetail)
def get_timetable(timetable_id: int, db: DbSession) -> TimetableDetail:
    # Full session detail, grouped by division then day then time not a flat list the
    # frontend has to re-sort itself.
    timetable = db.get(Timetable, timetable_id)
    if timetable is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Timetable {timetable_id} does not exist.")

    sessions = db.scalars(
        select(TimetableSession).where(TimetableSession.timetable_id == timetable_id)
    ).all()
    divisions = {row.id: row for row in db.scalars(select(Division))}
    courses = {row.id: row for row in db.scalars(select(Course))}
    teachers = {row.id: row for row in db.scalars(select(Teacher))}
    rooms = {row.id: row for row in db.scalars(select(Classroom))}

    by_division_day: dict[int, dict[str, list[TimetableSession]]] = defaultdict(lambda: defaultdict(list))
    for session_row in sessions:
        for division_id in session_row.division_ids:
            by_division_day[division_id][session_row.day].append(session_row)

    division_schedules = []
    for division_id in sorted(by_division_day, key=lambda did: divisions[did].label if did in divisions else ""):
        division = divisions.get(division_id)
        days_out = []
        for day in DAYS:
            day_sessions = sorted(by_division_day[division_id].get(day, []), key=lambda s: s.start_time)
            if not day_sessions:
                continue
            days_out.append(
                DayOut(
                    day=day,
                    sessions=[
                        SessionOut(
                            start_time=s.start_time,
                            end_time=s.end_time,
                            course_code=courses[s.course_id].code,
                            course_name=courses[s.course_id].name,
                            teacher_name=teachers[s.teacher_id].full_name,
                            room_name=rooms[s.room_id].name,
                            is_lab=s.is_lab,
                            division_labels=[divisions[d].label for d in s.division_ids if d in divisions],
                        )
                        for s in day_sessions
                    ],
                )
            )
        division_schedules.append(
            DivisionScheduleOut(
                division_id=division_id,
                division_label=division.label if division else f"Division {division_id}",
                days=days_out,
            )
        )

    summary = _to_summary(db, timetable, session_count=len(sessions))
    return TimetableDetail(
        **summary.model_dump(),
        generation_params=timetable.generation_params,
        conflict_list=timetable.conflict_list,
        divisions=division_schedules,
    )


@router.get("/{timetable_id}/export")
def export_timetable(timetable_id: int, db: DbSession) -> StreamingResponse:
    # Renders a saved timetable to a .docx file and streams it straight back nothing is
    # written to disk or kept between requests, so a re-export always reflects the current
    # database state (docs/PROJECT_ARCHITECTURE.md §9).
    timetable = db.get(Timetable, timetable_id)
    if timetable is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Timetable {timetable_id} does not exist.")

    document_bytes = export_service.build_timetable_document(db, timetable)
    filename = f"timetable-{timetable_id}.docx"
    return StreamingResponse(
        io.BytesIO(document_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _to_summary(db, timetable: Timetable, session_count: int | None = None) -> TimetableSummary:
    # Shapes one timetable row for the list view: its status plus which divisions it covers.
    if session_count is None:
        session_count = len(
            db.scalars(select(TimetableSession.id).where(TimetableSession.timetable_id == timetable.id)).all()
        )

    division_ids = timetable.generation_params.get("division_ids", [])
    labels = (
        [row.label for row in db.scalars(select(Division).where(Division.id.in_(division_ids)))]
        if division_ids
        else []
    )
    return TimetableSummary(
        id=timetable.id,
        label=timetable.label,
        status=timetable.status.value,
        converged=timetable.converged,
        fitness_score=timetable.fitness_score,
        generation_count=timetable.generation_count,
        session_count=session_count,
        division_labels=labels,
        created_at=timetable.created_at,
    )
