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
    ExtractionResponse,
    SchemeCreate,
    SchemeDetail,
    SchemeSummary,
)
from app.services import course_scheme_service as service

router = APIRouter(prefix="/course-schemes")


@router.post("/extract", response_model=ExtractionResponse)
async def extract_scheme_text(file: Annotated[UploadFile, File()]) -> ExtractionResponse:
    # Step 1: read the uploaded document and hand its text back for the admin to review.
    # Nothing is stored here — this is a read-only preview of the file.
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

    existing = db.scalar(
        select(CourseScheme).where(
            CourseScheme.program_id == scheme_in.program_id,
            CourseScheme.scheme_year == scheme_in.scheme_year,
        )
    )
    if existing is not None and existing.is_active:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"{program.display_name} already has an active {scheme_in.scheme_year} scheme. "
            "Delete it before uploading a replacement.",
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
        # Reuse the soft-deleted row for this program/year if there is one; the unique
        # constraint on (program_id, scheme_year) means we cannot simply insert another.
        scheme = existing or CourseScheme(
            program_id=scheme_in.program_id, scheme_year=scheme_in.scheme_year
        )
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
    return [_to_summary(db, scheme, program) for scheme, program in rows]


@router.get("/{scheme_id}", response_model=SchemeDetail)
def get_scheme(scheme_id: int, db: DbSession) -> SchemeDetail:
    # Full scheme including its content JSON, for viewing one saved scheme.
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
    return _to_summary(db, scheme, program)


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


def _count_courses(db: Session, scheme_id: int) -> int:
    # How many materialized Course rows this scheme produced.
    return db.scalar(select(func.count()).select_from(Course).where(Course.scheme_id == scheme_id)) or 0


def _to_summary(db: Session, scheme: CourseScheme, program: Program) -> SchemeSummary:
    # Shapes one scheme row for the list view.
    return SchemeSummary(
        id=scheme.id,
        program_id=scheme.program_id,
        program_name=program.display_name,
        scheme_year=scheme.scheme_year,
        source_filename=scheme.source_filename,
        file_url=scheme.file_url,
        uploaded_at=scheme.uploaded_at,
        is_active=scheme.is_active,
        course_count=_count_courses(db, scheme.id),
    )


def _to_detail(db: Session, scheme: CourseScheme, program: Program) -> SchemeDetail:
    # Same as the summary, plus the stored content JSON.
    return SchemeDetail(**_to_summary(db, scheme, program).model_dump(), content=scheme.content)
