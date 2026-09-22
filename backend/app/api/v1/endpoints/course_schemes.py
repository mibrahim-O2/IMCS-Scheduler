"""Course Scheme endpoints: extract, save, list, read and soft-delete.

Flow per docs/PROJECT_ARCHITECTURE.md §7: the admin uploads a file, reviews the
extracted text, fills in the structured course rows, previews, then confirms.
Only on confirm is anything written or stored.
"""

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import DbSession
from app.models import Course, CourseScheme, Program
from app.schemas.course_scheme import (
    CourseListItem,
    ExtractionResponse,
    NewSubjectCreate,
    SchemeCreate,
    SchemeDetail,
    SchemeSummary,
)
from app.services import course_scheme_service as service

router = APIRouter(prefix="/course-schemes")

# A separate router for /api/v1/courses a different resource (materialized Course rows)
# from /course-schemes (the uploaded documents they're materialized from), so it gets its
# own prefix even though both live in this file for now.
courses_router = APIRouter(prefix="/courses")

# scheme_year used for the per-program "manually added subjects" scheme the Phase 9
# data-entry dashboard's "add a new subject" quick-create writes into when no official
# Course Scheme has been uploaded yet for that program. Kept inactive, like the Phase 7
# synthetic BSCS scheme, so it never appears in the Course Scheme upload/list UI.
MANUAL_SCHEME_YEAR = 9999


@router.post("/extract", response_model=ExtractionResponse)
async def extract_scheme_text(file: Annotated[UploadFile, File()]) -> ExtractionResponse:
    # Step 1: read the uploaded document and hand its text back for the admin to review.
    # Nothing is stored here this is a read-only preview of the file.
    data = await file.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The uploaded file is empty.")

    try:
        result = service.extract_text(file.filename or "upload", data)
    except service.OcrUnavailableError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except service.SchemeFileError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    return ExtractionResponse(
        filename=file.filename or "upload",
        method=result.method,
        page_count=result.page_count,
        character_count=len(result.text),
        text=result.text,
        warnings=result.warnings,
    )


@router.post("", response_model=SchemeDetail, status_code=status.HTTP_201_CREATED)
async def create_scheme(
    db: DbSession,
    payload: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
) -> SchemeDetail:
    # Step 2 confirm: store the original file, save the structured content, and
    # materialize Course rows from it. The payload travels as a JSON string because
    # the original document rides along in the same multipart request.
    scheme_in = _parse_payload(payload)
    program = db.get(Program, scheme_in.program_id)
    if program is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Program {scheme_in.program_id} does not exist.")

    # A program can have only one ACTIVE scheme per Part slot (Phase 10) — the frontend's
    # per-slot "Replace" flow soft-deletes the old one first, but this check is the real
    # enforcement, not the UI. Keyed on the slot (program + Part), not the year: uploading a
    # different year into an already-filled slot is still a replacement, not a new slot.
    active_in_slot = db.scalar(
        select(CourseScheme).where(
            CourseScheme.program_id == scheme_in.program_id,
            CourseScheme.applies_to_part == scheme_in.applies_to_part,
            CourseScheme.is_active.is_(True),
        )
    )
    if active_in_slot is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"{program.display_name} Part-{scheme_in.applies_to_part} already has an active "
            f"{active_in_slot.scheme_year} scheme. Delete it before uploading a replacement.",
        )

    # A soft-deleted row for this exact slot+year is reused in place rather than inserted
    # again, matching the unique constraint on (program_id, applies_to_part, scheme_year).
    existing = db.scalar(
        select(CourseScheme).where(
            CourseScheme.program_id == scheme_in.program_id,
            CourseScheme.applies_to_part == scheme_in.applies_to_part,
            CourseScheme.scheme_year == scheme_in.scheme_year,
        )
    )

    data = await file.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The uploaded file is empty.")

    file_url = service.store_scheme_file(
        program_id=scheme_in.program_id,
        scheme_year=scheme_in.scheme_year,
        filename=file.filename or "scheme",
        data=data,
        content_type=file.content_type or "application/octet-stream",
    )

    content = scheme_in.content.model_dump()
    if scheme_in.raw_text:
        content["raw_text"] = scheme_in.raw_text

    try:
        scheme = existing or CourseScheme(
            program_id=scheme_in.program_id,
            applies_to_part=scheme_in.applies_to_part,
            scheme_year=scheme_in.scheme_year,
        )
        scheme.applies_to_part = scheme_in.applies_to_part
        scheme.source_filename = file.filename
        scheme.file_url = file_url
        scheme.content = content
        scheme.is_active = True
        scheme.uploaded_at = func.now()
        db.add(scheme)
        db.flush()

        service.materialize_courses(db, scheme)
        db.commit()
    except Exception:
        # Do not leave an orphaned file in Storage if the database write fails.
        db.rollback()
        service.remove_scheme_file(file_url)
        raise

    db.refresh(scheme)
    return _to_detail(db, scheme, program)


@router.get("", response_model=list[SchemeSummary])
def list_schemes(db: DbSession, include_inactive: bool = False) -> list[SchemeSummary]:
    # List view: newest upload first, with the program name and how many courses each scheme holds.
    statement = select(CourseScheme, Program).join(Program, Program.id == CourseScheme.program_id)
    if not include_inactive:
        statement = statement.where(CourseScheme.is_active.is_(True))

    rows = db.execute(statement.order_by(CourseScheme.uploaded_at.desc())).all()
    counts = service.course_counts(db, [scheme.id for scheme, _ in rows])
    return [_to_summary(scheme, program, counts.get(scheme.id, (0, 0))) for scheme, program in rows]


@router.get("/{scheme_id}", response_model=SchemeDetail)
def get_scheme(scheme_id: int, db: DbSession) -> SchemeDetail:
    # One saved scheme with its courses grouped by semester, labs shown on their theory course.
    scheme, program = _get_scheme_or_404(db, scheme_id)
    return _to_detail(db, scheme, program)


@router.delete("/{scheme_id}", response_model=SchemeSummary)
def delete_scheme(scheme_id: int, db: DbSession) -> SchemeSummary:
    # Soft delete only: a published timetable may depend on this scheme, and history must stay intact.
    scheme, program = _get_scheme_or_404(db, scheme_id)

    blocking = service.find_blocking_timetables(db, scheme.id)
    if blocking:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"This scheme is used by a published timetable ({', '.join(blocking)}) and cannot be deleted.",
        )

    scheme.is_active = False
    db.commit()
    db.refresh(scheme)
    return _to_summary(scheme, program, _counts_for(db, scheme.id))


@courses_router.get("", response_model=list[CourseListItem])
def list_courses(db: DbSession, program_id: int, semester: int) -> list[CourseListItem]:
    # Course dropdown for the Phase 9 data-entry dashboard: every course for this program's
    # currently active Course Scheme, plus anything added through "add a new subject" below
    # (its manual scheme is deliberately inactive, so it's included by scheme_year, not by
    # is_active see MANUAL_SCHEME_YEAR's comment).
    scheme_ids = db.scalars(
        select(CourseScheme.id).where(
            CourseScheme.program_id == program_id,
            (CourseScheme.is_active.is_(True)) | (CourseScheme.scheme_year == MANUAL_SCHEME_YEAR),
        )
    ).all()
    if not scheme_ids:
        return []

    rows = db.scalars(
        select(Course)
        .where(Course.scheme_id.in_(scheme_ids), Course.semester == semester)
        .order_by(Course.name)
    ).all()
    return [
        CourseListItem(
            id=row.id, scheme_id=row.scheme_id, code=row.code, name=row.name, credit_hours=row.credit_hours,
            semester=row.semester, has_lab=row.has_lab, lab_credit_hours=row.lab_credit_hours,
        )
        for row in rows
    ]


@courses_router.post("", response_model=CourseListItem, status_code=status.HTTP_201_CREATED)
def add_subject(payload: NewSubjectCreate, db: DbSession) -> CourseListItem:
    # "Add a new subject" without a full Course Scheme upload creates (or reuses) this
    # program's manual scheme, then one Course row in it, with a generated code since no
    # official document names one.
    program = db.get(Program, payload.program_id)
    if program is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Program {payload.program_id} does not exist.")

    scheme = db.scalar(
        select(CourseScheme).where(
            CourseScheme.program_id == payload.program_id, CourseScheme.scheme_year == MANUAL_SCHEME_YEAR
        )
    )
    if scheme is None:
        scheme = CourseScheme(
            program_id=payload.program_id,
            scheme_year=MANUAL_SCHEME_YEAR,
            is_active=False,
            content={
                "note": (
                    "Subjects added one at a time through the build-timetable dashboard "
                    "(Phase 9) not an official Course Scheme upload."
                )
            },
        )
        db.add(scheme)
        db.flush()

    taken_codes = set(db.scalars(select(Course.code).where(Course.scheme_id == scheme.id)))
    course = Course(
        scheme_id=scheme.id,
        code=service.make_course_code(payload.name, taken_codes),
        name=payload.name,
        credit_hours=payload.credit_hours,
        semester=payload.semester,
        has_lab=payload.has_lab,
        lab_credit_hours=payload.lab_credit_hours if payload.has_lab else None,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return CourseListItem(
        id=course.id, scheme_id=course.scheme_id, code=course.code, name=course.name,
        credit_hours=course.credit_hours, semester=course.semester, has_lab=course.has_lab,
        lab_credit_hours=course.lab_credit_hours,
    )


def _parse_payload(payload: str) -> SchemeCreate:
    # The structured form arrives as a JSON string field; turn it into a validated model.
    try:
        return SchemeCreate.model_validate_json(payload)
    except ValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, exc.errors()) from exc


def _get_scheme_or_404(db: Session, scheme_id: int) -> tuple[CourseScheme, Program]:
    # Fetches a scheme with its program, or raises the 404 every read endpoint would otherwise repeat.
    row = db.execute(
        select(CourseScheme, Program)
        .join(Program, Program.id == CourseScheme.program_id)
        .where(CourseScheme.id == scheme_id)
    ).first()

    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Course scheme {scheme_id} does not exist.")
    return row[0], row[1]


def _counts_for(db: Session, scheme_id: int) -> tuple[int, int]:
    # (total courses, courses with a lab) for a single scheme.
    return service.course_counts(db, [scheme_id]).get(scheme_id, (0, 0))


def _to_summary(scheme: CourseScheme, program: Program, counts: tuple[int, int]) -> SchemeSummary:
    # Shapes one scheme row for the list view.
    course_count, lab_course_count = counts
    return SchemeSummary(
        id=scheme.id,
        program_id=scheme.program_id,
        program_name=program.display_name,
        applies_to_part=scheme.applies_to_part,
        scheme_year=scheme.scheme_year,
        source_filename=scheme.source_filename,
        file_url=scheme.file_url,
        uploaded_at=scheme.uploaded_at,
        is_active=scheme.is_active,
        course_count=course_count,
        lab_course_count=lab_course_count,
    )


def _to_detail(db: Session, scheme: CourseScheme, program: Program) -> SchemeDetail:
    # The summary plus the stored content and the paired per-semester course view.
    return SchemeDetail(
        **_to_summary(scheme, program, _counts_for(db, scheme.id)).model_dump(),
        content=scheme.content,
        semesters=service.paired_semesters(scheme.content),
    )
