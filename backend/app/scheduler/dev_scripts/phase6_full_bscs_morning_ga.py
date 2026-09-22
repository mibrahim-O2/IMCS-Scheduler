"""Phase 6 dev script: the whole BS(CS) Morning shift, Part-I through Part-IV.

Standalone like Phases 4 and 5 no database, no API, no frontend. Everything comes
off the official "Class Time Table for 2nd Semester 2026, MORNING" PDF: page 1
Part-I, page 2 Part-II, page 3 Part-III, page 4 Part-IV. Subjects, teachers by full
name from each sheet's own legend, the days each person actually appears, and the
room each group sits in.

What the added sheets changed:

* All four Parts split Pre-Medical / Pre-Engineering, so there are eight divisions.
* Part-III and Part-IV are both printed with "ROOM NO:= 03 For PM and ROOM NO:= 04
  For PE" they share rooms. Until now each division had a room to itself and only
  labs could collide; now two divisions compete for the same lecture room.
* The initials clash worse the more sheets you read. A.B is Dr. Asad Buledi on
  Part-I, Mr. Adil Bhatti on Part-II and Ms. Afia Bhutto on Part-III. H.B is
  Dr. Hameedullah Bhutto on Part-I but Mr. Hammad Bhutto on Part-III two
  different people with nearly the same name. A.A is a teacher on Parts I and II
  and a subject (Analysis of Algorithms) on Part-III.

GA machinery is Phase 5's unchanged: tournament selection, elitism, two-point
crossover, blame-carrying violations and targeted mutation.

Run it with:
    python -m app.scheduler.dev_scripts.phase6_full_bscs_morning_ga --runs 10

Note (post-cleanup): the hand-typed-from-PDF approach used below is
superseded going forward by docs/timetable.json, a clean structured export
covering all BSCS/BSAI Morning divisions with full teacher names and no
initials ambiguity (it already includes BSAI, so the natural next dev
script full department scale can read it directly instead of
transcribing more PDF sheets by hand). This file's own data and logic are
left as-is this is just a pointer for whoever writes that next script.
"""

from __future__ import annotations

import argparse
import random
import time
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

# Still an assumption: the PDF never names a room for lab sessions. Two labs is what the
# real arrangement needs Part-III runs two labs at once on Monday and Tuesday.
LAB_ROOMS = ("Computer Lab 01", "Computer Lab 02")

HARD_WEIGHT = 100

PART_LABELS = {"P1": "Part-I", "P2": "Part-II", "P3": "Part-III", "P4": "Part-IV"}


@dataclass(frozen=True)
class Division:
    key: str
    label: str
    home_room: str  # exactly the room printed on that Part's sheet


DIVISIONS: dict[str, Division] = {
    division.key: division
    for division in (
        Division("P1-PM", "BS(CS) Part-I · Pre-Medical", "Room 01"),
        Division("P1-PE", "BS(CS) Part-I · Pre-Engineering", "Room 02"),
        Division("P2-PM", "BS(CS) Part-II · Pre-Medical", "Room 05"),
        Division("P2-PE", "BS(CS) Part-II · Pre-Engineering", "Room 06"),
        # Part-III and Part-IV are both printed with rooms 03 (PM) and 04 (PE).
        Division("P3-PM", "BS(CS) Part-III · Pre-Medical", "Room 03"),
        Division("P3-PE", "BS(CS) Part-III · Pre-Engineering", "Room 04"),
        Division("P4-PM", "BS(CS) Part-IV · Pre-Medical", "Room 03"),
        Division("P4-PE", "BS(CS) Part-IV · Pre-Engineering", "Room 04"),
    )
}


def part_of(division_key: str) -> str:
    # "P3-PE" -> "Part-III". Used wherever something is counted per Part rather than per group.
    return PART_LABELS[division_key.split("-")[0]]


@dataclass(frozen=True)
class Teacher:
    full_name: str
    # The days this person actually appears teaching, pooled across every sheet they are on.
    available_days: tuple[str, ...]
    # How each sheet abbreviates them, kept so any row can be traced back to the PDF.
    pdf_initials: tuple[str, ...]


TEACHERS: dict[str, Teacher] = {
    teacher.full_name: teacher
    for teacher in (
        # --- Part-I sheet legend ---
        Teacher("Prof. Dr. Fida Chandio", ("Tue", "Thu"), ("F.C (Part-I)",)),
        Teacher("Dr. Gulsher Laghari", ("Tue", "Wed", "Thu", "Fri"), ("G.L (Part-I)", "G.L (Part-II)")),
        Teacher("Mr. M. Rafiq Mallah", ("Mon", "Tue", "Wed"), ("M.R (Part-I)", "M.R (Part-III)")),
        Teacher("Dr. Hameedullah Bhutto", ("Mon", "Tue"), ("H.B (Part-I)",)),
        Teacher("Dr. Asad Buledi", ("Tue", "Thu"), ("A.B (Part-I)",)),
        Teacher("Ms. Madhia Khemtio", ("Mon", "Tue", "Wed"), ("M.K (Part-I)",)),
        Teacher("Dr. Nazish Nawaz", ("Mon", "Tue", "Wed", "Thu"), ("N.N (Part-I)", "N.N (Part-III)")),
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
        # --- Part-III sheet legend ---
        Teacher("Dr. Hira Fatima", ("Mon", "Tue", "Wed"), ("H.F (Part-III)",)),
        Teacher("Dr. Shazia Samoon", ("Tue", "Wed"), ("S.S (Part-III)",)),
        Teacher("Mr. Rajesh Kumar", ("Mon", "Tue", "Thu", "Fri"), ("R.K (Part-III)", "R.K (Part-IV)")),
        Teacher("Ms. Afia Bhutto", ("Mon", "Tue"), ("A.B (Part-III)",)),
        Teacher("Ms. Asia Soomro", ("Mon", "Wed"), ("A.S (Part-III)",)),
        Teacher("Mr. Hammad Bhutto", ("Tue", "Wed"), ("H.B (Part-III)",)),
        Teacher("Mr. Gulzar Brohi", ("Mon", "Wed"), ("G.B (Part-III)",)),
        # --- Part-IV sheet legend ---
        Teacher("Prof. Dr. Ayaz Keerio", ("Thu", "Fri"), ("A.K (Part-IV)",)),
        Teacher("Mr. Zohaib Maqsood", ("Thu", "Fri"), ("Z.M (Part-IV)",)),
        Teacher("Mr. Kamran Brohi", ("Thu", "Fri"), ("K.B (Part-IV)",)),
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

# Straight off the four sheets: subject, full name from the legend, group(s), theory periods
# a week, lab periods. Period counts are what the PDF actually prints.
PDF_SESSIONS: tuple[tuple[str, str, str, tuple[str, ...], int, int], ...] = (
    # --- BS(CS) Part-I, Pre-Medical (Room 01) ---
    ("E.W", "Expository Writing", "Ms. Madhia Khemtio", ("P1-PM",), 3, 0),
    ("M-II", "Mathematics-II", "Mr. M. Rafiq Mallah", ("P1-PM",), 3, 0),
    ("I.S", "Islamic Studies", "Dr. Hameedullah Bhutto", ("P1-PM",), 2, 0),
    ("IOT", "Internet of Things (Basics)", "Dr. Asad Buledi", ("P1-PM",), 3, 0),
    ("DLD", "Digital Logic Design", "Dr. Abdul Rehman Nangraj", ("P1-PM",), 3, 1),
    ("OOP", "Object Oriented Programming", "Dr. Gulsher Laghari", ("P1-PM",), 3, 2),
    ("UHQ-II", "Understanding Holy Quran-II", "Mr. Ahmed Raza Chandio", ("P1-PM",), 2, 0),
    # Printed "H-II(PM/PE)": both Part-I groups sit it together, so one session, two divisions.
    ("H-II", "History-II (for non-Muslims)", "Ms. Asma Mughal", ("P1-PM", "P1-PE"), 2, 0),
    # --- BS(CS) Part-I, Pre-Engineering (Room 02) ---
    ("I.S", "Islamic Studies", "Dr. Hameedullah Bhutto", ("P1-PE",), 2, 0),
    ("IOT", "Internet of Things (Basics)", "Dr. Altaf Abro", ("P1-PE",), 3, 0),
    ("E.W", "Expository Writing", "Ms. Madhia Khemtio", ("P1-PE",), 3, 0),
    ("OOP", "Object Oriented Programming", "Prof. Dr. Fida Chandio", ("P1-PE",), 3, 2),
    ("DLD", "Digital Logic Design", "Dr. Nazish Nawaz", ("P1-PE",), 3, 1),
    ("UHQ-II", "Understanding Holy Quran-II", "Mr. Ahmed Raza Chandio", ("P1-PE",), 2, 0),
    # --- BS(CS) Part-II, Pre-Medical (Room 05) ---
    ("C.A", "Computer Architecture", "Dr. Abdul Rehman Nangraj", ("P2-PM",), 3, 1),
    ("Q.R-II", "Quantitative Reasoning-II", "Mr. Asad Ali Khore", ("P2-PM",), 3, 0),
    ("EPS", "Entrepreneurship", "Dr. Shahmurad Chandio", ("P2-PM",), 2, 0),
    ("A.T", "Theory of Automata", "Mr. Fiaz Memon", ("P2-PM",), 3, 0),
    ("DBS", "Data Base System", "Dr. Gulsher Laghari", ("P2-PM",), 3, 1),
    ("P.P", "Professional Practices", "Mr. Adil Bhatti", ("P2-PM",), 2, 0),
    # --- BS(CS) Part-II, Pre-Engineering (Room 06) ---
    ("P.P", "Professional Practices", "Mr. Yasir Nawaz", ("P2-PE",), 2, 0),
    ("Q.R-II", "Quantitative Reasoning-II", "Ms. Noor Ul Ain Soomro", ("P2-PE",), 3, 0),
    ("A.T", "Theory of Automata", "Mr. Fiaz Memon", ("P2-PE",), 3, 0),
    ("DBS", "Data Base System", "Dr. Aftab Chandio", ("P2-PE",), 3, 1),
    ("C.A", "Computer Architecture", "Prof. Dr. Imtiaz Korejo", ("P2-PE",), 3, 1),
    ("EPS", "Entrepreneurship", "Dr. Shahmurad Chandio", ("P2-PE",), 2, 0),
    # --- BS(CS) Part-III, Pre-Medical (Room 03) ---
    ("A.A", "Analysis of Algorithms", "Dr. Hira Fatima", ("P3-PM",), 3, 0),
    ("HCICG", "HCI & Computer Graphics", "Dr. Nazish Nawaz", ("P3-PM",), 3, 1),
    ("C.N", "Computer Network", "Mr. Gulzar Brohi", ("P3-PM",), 3, 1),
    ("PDC", "Parallel & Distributed Computing", "Dr. Shazia Samoon", ("P3-PM",), 3, 1),
    ("M.C", "Multivariable Calculus", "Mr. Hammad Bhutto", ("P3-PM",), 3, 0),
    # --- BS(CS) Part-III, Pre-Engineering (Room 04) ---
    ("A.A", "Analysis of Algorithms", "Dr. Hira Fatima", ("P3-PE",), 3, 0),
    ("HCICG", "HCI & Computer Graphics", "Mr. Rajesh Kumar", ("P3-PE",), 3, 1),
    ("C.N", "Computer Network", "Ms. Afia Bhutto", ("P3-PE",), 3, 1),
    ("PDC", "Parallel & Distributed Computing", "Ms. Asia Soomro", ("P3-PE",), 3, 1),
    ("M.C", "Multivariable Calculus", "Mr. M. Rafiq Mallah", ("P3-PE",), 3, 0),
    # --- BS(CS) Part-IV, Pre-Medical (Room 03) ---
    ("E.C", "E-Commerce", "Mr. Rajesh Kumar", ("P4-PM",), 3, 0),
    ("MAD", "Mobile Application Development", "Mr. Kamran Brohi", ("P4-PM",), 3, 0),
    ("A.P", "A.P undefined in the Part-IV legend", "Prof. Dr. Ayaz Keerio", ("P4-PM",), 3, 0),
    # --- BS(CS) Part-IV, Pre-Engineering (Room 04) ---
    ("E.C", "E-Commerce", "Mr. Zohaib Maqsood", ("P4-PE",), 3, 0),
    ("MAD", "Mobile Application Development", "Mr. Kamran Brohi", ("P4-PE",), 3, 0),
    ("A.P", "A.P undefined in the Part-IV legend", "Prof. Dr. Ayaz Keerio", ("P4-PE",), 3, 0),
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


def teacher_parts(requirements: list[SessionRequirement]) -> dict[str, set[str]]:
    # Which Parts each teacher works in the cross-Part pressure this phase is about.
    parts: dict[str, set[str]] = defaultdict(set)
    for requirement in requirements:
        parts[requirement.teacher].add(part_of(requirement.divisions[0]))
    return parts


def multi_part_teachers(requirements: list[SessionRequirement], minimum: int = 2) -> dict[str, set[str]]:
    # Teachers working in at least `minimum` Parts, worst first when the caller sorts.
    return {name: parts for name, parts in teacher_parts(requirements).items() if len(parts) >= minimum}


def shared_rooms() -> dict[str, list[str]]:
    # Rooms that more than one division calls home Part-III and Part-IV share 03 and 04.
    rooms: dict[str, list[str]] = defaultdict(list)
    for division in DIVISIONS.values():
        rooms[division.home_room].append(division.key)
    return {room: keys for room, keys in rooms.items() if len(keys) > 1}


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


# --- Hard constraints, unchanged in definition from Phase 5. Each blames the genes at fault. ---


@dataclass(frozen=True)
class Violation:
    message: str
    gene_indexes: tuple[int, ...]


def teacher_double_booked(chromosome: Chromosome, requirements: list[SessionRequirement]) -> list[Violation]:
    # Nobody can teach two sessions in one period. The key ignores division on purpose: that is
    # what makes a Part-I session and a Part-III session collide for a teacher who works in both.
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
    # Two sessions cannot share a room in the same period. With Part-III and Part-IV both
    # assigned rooms 03 and 04, this now bites on ordinary lectures, not just on labs.
    seen: dict[tuple[str, str, str], int] = {}
    violations = []
    for index, gene in enumerate(chromosome):
        key = (gene.room, gene.day, gene.time_slot)
        first = seen.get(key)
        if first is None:
            seen[key] = index
            continue
        where_first = "/".join(requirements[first].divisions)
        where_now = "/".join(requirements[index].divisions)
        violations.append(
            Violation(
                f"{gene.room} is double-booked on {gene.day} {gene.time_slot}: "
                f"{chromosome[first].course_code} ({where_first}) and {gene.course_code} ({where_now})",
                (first, index),
            )
        )
    return violations


def teacher_outside_availability(chromosome: Chromosome, requirements: list[SessionRequirement]) -> list[Violation]:
    # Availability is the days each person actually appears in the PDF; the algorithm works
    # around it rather than overriding it.
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
    # A group of students can only sit in one session at a time. Checked per division, so two
    # different Parts in the same period are fine different students.
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


def cross_part_teacher_clashes(chromosome: Chromosome, requirements: list[SessionRequirement]) -> list[str]:
    # A direct lens on the rule this phase stresses: a teacher working in several Parts must
    # never be in two of them at once. The general teacher check already penalises it, so this
    # deliberately adds no extra penalty it exists for evidence.
    overlapping = multi_part_teachers(requirements)
    placements: dict[tuple[str, str, str], list[tuple[str, str]]] = defaultdict(list)
    for gene, requirement in zip(chromosome, requirements, strict=True):
        if gene.teacher not in overlapping:
            continue
        placements[(gene.teacher, gene.day, gene.time_slot)].append(
            (part_of(requirement.divisions[0]), gene.course_code)
        )

    clashes = []
    for (teacher, day, slot), entries in sorted(placements.items()):
        if len({part for part, _ in entries}) > 1:
            detail = ", ".join(f"{code} ({part})" for part, code in entries)
            clashes.append(f"{teacher} is in two Parts at once on {day} {slot}: {detail}")
    return clashes


# --- GA machinery, unchanged from Phase 5 (§6.3) ---


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
    blame_rate: float = 0.0,
) -> Chromosome:
    # Phase 4's mutation: every gene has the same small chance of being re-placed.
    # blame_rate is accepted and ignored so both modes share one call signature.
    mutated = list(chromosome)
    for index, requirement in enumerate(requirements):
        if rng.random() < mutation_rate:
            mutated[index] = random_gene(rng, requirement)
    return mutated


# How likely a gene that is causing a violation gets re-placed. Phase 5 hard-coded 0.6; it is a
# knob here because with 133 sessions a bad early individual can have dozens of blamed genes,
# and re-rolling most of them at once throws away the parts that were already right.
DEFAULT_BLAME_RATE = 0.6


def mutate_targeted(
    rng: random.Random,
    chromosome: Chromosome,
    requirements: list[SessionRequirement],
    mutation_rate: float,
    blame_rate: float = DEFAULT_BLAME_RATE,
) -> Chromosome:
    # Re-places the genes actually causing violations and only rarely touches the rest. This is
    # what got Phase 5 to 10/10; blind mutation spends its effort on sessions that were fine.
    mutated = list(chromosome)
    blamed = {
        index
        for found in all_violations(chromosome, requirements).values()
        for violation in found
        for index in violation.gene_indexes
    }
    for index, requirement in enumerate(requirements):
        chance = blame_rate if index in blamed else mutation_rate
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
    seconds: float


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
    blame_rate: float = DEFAULT_BLAME_RATE,
) -> RunResult:
    # Score everyone, carry the best through untouched, breed the rest until the timetable is
    # clean or the generation cap is reached.
    mutate = MUTATION_MODES[mutation_mode]
    started = time.perf_counter()
    population = [random_chromosome(rng, requirements) for _ in range(population_size)]

    for generation in range(1, max_generations + 1):
        scored = sorted(
            ((fitness(chromosome, requirements), chromosome) for chromosome in population),
            key=lambda pair: pair[0],
            reverse=True,
        )
        best_fitness, best = scored[0]
        if best_fitness == 0.0:
            return RunResult(best, generation, best_fitness, 0, True, time.perf_counter() - started)

        next_population = [chromosome for _, chromosome in scored[:elite_count]]
        while len(next_population) < population_size:
            parent_a = tournament_select(rng, scored, tournament_size)
            parent_b = tournament_select(rng, scored, tournament_size)
            child = (
                two_point_crossover(rng, parent_a, parent_b)
                if rng.random() < crossover_rate
                else list(parent_a)
            )
            next_population.append(mutate(rng, child, requirements, mutation_rate, blame_rate))
        population = next_population

    final = max(((fitness(c, requirements), c) for c in population), key=lambda pair: pair[0])
    return RunResult(
        final[1], max_generations, final[0], count_violations(final[1], requirements),
        False, time.perf_counter() - started,
    )


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


def format_compact_division(
    chromosome: Chromosome, requirements: list[SessionRequirement], division_key: str
) -> str:
    # A one-line-per-period listing, for when eight full grids would be unreadable.
    division = DIVISIONS[division_key]
    rows = sorted(
        (
            (DAYS.index(gene.day), TIME_SLOTS.index(gene.time_slot), gene, requirement)
            for gene, requirement in zip(chromosome, requirements, strict=True)
            if division_key in requirement.divisions
        )
    )
    lines = [f"{division.label}  (home room {division.home_room}) {len(rows)} sessions"]
    for _, _, gene, requirement in rows:
        label = f"{gene.course_code}{' (LAB)' if requirement.is_lab else ''}{' *' if len(requirement.divisions) > 1 else ''}"
        lines.append(f"   {gene.day} {gene.time_slot}  {label:<14}{gene.teacher:<28}{gene.room}")
    return "\n".join(lines)


def print_multi_part_evidence(chromosome: Chromosome, requirements: list[SessionRequirement]) -> None:
    # Every teacher working in more than one Part, with their week laid out per Part, so the
    # absence of an overlap can be read rather than taken on trust.
    overlapping = multi_part_teachers(requirements)
    if not overlapping:
        print("  no teacher works across more than one Part in this data")
        return

    for name in sorted(overlapping, key=lambda key: (-len(overlapping[key]), key)):
        parts = sorted(overlapping[name])
        by_part: dict[str, list[str]] = defaultdict(list)
        for gene, requirement in zip(chromosome, requirements, strict=True):
            if gene.teacher != name:
                continue
            label = f"{gene.course_code}{' LAB' if requirement.is_lab else ''}"
            by_part[part_of(requirement.divisions[0])].append(
                f"{DAYS.index(gene.day)}{gene.day} {gene.time_slot} {label}"
            )

        print(f"\n  {name}  ({len(parts)} Parts: {', '.join(parts)}; available {', '.join(TEACHERS[name].available_days)})")
        columns = [sorted(by_part[part]) for part in parts]
        header = "".join(f"{part:<40}" for part in parts)
        print(f"    {header}")
        for index in range(max(len(column) for column in columns)):
            row = "".join(f"{(column[index][1:] if index < len(column) else ''):<40}" for column in columns)
            print(f"    {row}")

        periods = [{entry[1:16] for entry in column} for column in columns]
        overlaps: set[str] = set()
        for first in range(len(periods)):
            for second in range(first + 1, len(periods)):
                overlaps |= periods[first] & periods[second]
        print(f"    -> periods used in more than one Part: {sorted(overlaps) if overlaps else 'none'}")


def print_shared_room_evidence(chromosome: Chromosome, requirements: list[SessionRequirement]) -> None:
    # Part-III and Part-IV share rooms 03 and 04, so show those rooms are never booked twice.
    for room, division_keys in sorted(shared_rooms().items()):
        usage: dict[tuple[str, str], list[str]] = defaultdict(list)
        for gene, requirement in zip(chromosome, requirements, strict=True):
            if gene.room != room:
                continue
            usage[(gene.day, gene.time_slot)].append(
                f"{gene.course_code} ({'/'.join(requirement.divisions)})"
            )
        clashes = {slot: entries for slot, entries in usage.items() if len(entries) > 1}
        per_division = {
            key: sum(1 for r in requirements if key in r.divisions and not r.is_lab) for key in division_keys
        }
        print(f"\n  {room} is home to {', '.join(division_keys)} "
              f"({', '.join(f'{key}: {count} lectures' for key, count in per_division.items())})")
        print(f"    periods used: {len(usage)} of {len(DAYS) * len(TIME_SLOTS)}")
        print(f"    double-booked periods: {clashes if clashes else 'none'}")


def print_break_checks(chromosome: Chromosome, requirements: list[SessionRequirement]) -> None:
    # Breaks the clean timetable one rule at a time and shows each detector firing.
    def counts(candidate: Chromosome) -> dict[str, int]:
        # Violations per constraint, for the before/after lines.
        return {name: len(found) for name, found in all_violations(candidate, requirements).items()}

    print(f"clean solution: {counts(chromosome)}")
    print(f"clean cross-Part check: {cross_part_teacher_clashes(chromosome, requirements) or 'no clashes'}")

    # Every teacher who works in more than one Part gets their own cross-Part break test.
    print("\n  --- cross-Part clash, one test per multi-Part teacher ---")
    overlapping = multi_part_teachers(requirements)
    for name in sorted(overlapping):
        parts = sorted(overlapping[name])
        first_index = next(
            index
            for index, requirement in enumerate(requirements)
            if requirement.teacher == name and part_of(requirement.divisions[0]) == parts[0]
        )
        second_index = next(
            index
            for index, requirement in enumerate(requirements)
            if requirement.teacher == name and part_of(requirement.divisions[0]) == parts[1]
        )
        broken = list(chromosome)
        anchor = broken[first_index]
        broken[second_index] = broken[second_index]._replace(day=anchor.day, time_slot=anchor.time_slot)

        found = all_violations(broken, requirements)["teacher double-booked"]
        cross = cross_part_teacher_clashes(broken, requirements)
        blamed_name = [v for v in found if name in v.message]
        print(f"\n  {name}: {parts[1]} session dragged onto their {parts[0]} period "
              f"({anchor.day} {anchor.time_slot})")
        print(f"    teacher double-booked: {'DETECTED' if blamed_name else 'MISSED'} ({len(blamed_name)})")
        if blamed_name:
            print(f"    -> {blamed_name[0].message}")
        print(f"    cross-Part check: {'DETECTED' if cross else 'MISSED'} ({len(cross)})")

    # The other four rules, one break each.
    print("\n  --- the other rules ---")
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
    # Two divisions that share a room, to break the room rule the way this phase makes possible.
    shared_room, shared_keys = next(iter(sorted(shared_rooms().items())))
    room_index_a = next(
        index for index, r in enumerate(requirements) if r.divisions[0] == shared_keys[0] and not r.is_lab
    )
    room_index_b = next(
        index for index, r in enumerate(requirements) if r.divisions[0] == shared_keys[1] and not r.is_lab
    )

    cases: list[tuple[str, Chromosome, str]] = []

    broken = list(chromosome)
    broken[room_index_b] = broken[room_index_b]._replace(
        day=broken[room_index_a].day, time_slot=broken[room_index_a].time_slot
    )
    cases.append((
        "room double-booked",
        broken,
        f"{shared_keys[0]} and {shared_keys[1]} lectures put in {shared_room} at the same time",
    ))

    broken = list(chromosome)
    teacher = TEACHERS[broken[theory_index].teacher]
    unavailable_day = next(day for day in DAYS if day not in teacher.available_days)
    broken[theory_index] = broken[theory_index]._replace(day=unavailable_day)
    cases.append(("teacher outside availability", broken, f"moved onto {unavailable_day}"))

    broken = list(chromosome)
    broken[same_division_other] = broken[same_division_other]._replace(
        day=broken[theory_index].day, time_slot=broken[theory_index].time_slot
    )
    cases.append(("division double-booked", broken, "two subjects for one group at once"))

    broken = list(chromosome)
    broken[lab_index] = broken[lab_index]._replace(
        room=DIVISIONS[requirements[lab_index].divisions[0]].home_room
    )
    cases.append(("lab session rules", broken, "lab moved out of the lab pool"))

    for constraint, candidate, description in cases:
        found = all_violations(candidate, requirements)[constraint]
        print(f"\n  break: {description}")
        print(f"    {constraint}: {'DETECTED' if found else 'MISSED'} ({len(found)})")
        if found:
            print(f"    -> {found[0].message}")


def print_dataset(requirements: list[SessionRequirement]) -> None:
    # The data this run is built from, so it can be checked against the PDF.
    print("Divisions (rooms exactly as printed on each sheet):")
    for division in DIVISIONS.values():
        own = sum(1 for r in requirements if division.key in r.divisions)
        print(f"  {division.key:<7}{division.label:<42}{division.home_room:<10}{own} sessions/week")

    print("\nRooms shared by more than one division:")
    for room, keys in sorted(shared_rooms().items()):
        print(f"  {room:<12}{', '.join(keys)}")

    print("\nSubjects, teachers and weekly periods (from the PDF):")
    for code, name, teacher, divisions, theory, lab in PDF_SESSIONS:
        where = "+".join(divisions)
        lab_note = f" + {lab} lab" if lab else ""
        print(f"  {where:<14}{code:<8}{name[:36]:<38}{theory} periods{lab_note:<10} {teacher}")

    print("\nTeachers by number of Parts taught:")
    counted = teacher_parts(requirements)
    for name in sorted(counted, key=lambda key: (-len(counted[key]), key)):
        parts = sorted(counted[name])
        marker = "  <-- multi-Part" if len(parts) > 1 else ""
        print(f"  {len(parts)} Part(s)  {name:<32}{', '.join(parts):<28}{marker}")
    most = max(len(parts) for parts in counted.values())
    print(f"  most Parts taught by any one teacher: {most}")

    print(f"\nSessions to place: {len(requirements)} "
          f"({sum(1 for r in requirements if not r.is_lab)} theory, {sum(1 for r in requirements if r.is_lab)} lab)")
    print(f"Grid per division: {len(DAYS)} days x {len(TIME_SLOTS)} periods; lab pool {LAB_ROOMS}")


def parse_args() -> argparse.Namespace:
    # Command-line knobs so runs can be compared without editing the file.
    parser = argparse.ArgumentParser(description="Phase 6 full BS(CS) Morning shift GA")
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--seed", type=int, default=200, help="base seed; run N uses seed + N")
    parser.add_argument("--population", type=int, default=120)
    parser.add_argument("--generations", type=int, default=2000)
    parser.add_argument("--tournament", type=int, default=4)
    parser.add_argument("--crossover-rate", type=float, default=0.9)
    parser.add_argument("--mutation-rate", type=float, default=0.03)
    parser.add_argument("--elites", type=int, default=4)
    parser.add_argument("--mutation-mode", choices=sorted(MUTATION_MODES), default="targeted")
    parser.add_argument("--blame-rate", type=float, default=DEFAULT_BLAME_RATE,
                        help="chance a violating gene is re-placed (targeted mode)")
    parser.add_argument("--compact", action="store_true", help="list sessions instead of drawing grids")
    parser.add_argument("--quiet", action="store_true", help="only print the run table")
    return parser.parse_args()


def main() -> None:
    # Runs the GA several times, then shows one full solution with the evidence behind it.
    args = parse_args()
    requirements = build_session_requirements()

    print("=" * 128)
    print("PHASE 6 full BS(CS) Morning shift: Part-I, Part-II, Part-III, Part-IV")
    print("=" * 128)
    print_dataset(requirements)

    print("\n" + "=" * 128)
    print(f"RUNS (population {args.population}, tournament {args.tournament}, crossover {args.crossover_rate}, "
          f"mutation {args.mutation_rate}/{args.mutation_mode} blame {args.blame_rate}, "
          f"elites {args.elites}, cap {args.generations})")
    print("=" * 128)
    print(f"{'run':<6}{'seed':<8}{'generations':<14}{'fitness':<12}{'violations':<13}"
          f"{'seconds':<10}{'sec/gen':<10}{'result'}")

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
            blame_rate=args.blame_rate,
        )
        results.append(result)
        outcome = "converged" if result.converged else "HIT GENERATION CAP"
        print(f"{run_number:<6}{seed:<8}{result.generations:<14}{result.fitness:<12.1f}{result.violations:<13}"
              f"{result.seconds:<10.1f}{result.seconds / result.generations:<10.4f}{outcome}")

    converged = [result for result in results if result.converged]
    total_seconds = sum(result.seconds for result in results)
    total_generations = sum(result.generations for result in results)
    if converged:
        generations = [result.generations for result in converged]
        print(f"\nconverged {len(converged)}/{len(results)} runs; generations min {min(generations)}, "
              f"max {max(generations)}, mean {sum(generations) / len(generations):.1f}")
    else:
        print(f"\nNo run converged within {args.generations} generations.")
    print(f"timing: {total_generations} generations in {total_seconds:.1f}s "
          f"= {total_seconds / total_generations:.4f}s per generation")

    if args.quiet:
        return

    representative = converged[0] if converged else results[0]
    outcome = (
        f"converged in {representative.generations} generations"
        if representative.converged
        else f"best effort after {representative.generations} generations"
    )

    print("\n" + "=" * 128)
    print(f"TIMETABLE from the first converged run ({outcome}).  * = both groups of that Part together")
    print("=" * 128)
    for division_key in DIVISIONS:
        if args.compact:
            print(format_compact_division(representative.best, requirements, division_key) + "\n")
        else:
            print(format_division_timetable(representative.best, requirements, division_key))

    print("=" * 128)
    print("HARD CONSTRAINT CHECK")
    print("=" * 128)
    for name, found in all_violations(representative.best, requirements).items():
        print(f"  {name:<32}{len(found)} violation(s)")
        for violation in found:
            print(f"      {violation.message}")

    print("\n" + "=" * 128)
    print("EVIDENCE: teachers working in more than one Part are never in two at once")
    print("=" * 128)
    print_multi_part_evidence(representative.best, requirements)

    print("\n" + "=" * 128)
    print("EVIDENCE: rooms shared by two divisions are never double-booked")
    print("=" * 128)
    print_shared_room_evidence(representative.best, requirements)

    print("\n" + "=" * 128)
    print("EVIDENCE: each detector fires when the rule is deliberately broken")
    print("=" * 128)
    print_break_checks(representative.best, requirements)


if __name__ == "__main__":
    main()
