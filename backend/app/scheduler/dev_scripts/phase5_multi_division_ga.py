"""Phase 5 dev script: the GA across several divisions at once, on real PDF data.

Standalone, like Phase 4 no database, no API, no frontend. Everything below was
read off the official "Class Time Table for 2nd Semester 2026, MORNING" PDF,
pages 1 (BS(CS) Part-I) and 2 (BS(CS) Part-II): the subjects, who teaches them by
full name from each sheet's own legend, the days each person actually appears, and
the room each group sits in.

Two things the real document forced:

* Each Part is split into Pre-Medical and Pre-Engineering groups sitting in
  different rooms and taking different subjects at the same time, so the unit that
  can only be in one place at once is the group, not the Part. Hence four
  divisions, not two.
* Initials are not identifiers. On the Part-I sheet A.B is Dr. Asad Buledi and
  A.A is Dr. Altaf Abro; on the Part-II sheet A.B is Mr. Adil Bhatti and A.A is
  Mr. Asad Ali Khore. Every teacher here is keyed by full name.

The GA machinery is the same as Phase 4 (tournament selection, elitism, two-point
crossover, mutation that only re-rolls room/day/slot). It is copied rather than
imported so each dev script runs on its own. The one real change is that
constraints now report which genes they blame, which lets mutation target the
genes actually causing violations see --mutation-mode.

Run it with:
    python -m app.scheduler.dev_scripts.phase5_multi_division_ga --runs 10

Note (post-Phase 6 cleanup): the hand-typed-from-PDF approach used below is
superseded going forward by docs/timetable.json, a clean structured export
covering all BSCS/BSAI Morning divisions with full teacher names and no
initials ambiguity. This file's own data and logic are left as-is this is
just a pointer for whoever writes the next dev script.
"""

from __future__ import annotations

import argparse
import random
from collections import defaultdict
from dataclasses import dataclass
from typing import NamedTuple

DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri")
TIME_SLOTS = (
    "08:30-09:20",
    "09:20-10:10",
    "10:10-11:00",
    "11:00-11:50",
    "11:50-12:40",
    "12:40-13:30",
)

# The PDF does not name a room for lab sessions, so this is an assumption: labs go to
# a shared computer lab pool. Two labs is what the real arrangement needs, because
# Part-I runs two labs at once on Thursday and Part-II does the same on Tuesday.
LAB_ROOMS = ("Computer Lab 01", "Computer Lab 02")

HARD_WEIGHT = 100


@dataclass(frozen=True)
class Division:
    key: str
    label: str
    home_room: str  # "Room No: 01 (PM) and Room No: 02 (PE)" etc., printed on each sheet


DIVISIONS: dict[str, Division] = {
    division.key: division
    for division in (
        Division("P1-PM", "BS(CS) Part-I · Pre-Medical", "Room 01"),
        Division("P1-PE", "BS(CS) Part-I · Pre-Engineering", "Room 02"),
        Division("P2-PM", "BS(CS) Part-II · Pre-Medical", "Room 05"),
        Division("P2-PE", "BS(CS) Part-II · Pre-Engineering", "Room 06"),
    )
}

PART_I_DIVISIONS = ("P1-PM", "P1-PE")
PART_II_DIVISIONS = ("P2-PM", "P2-PE")


@dataclass(frozen=True)
class Teacher:
    full_name: str
    # Days this person actually appears teaching in the PDF, pooled across both sheets.
    available_days: tuple[str, ...]
    # How each sheet abbreviates them, kept only so the data can be traced back to the PDF.
    pdf_initials: tuple[str, ...]


TEACHERS: dict[str, Teacher] = {
    teacher.full_name: teacher
    for teacher in (
        # --- Part-I sheet legend ---
        Teacher("Prof. Dr. Fida Chandio", ("Tue", "Thu"), ("F.C (Part-I)",)),
        Teacher("Dr. Gulsher Laghari", ("Tue", "Wed", "Thu", "Fri"), ("G.L (Part-I)", "G.L (Part-II)")),
        Teacher("Mr. M. Rafiq Mallah", ("Mon", "Tue"), ("M.R (Part-I)",)),
        Teacher("Dr. Hameedullah Bhutto", ("Mon", "Tue"), ("H.B (Part-I)",)),
        Teacher("Dr. Asad Buledi", ("Tue", "Thu"), ("A.B (Part-I)",)),
        Teacher("Ms. Madhia Khemtio", ("Mon", "Tue", "Wed"), ("M.K (Part-I)",)),
        Teacher("Dr. Nazish Nawaz", ("Wed", "Thu"), ("N.N (Part-I)",)),
        Teacher("Dr. Abdul Rehman Nangraj", ("Mon", "Tue", "Wed", "Thu"), ("A.R (Part-I)", "A.R (Part-II)")),
        Teacher("Ms. Asma Mughal", ("Mon",), ("A.M (Part-I)",)),
        Teacher("Dr. Altaf Abro", ("Mon", "Tue"), ("A.A (Part-I)",)),
        Teacher("Mr. Ahmed Raza Chandio", ("Wed", "Fri"), ("ARC (Part-I)",)),
        # --- Part-II sheet legend ---
        Teacher("Mr. Fiaz Memon", ("Mon", "Tue", "Wed", "Thu"), ("F.M (Part-II)",)),
        Teacher("Dr. Aftab Chandio", ("Tue", "Thu"), ("A.C (Part-II)",)),
        Teacher("Mr. Asad Ali Khore", ("Mon", "Tue", "Wed"), ("A.A (Part-II)",)),
        Teacher("Mr. Yasir Nawaz", ("Mon",), ("Y.N (Part-II)",)),
        Teacher("Prof. Dr. Imtiaz Korejo", ("Tue", "Wed"), ("I.K (Part-II)",)),
        Teacher("Dr. Shahmurad Chandio", ("Mon", "Thu"), ("SMC (Part-II)",)),
        Teacher("Mr. Adil Bhatti", ("Wed", "Thu"), ("A.B (Part-II)",)),
        Teacher("Ms. Noor Ul Ain Soomro", ("Mon", "Tue", "Wed"), ("N.S (Part-II)",)),
    )
}


class Gene(NamedTuple):
    """One placed session the gene shape from §6.1."""

    course_code: str
    teacher: str
    room: str
    day: str
    time_slot: str


@dataclass(frozen=True)
class SessionRequirement:
    """The fixed half of a gene: which subject, whose class, which group(s), theory or lab."""

    course_code: str
    course_name: str
    teacher: str
    divisions: tuple[str, ...]  # more than one when the groups sit the subject together
    is_lab: bool


Chromosome = list[Gene]

# Straight off the two sheets: subject, full name from the legend, which group(s), how many
# theory periods a week, how many lab periods. Period counts are what the PDF actually prints.
# History-II is the one subject both Part-I groups attend together ("H-II(PM/PE)").
PDF_SESSIONS: tuple[tuple[str, str, str, tuple[str, ...], int, int], ...] = (
    # BS(CS) Part-I Pre-Medical (Room 01)
    ("E.W", "Expository Writing", "Ms. Madhia Khemtio", ("P1-PM",), 3, 0),
    ("M-II", "Mathematics-II", "Mr. M. Rafiq Mallah", ("P1-PM",), 3, 0),
    ("I.S", "Islamic Studies", "Dr. Hameedullah Bhutto", ("P1-PM",), 2, 0),
    ("IOT", "Internet of Things (Basics)", "Dr. Asad Buledi", ("P1-PM",), 3, 0),
    ("DLD", "Digital Logic Design", "Dr. Abdul Rehman Nangraj", ("P1-PM",), 3, 1),
    ("OOP", "Object Oriented Programming", "Dr. Gulsher Laghari", ("P1-PM",), 3, 2),
    ("UHQ-II", "Understanding Holy Quran-II", "Mr. Ahmed Raza Chandio", ("P1-PM",), 2, 0),
    # Taught to both Part-I groups in one room, so it is a single session in two divisions.
    ("H-II", "History-II (for non-Muslims)", "Ms. Asma Mughal", ("P1-PM", "P1-PE"), 2, 0),
    # BS(CS) Part-I Pre-Engineering (Room 02)
    ("I.S", "Islamic Studies", "Dr. Hameedullah Bhutto", ("P1-PE",), 2, 0),
    ("IOT", "Internet of Things (Basics)", "Dr. Altaf Abro", ("P1-PE",), 3, 0),
    ("E.W", "Expository Writing", "Ms. Madhia Khemtio", ("P1-PE",), 3, 0),
    ("OOP", "Object Oriented Programming", "Prof. Dr. Fida Chandio", ("P1-PE",), 3, 2),
    ("DLD", "Digital Logic Design", "Dr. Nazish Nawaz", ("P1-PE",), 3, 1),
    ("UHQ-II", "Understanding Holy Quran-II", "Mr. Ahmed Raza Chandio", ("P1-PE",), 2, 0),
    # BS(CS) Part-II Pre-Medical (Room 05)
    ("C.A", "Computer Architecture", "Dr. Abdul Rehman Nangraj", ("P2-PM",), 3, 1),
    ("Q.R-II", "Quantitative Reasoning-II", "Mr. Asad Ali Khore", ("P2-PM",), 3, 0),
    ("EPS", "Entrepreneurship", "Dr. Shahmurad Chandio", ("P2-PM",), 2, 0),
    ("A.T", "Theory of Automata", "Mr. Fiaz Memon", ("P2-PM",), 3, 0),
    ("DBS", "Data Base System", "Dr. Gulsher Laghari", ("P2-PM",), 3, 1),
    ("P.P", "Professional Practices", "Mr. Adil Bhatti", ("P2-PM",), 2, 0),
    # BS(CS) Part-II Pre-Engineering (Room 06)
    ("P.P", "Professional Practices", "Mr. Yasir Nawaz", ("P2-PE",), 2, 0),
    ("Q.R-II", "Quantitative Reasoning-II", "Ms. Noor Ul Ain Soomro", ("P2-PE",), 3, 0),
    ("A.T", "Theory of Automata", "Mr. Fiaz Memon", ("P2-PE",), 3, 0),
    ("DBS", "Data Base System", "Dr. Aftab Chandio", ("P2-PE",), 3, 1),
    ("C.A", "Computer Architecture", "Prof. Dr. Imtiaz Korejo", ("P2-PE",), 3, 1),
    ("EPS", "Entrepreneurship", "Dr. Shahmurad Chandio", ("P2-PE",), 2, 0),
)


def build_session_requirements() -> list[SessionRequirement]:
    # Expands the PDF table into one requirement per weekly period, theory first then labs.
    requirements: list[SessionRequirement] = []
    for code, name, teacher, divisions, theory_periods, lab_periods in PDF_SESSIONS:
        for _ in range(theory_periods):
            requirements.append(SessionRequirement(code, name, teacher, divisions, is_lab=False))
        for _ in range(lab_periods):
            requirements.append(SessionRequirement(code, name, teacher, divisions, is_lab=True))
    return requirements


def rooms_for(requirement: SessionRequirement) -> tuple[str, ...]:
    # A lecture happens in the group's own room; a lab has to find space in the lab pool.
    if requirement.is_lab:
        return LAB_ROOMS
    return (DIVISIONS[requirement.divisions[0]].home_room,)


def shared_teachers(requirements: list[SessionRequirement]) -> dict[str, set[str]]:
    # Teachers who work across more than one Part the people this phase exists to stress.
    parts: dict[str, set[str]] = defaultdict(set)
    for requirement in requirements:
        part = "Part-I" if requirement.divisions[0] in PART_I_DIVISIONS else "Part-II"
        parts[requirement.teacher].add(part)
    return {name: found for name, found in parts.items() if len(found) > 1}


def random_gene(rng: random.Random, requirement: SessionRequirement) -> Gene:
    # A random placement for one required session; subject and teacher are fixed.
    return Gene(
        course_code=requirement.course_code,
        teacher=requirement.teacher,
        room=rng.choice(rooms_for(requirement)),
        day=rng.choice(DAYS),
        time_slot=rng.choice(TIME_SLOTS),
    )


def random_chromosome(rng: random.Random, requirements: list[SessionRequirement]) -> Chromosome:
    # One complete candidate timetable covering every division at once.
    return [random_gene(rng, requirement) for requirement in requirements]


# --- Hard constraints. Each reports the genes it blames, so mutation can target them. ---


@dataclass(frozen=True)
class Violation:
    message: str
    gene_indexes: tuple[int, ...]


def teacher_double_booked(chromosome: Chromosome, requirements: list[SessionRequirement]) -> list[Violation]:
    # Nobody can teach two sessions in one period. The key ignores division on purpose:
    # that is what makes a Part-I session and a Part-II session collide for a shared teacher.
    seen: dict[tuple[str, str, str], int] = {}
    violations = []
    for index, gene in enumerate(chromosome):
        key = (gene.teacher, gene.day, gene.time_slot)
        first = seen.get(key)
        if first is None:
            seen[key] = index
            continue
        where_first = "/".join(requirements[first].divisions)
        where_now = "/".join(requirements[index].divisions)
        violations.append(
            Violation(
                f"{gene.teacher} is double-booked on {gene.day} {gene.time_slot}: "
                f"{chromosome[first].course_code} ({where_first}) and {gene.course_code} ({where_now})",
                (first, index),
            )
        )
    return violations


def room_double_booked(chromosome: Chromosome, requirements: list[SessionRequirement]) -> list[Violation]:
    # Two sessions cannot share a room in the same period in practice this bites when two
    # divisions both want a computer lab at once.
    seen: dict[tuple[str, str, str], int] = {}
    violations = []
    for index, gene in enumerate(chromosome):
        key = (gene.room, gene.day, gene.time_slot)
        first = seen.get(key)
        if first is None:
            seen[key] = index
            continue
        violations.append(
            Violation(
                f"{gene.room} is double-booked on {gene.day} {gene.time_slot}: "
                f"{chromosome[first].course_code} and {gene.course_code}",
                (first, index),
            )
        )
    return violations


def teacher_outside_availability(chromosome: Chromosome, requirements: list[SessionRequirement]) -> list[Violation]:
    # Availability comes from the days each person actually appears in the PDF; the algorithm
    # works around it rather than overriding it.
    violations = []
    for index, gene in enumerate(chromosome):
        teacher = TEACHERS[gene.teacher]
        if gene.day not in teacher.available_days:
            violations.append(
                Violation(
                    f"{gene.teacher} is scheduled on {gene.day} {gene.time_slot} for {gene.course_code} "
                    f"but only teaches {', '.join(teacher.available_days)}",
                    (index,),
                )
            )
    return violations


def division_double_booked(chromosome: Chromosome, requirements: list[SessionRequirement]) -> list[Violation]:
    # A group of students can only sit in one session at a time. Checked per division, so a
    # Part-I session and a Part-II session in the same period are fine different students.
    seen: dict[tuple[str, str, str], int] = {}
    violations = []
    for index, (gene, requirement) in enumerate(zip(chromosome, requirements, strict=True)):
        for division in requirement.divisions:
            key = (division, gene.day, gene.time_slot)
            first = seen.get(key)
            if first is None:
                seen[key] = index
                continue
            violations.append(
                Violation(
                    f"{DIVISIONS[division].label} has two sessions on {gene.day} {gene.time_slot}: "
                    f"{chromosome[first].course_code} and {gene.course_code}",
                    (first, index),
                )
            )
    return violations


def lab_session_rules(chromosome: Chromosome, requirements: list[SessionRequirement]) -> list[Violation]:
    # A lab is its own session in a lab room, and never on top of its own subject's theory
    # period for the same group.
    violations = []
    theory_slots: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
    for gene, requirement in zip(chromosome, requirements, strict=True):
        if not requirement.is_lab:
            for division in requirement.divisions:
                theory_slots[(requirement.course_code, division)].add((gene.day, gene.time_slot))

    for index, (gene, requirement) in enumerate(zip(chromosome, requirements, strict=True)):
        if not requirement.is_lab:
            if gene.room in LAB_ROOMS:
                violations.append(
                    Violation(f"{gene.course_code} lecture is taking up {gene.room}, a lab room", (index,))
                )
            continue

        if gene.room not in LAB_ROOMS:
            violations.append(
                Violation(f"{gene.course_code} lab is in {gene.room}, which is not a lab room", (index,))
            )
        for division in requirement.divisions:
            if (gene.day, gene.time_slot) in theory_slots[(requirement.course_code, division)]:
                violations.append(
                    Violation(
                        f"{gene.course_code} lab clashes with its own theory period for "
                        f"{DIVISIONS[division].label} on {gene.day} {gene.time_slot}",
                        (index,),
                    )
                )
    return violations


# All five take the same (chromosome, requirements) signature so they can be called alike,
# even where one of them does not need the requirements.
CONSTRAINTS = {
    "teacher double-booked": teacher_double_booked,
    "room double-booked": room_double_booked,
    "teacher outside availability": teacher_outside_availability,
    "division double-booked": division_double_booked,
    "lab session rules": lab_session_rules,
}


def all_violations(chromosome: Chromosome, requirements: list[SessionRequirement]) -> dict[str, list[Violation]]:
    # Every hard constraint, kept separate so a failure can be read and blamed.
    return {name: check(chromosome, requirements) for name, check in CONSTRAINTS.items()}


def count_violations(chromosome: Chromosome, requirements: list[SessionRequirement]) -> int:
    # Total hard violations across all constraints.
    return sum(len(found) for found in all_violations(chromosome, requirements).values())


def fitness(chromosome: Chromosome, requirements: list[SessionRequirement]) -> float:
    # Negative weighted violation count (§6.2); a clean timetable scores 0. No soft constraints yet.
    violations = count_violations(chromosome, requirements)
    return -float(violations * HARD_WEIGHT) if violations else 0.0


def cross_division_teacher_clashes(
    chromosome: Chromosome, requirements: list[SessionRequirement]
) -> list[str]:
    # The point of this phase, checked directly: a teacher working in both Parts must never be
    # in two Parts at once. The general teacher check already penalises this; this is a separate
    # lens on the same rule for evidence, so it deliberately adds no extra penalty.
    overlapping = shared_teachers(requirements)
    placements: dict[tuple[str, str, str], list[tuple[str, str]]] = defaultdict(list)
    for gene, requirement in zip(chromosome, requirements, strict=True):
        if gene.teacher not in overlapping:
            continue
        part = "Part-I" if requirement.divisions[0] in PART_I_DIVISIONS else "Part-II"
        placements[(gene.teacher, gene.day, gene.time_slot)].append((part, gene.course_code))

    clashes = []
    for (teacher, day, slot), entries in sorted(placements.items()):
        parts = {part for part, _ in entries}
        if len(parts) > 1:
            detail = ", ".join(f"{code} ({part})" for part, code in entries)
            clashes.append(f"{teacher} is in both Parts on {day} {slot}: {detail}")
    return clashes


# --- GA machinery, same as Phase 4 (§6.3) ---


def tournament_select(
    rng: random.Random, scored: list[tuple[float, Chromosome]], tournament_size: int
) -> Chromosome:
    # Takes a few individuals at random and returns the fittest of them.
    contenders = rng.sample(scored, min(tournament_size, len(scored)))
    return max(contenders, key=lambda pair: pair[0])[1]


def two_point_crossover(rng: random.Random, parent_a: Chromosome, parent_b: Chromosome) -> Chromosome:
    # Swaps a middle stretch of placements. Gene positions line up with requirements, so the
    # child is always a complete timetable.
    if len(parent_a) < 3:
        return list(parent_a)
    first, second = sorted(rng.sample(range(1, len(parent_a)), 2))
    return list(parent_a[:first]) + list(parent_b[first:second]) + list(parent_a[second:])


def mutate_uniform(
    rng: random.Random,
    chromosome: Chromosome,
    requirements: list[SessionRequirement],
    mutation_rate: float,
) -> Chromosome:
    # Phase 4's mutation: every gene has the same small chance of being re-placed.
    mutated = list(chromosome)
    for index, requirement in enumerate(requirements):
        if rng.random() < mutation_rate:
            mutated[index] = random_gene(rng, requirement)
    return mutated


def mutate_targeted(
    rng: random.Random,
    chromosome: Chromosome,
    requirements: list[SessionRequirement],
    mutation_rate: float,
) -> Chromosome:
    # Re-places the genes that are actually causing violations, and only rarely touches the rest.
    # With 79 sessions, blind mutation spends nearly all its effort on sessions that were already fine.
    mutated = list(chromosome)
    blamed = {
        index
        for found in all_violations(chromosome, requirements).values()
        for violation in found
        for index in violation.gene_indexes
    }
    for index, requirement in enumerate(requirements):
        chance = 0.6 if index in blamed else mutation_rate
        if rng.random() < chance:
            mutated[index] = random_gene(rng, requirement)
    return mutated


MUTATION_MODES = {"uniform": mutate_uniform, "targeted": mutate_targeted}


@dataclass
class RunResult:
    best: Chromosome
    generations: int
    fitness: float
    violations: int
    converged: bool


def evolve(
    requirements: list[SessionRequirement],
    rng: random.Random,
    *,
    population_size: int,
    max_generations: int,
    tournament_size: int,
    crossover_rate: float,
    mutation_rate: float,
    elite_count: int,
    mutation_mode: str,
) -> RunResult:
    # Score everyone, carry the best through untouched, breed the rest until the timetable is
    # clean or the generation cap is reached.
    mutate = MUTATION_MODES[mutation_mode]
    population = [random_chromosome(rng, requirements) for _ in range(population_size)]

    for generation in range(1, max_generations + 1):
        scored = sorted(
            ((fitness(chromosome, requirements), chromosome) for chromosome in population),
            key=lambda pair: pair[0],
            reverse=True,
        )
        best_fitness, best = scored[0]
        if best_fitness == 0.0:
            return RunResult(best, generation, best_fitness, 0, converged=True)

        next_population = [chromosome for _, chromosome in scored[:elite_count]]
        while len(next_population) < population_size:
            parent_a = tournament_select(rng, scored, tournament_size)
            parent_b = tournament_select(rng, scored, tournament_size)
            child = (
                two_point_crossover(rng, parent_a, parent_b)
                if rng.random() < crossover_rate
                else list(parent_a)
            )
            next_population.append(mutate(rng, child, requirements, mutation_rate))
        population = next_population

    final = max(((fitness(c, requirements), c) for c in population), key=lambda pair: pair[0])
    return RunResult(final[1], max_generations, final[0], count_violations(final[1], requirements), False)


# --- Output and verification ---


def format_division_timetable(
    chromosome: Chromosome, requirements: list[SessionRequirement], division_key: str
) -> str:
    # One division's grid, the way the department reads a timetable.
    division = DIVISIONS[division_key]
    placed = {
        (gene.day, gene.time_slot): (gene, requirement)
        for gene, requirement in zip(chromosome, requirements, strict=True)
        if division_key in requirement.divisions
    }

    width = 24
    lines = [f"{division.label}  (home room {division.home_room})"]
    lines.append("".ljust(13) + "".join(day.ljust(width) for day in DAYS))
    lines.append("-" * (13 + width * len(DAYS)))

    for slot in TIME_SLOTS:
        rows: list[list[str]] = [[], [], []]
        for day in DAYS:
            entry = placed.get((day, slot))
            if entry is None:
                rows[0].append(" ".ljust(width))
                rows[1].append("".ljust(width))
                rows[2].append("".ljust(width))
                continue
            gene, requirement = entry
            label = f"{gene.course_code}{' (LAB)' if requirement.is_lab else ''}"
            if len(requirement.divisions) > 1:
                label += " *"
            rows[0].append(label.ljust(width))
            rows[1].append(gene.teacher[: width - 1].ljust(width))
            rows[2].append(gene.room.ljust(width))
        lines.append(slot.ljust(13) + "".join(rows[0]))
        lines.append("".ljust(13) + "".join(rows[1]))
        lines.append("".ljust(13) + "".join(rows[2]))
        lines.append("")
    return "\n".join(lines)


def print_shared_teacher_evidence(chromosome: Chromosome, requirements: list[SessionRequirement]) -> None:
    # Lists every teacher working in both Parts with their Part-I and Part-II periods side by
    # side, so the absence of an overlap can be read rather than taken on trust.
    overlapping = shared_teachers(requirements)
    if not overlapping:
        print("  no teacher works across both Parts in this data")
        return

    for name in sorted(overlapping):
        by_part: dict[str, list[str]] = defaultdict(list)
        for gene, requirement in zip(chromosome, requirements, strict=True):
            if gene.teacher != name:
                continue
            part = "Part-I" if requirement.divisions[0] in PART_I_DIVISIONS else "Part-II"
            label = f"{gene.course_code}{' LAB' if requirement.is_lab else ''}"
            by_part[part].append(f"{gene.day} {gene.time_slot} {label}")

        part_one = sorted(by_part["Part-I"])
        part_two = sorted(by_part["Part-II"])
        print(f"\n  {name}  (available {', '.join(TEACHERS[name].available_days)})")
        print(f"    {'Part-I':<40}{'Part-II'}")
        for index in range(max(len(part_one), len(part_two))):
            left = part_one[index] if index < len(part_one) else ""
            right = part_two[index] if index < len(part_two) else ""
            print(f"    {left:<40}{right}")

        overlaps = {entry[:15] for entry in part_one} & {entry[:15] for entry in part_two}
        print(f"    -> periods used in both Parts: {sorted(overlaps) if overlaps else 'none'}")


def print_break_checks(chromosome: Chromosome, requirements: list[SessionRequirement]) -> None:
    # Breaks the clean timetable one rule at a time and shows each detector firing.
    def counts(candidate: Chromosome) -> dict[str, int]:
        # Violations per constraint, for the before/after lines.
        return {name: len(found) for name, found in all_violations(candidate, requirements).items()}

    print(f"clean solution: {counts(chromosome)}")
    print(f"clean cross-division check: {cross_division_teacher_clashes(chromosome, requirements) or 'no clashes'}")

    overlapping = sorted(shared_teachers(requirements))
    shared_name = overlapping[0]
    part_one_index = next(
        index
        for index, requirement in enumerate(requirements)
        if requirement.teacher == shared_name and requirement.divisions[0] in PART_I_DIVISIONS
    )
    part_two_index = next(
        index
        for index, requirement in enumerate(requirements)
        if requirement.teacher == shared_name and requirement.divisions[0] in PART_II_DIVISIONS
    )
    lab_index = next(index for index, requirement in enumerate(requirements) if requirement.is_lab)
    theory_index = next(index for index, requirement in enumerate(requirements) if not requirement.is_lab)
    same_division_other = next(
        index
        for index, requirement in enumerate(requirements)
        if index != theory_index
        and not requirement.is_lab
        and requirement.divisions == requirements[theory_index].divisions
        and requirement.course_code != requirements[theory_index].course_code
    )

    cases: list[tuple[str, Chromosome, str]] = []

    # The whole point of this phase: drag a shared teacher's Part-II session onto the period
    # where they are already teaching Part-I.
    broken = list(chromosome)
    anchor = broken[part_one_index]
    broken[part_two_index] = broken[part_two_index]._replace(day=anchor.day, time_slot=anchor.time_slot)
    cases.append((
        "teacher double-booked",
        broken,
        f"{shared_name}'s Part-II session moved onto their Part-I period ({anchor.day} {anchor.time_slot})",
    ))

    # Room clash: two labs forced into one lab room at once.
    broken = list(chromosome)
    other_lab = next(
        index for index, requirement in enumerate(requirements) if requirement.is_lab and index != lab_index
    )
    broken[other_lab] = broken[other_lab]._replace(
        day=broken[lab_index].day, time_slot=broken[lab_index].time_slot, room=broken[lab_index].room
    )
    cases.append(("room double-booked", broken, "two labs put in one lab room at the same time"))

    # Availability: move a session onto a day its teacher never appears.
    broken = list(chromosome)
    teacher = TEACHERS[broken[theory_index].teacher]
    unavailable_day = next(day for day in DAYS if day not in teacher.available_days)
    broken[theory_index] = broken[theory_index]._replace(day=unavailable_day)
    cases.append(("teacher outside availability", broken, f"moved onto {unavailable_day}"))

    # Division clash: two subjects for the same group in one period.
    broken = list(chromosome)
    broken[same_division_other] = broken[same_division_other]._replace(
        day=broken[theory_index].day, time_slot=broken[theory_index].time_slot
    )
    cases.append(("division double-booked", broken, "two subjects for one group at once"))

    # Lab in a lecture room.
    broken = list(chromosome)
    broken[lab_index] = broken[lab_index]._replace(room=DIVISIONS[requirements[lab_index].divisions[0]].home_room)
    cases.append(("lab session rules", broken, "lab moved out of the lab pool"))

    for constraint, candidate, description in cases:
        found = all_violations(candidate, requirements)[constraint]
        print(f"\n  break: {description}")
        print(f"    {constraint}: {'DETECTED' if found else 'MISSED'} ({len(found)})")
        if found:
            print(f"    -> {found[0].message}")
        if constraint == "teacher double-booked":
            cross = cross_division_teacher_clashes(candidate, requirements)
            print(f"    cross-division check: {'DETECTED' if cross else 'MISSED'} ({len(cross)})")
            if cross:
                print(f"    -> {cross[0]}")


def print_dataset(requirements: list[SessionRequirement]) -> None:
    # The data this run is built from, so it can be checked against the PDF.
    print("Divisions (rooms as printed on each sheet):")
    for division in DIVISIONS.values():
        own = sum(1 for r in requirements if division.key in r.divisions)
        print(f"  {division.key:<7}{division.label:<40}{division.home_room:<10}{own} sessions/week")

    print("\nSubjects, teachers and weekly periods (from the PDF):")
    for code, name, teacher, divisions, theory, lab in PDF_SESSIONS:
        where = "+".join(divisions)
        lab_note = f" + {lab} lab" if lab else ""
        print(f"  {where:<14}{code:<8}{name[:34]:<36}{theory} periods{lab_note:<10} {teacher}")

    overlapping = shared_teachers(requirements)
    print("\nTeachers working across both Parts (the cross-division pressure):")
    for name in sorted(overlapping):
        teacher = TEACHERS[name]
        print(f"  {name:<32}{', '.join(teacher.pdf_initials):<28}"
              f"available {', '.join(teacher.available_days)}")

    print(f"\nSessions to place: {len(requirements)} "
          f"({sum(1 for r in requirements if not r.is_lab)} theory, {sum(1 for r in requirements if r.is_lab)} lab)")
    print(f"Grid per division: {len(DAYS)} days x {len(TIME_SLOTS)} periods; lab pool {LAB_ROOMS}")


def parse_args() -> argparse.Namespace:
    # Command-line knobs so runs can be compared without editing the file.
    parser = argparse.ArgumentParser(description="Phase 5 multi-division GA")
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--seed", type=int, default=100, help="base seed; run N uses seed + N")
    parser.add_argument("--population", type=int, default=120)
    parser.add_argument("--generations", type=int, default=1500)
    parser.add_argument("--tournament", type=int, default=4)
    parser.add_argument("--crossover-rate", type=float, default=0.9)
    parser.add_argument("--mutation-rate", type=float, default=0.03)
    parser.add_argument("--elites", type=int, default=4)
    parser.add_argument("--mutation-mode", choices=sorted(MUTATION_MODES), default="targeted")
    parser.add_argument("--quiet", action="store_true", help="only print the run table")
    return parser.parse_args()


def main() -> None:
    # Runs the GA several times, then shows one full solution with the evidence behind it.
    args = parse_args()
    requirements = build_session_requirements()

    print("=" * 128)
    print("PHASE 5 multi-division GA: BS(CS) Part-I and Part-II, Morning shift")
    print("=" * 128)
    print_dataset(requirements)

    print("\n" + "=" * 128)
    print(f"RUNS (population {args.population}, tournament {args.tournament}, crossover {args.crossover_rate}, "
          f"mutation {args.mutation_rate}/{args.mutation_mode}, elites {args.elites}, cap {args.generations})")
    print("=" * 128)
    print(f"{'run':<6}{'seed':<8}{'generations':<14}{'fitness':<12}{'hard violations':<18}{'result'}")

    results: list[RunResult] = []
    for run_number in range(1, args.runs + 1):
        seed = args.seed + run_number
        result = evolve(
            requirements,
            random.Random(seed),
            population_size=args.population,
            max_generations=args.generations,
            tournament_size=args.tournament,
            crossover_rate=args.crossover_rate,
            mutation_rate=args.mutation_rate,
            elite_count=args.elites,
            mutation_mode=args.mutation_mode,
        )
        results.append(result)
        outcome = "converged" if result.converged else "HIT GENERATION CAP"
        print(f"{run_number:<6}{seed:<8}{result.generations:<14}{result.fitness:<12.1f}"
              f"{result.violations:<18}{outcome}")

    converged = [result for result in results if result.converged]
    if converged:
        generations = [result.generations for result in converged]
        print(f"\nconverged {len(converged)}/{len(results)} runs; generations min {min(generations)}, "
              f"max {max(generations)}, mean {sum(generations) / len(generations):.1f}")
    else:
        print(f"\nNo run converged within {args.generations} generations.")

    if args.quiet:
        return

    representative = converged[0] if converged else results[0]
    outcome = (
        f"converged in {representative.generations} generations"
        if representative.converged
        else f"best effort after {representative.generations} generations"
    )

    print("\n" + "=" * 128)
    print(f"TIMETABLE from the first converged run ({outcome}).  * = both Part-I groups together")
    print("=" * 128)
    for division_key in DIVISIONS:
        print(format_division_timetable(representative.best, requirements, division_key))

    print("=" * 128)
    print("HARD CONSTRAINT CHECK")
    print("=" * 128)
    for name, found in all_violations(representative.best, requirements).items():
        print(f"  {name:<32}{len(found)} violation(s)")
        for violation in found:
            print(f"      {violation.message}")

    print("\n" + "=" * 128)
    print("EVIDENCE: teachers who work in both Parts are never in both at once")
    print("=" * 128)
    print_shared_teacher_evidence(representative.best, requirements)

    print("\n" + "=" * 128)
    print("EVIDENCE: each detector fires when the rule is deliberately broken")
    print("=" * 128)
    print_break_checks(representative.best, requirements)


if __name__ == "__main__":
    main()
