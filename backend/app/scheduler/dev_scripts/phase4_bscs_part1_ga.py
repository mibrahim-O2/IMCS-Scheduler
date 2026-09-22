"""Phase 4 dev script: the core GA, solving BSCS Part-I Morning (semester 1).

Standalone on purpose no database, no API, no frontend. The course data below
was read out of the saved BSCS 2024 scheme (scheme #6, from the university's own
course scheme PDF) and pasted here so this script runs on its own; the teachers
and their available days come from the legend of the real BSCS Part-I Morning
timetable PDF. Design follows docs/PROJECT_ARCHITECTURE.md §6: a chromosome is
one candidate timetable, a gene is one placed session, and every hard constraint
is its own function rather than being buried inside the fitness function.

Run it with:
    python -m app.scheduler.dev_scripts.phase4_bscs_part1_ga --runs 5

Note (post-Phase 6 cleanup): the hand-typed-from-PDF approach used below is
superseded going forward by docs/timetable.json, a clean structured export
covering all BSCS/BSAI Morning divisions with full teacher names and no
initials ambiguity. This file's own data and logic are left as-is this is
just a pointer for whoever writes the next dev script.
"""

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from typing import NamedTuple

# The real 50-minute period structure and days from the BSCS Part-I Morning PDF.
DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri")
TIME_SLOTS = (
    "08:30-09:20",
    "09:20-10:10",
    "10:10-11:00",
    "11:00-11:50",
    "11:50-12:40",
    "12:40-13:30",
)

# Part-I Morning sits in Rooms 01/02 in the real timetable; labs need the computer lab.
LECTURE_ROOMS = ("Room 01", "Room 02")
LAB_ROOMS = ("Computer Lab 01",)

# Only hard constraints exist in this phase, so every violation costs the same heavy amount.
HARD_WEIGHT = 100

# A non-credit subject still occupies periods in the real timetable; two a week is realistic.
NON_CREDIT_SESSIONS_PER_WEEK = 2


@dataclass(frozen=True)
class Teacher:
    full_name: str
    # Days this teacher is available, loosely based on the days they appear in the real PDF.
    available_days: tuple[str, ...]


# Full names from the real timetable legend. Initials are never used as identifiers
# they collide across sheets and refer to different people.
TEACHERS: dict[str, Teacher] = {
    teacher.full_name: teacher
    for teacher in (
        Teacher("Prof. Dr. Fida Chandio", ("Tue", "Thu")),
        Teacher("Mr. M. Rafiq Mallah", ("Mon", "Tue")),
        Teacher("Dr. Altaf Abro", ("Mon", "Tue")),
        Teacher("Ms. Madhia Khemtio", ("Mon", "Tue", "Wed")),
        Teacher("Dr. Hameedullah Bhutto", ("Mon", "Tue")),
        Teacher("Dr. Asad Buledi", ("Tue", "Thu")),
        Teacher("Dr. Gulsher Laghari", ("Wed", "Fri")),
        Teacher("Dr. Nazish Nawaz", ("Wed", "Thu")),
        Teacher("Mr. Ahmed Raza Chandio", ("Wed", "Fri")),
    )
}


@dataclass(frozen=True)
class Course:
    code: str
    name: str
    credit_hours: int | None  # None means non-credit ("NC" in the scheme document)
    has_lab: bool
    lab_credit_hours: int | None
    teacher: str
    lab_teacher: str | None


# Exactly the six semester-1 courses stored for BS Computer Science, scheme year 2024,
# after Phase 3's lab pairing (a lab belongs to its theory course, not a course of its own).
COURSES: tuple[Course, ...] = (
    Course("CSPF302", "PROGRAMMING FUNDAMENTALS", 3, True, 1,
           "Prof. Dr. Fida Chandio", "Dr. Gulsher Laghari"),
    Course("DCMT300", "PRE-CALCULUS -I", None, False, None,
           "Mr. M. Rafiq Mallah", None),
    Course("GAPH310", "APPLIED PHYSICS", 2, True, 1,
           "Dr. Altaf Abro", "Dr. Nazish Nawaz"),
    Course("GENG300", "FUNCTIONAL ENGLISH", 3, False, None,
           "Ms. Madhia Khemtio", None),
    Course("GICP300", "IDEOLOGY AND CONSTITUTION OF PAKISTAN", 2, False, None,
           "Dr. Hameedullah Bhutto", None),
    Course("GICT306", "APPLICATIONS OF INFORMATION & COMMUNICATION TECHNOLOGIES", 3, True, 1,
           "Dr. Asad Buledi", "Mr. Ahmed Raza Chandio"),
)


class Gene(NamedTuple):
    """One placed session the gene shape from §6.1."""

    course_code: str
    teacher: str
    room: str
    day: str
    time_slot: str


@dataclass(frozen=True)
class SessionRequirement:
    """What a gene at this position must always be: which course, whose class, theory or lab.

    Mutation only ever re-rolls room, day and time slot, so gene i always answers
    requirement i and the course/teacher pairing stays fixed (§6.3).
    """

    course_code: str
    teacher: str
    is_lab: bool


Chromosome = list[Gene]


def build_session_requirements(courses: tuple[Course, ...]) -> list[SessionRequirement]:
    # One weekly period per credit hour, plus one period for a course's lab.
    requirements: list[SessionRequirement] = []
    for course in courses:
        weekly_periods = course.credit_hours or NON_CREDIT_SESSIONS_PER_WEEK
        for _ in range(weekly_periods):
            requirements.append(SessionRequirement(course.code, course.teacher, is_lab=False))
        if course.has_lab and course.lab_teacher:
            requirements.append(SessionRequirement(course.code, course.lab_teacher, is_lab=True))
    return requirements


def rooms_for(requirement: SessionRequirement) -> tuple[str, ...]:
    # Labs can only go in a lab room, lectures only in a lecture room.
    return LAB_ROOMS if requirement.is_lab else LECTURE_ROOMS


def random_gene(rng: random.Random, requirement: SessionRequirement) -> Gene:
    # A random placement for one required session; the course and teacher are fixed.
    return Gene(
        course_code=requirement.course_code,
        teacher=requirement.teacher,
        room=rng.choice(rooms_for(requirement)),
        day=rng.choice(DAYS),
        time_slot=rng.choice(TIME_SLOTS),
    )


def random_chromosome(rng: random.Random, requirements: list[SessionRequirement]) -> Chromosome:
    # One complete candidate timetable, placed at random.
    return [random_gene(rng, requirement) for requirement in requirements]


# --- Hard constraints: one function each, so they can be tested on their own (§6.2) ---


def teacher_double_booked(chromosome: Chromosome) -> list[str]:
    # A teacher cannot be in two places in the same period.
    seen: dict[tuple[str, str, str], Gene] = {}
    violations = []
    for gene in chromosome:
        key = (gene.teacher, gene.day, gene.time_slot)
        clash = seen.get(key)
        if clash:
            violations.append(
                f"{gene.teacher} is double-booked on {gene.day} {gene.time_slot} "
                f"({clash.course_code} and {gene.course_code})"
            )
        else:
            seen[key] = gene
    return violations


def room_double_booked(chromosome: Chromosome) -> list[str]:
    # Two sessions cannot occupy the same room in the same period.
    seen: dict[tuple[str, str, str], Gene] = {}
    violations = []
    for gene in chromosome:
        key = (gene.room, gene.day, gene.time_slot)
        clash = seen.get(key)
        if clash:
            violations.append(
                f"{gene.room} is double-booked on {gene.day} {gene.time_slot} "
                f"({clash.course_code} and {gene.course_code})"
            )
        else:
            seen[key] = gene
    return violations


def teacher_outside_availability(chromosome: Chromosome) -> list[str]:
    # Nobody is scheduled on a day they said they are not available; availability is an
    # input the algorithm works around, not something it may override.
    violations = []
    for gene in chromosome:
        teacher = TEACHERS[gene.teacher]
        if gene.day not in teacher.available_days:
            violations.append(
                f"{gene.teacher} is scheduled on {gene.day} {gene.time_slot} for {gene.course_code} "
                f"but is only available {', '.join(teacher.available_days)}"
            )
    return violations


def division_double_booked(chromosome: Chromosome) -> list[str]:
    # The whole of BSCS Part-I Morning attends together, so it can only be in one session at a time.
    # (Not in the original four, but without it the grid would put two subjects in one period.)
    seen: dict[tuple[str, str], Gene] = {}
    violations = []
    for gene in chromosome:
        key = (gene.day, gene.time_slot)
        clash = seen.get(key)
        if clash:
            violations.append(
                f"BSCS Part-I Morning has two sessions on {gene.day} {gene.time_slot} "
                f"({clash.course_code} and {gene.course_code})"
            )
        else:
            seen[key] = gene
    return violations


def lab_session_rules(chromosome: Chromosome, requirements: list[SessionRequirement]) -> list[str]:
    # A lab is its own session: it runs in a lab room, lectures do not, and a lab never
    # sits in the same period as one of its own course's theory sessions.
    violations = []
    theory_slots: dict[str, set[tuple[str, str]]] = {}
    for gene, requirement in zip(chromosome, requirements, strict=True):
        if not requirement.is_lab:
            theory_slots.setdefault(gene.course_code, set()).add((gene.day, gene.time_slot))

    for gene, requirement in zip(chromosome, requirements, strict=True):
        if requirement.is_lab:
            if gene.room not in LAB_ROOMS:
                violations.append(
                    f"{gene.course_code} lab is in {gene.room}, which is not a lab room"
                )
            if (gene.day, gene.time_slot) in theory_slots.get(gene.course_code, set()):
                violations.append(
                    f"{gene.course_code} lab clashes with its own theory session "
                    f"on {gene.day} {gene.time_slot}"
                )
        elif gene.room in LAB_ROOMS:
            violations.append(
                f"{gene.course_code} theory session is taking up {gene.room}, a lab room"
            )
    return violations


def all_violations(chromosome: Chromosome, requirements: list[SessionRequirement]) -> dict[str, list[str]]:
    # Every hard constraint checked in one place, kept per constraint so failures can be read.
    return {
        "teacher double-booked": teacher_double_booked(chromosome),
        "room double-booked": room_double_booked(chromosome),
        "teacher outside availability": teacher_outside_availability(chromosome),
        "division double-booked": division_double_booked(chromosome),
        "lab session rules": lab_session_rules(chromosome, requirements),
    }


def count_violations(chromosome: Chromosome, requirements: list[SessionRequirement]) -> int:
    # Total hard violations across all constraints.
    return sum(len(found) for found in all_violations(chromosome, requirements).values())


def fitness(chromosome: Chromosome, requirements: list[SessionRequirement]) -> float:
    # Fitness is the negative weighted violation count (§6.2), so a perfect timetable scores 0.
    # Soft constraints are deliberately not part of this phase.
    violations = count_violations(chromosome, requirements)
    return -float(violations * HARD_WEIGHT) if violations else 0.0


# --- Selection, crossover, mutation and the generation loop (§6.3) ---


def tournament_select(
    rng: random.Random, scored: list[tuple[float, Chromosome]], tournament_size: int
) -> Chromosome:
    # Takes a few random individuals and returns the fittest of them a real comparison,
    # not an unconditioned random pick.
    contenders = rng.sample(scored, min(tournament_size, len(scored)))
    return max(contenders, key=lambda pair: pair[0])[1]


def two_point_crossover(rng: random.Random, parent_a: Chromosome, parent_b: Chromosome) -> Chromosome:
    # Swaps a middle stretch of placements between two parents. Positions line up with the
    # session requirements, so the child is always a complete, well-formed timetable.
    if len(parent_a) < 3:
        return list(parent_a)
    first, second = sorted(rng.sample(range(1, len(parent_a)), 2))
    return list(parent_a[:first]) + list(parent_b[first:second]) + list(parent_a[second:])


def mutate(
    rng: random.Random,
    chromosome: Chromosome,
    requirements: list[SessionRequirement],
    mutation_rate: float,
) -> Chromosome:
    # Re-rolls a gene's room, day and time slot. The course/teacher pairing is never re-rolled
    # that comes from the course scheme.
    mutated = list(chromosome)
    for index, requirement in enumerate(requirements):
        if rng.random() < mutation_rate:
            mutated[index] = random_gene(rng, requirement)
    return mutated


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
) -> RunResult:
    # The generation loop: score everyone, keep the best untouched, then breed the rest
    # by selection, crossover and mutation until nothing is violated or we run out of generations.
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

        # Elitism: the fittest individuals move on exactly as they are, never mutated.
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


def format_timetable(chromosome: Chromosome, requirements: list[SessionRequirement]) -> str:
    # Lays the solution out as a day-by-period grid, the way the department reads a timetable.
    placed = {
        (gene.day, gene.time_slot): (gene, requirement)
        for gene, requirement in zip(chromosome, requirements, strict=True)
    }
    width = 26
    lines = ["".ljust(13) + "".join(day.ljust(width) for day in DAYS)]
    lines.append("-" * (13 + width * len(DAYS)))

    for slot in TIME_SLOTS:
        rows = [[], [], []]
        for day in DAYS:
            entry = placed.get((day, slot))
            if entry is None:
                rows[0].append(" ".ljust(width))
                rows[1].append("".ljust(width))
                rows[2].append("".ljust(width))
                continue
            gene, requirement = entry
            label = f"{gene.course_code}{' (LAB)' if requirement.is_lab else ''}"
            rows[0].append(label.ljust(width))
            rows[1].append(gene.teacher[:width - 1].ljust(width))
            rows[2].append(gene.room.ljust(width))
        lines.append(slot.ljust(13) + "".join(rows[0]))
        lines.append("".ljust(13) + "".join(rows[1]))
        lines.append("".ljust(13) + "".join(rows[2]))
        lines.append("")
    return "\n".join(lines)


def print_availability_evidence(chromosome: Chromosome) -> None:
    # Shows, teacher by teacher, the days they declared against the days they actually got,
    # so the availability constraint can be seen holding rather than just asserted.
    scheduled: dict[str, list[str]] = {}
    for gene in chromosome:
        scheduled.setdefault(gene.teacher, []).append(f"{gene.day} {gene.time_slot}")

    print(f"{'Teacher':<26}{'Declared available':<22}{'Actually scheduled'}")
    print("-" * 110)
    for name, teacher in TEACHERS.items():
        slots = sorted(scheduled.get(name, []))
        days_used = sorted({slot.split()[0] for slot in slots}, key=DAYS.index)
        outside = [slot for slot in slots if slot.split()[0] not in teacher.available_days]
        verdict = "OK" if not outside else f"OUTSIDE: {outside}"
        print(f"{name:<26}{', '.join(teacher.available_days):<22}{', '.join(slots) or '(none)'}")
        print(f"{'':<26}{'':<22}days used: {', '.join(days_used) or '(none)'} -> {verdict}")


def print_detector_checks(chromosome: Chromosome, requirements: list[SessionRequirement]) -> None:
    # Breaks a known-good timetable on purpose, one rule at a time, to prove each detector fires.
    def counts(candidate: Chromosome) -> dict[str, int]:
        return {name: len(found) for name, found in all_violations(candidate, requirements).items()}

    print(f"clean solution: {counts(chromosome)}")

    lab_index = next(index for index, req in enumerate(requirements) if req.is_lab)
    theory_index = next(index for index, req in enumerate(requirements) if not req.is_lab)
    same_teacher = [
        index
        for index, req in enumerate(requirements)
        if req.teacher == requirements[theory_index].teacher
    ][:2]
    # A different course's session, so the clash messages name two different subjects.
    other_course_index = next(
        index
        for index, req in enumerate(requirements)
        if not req.is_lab and req.course_code != requirements[theory_index].course_code
    )

    cases: list[tuple[str, Chromosome, str]] = []

    # Teacher clash: put two of one teacher's sessions in the same period, in different rooms.
    broken = list(chromosome)
    anchor = broken[same_teacher[0]]
    free_room = LECTURE_ROOMS[1] if anchor.room == LECTURE_ROOMS[0] else LECTURE_ROOMS[0]
    broken[same_teacher[1]] = broken[same_teacher[1]]._replace(
        day=anchor.day, time_slot=anchor.time_slot, room=free_room
    )
    cases.append(("teacher double-booked", broken, "two sessions of one teacher in one period"))

    # Room clash: two different courses forced into the same room and period.
    broken = list(chromosome)
    broken[other_course_index] = broken[other_course_index]._replace(
        day=broken[theory_index].day,
        time_slot=broken[theory_index].time_slot,
        room=broken[theory_index].room,
    )
    cases.append(("room double-booked", broken, "two different subjects in one room and period"))

    # Availability: move a session onto a day its teacher never offered.
    broken = list(chromosome)
    teacher = TEACHERS[broken[theory_index].teacher]
    unavailable_day = next(day for day in DAYS if day not in teacher.available_days)
    broken[theory_index] = broken[theory_index]._replace(day=unavailable_day)
    cases.append(("teacher outside availability", broken, f"moved onto {unavailable_day}"))

    # Lab in a lecture room.
    broken = list(chromosome)
    broken[lab_index] = broken[lab_index]._replace(room=LECTURE_ROOMS[0])
    cases.append(("lab session rules", broken, "lab moved out of the lab room"))

    # Lab on top of its own theory session.
    broken = list(chromosome)
    lab_course = requirements[lab_index].course_code
    partner = next(
        i for i, req in enumerate(requirements) if req.course_code == lab_course and not req.is_lab
    )
    broken[lab_index] = broken[lab_index]._replace(
        day=broken[partner].day, time_slot=broken[partner].time_slot
    )
    cases.append(("lab session rules", broken, "lab put on its own theory period"))

    # Division clash: two different courses in the same period, in different rooms.
    broken = list(chromosome)
    broken[other_course_index] = broken[other_course_index]._replace(
        day=broken[theory_index].day, time_slot=broken[theory_index].time_slot
    )
    cases.append(("division double-booked", broken, "two different subjects for the class at once"))

    for constraint, candidate, description in cases:
        found = all_violations(candidate, requirements)[constraint]
        status = "DETECTED" if found else "MISSED"
        print(f"\n  break: {description}")
        print(f"    {constraint}: {status} ({len(found)})")
        if found:
            print(f"    -> {found[0]}")


def print_dataset(requirements: list[SessionRequirement]) -> None:
    # Prints the data this run is built from, so it can be checked against the scheme and the PDF.
    print("Courses (BS Computer Science, scheme year 2024, semester 1):")
    for course in COURSES:
        credit = "NC" if course.credit_hours is None else course.credit_hours
        weekly = course.credit_hours or NON_CREDIT_SESSIONS_PER_WEEK
        lab = f" + lab ({course.lab_credit_hours} cr, {course.lab_teacher})" if course.has_lab else ""
        print(f"  {course.code:<9} {course.name[:52]:<54} cr={credit:<3} {weekly} periods/week{lab}")
        print(f"  {'':<9} teacher: {course.teacher}")
    print(f"\nSessions to place: {len(requirements)} "
          f"({sum(1 for r in requirements if not r.is_lab)} theory, {sum(1 for r in requirements if r.is_lab)} lab)")
    print(f"Grid: {len(DAYS)} days x {len(TIME_SLOTS)} periods, rooms {LECTURE_ROOMS + LAB_ROOMS}")


def parse_args() -> argparse.Namespace:
    # Command-line knobs, so several runs can be compared without editing the file.
    parser = argparse.ArgumentParser(description="Phase 4 GA for BSCS Part-I Morning")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--seed", type=int, default=1, help="base seed; run N uses seed + N")
    parser.add_argument("--population", type=int, default=60)
    parser.add_argument("--generations", type=int, default=300, help="generation cap per run")
    parser.add_argument("--tournament", type=int, default=3)
    parser.add_argument("--crossover-rate", type=float, default=0.9)
    parser.add_argument("--mutation-rate", type=float, default=0.15)
    parser.add_argument("--elites", type=int, default=2)
    return parser.parse_args()


def main() -> None:
    # Runs the GA several times, reports how long each took, then shows one full solution
    # together with the evidence that the hard constraints really hold.
    args = parse_args()
    requirements = build_session_requirements(COURSES)

    print("=" * 110)
    print("PHASE 4 core GA, BSCS Part-I Morning (semester 1)")
    print("=" * 110)
    print_dataset(requirements)

    print("\n" + "=" * 110)
    print(f"RUNS (population {args.population}, tournament {args.tournament}, crossover {args.crossover_rate}, "
          f"mutation {args.mutation_rate}, elites {args.elites}, cap {args.generations})")
    print("=" * 110)
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
        )
        results.append(result)
        outcome = "converged" if result.converged else "HIT GENERATION CAP"
        print(f"{run_number:<6}{seed:<8}{result.generations:<14}{result.fitness:<12.1f}"
              f"{result.violations:<18}{outcome}")

    converged = [r for r in results if r.converged]
    if converged:
        generations = [r.generations for r in converged]
        print(f"\nconverged {len(converged)}/{len(results)} runs; "
              f"generations min {min(generations)}, max {max(generations)}, "
              f"mean {sum(generations) / len(generations):.1f}")
    else:
        print("\nNo run converged see the timetable below for the best attempt.")

    representative = converged[0] if converged else results[0]
    outcome = (
        f"converged in {representative.generations} generations"
        if representative.converged
        else "best effort, generation cap reached"
    )
    print("\n" + "=" * 110)
    print(f"TIMETABLE from the first converged run ({outcome})")
    print("=" * 110)
    print(format_timetable(representative.best, requirements))

    print("=" * 110)
    print("HARD CONSTRAINT CHECK on that timetable")
    print("=" * 110)
    for name, found in all_violations(representative.best, requirements).items():
        print(f"  {name:<32}{len(found)} violation(s)")
        for line in found:
            print(f"      {line}")

    print("\n" + "=" * 110)
    print("EVIDENCE: teacher availability")
    print("=" * 110)
    print_availability_evidence(representative.best)

    print("\n" + "=" * 110)
    print("EVIDENCE: each detector fires when the rule is deliberately broken")
    print("=" * 110)
    print_detector_checks(representative.best, requirements)


if __name__ == "__main__":
    main()
