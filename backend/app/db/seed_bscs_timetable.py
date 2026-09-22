"""Seeds real Teachers, Classrooms, Divisions and DivisionCourse assignments
for BS Computer Science Part-I through Part-IV (Morning shift), read straight
out of docs/timetable.json the real, structured export of the official
timetable, adopted in the cleanup phase as the GA's reference data source.

Run with `python -m app.db.seed_bscs_timetable`. Safe to run repeatedly
everything is matched on a natural key and updated in place, same pattern as
app/db/seed.py.

What this reads from the JSON and how it's turned into rows:
- Each Part's schedule rows are grouped by (section, subject). A "Lab (XYZ)"
  subject is a lab session for the matching theory subject XYZ the
  abbreviation is resolved through LAB_ABBREVIATION_MAP below, built by
  checking that the lab row's teacher matches that subject's teacher for the
  same section (confirmed for every abbreviation actually present).
- A subject shown with section "PM/PE" is one session both groups sit
  together (e.g. History-II) it becomes ONE DivisionCourse row on the PM
  division with `joint_division_id` pointing at PE; PE gets no separate row.
- Two teacher names collide after stripping titles/punctuation the classic
  "initials aren't identifiers" problem, this time as a spelling
  inconsistency rather than initials: "Dr. Abdul Rehman Nangraj" is also
  printed "Mr. Abdul Rehman Nangraj" on the Part-II sheet, and
  "Mr. M. Rafiq Mallah" is also printed "Mr. M Rafiq Mallah" (missing the
  period) on the Part-I sheet. TEACHER_ALIASES canonicalizes both without
  this, the seed would create two Teacher rows for one real person and the
  cross-division clash check would silently miss a real clash for them.
- Room names, lecture: each Part's "classrooms" entry names the fixed lecture room
  per group ("Room No: 01" -> "Room 01"). A room shown as "Room No: 01/02" (the
  joint-session room) is recorded as the PM division's own room a deliberate
  simplification, documented rather than modeled as a third physical space.
- Room names, labs: the JSON writes lab rooms as "Lab / Room No: 01" .. "06"
  six numbered strings that follow the LECTURE room numbering. They are NOT the
  real labs. The department's real labs are five, shared by every division:
  Lab A, Lab B, Lab C, Lab D, Lab E (confirmed by the department, not derived
  from the JSON). The JSON therefore only tells us "this is a lab session" and
  when; it never says which of the five a session uses. So this seed creates
  exactly those five rooms, and which lab a given session sits in is decided
  by the GA's search (clash-avoiding), i.e. inferred, never sourced. An earlier
  version wrongly turned "Lab / Room No: 03" into a "Room 03 (Lab)" room;
  remove_placeholder_lab_rooms() clears those out.
- Credit hours are NOT assumed symmetric between PM and PE: IOT actually
  runs 3 periods/week for Part-I PM but only 2 for Part-I PE in the real
  data, and Mathematics-II is PM-only. DivisionCourse.weekly_theory_periods
  is read per (division, subject) exactly as printed, never averaged or
  assumed equal.
"""

import json
import re
from collections import defaultdict
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import (
    Classroom,
    ClassroomType,
    Course,
    CourseScheme,
    Department,
    Division,
    DivisionCourse,
    Program,
    Teacher,
    Timetable,
    TimetableSession,
    TimetableStatus,
)
from app.services.course_scheme_service import make_course_code

TIMETABLE_JSON_PATH = Path(__file__).resolve().parents[3] / "docs" / "timetable.json"

DAY_ABBREVIATIONS = {
    "Monday": "Mon", "Tuesday": "Tue", "Wednesday": "Wed", "Thursday": "Thu", "Friday": "Fri",
}

LAB_RE = re.compile(r"^Lab\s*\(([A-Za-z0-9]+)\)$", re.IGNORECASE)

# Maps each lab abbreviation to the exact theory subject name it belongs to. Verified by
# checking the lab row's teacher matches that subject's teacher, per section, for every
# entry actually present in the JSON see the module docstring.
LAB_ABBREVIATION_MAP = {
    "DLD": "Digital Logic Design",
    "OOP": "Object Oriented Programming",
    "CA": "Computer Architecture",
    "DBS": "Data Base System",
    "CN": "Computer Network",
    "HCICG": "HCI & Computer Graphics",
    "PDC": "Parallel & Distributed Computing",
}

# Real name collisions found in the JSON (see module docstring). Maps every spelling
# actually printed to one canonical full name, so one real person gets one Teacher row.
TEACHER_ALIASES = {
    "Mr. Abdul Rehman Nangraj": "Dr. Abdul Rehman Nangraj",
    "Mr. M Rafiq Mallah": "Mr. M. Rafiq Mallah",
}

# Subjects shown with section "PM/PE" one session both groups sit together.
JOINT_SUBJECTS = {"History-II", "Ethics"}

# The department's five real, physical labs, shared by every BSCS division.
LAB_ROOM_NAMES = ("Lab A", "Lab B", "Lab C", "Lab D", "Lab E")

# What an earlier seed wrongly created for labs: "Room 03 (Lab)" etc, one per lecture room.
PLACEHOLDER_LAB_ROOM_RE = re.compile(r"^Room \d+ \(Lab\)$")

GROUP_LABELS = {"PM": "Pre-Medical", "PE": "Pre-Engineering"}


def load_bscs_programs(timetable: dict) -> list[dict]:
    # Pulls out just the four BS(CS) Part entries; BS(AI) is in the same file but out of
    # scope for this seed (Phase 7 is BSCS Part-I to Part-IV only).
    programs = [
        program
        for department in timetable["departments"]
        for program in department["programs"]
        if program["class"].startswith("BS(CS)")
    ]
    if len(programs) != 4:
        raise ValueError(f"expected 4 BS(CS) parts in {TIMETABLE_JSON_PATH}, found {len(programs)}")
    return programs


def canonical_teacher_name(raw_name: str) -> str:
    # Collapses a known alias spelling onto its canonical full name; everyone else passes through.
    return TEACHER_ALIASES.get(raw_name, raw_name)


def room_base_name(raw_room: str) -> str:
    # Pulls the plain "Room NN" name out of a JSON room string, e.g. "Room No: 01" or the
    # joint PM/PE room "Room No: 01/02" (recorded as the lower-numbered room see module
    # docstring) both become "Room 01". Only ever called on the JSON's own "classrooms"
    # entry, which is never prefixed "Lab /", so there's nothing to strip for that case.
    number = re.search(r"\d+", raw_room).group()
    return f"Room {number}"


def parse_part_schedule(program: dict) -> dict:
    # Groups one Part's raw schedule rows into theory and lab entries, keyed by section,
    # so the rest of the seed can ask "how many periods a week does PM's Digital Logic
    # Design theory session need, and who teaches it" directly.
    theory: dict[tuple[str, str], list[dict]] = defaultdict(list)
    labs: dict[tuple[str, str], list[dict]] = defaultdict(list)

    for row in program["schedule"]:
        match = LAB_RE.match(row["subject"])
        if match:
            labs[(row["section"], match.group(1))].append(row)
        else:
            theory[(row["section"], row["subject"])].append(row)

    return {"theory": theory, "labs": labs}


def upsert_teacher(session: Session, full_name: str, home_program_id: int, days: set[str]) -> Teacher:
    # Finds a teacher by their canonical full name, or creates one; the availability
    # union grows if the same person is seen teaching on a day not recorded yet.
    teacher = session.scalar(select(Teacher).where(Teacher.full_name == full_name))
    if teacher is None:
        teacher = Teacher(full_name=full_name, home_program_id=home_program_id, availability={"days": []})
        session.add(teacher)
        session.flush()

    existing_days = set(teacher.availability.get("days", []))
    teacher.availability = {"days": sorted(existing_days | days, key=["Mon", "Tue", "Wed", "Thu", "Fri"].index)}
    return teacher


def upsert_classroom(session: Session, name: str, room_type: ClassroomType) -> Classroom:
    # A classroom is looked up by its exact name (unique in the schema) and created if new.
    classroom = session.scalar(select(Classroom).where(Classroom.name == name))
    if classroom is None:
        classroom = Classroom(name=name, type=room_type, features={})
        session.add(classroom)
        session.flush()
    return classroom


def upsert_lab_rooms(session: Session) -> list[Classroom]:
    # Makes sure exactly the five real labs exist, typed as labs. They belong to no
    # division: any lab session may use any of them.
    return [upsert_classroom(session, name, ClassroomType.LAB) for name in LAB_ROOM_NAMES]


def remove_placeholder_lab_rooms(session: Session) -> dict[str, int]:
    # Deletes the invented "Room NN (Lab)" rooms an earlier seed created. Any timetable
    # that put a lab in one of them describes a room that doesn't exist, so it is stale and
    # is removed with them but only if it is still a draft: a published timetable is never
    # silently deleted, the seed stops and says so instead.
    fake_rooms = [
        room
        for room in session.scalars(select(Classroom).where(Classroom.type == ClassroomType.LAB))
        if PLACEHOLDER_LAB_ROOM_RE.match(room.name)
    ]
    if not fake_rooms:
        return {"rooms": 0, "timetables": 0, "sessions": 0}

    fake_ids = [room.id for room in fake_rooms]
    stale_ids = set(
        session.scalars(select(TimetableSession.timetable_id).where(TimetableSession.room_id.in_(fake_ids)))
    )
    stale = session.scalars(select(Timetable).where(Timetable.id.in_(stale_ids))).all() if stale_ids else []
    kept = [t.id for t in stale if t.status != TimetableStatus.DRAFT]
    if kept:
        raise RuntimeError(f"Non-draft timetable(s) {kept} use placeholder lab rooms; resolve them by hand first.")

    sessions_deleted = 0
    if stale_ids:
        sessions_deleted = session.execute(
            delete(TimetableSession).where(TimetableSession.timetable_id.in_(stale_ids))
        ).rowcount
        session.execute(delete(Timetable).where(Timetable.id.in_(stale_ids)))
    session.execute(delete(Classroom).where(Classroom.id.in_(fake_ids)))
    return {"rooms": len(fake_ids), "timetables": len(stale_ids), "sessions": sessions_deleted}


def upsert_synthetic_scheme(session: Session, program_id: int) -> CourseScheme:
    # One scheme row to hang the real-timetable-derived Course rows off of. Kept inactive
    # so it never shows up in the admin Course Scheme UI (which is for uploaded official
    # documents) this one is seeded from the live timetable, not an admission-year scheme.
    scheme = session.scalar(
        select(CourseScheme).where(CourseScheme.program_id == program_id, CourseScheme.scheme_year == 2026)
    )
    if scheme is None:
        scheme = CourseScheme(program_id=program_id, scheme_year=2026)
        session.add(scheme)
        session.flush()

    scheme.source_filename = "docs/timetable.json"
    scheme.is_active = False
    scheme.content = {
        "note": (
            "Synthetic scheme materialized from the real Morning-shift timetable for GA "
            "seeding (Phase 7) not an official admission-year document. See "
            "docs/PROJECT_AUDIT.md."
        )
    }
    return scheme


def upsert_course(
    session: Session,
    scheme_id: int,
    name: str,
    credit_hours: int,
    has_lab: bool,
    lab_credit_hours: int | None,
    code_registry: set[str],
) -> Course:
    # One Course row per distinct subject name in the synthetic scheme looked up by NAME,
    # not a generated code, so the same subject taught to both PM and PE (two separate calls
    # into this function) reuses one row instead of getting a second row with a different code.
    course = session.scalar(select(Course).where(Course.scheme_id == scheme_id, Course.name == name))
    if course is None:
        course = Course(scheme_id=scheme_id, code=make_course_code(name, code_registry))
        session.add(course)

    # Real weekly periods can differ between PM and PE for the same subject (e.g. IOT: 3 vs
    # 2 in the actual data). Course keeps the higher figure as a reference value; the real
    # per-division figure that the GA actually schedules from is DivisionCourse.weekly_theory_periods.
    course.name = name
    course.credit_hours = max(credit_hours, course.credit_hours or 0)
    course.has_lab = course.has_lab or has_lab
    course.lab_credit_hours = max(lab_credit_hours or 0, course.lab_credit_hours or 0) or None
    return course


def upsert_division(
    session: Session,
    program_id: int,
    part: int,
    group: str,
    scheme_id: int,
    home_room_id: int,
) -> Division:
    # Matched on (program, part, shift, group) the natural key for "one specific class".
    division = session.scalar(
        select(Division).where(
            Division.program_id == program_id,
            Division.part == part,
            Division.shift == "Morning",
            Division.group == group,
        )
    )
    if division is None:
        division = Division(program_id=program_id, part=part, shift="Morning", group=group)
        session.add(division)

    # "2nd Semester 2026" (the JSON's own title) plus every Part-I subject matching the
    # official scheme's semester-2 list is what fixes semester = part * 2 see the
    # part/semester comment in app/models/division.py for the honesty caveat on this.
    division.semester = part * 2
    division.course_scheme_id = scheme_id
    division.label = f"BS Computer Science Part-{'I' * part if part <= 3 else 'IV'} (Morning) {GROUP_LABELS[group]}"
    division.home_room_id = home_room_id
    return division


def upsert_division_course(
    session: Session,
    division_id: int,
    course_id: int,
    teacher_id: int,
    weekly_theory_periods: int,
    has_lab: bool,
    lab_teacher_id: int | None,
    weekly_lab_periods: int | None,
    joint_division_id: int | None,
) -> DivisionCourse:
    # Matched on (division, course) one assignment row per subject a division actually takes.
    assignment = session.scalar(
        select(DivisionCourse).where(
            DivisionCourse.division_id == division_id, DivisionCourse.course_id == course_id
        )
    )
    if assignment is None:
        assignment = DivisionCourse(division_id=division_id, course_id=course_id)
        session.add(assignment)

    assignment.teacher_id = teacher_id
    assignment.weekly_theory_periods = weekly_theory_periods
    assignment.has_lab = has_lab
    assignment.lab_teacher_id = lab_teacher_id
    assignment.weekly_lab_periods = weekly_lab_periods
    assignment.joint_division_id = joint_division_id
    return assignment


def seed_part(
    session: Session,
    program_id: int,
    scheme_id: int,
    part_number: int,
    program_json: dict,
    code_registry: set[str],
) -> None:
    # Does one BSCS Part end to end: divisions, courses, teachers, classrooms, assignments.
    parsed = parse_part_schedule(program_json)

    # Each group's fixed lecture room comes straight from the JSON's own "classrooms" entry
    # for this Part (e.g. {"PM": "Room No: 01", "PE": "Room No: 02"}). Labs are not set here:
    # they are the five shared labs, chosen per session by the GA (see Division.home_room_id).
    divisions = {}
    for group in ("PM", "PE"):
        lecture_room = upsert_classroom(session, room_base_name(program_json["classrooms"][group]), ClassroomType.LECTURE)
        divisions[group] = upsert_division(session, program_id, part_number, group, scheme_id, lecture_room.id)
    session.flush()

    # Every distinct subject in this Part, with its per-section rows, so credit hours and
    # labs can be read out per (section, subject) rather than assumed symmetric.
    subjects = sorted({subject for (_, subject) in parsed["theory"]})

    for subject in subjects:
        is_joint = subject in JOINT_SUBJECTS
        # A joint subject's rows are filed under the JSON's own "PM/PE" section key, not
        # under "PM" or "PE" separately look it up there and record it once, on the PM
        # division, pointing at PE. Everything else is one row per section actually present.
        if is_joint:
            owning_sections = [("PM", "PM/PE")] if ("PM/PE", subject) in parsed["theory"] else []
        else:
            owning_sections = [(group, group) for group in ("PM", "PE") if (group, subject) in parsed["theory"]]
        if not owning_sections:
            continue

        for group, source_section in owning_sections:
            rows = parsed["theory"][(source_section, subject)]
            teacher_names = {canonical_teacher_name(r["teacher"]) for r in rows}
            if len(teacher_names) != 1:
                raise ValueError(f"{subject} ({group}, Part-{part_number}) has more than one teacher: {teacher_names}")
            teacher_name = next(iter(teacher_names))

            teacher = upsert_teacher(
                session, teacher_name, program_id, {DAY_ABBREVIATIONS[r["day"]] for r in rows}
            )

            lab_entries = None
            for abbreviation, expansion in LAB_ABBREVIATION_MAP.items():
                if expansion == subject and (group, abbreviation) in parsed["labs"]:
                    lab_entries = parsed["labs"][(group, abbreviation)]
                    break

            lab_teacher = None
            weekly_lab_periods = None
            if lab_entries:
                lab_teacher_names = {canonical_teacher_name(r["teacher"]) for r in lab_entries}
                lab_teacher = upsert_teacher(
                    session, next(iter(lab_teacher_names)), program_id,
                    {DAY_ABBREVIATIONS[r["day"]] for r in lab_entries},
                )
                weekly_lab_periods = len(lab_entries)

            course = upsert_course(
                session, scheme_id, subject,
                credit_hours=len(rows), has_lab=lab_entries is not None,
                lab_credit_hours=weekly_lab_periods, code_registry=code_registry,
            )
            session.flush()

            joint_division_id = divisions["PE"].id if is_joint else None
            upsert_division_course(
                session,
                division_id=divisions[group].id,
                course_id=course.id,
                teacher_id=teacher.id,
                weekly_theory_periods=len(rows),
                has_lab=lab_entries is not None,
                lab_teacher_id=lab_teacher.id if lab_teacher else None,
                weekly_lab_periods=weekly_lab_periods,
                joint_division_id=joint_division_id,
            )


def seed(session: Session) -> None:
    # Top-level entry point: reads the JSON once, then seeds all four Parts under one transaction.
    timetable = json.loads(TIMETABLE_JSON_PATH.read_text(encoding="utf-8"))
    bscs_parts = load_bscs_programs(timetable)

    program = session.scalar(
        select(Program)
        .join(Department, Department.id == Program.department_id)
        .where(Department.short_code == "CS", Program.level == "BS")
    )
    if program is None:
        raise RuntimeError("BS Computer Science program not found run app.db.seed first.")

    upsert_lab_rooms(session)
    removed = remove_placeholder_lab_rooms(session)
    if removed["rooms"]:
        print(f"removed placeholder lab rooms: {removed}")

    scheme = upsert_synthetic_scheme(session, program.id)
    session.flush()

    code_registry: set[str] = set(session.scalars(select(Course.code).where(Course.scheme_id == scheme.id)))

    for part_number, program_json in enumerate(bscs_parts, start=1):
        seed_part(session, program.id, scheme.id, part_number, program_json, code_registry)

    session.commit()


def main() -> None:
    # CLI entry point; prints what ended up in the database so the run is verifiable.
    with SessionLocal() as session:
        seed(session)

        counts = {
            "divisions": session.scalar(select(func.count()).select_from(Division)),
            "division_courses": session.scalar(select(func.count()).select_from(DivisionCourse)),
            "teachers": session.scalar(select(func.count()).select_from(Teacher)),
            "classrooms": session.scalar(select(func.count()).select_from(Classroom)),
            "courses (synthetic scheme only)": session.scalar(
                select(func.count()).select_from(Course).where(
                    Course.scheme_id.in_(select(CourseScheme.id).where(CourseScheme.scheme_year == 2026))
                )
            ),
        }
    for label, value in counts.items():
        print(f"{label}: {value}")
    with SessionLocal() as session:
        rooms = session.scalars(select(Classroom).order_by(Classroom.type, Classroom.name)).all()
    print("rooms:", ", ".join(f"{room.name} [{room.type.value}]" for room in rooms))


if __name__ == "__main__":
    main()
