"""Fitness function: aggregates penalties from scheduler/constraints/hard.py.

fitness = -(hard_violation_count * HARD_WEIGHT), so a perfect timetable scores
0.0 and every violation counts equally. There are no soft constraints yet
(docs/PROJECT_ARCHITECTURE.md §6.2) — this file grows a second term for them
once those are designed.
"""

from app.scheduler.constraints.hard import HARD_WEIGHT, Violation, count_violations


def fitness_from_violations(all_violations_result: dict[str, list[Violation]]) -> float:
    # Turns an already-computed violation count into a score. Takes the violations dict
    # rather than a chromosome so callers reuse one evaluation instead of running the
    # constraint checks twice (once for fitness, once for anything else that needs them).
    violations = count_violations(all_violations_result)
    return -float(violations * HARD_WEIGHT) if violations else 0.0
