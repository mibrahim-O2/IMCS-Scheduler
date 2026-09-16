"""Dashboard queries.

Today this only produces a stats overview — plain counts read from the
database. The "what's happening right now" view in docs/PROJECT_ARCHITECTURE.md
§8 needs published timetables, which do not exist yet, and will be added here
once they do.
"""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Classroom, CourseScheme, Department, Program, Teacher
from app.schemas.dashboard import CourseCounts, DashboardStats, ProgramCounts, SchemeBreakdown
from app.services.course_scheme_service import course_counts


def _count(session: Session, model, *conditions) -> int:
    # Row count for one table, optionally filtered.
    return session.scalar(select(func.count()).select_from(model).where(*conditions)) or 0


def collect_stats(session: Session) -> DashboardStats:
    # Gathers every number the stats page shows. Course figures only include active
    # schemes, since soft-deleted schemes are history rather than current data.
    active_schemes = session.execute(
        select(CourseScheme.id, CourseScheme.scheme_year, Program.display_name)
        .join(Program, Program.id == CourseScheme.program_id)
        .where(CourseScheme.is_active.is_(True))
        .order_by(Program.id, CourseScheme.scheme_year.desc())
    ).all()

    counts = course_counts(session, [scheme_id for scheme_id, _, _ in active_schemes])
    breakdown = [
        SchemeBreakdown(
            scheme_id=scheme_id,
            program_name=program_name,
            scheme_year=scheme_year,
            course_count=counts.get(scheme_id, (0, 0))[0],
            lab_course_count=counts.get(scheme_id, (0, 0))[1],
        )
        for scheme_id, scheme_year, program_name in active_schemes
    ]

    total_programs = _count(session, Program)
    schedulable_programs = _count(session, Program, Program.is_schedulable.is_(True))

    return DashboardStats(
        departments=_count(session, Department),
        programs=ProgramCounts(
            total=total_programs,
            schedulable=schedulable_programs,
            not_yet_schedulable=total_programs - schedulable_programs,
        ),
        course_schemes=len(breakdown),
        scheme_breakdown=breakdown,
        courses=CourseCounts(
            total=sum(item.course_count for item in breakdown),
            with_lab=sum(item.lab_course_count for item in breakdown),
        ),
        classrooms=_count(session, Classroom),
        teachers=_count(session, Teacher),
        generated_at=datetime.now(UTC),
    )
