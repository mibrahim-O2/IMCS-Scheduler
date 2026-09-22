"""GA operators: selection, crossover, and the blame-carrying targeted mutation
Phase 5-6 proved necessary for reliable convergence at real-department scale.

Phase 4's original mutation (every gene an equal small chance of being
re-placed) was tried again on Phase 5's problem size in Phase 6's report and
only converged 2 of 5 times, with runs stalling at a single remaining
violation for a thousand-plus generations. Targeted mutation — re-place the
genes actually causing a violation, leave the rest mostly alone — got 10/10
in both Phase 5 and Phase 6, so that is the only mutation this module
implements; there is no "simple" fallback to accidentally regress to.
See docs/PROJECT_ARCHITECTURE.md §6.3.
"""

import random

from app.scheduler.chromosome import Chromosome, SessionRequirement, random_gene
from app.scheduler.constraints.hard import Violation, blamed_gene_indexes


def tournament_select(rng: random.Random, evaluated: list[tuple], tournament_size: int) -> tuple:
    # Samples a few already-scored individuals at random and returns the fittest of them —
    # a real comparison, not an unconditioned random pick. `evaluated` rows are whatever
    # the caller scored them as (fitness, ...extra); only element 0 (fitness) is used to
    # compare, so the caller gets back the *whole* row, including anything it attached
    # (e.g. that individual's already-computed violations) rather than just the chromosome.
    contenders = rng.sample(evaluated, min(tournament_size, len(evaluated)))
    return max(contenders, key=lambda row: row[0])


def two_point_crossover(rng: random.Random, parent_a: Chromosome, parent_b: Chromosome) -> Chromosome:
    # Swaps a middle stretch of gene placements between two parents. Gene positions line
    # up with requirements for both parents, so the child is always a complete timetable.
    # A gene whose requirement has a pre-assigned (fixed) room — Phase 9 — is unaffected by
    # which parent it's copied from: every individual's chromosome, everywhere, only ever
    # places that gene's room from SessionRequirement.candidate_rooms, which is a
    # single-element tuple for a fixed room. Both parents already agree on that one room at
    # that position, so swapping the gene swaps day/slot only, in effect.
    if len(parent_a) < 3:
        return list(parent_a)
    first, second = sorted(rng.sample(range(1, len(parent_a)), 2))
    return list(parent_a[:first]) + list(parent_b[first:second]) + list(parent_a[second:])


# How likely a gene that is causing a violation gets re-placed, versus the baseline rate
# for genes that currently look fine. Proven in Phase 5-6 at 0.6; kept as a named constant
# rather than buried in a call so the "why 0.6" question has one place to answer it: it is
# high enough that a blamed gene usually does move, but not certain, so a genuinely hard
# clash (e.g. a teacher with very few available days) still gets a few tries at different
# placements rather than being reshuffled to the same dead end every single generation.
BLAME_MUTATION_RATE = 0.6


def mutate_targeted(
    rng: random.Random,
    chromosome: Chromosome,
    requirements: list[SessionRequirement],
    all_violations_result: dict[str, list[Violation]],
    mutation_rate: float,
) -> Chromosome:
    # Re-places genes actually causing a violation far more often than genes that are
    # already fine. Takes the violations dict the caller already computed for this
    # chromosome (for fitness) instead of recomputing it here — see constraints/hard.py.
    # A re-placed gene still can't leave a pre-assigned room: random_gene draws the room
    # from the requirement's candidate_rooms, which for a fixed room is one element (see
    # chromosome.build_session_requirements) — day and slot are what actually move.
    blamed = blamed_gene_indexes(all_violations_result)
    mutated = list(chromosome)
    for index, requirement in enumerate(requirements):
        chance = BLAME_MUTATION_RATE if index in blamed else mutation_rate
        if rng.random() < chance:
            mutated[index] = random_gene(rng, requirement)
    return mutated
