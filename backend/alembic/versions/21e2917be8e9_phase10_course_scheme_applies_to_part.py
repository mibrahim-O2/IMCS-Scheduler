"""phase10 course scheme applies to part

Revision ID: 21e2917be8e9
Revises: 6546114ebf29
Create Date: 2026-09-22 19:56:07.711124

Splits any existing whole-program scheme (one row whose content covers semesters from
more than one Part, e.g. the original BSCS 2024 upload covering all 8 semesters) into
one row per Part, so every CourseScheme row fits the new per-Part model cleanly instead
of one row being force-labelled with a single Part number that misrepresents the rest of
its content. Course rows follow their semester to the matching new scheme row. A scheme
with no semester grouping in its content (the Phase 7 synthetic scheme, and Phase 9's
per-program "manually added subjects" schemes) is left with applies_to_part = NULL see
the CourseScheme model docstring.
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '21e2917be8e9'
down_revision: str | Sequence[str] | None = '6546114ebf29'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Lightweight Core table definitions for the data migration below deliberately not the
# real ORM models, which are free to keep changing after this migration is written.
course_schemes = sa.table(
    "course_schemes",
    sa.column("id", sa.Integer),
    sa.column("program_id", sa.Integer),
    sa.column("applies_to_part", sa.Integer),
    sa.column("scheme_year", sa.Integer),
    sa.column("source_filename", sa.String),
    sa.column("file_url", sa.String),
    sa.column("is_active", sa.Boolean),
    sa.column("content", JSONB),
)
courses = sa.table(
    "courses",
    sa.column("id", sa.Integer),
    sa.column("scheme_id", sa.Integer),
    sa.column("semester", sa.Integer),
)


def _part_of(semester: int) -> int:
    # Part-I is semesters 1-2, Part-II is 3-4, Part-III is 5-6, Part-IV is 7-8.
    return (semester + 1) // 2


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('course_schemes', sa.Column('applies_to_part', sa.Integer(), nullable=True))
    op.drop_constraint(op.f('uq_scheme_program_year'), 'course_schemes', type_='unique')

    bind = op.get_bind()
    for scheme in bind.execute(sa.select(course_schemes)).mappings().all():
        semesters = scheme["content"].get("semesters") if isinstance(scheme["content"], dict) else None
        if not semesters:
            continue  # no semester grouping to split by leave applies_to_part null

        by_part: dict[int, list[dict]] = {}
        for entry in semesters:
            by_part.setdefault(_part_of(entry["semester"]), []).append(entry)
        parts_present = sorted(by_part)

        # The lowest Part becomes this row's own part; its content is trimmed to just that
        # Part's semesters so the row no longer silently claims the others too.
        first_part = parts_present[0]
        new_content = {**scheme["content"], "semesters": by_part[first_part]}
        bind.execute(
            course_schemes.update()
            .where(course_schemes.c.id == scheme["id"])
            .values(applies_to_part=first_part, content=new_content)
        )

        # Every other Part this row used to cover gets its own new row, and its Course rows
        # (matched by semester) move over to it.
        for part in parts_present[1:]:
            part_content = {**scheme["content"], "semesters": by_part[part]}
            new_id = bind.execute(
                course_schemes.insert()
                .values(
                    program_id=scheme["program_id"],
                    applies_to_part=part,
                    scheme_year=scheme["scheme_year"],
                    source_filename=scheme["source_filename"],
                    file_url=scheme["file_url"],
                    is_active=scheme["is_active"],
                    content=part_content,
                )
                .returning(course_schemes.c.id)
            ).scalar_one()

            semesters_in_part = {entry["semester"] for entry in by_part[part]}
            bind.execute(
                courses.update()
                .where(courses.c.scheme_id == scheme["id"], courses.c.semester.in_(semesters_in_part))
                .values(scheme_id=new_id)
            )

    op.create_unique_constraint(
        'uq_scheme_program_part_year', 'course_schemes', ['program_id', 'applies_to_part', 'scheme_year']
    )


def downgrade() -> None:
    """Downgrade schema."""
    # The split above is not reversed (merging rows back and moving courses again would
    # need the same care in reverse); downgrading only removes the column/constraint, which
    # leaves the split rows in place as ordinary CourseScheme rows with no applies_to_part.
    op.drop_constraint('uq_scheme_program_part_year', 'course_schemes', type_='unique')
    op.create_unique_constraint(
        op.f('uq_scheme_program_year'), 'course_schemes', ['program_id', 'scheme_year'],
        postgresql_nulls_not_distinct=False,
    )
    op.drop_column('course_schemes', 'applies_to_part')
