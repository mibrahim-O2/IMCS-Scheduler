"""Seeds the fixed departments and program levels.

Run with `python -m app.db.seed`. Safe to run repeatedly rows are matched on
department short code and (department, level), then updated in place. Only the
three BS programs are schedulable today (docs/PROJECT_ARCHITECTURE.md §3.1).
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import Department, Program, ProgramLevel

SHIFT_SPLIT_DEPARTMENTS = {"CS", "AI"}

# Each department with the program levels it offers, per the university's course scheme portal.
DEPARTMENT_SEED: list[dict] = [
    {
        "name": "Computer Science",
        "short_code": "CS",
        "display_order": 1,
        "programs": [
            (ProgramLevel.BS, "BS Computer Science"),
            (ProgramLevel.MASTER, "Master of Computer Science (MCS)"),
            (ProgramLevel.MPHIL, "M.Phil Computer Science"),
            (ProgramLevel.MPHIL_BIOINFORMATICS, "M.Phil (Bioinformatics) Computer Science"),
            (ProgramLevel.PHD, "Ph.D Computer Science"),
            (ProgramLevel.MSC_PASS, "M.Sc. (Pass) Computer Science"),
            (ProgramLevel.PGD, "Post Graduate Diploma Computer Science"),
        ],
    },
    {
        "name": "Artificial Intelligence",
        "short_code": "AI",
        "display_order": 2,
        "programs": [
            (ProgramLevel.BS, "BS Artificial Intelligence"),
            (ProgramLevel.MASTER, "Master of Artificial Intelligence"),
            (ProgramLevel.MPHIL, "M.Phil Artificial Intelligence"),
            (ProgramLevel.MPHIL_BIOINFORMATICS, "M.Phil (Bioinformatics) Artificial Intelligence"),
            (ProgramLevel.PHD, "Ph.D Artificial Intelligence"),
            (ProgramLevel.MSC_PASS, "M.Sc. (Pass) Artificial Intelligence"),
            (ProgramLevel.PGD, "Post Graduate Diploma Artificial Intelligence"),
        ],
    },
    {
        "name": "Mathematics",
        "short_code": "MATH",
        "display_order": 3,
        "programs": [
            (ProgramLevel.BS, "BS Mathematics"),
            (ProgramLevel.MSC_PASS, "M.Sc. (Pass) Mathematics"),
            (ProgramLevel.MPHIL, "M.Phil Mathematics"),
            (ProgramLevel.PHD, "Ph.D Mathematics"),
        ],
    },
]


def program_attributes(level: ProgramLevel, short_code: str) -> dict:
    # BS is the only level we schedule, so it is the only one carrying semester/shift/group settings.
    if level is not ProgramLevel.BS:
        return {
            "total_semesters": None,
            "is_schedulable": False,
            "has_shift_split": False,
            "has_pm_pe_split_from_part": None,
        }

    splits_into_groups = short_code in SHIFT_SPLIT_DEPARTMENTS
    return {
        "total_semesters": 8,
        "is_schedulable": True,
        "has_shift_split": splits_into_groups,
        "has_pm_pe_split_from_part": 2 if splits_into_groups else None,
    }


def upsert_department(session: Session, spec: dict) -> Department:
    # Finds the department by short code and refreshes its fields, creating it on first run.
    department = session.scalar(
        select(Department).where(Department.short_code == spec["short_code"])
    )
    if department is None:
        department = Department(short_code=spec["short_code"])
        session.add(department)

    department.name = spec["name"]
    department.display_order = spec["display_order"]
    return department


def upsert_program(
    session: Session, department: Department, level: ProgramLevel, display_name: str
) -> Program:
    # Same idea for one program level under a department: update if present, insert if not.
    program = session.scalar(
        select(Program).where(Program.department_id == department.id, Program.level == level)
    )
    if program is None:
        program = Program(department_id=department.id, level=level)
        session.add(program)

    program.display_name = display_name
    for field, value in program_attributes(level, department.short_code).items():
        setattr(program, field, value)
    return program


def seed(session: Session) -> None:
    # Writes every department and its program levels in one transaction.
    for spec in DEPARTMENT_SEED:
        department = upsert_department(session, spec)
        session.flush()  # need the department id before its programs can reference it

        for level, display_name in spec["programs"]:
            upsert_program(session, department, level, display_name)

    session.commit()


def main() -> None:
    # CLI entry point; prints what ended up in the database so the run is verifiable.
    with SessionLocal() as session:
        seed(session)

        departments = session.scalar(select(func.count()).select_from(Department))
        programs = session.scalar(select(func.count()).select_from(Program))
        schedulable = session.scalar(
            select(func.count()).select_from(Program).where(Program.is_schedulable.is_(True))
        )

    print(f"departments: {departments}")
    print(f"programs: {programs}")
    print(f"schedulable programs: {schedulable}")


if __name__ == "__main__":
    main()
