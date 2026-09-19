"""GA generation loop: population -> selection -> crossover -> mutation -> iterate.

Takes a set of Division ids, reads everything it needs from the database
(DivisionCourse, Teacher availability, Classroom), and returns a
GenerationResult: either a converged (zero hard violations) chromosome, or an
honest report that the run stagnated or hit its generation cap. This is the
entry point the API's generate endpoint calls — it contains no HTTP or
database-write concerns of its own (docs/PROJECT_ARCHITECTURE.md §6.3).
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Teacher
from app.scheduler.chromosome import (
    Chromosome,
    DivisionInfo,
    SessionRequirement,
    build_session_requirements,
    load_divisions,
    random_chromosome,
)
from app.scheduler.constraints.hard import Violation, all_violations
from app.scheduler.fitness import fitness_from_violations
from app.scheduler.operators import mutate_targeted, tournament_select, two_point_crossover
from app.scheduler.seeding import constructive_chromosome

ALGORITHM_VERSION = "ga-v2-phase8"  # v2: greedy constructive starting population

# How many generations without a fitness improvement before the run is considered
# stagnant. Chosen from Phase 6's own numbers: its slowest converged run (population 120,
# ~133 sessions) took 2080 generations, and one population-250 experiment sat at exactly
# one violation for the full 3000-generation cap without ever recovering — so "no
# improvement for 400 generations" is comfortably past normal slow progress but short
# enough to trigger a restart before a run wastes thousands of generations doing nothing.
STAGNATION_WINDOW = 400

# How many times a stagnant run gets a partial-population restart before the engine gives
# up and reports "stagnated" instead of quietly running out the generation cap. Raised from
# an initial 3 after real testing on the full 8-division, 132-session, 9-constraint problem:
# two runs on different seeds both stagnated with only a handful of violations left (7 and
# 20), and each restart along the way visibly cut the violation count further before
# stalling again — so more attempts is worth the (bounded) extra time rather than giving up
# early on a search that keeps making real progress. See docs/PROJECT_AUDIT.md for the
# measured numbers this is based on.
MAX_RESTARTS = 8


@dataclass
class GaSettings:
    population_size: int = 120
    max_generations: int = 4000
    tournament_size: int = 4
    crossover_rate: float = 0.9
    mutation_rate: float = 0.03
    elite_count: int = 4
    seed: int | None = None
    # Share of each fresh batch of individuals (the starting population, and the refill
    # after a restart) built by the greedy constructive seeder instead of pure random.
    # 0.0 reproduces the old all-random behaviour; the rest stays random on purpose so
    # the whole population can't collapse into one local optimum.
    constructive_fraction: float = 0.5

    def as_dict(self) -> dict:
        # For Timetable.generation_params — a record of exactly what settings produced this run.
        return {
            "population_size": self.population_size,
            "max_generations": self.max_generations,
            "tournament_size": self.tournament_size,
            "crossover_rate": self.crossover_rate,
            "mutation_rate": self.mutation_rate,
            "elite_count": self.elite_count,
            "seed": self.seed,
            "constructive_fraction": self.constructive_fraction,
            "algorithm_version": ALGORITHM_VERSION,
            "stagnation_window": STAGNATION_WINDOW,
            "max_restarts": MAX_RESTARTS,
        }


@dataclass
class GenerationResult:
    chromosome: Chromosome
    requirements: list[SessionRequirement]
    divisions: dict[int, DivisionInfo]
    fitness: float
    generation_count: int
    converged: bool
    stagnated: bool
    restarts_used: int
    wall_seconds: float
    final_violations: dict[str, list[Violation]] = field(default_factory=dict)


def load_teacher_availability(session: Session, requirements: list[SessionRequirement]) -> dict[int, set[str]]:
    # Reads each involved teacher's declared availability days out of the database, once
    # per run, into a plain dict — this is the real replacement for the dev scripts'
    # hardcoded TEACHERS dict.
    teacher_ids = {requirement.teacher_id for requirement in requirements}
    if not teacher_ids:
        return {}
    rows = session.scalars(select(Teacher).where(Teacher.id.in_(teacher_ids))).all()
    return {row.id: set(row.availability.get("days", [])) for row in rows}


def _score(
    chromosome: Chromosome,
    requirements: list[SessionRequirement],
    divisions: dict[int, DivisionInfo],
    teacher_availability: dict[int, set[str]],
) -> tuple[float, dict[str, list[Violation]]]:
    # Runs every constraint exactly once for this chromosome and derives both the fitness
    # score and the full violation detail from that single pass — the dev scripts computed
    # this twice per individual (once for fitness, once for mutation's blame set), which
    # Phase 6 flagged as the likely main cost; this is the actual fix, not just deferring
    # message strings (see constraints/hard.py's module docstring).
    violations = all_violations(chromosome, requirements, divisions, teacher_availability)
    return fitness_from_violations(violations), violations


def fresh_individuals(
    rng: random.Random,
    count: int,
    requirements: list[SessionRequirement],
    teacher_availability: dict[int, set[str]],
    constructive_fraction: float,
) -> list[Chromosome]:
    # A batch of brand-new individuals: the first share are built greedily to dodge clashes,
    # the rest are pure random so the population keeps genuinely different starting points.
    constructive_count = round(count * constructive_fraction)
    built = [constructive_chromosome(rng, requirements, teacher_availability) for _ in range(constructive_count)]
    built += [random_chromosome(rng, requirements) for _ in range(count - constructive_count)]
    return built


def evolve(
    requirements: list[SessionRequirement],
    divisions: dict[int, DivisionInfo],
    teacher_availability: dict[int, set[str]],
    settings: GaSettings,
) -> GenerationResult:
    # The generation loop itself: score everyone, carry the best through untouched, breed
    # the rest by selection/crossover/mutation, restart part of the population if progress
    # stalls, until the timetable is clean or the generation cap is reached.
    started = time.perf_counter()
    rng = random.Random(settings.seed)
    population = fresh_individuals(
        rng, settings.population_size, requirements, teacher_availability, settings.constructive_fraction
    )

    best_fitness_ever = float("-inf")
    generations_without_improvement = 0
    restarts_used = 0

    for generation in range(1, settings.max_generations + 1):
        # Score every individual exactly once (fitness AND violation detail together —
        # see _score's docstring), then rank by fitness. best_violations is already
        # sitting right there, no second evaluation needed for the top individual.
        evaluated = [(*_score(c, requirements, divisions, teacher_availability), c) for c in population]
        evaluated.sort(key=lambda row: row[0], reverse=True)
        best_fitness, best_violations, best_chromosome = evaluated[0]

        if best_fitness == 0.0:
            return GenerationResult(
                best_chromosome, requirements, divisions, best_fitness, generation,
                converged=True, stagnated=False, restarts_used=restarts_used,
                wall_seconds=time.perf_counter() - started, final_violations=best_violations,
            )

        if best_fitness > best_fitness_ever:
            best_fitness_ever = best_fitness
            generations_without_improvement = 0
        else:
            generations_without_improvement += 1

        if generations_without_improvement >= STAGNATION_WINDOW:
            if restarts_used >= MAX_RESTARTS:
                return GenerationResult(
                    best_chromosome, requirements, divisions, best_fitness, generation,
                    converged=False, stagnated=True, restarts_used=restarts_used,
                    wall_seconds=time.perf_counter() - started, final_violations=best_violations,
                )
            # Partial restart: keep the elites (the best genetic material found so far),
            # refill everyone else with a fresh half-greedy, half-random batch to escape the stall.
            elites = [chromosome for _, _violations, chromosome in evaluated[: settings.elite_count]]
            fresh = fresh_individuals(
                rng, settings.population_size - len(elites), requirements, teacher_availability,
                settings.constructive_fraction,
            )
            population = elites + fresh
            restarts_used += 1
            generations_without_improvement = 0
            continue

        next_population = [chromosome for _, _violations, chromosome in evaluated[: settings.elite_count]]
        while len(next_population) < settings.population_size:
            _fitness_a, violations_a, parent_a = tournament_select(rng, evaluated, settings.tournament_size)
            _fitness_b, _violations_b, parent_b = tournament_select(rng, evaluated, settings.tournament_size)

            if rng.random() < settings.crossover_rate:
                child = two_point_crossover(rng, parent_a, parent_b)
                child_violations = all_violations(child, requirements, divisions, teacher_availability)
            else:
                # No crossover this time — the child is an exact copy of parent_a, so its
                # violations are already known; skip re-running all 9 constraints on it.
                child = list(parent_a)
                child_violations = violations_a

            next_population.append(mutate_targeted(rng, child, requirements, child_violations, settings.mutation_rate))
        population = next_population

    # Ran out of generations without either converging or being declared stagnant — report
    # the best effort honestly, distinct from a clean convergence.
    final_scored = [(_score(c, requirements, divisions, teacher_availability), c) for c in population]
    (best_fitness, best_violations), best_chromosome = max(final_scored, key=lambda pair: pair[0][0])
    return GenerationResult(
        best_chromosome, requirements, divisions, best_fitness, settings.max_generations,
        converged=False, stagnated=False, restarts_used=restarts_used,
        wall_seconds=time.perf_counter() - started, final_violations=best_violations,
    )


def generate_timetable(session: Session, division_ids: list[int], settings: GaSettings | None = None) -> GenerationResult:
    # The whole real-data path in one call: build the requirements from the database, read
    # teacher availability, then run the GA. This is what the API endpoint calls directly.
    settings = settings or GaSettings()
    divisions = load_divisions(session, division_ids)
    requirements = build_session_requirements(session, division_ids)
    if not requirements:
        raise ValueError("No DivisionCourse assignments found for the requested divisions.")
    teacher_availability = load_teacher_availability(session, requirements)
    return evolve(requirements, divisions, teacher_availability, settings)
