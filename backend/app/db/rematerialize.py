"""Rebuilds Course rows from each scheme's stored content.

Run with `python -m app.db.rematerialize` for every scheme, or pass scheme ids
(`python -m app.db.rematerialize 6`). The content JSON is never modified only
the Course rows derived from it are regenerated, e.g. after the lab-pairing rule
changed. See docs/PROJECT_ARCHITECTURE.md §3.5–§3.6.
"""

import sys

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import CourseScheme
from app.services.course_scheme_service import course_counts, materialize_courses


def rematerialize(scheme_ids: list[int]) -> None:
    # Regenerates courses for the named schemes (all of them when the list is empty) and
    # prints the before/after counts so the change is visible.
    with SessionLocal() as session:
        statement = select(CourseScheme).order_by(CourseScheme.id)
        if scheme_ids:
            statement = statement.where(CourseScheme.id.in_(scheme_ids))
        schemes = session.scalars(statement).all()

        if not schemes:
            print("No matching course schemes.")
            return

        before = course_counts(session, [scheme.id for scheme in schemes])
        for scheme in schemes:
            materialize_courses(session, scheme)
        session.commit()
        after = course_counts(session, [scheme.id for scheme in schemes])

        for scheme in schemes:
            old_total, old_labs = before.get(scheme.id, (0, 0))
            new_total, new_labs = after.get(scheme.id, (0, 0))
            print(
                f"scheme #{scheme.id} ({scheme.scheme_year}): "
                f"{old_total} courses / {old_labs} with lab  ->  {new_total} courses / {new_labs} with lab"
            )


if __name__ == "__main__":
    rematerialize([int(arg) for arg in sys.argv[1:]])
