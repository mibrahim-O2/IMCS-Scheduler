"""phase9 course semester division rooms lock

Revision ID: 6546114ebf29
Revises: 2ef363712bc6
Create Date: 2026-09-22 15:02:05.095263

Course.semester lets the Phase 9 data-entry dashboard filter a program's course list by
semester; the backfill below fills it in for every course that already belongs to a scheme
with a real semester grouping (an official upload) from that grouping directly, so existing
BSCS 2024 courses aren't left null. Schemes with no "semesters" key in their content (the
Phase 7 synthetic timetable-derived scheme) are left alone on purpose — see
docs/PROJECT_AUDIT.md Phase 9.

Division's unique key gains semester (a Part now spans two Division rows, one per
semester, instead of one); DivisionCourse gains its own pre-assignable lecture_room_id and
lab_room_id; Division gains assignments_locked_at so the data-entry dashboard can lock a
division's course list once the admin finalizes it.
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6546114ebf29'
down_revision: str | Sequence[str] | None = '2ef363712bc6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('courses', sa.Column('semester', sa.Integer(), nullable=True))
    op.add_column('division_courses', sa.Column('lecture_room_id', sa.Integer(), nullable=True))
    op.add_column('division_courses', sa.Column('lab_room_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'division_courses_lecture_room_id_fkey', 'division_courses', 'classrooms',
        ['lecture_room_id'], ['id'], ondelete='SET NULL',
    )
    op.create_foreign_key(
        'division_courses_lab_room_id_fkey', 'division_courses', 'classrooms',
        ['lab_room_id'], ['id'], ondelete='SET NULL',
    )
    op.add_column('divisions', sa.Column('assignments_locked_at', sa.DateTime(timezone=True), nullable=True))
    op.drop_constraint(op.f('uq_division_program_part_shift_group'), 'divisions', type_='unique')
    op.create_unique_constraint(
        'uq_division_program_part_shift_group_semester', 'divisions',
        ['program_id', 'part', 'shift', 'group', 'semester'],
    )

    # Backfill: for every course whose scheme actually groups by semester (an official
    # upload), read that grouping straight out of the JSON and set courses.semester from it.
    op.execute(
        """
        UPDATE courses c
        SET semester = (sem.value ->> 'semester')::int
        FROM course_schemes s,
             jsonb_array_elements(s.content -> 'semesters') AS sem(value),
             jsonb_array_elements(sem.value -> 'courses') AS crs(value)
        WHERE c.scheme_id = s.id
          AND s.content ? 'semesters'
          AND crs.value ->> 'code' = c.code
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_division_program_part_shift_group_semester', 'divisions', type_='unique')
    op.create_unique_constraint(
        op.f('uq_division_program_part_shift_group'), 'divisions',
        ['program_id', 'part', 'shift', 'group'], postgresql_nulls_not_distinct=False,
    )
    op.drop_column('divisions', 'assignments_locked_at')
    op.drop_constraint('division_courses_lab_room_id_fkey', 'division_courses', type_='foreignkey')
    op.drop_constraint('division_courses_lecture_room_id_fkey', 'division_courses', type_='foreignkey')
    op.drop_column('division_courses', 'lab_room_id')
    op.drop_column('division_courses', 'lecture_room_id')
    op.drop_column('courses', 'semester')
