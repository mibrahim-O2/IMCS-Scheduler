"""Hard constraints (heavy penalty), one function per rule all 9 from
docs/CONSTRAINTS.md. Constraints 1-6 are ports of the proven Phase 4-6 dev-script
logic onto real database ids; constraints 7-9 are implemented here for the
first time.

Production hardening beyond the dev scripts: every violation is recorded as a
`Violation` gene indexes plus a few already-known raw values and NO
human-readable message is built while detecting violations. Phase 6 measured
that building an f-string per violation was the main cost of evaluating a
chromosome; a fitness check only ever needs a *count*, so message text is
built lazily, only by `describe()`, only when something actually needs to show
a violation to a person (the API's conflict_list, or a test proving a
detector fires). See docs/PROJECT_ARCHITECTURE.md §6.2.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from app.scheduler.chromosome import TIME_SLOTS, Chromosome, DivisionInfo, SessionRequirement

# Every violation costs the same amount for now there are no soft constraints yet
# to weigh against, so a flat weight is enough (docs/PROJECT_ARCHITECTURE.md §6.2).
HARD_WEIGHT = 100

# A theory subject's weekly sessions may not have more than this many on one day
# (constraint 7). Labs are exempt a lab is one session, not part of the spread.
MAX_SAME_SUBJECT_PER_DAY = 2

# A teacher may not be scheduled for more sessions than this on any single day
# (constraint 8), counted across every division they teach.
MAX_TEACHER_SESSIONS_PER_DAY = 3


@dataclass(frozen=True)
class Violation:
    """One broken rule. Cheap to create no string formatting so this can be built
    for every violation on every fitness evaluation without it being the hot path."""

    constraint: str
    gene_indexes: tuple[int, ...]
    context: dict[str, Any] = field(default_factory=dict)


def teacher_double_booked(
    chromosome: Chromosome, requirements: list[SessionRequirement], divisions: dict[int, DivisionInfo]
) -> list[Violation]:
    # A teacher cannot be in two sessions at once. Checked globally across every division
    # in the chromosome (not per-division), which is what makes this the same check that
    # catches a cross-division clash (constraint 6) see docs/CONSTRAINTS.md.
    seen: dict[tuple[int, str, int], int] = {}
    violations = []
    for index, (gene, requirement) in enumerate(zip(chromosome, requirements, strict=True)):
        key = (requirement.teacher_id, gene.day, gene.slot_index)
        first = seen.get(key)
        if first is None:
            seen[key] = index
            continue
        violations.append(
            Violation(
                "teacher_double_booked",
                (first, index),
                {"teacher_id": requirement.teacher_id, "day": gene.day, "slot_index": gene.slot_index},
            )
        )
    return violations


def room_double_booked(
    chromosome: Chromosome, requirements: list[SessionRequirement], divisions: dict[int, DivisionInfo]
) -> list[Violation]:
    # Two sessions cannot share a room in the same period.
    seen: dict[tuple[int, str, int], int] = {}
    violations = []
    for index, gene in enumerate(chromosome):
        key = (gene.room_id, gene.day, gene.slot_index)
        first = seen.get(key)
        if first is None:
            seen[key] = index
            continue
        violations.append(
            Violation(
                "room_double_booked",
                (first, index),
                {"room_id": gene.room_id, "day": gene.day, "slot_index": gene.slot_index},
            )
        )
    return violations


def teacher_outside_availability(
    chromosome: Chromosome,
    requirements: list[SessionRequirement],
    divisions: dict[int, DivisionInfo],
    teacher_availability: dict[int, set[str]],
) -> list[Violation]:
    # A teacher can only be placed on a day they've declared themselves available.
    violations = []
    for index, (gene, requirement) in enumerate(zip(chromosome, requirements, strict=True)):
        available_days = teacher_availability.get(requirement.teacher_id, set())
        if gene.day not in available_days:
            violations.append(
                Violation(
                    "teacher_outside_availability",
                    (index,),
                    {"teacher_id": requirement.teacher_id, "day": gene.day},
                )
            )
    return violations


def division_double_booked(
    chromosome: Chromosome, requirements: list[SessionRequirement], divisions: dict[int, DivisionInfo]
) -> list[Violation]:
    # A division's students can only be in one session at a time. Checked per division, so
    # two different divisions in the same period are fine a joint session (division_ids
    # has two entries) is one session belonging to both, not two sessions colliding.
    seen: dict[tuple[int, str, int], int] = {}
    violations = []
    for index, (gene, requirement) in enumerate(zip(chromosome, requirements, strict=True)):
        for division_id in requirement.division_ids:
            key = (division_id, gene.day, gene.slot_index)
            first = seen.get(key)
            if first is None:
                seen[key] = index
                continue
            violations.append(
                Violation(
                    "division_double_booked",
                    (first, index),
                    {"division_id": division_id, "day": gene.day, "slot_index": gene.slot_index},
                )
            )
    return violations


def lab_session_rules(
    chromosome: Chromosome, requirements: list[SessionRequirement], divisions: dict[int, DivisionInfo]
) -> list[Violation]:
    # A lab never lands on top of that same course's own theory session for the same
    # division. Which room a lab uses isn't checked here: a lab session can only ever be
    # placed in the shared lab pool (Lab A-E, see chromosome.py), and two labs in the same
    # lab at the same time is room_double_booked's job.
    violations = []
    theory_slots: dict[tuple[int, int], set[tuple[str, int]]] = defaultdict(set)
    for gene, requirement in zip(chromosome, requirements, strict=True):
        if not requirement.is_lab:
            for division_id in requirement.division_ids:
                theory_slots[(requirement.course_id, division_id)].add((gene.day, gene.slot_index))

    for index, (gene, requirement) in enumerate(zip(chromosome, requirements, strict=True)):
        if not requirement.is_lab:
            continue
        for division_id in requirement.division_ids:
            if (gene.day, gene.slot_index) in theory_slots.get((requirement.course_id, division_id), ()):
                violations.append(
                    Violation(
                        "lab_session_rules",
                        (index,),
                        {
                            "course_id": requirement.course_id,
                            "division_id": division_id,
                            "day": gene.day,
                            "slot_index": gene.slot_index,
                        },
                    )
                )
    return violations


def same_subject_daily_spread(
    chromosome: Chromosome, requirements: list[SessionRequirement], divisions: dict[int, DivisionInfo]
) -> list[Violation]:
    # Constraint 7: a theory subject's weekly sessions for one division can't pile up more
    # than MAX_SAME_SUBJECT_PER_DAY on a single day. Labs are exempt a lab is one session,
    # not part of this weekly spread. Every session past the cap on that day is flagged.
    by_division_course_day: dict[tuple[int, int, str], list[int]] = defaultdict(list)
    for index, (gene, requirement) in enumerate(zip(chromosome, requirements, strict=True)):
        if requirement.is_lab:
            continue
        for division_id in requirement.division_ids:
            by_division_course_day[(division_id, requirement.course_id, gene.day)].append(index)

    violations = []
    for (division_id, course_id, day), indexes in by_division_course_day.items():
        if len(indexes) > MAX_SAME_SUBJECT_PER_DAY:
            for index in indexes[MAX_SAME_SUBJECT_PER_DAY:]:
                violations.append(
                    Violation(
                        "same_subject_daily_spread",
                        (index,),
                        {"division_id": division_id, "course_id": course_id, "day": day, "count": len(indexes)},
                    )
                )
    return violations


def teacher_daily_load(
    chromosome: Chromosome, requirements: list[SessionRequirement], divisions: dict[int, DivisionInfo]
) -> list[Violation]:
    # Constraint 8: no teacher gets more than MAX_TEACHER_SESSIONS_PER_DAY sessions on one
    # day, counted across every division they teach (theory and lab both count).
    by_teacher_day: dict[tuple[int, str], list[int]] = defaultdict(list)
    for index, (gene, requirement) in enumerate(zip(chromosome, requirements, strict=True)):
        by_teacher_day[(requirement.teacher_id, gene.day)].append(index)

    violations = []
    for (teacher_id, day), indexes in by_teacher_day.items():
        if len(indexes) > MAX_TEACHER_SESSIONS_PER_DAY:
            for index in indexes[MAX_TEACHER_SESSIONS_PER_DAY:]:
                violations.append(
                    Violation(
                        "teacher_daily_load",
                        (index,),
                        {"teacher_id": teacher_id, "day": day, "count": len(indexes)},
                    )
                )
    return violations


def one_subject_per_teacher_per_division(
    chromosome: Chromosome, requirements: list[SessionRequirement], divisions: dict[int, DivisionInfo]
) -> list[Violation]:
    # Constraint 9: within this one generation run, a teacher takes exactly one subject
    # in any division they appear in. Unlike constraints 1-8, this is a fact about the
    # REQUIREMENTS (who's assigned to teach what), which the GA never changes mutation
    # only re-rolls room/day/slot, never course_id or teacher_id so in normal operation
    # this can never actually be violated by a generated chromosome. It's still checked
    # here, on the chromosome's own requirements, so it can be verified and deliberately
    # broken the same way every other constraint is (see the Phase 7 report).
    by_teacher_division: dict[tuple[int, int], set[int]] = defaultdict(set)
    index_by_teacher_division_course: dict[tuple[int, int, int], list[int]] = defaultdict(list)
    for index, requirement in enumerate(requirements):
        for division_id in requirement.division_ids:
            by_teacher_division[(requirement.teacher_id, division_id)].add(requirement.course_id)
            index_by_teacher_division_course[(requirement.teacher_id, division_id, requirement.course_id)].append(index)

    violations = []
    for (teacher_id, division_id), course_ids in by_teacher_division.items():
        if len(course_ids) > 1:
            for course_id in course_ids:
                for index in index_by_teacher_division_course[(teacher_id, division_id, course_id)]:
                    violations.append(
                        Violation(
                            "one_subject_per_teacher_per_division",
                            (index,),
                            {"teacher_id": teacher_id, "division_id": division_id, "course_ids": tuple(sorted(course_ids))},
                        )
                    )
    return violations


# All nine share a (chromosome, requirements, divisions, ...) signature. The two that need
# extra context (availability) are wrapped below so every entry in this dict is callable alike.
def _all_checks(
    chromosome: Chromosome,
    requirements: list[SessionRequirement],
    divisions: dict[int, DivisionInfo],
    teacher_availability: dict[int, set[str]],
) -> dict[str, list[Violation]]:
    # Runs every one of the 9 constraints and hands back its findings under its own name.
    return {
        "teacher_double_booked": teacher_double_booked(chromosome, requirements, divisions),
        "room_double_booked": room_double_booked(chromosome, requirements, divisions),
        "teacher_outside_availability": teacher_outside_availability(
            chromosome, requirements, divisions, teacher_availability
        ),
        "division_double_booked": division_double_booked(chromosome, requirements, divisions),
        "lab_session_rules": lab_session_rules(chromosome, requirements, divisions),
        "same_subject_daily_spread": same_subject_daily_spread(chromosome, requirements, divisions),
        "teacher_daily_load": teacher_daily_load(chromosome, requirements, divisions),
        "one_subject_per_teacher_per_division": one_subject_per_teacher_per_division(chromosome, requirements, divisions),
    }


def all_violations(
    chromosome: Chromosome,
    requirements: list[SessionRequirement],
    divisions: dict[int, DivisionInfo],
    teacher_availability: dict[int, set[str]],
) -> dict[str, list[Violation]]:
    # Every hard constraint, run once, kept separate so a failure can be read and blamed.
    # This result is reused for fitness, elitism and mutation in one generation never
    # recomputed twice per individual the way the dev scripts did (see module docstring).
    return _all_checks(chromosome, requirements, divisions, teacher_availability)


def count_violations(all_violations_result: dict[str, list[Violation]]) -> int:
    # Total violations across every constraint the only thing fitness actually needs.
    return sum(len(found) for found in all_violations_result.values())


def blamed_gene_indexes(all_violations_result: dict[str, list[Violation]]) -> set[int]:
    # Every gene index implicated in at least one violation, for targeted mutation.
    return {index for found in all_violations_result.values() for violation in found for index in violation.gene_indexes}


def describe(violation: Violation) -> str:
    # Builds a human-readable message for ONE violation called only when a violation
    # actually needs to be shown to someone (API response, CLI report, test evidence),
    # never during the fitness/mutation hot path.
    c = violation.context
    if violation.constraint == "teacher_double_booked":
        return f"Teacher {c['teacher_id']} is double-booked on {c['day']} {TIME_SLOTS[c['slot_index']][0]}."
    if violation.constraint == "room_double_booked":
        return f"Room {c['room_id']} is double-booked on {c['day']} {TIME_SLOTS[c['slot_index']][0]}."
    if violation.constraint == "teacher_outside_availability":
        return f"Teacher {c['teacher_id']} is scheduled on {c['day']}, outside their declared availability."
    if violation.constraint == "division_double_booked":
        return f"Division {c['division_id']} has two sessions on {c['day']} {TIME_SLOTS[c['slot_index']][0]}."
    if violation.constraint == "lab_session_rules":
        return (
            f"Course {c['course_id']}'s lab clashes with its own theory session for division "
            f"{c['division_id']} on {c['day']} {TIME_SLOTS[c['slot_index']][0]}."
        )
    if violation.constraint == "same_subject_daily_spread":
        return (
            f"Course {c['course_id']} has {c['count']} sessions on {c['day']} for division "
            f"{c['division_id']} (max {MAX_SAME_SUBJECT_PER_DAY})."
        )
    if violation.constraint == "teacher_daily_load":
        return f"Teacher {c['teacher_id']} has {c['count']} sessions on {c['day']} (max {MAX_TEACHER_SESSIONS_PER_DAY})."
    if violation.constraint == "one_subject_per_teacher_per_division":
        return (
            f"Teacher {c['teacher_id']} is assigned more than one subject "
            f"({c['course_ids']}) in division {c['division_id']}."
        )
    return f"{violation.constraint}: {c}"
