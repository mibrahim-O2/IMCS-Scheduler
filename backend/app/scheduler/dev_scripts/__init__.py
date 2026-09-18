"""Throwaway exploration scripts for the scheduling engine.

Nothing here is production code. These scripts are for trying an approach out
end to end before any of it is promoted into app/scheduler/ proper.

KEPT, NOT DELETED, as of Phase 7 — deliberately, not by default:
Phase 7 built the real production GA (app/scheduler/chromosome.py,
constraints/hard.py, fitness.py, operators.py, engine.py) and the task asked
for these dev scripts to be deleted once production code was proven to
reproduce their results. That proof is only partial:

  - phase4 (single division, ~42 sessions): reproduced cleanly. The real
    POST /api/v1/timetables/generate endpoint, called with BSCS Part-I's two
    real divisions, converged in 84 generations / 3.2s — comparable to this
    script's own numbers.
  - phase5 (multi-division, ~78-79 sessions): NOT reproduced. The production
    engine run on the matching real 4-division subset stagnated with 1
    violation left after 1736 generations, where this dev script reliably
    hit 10/10 converged runs. The difference is real: production checks all
    9 hard constraints (docs/CONSTRAINTS.md) where this script checked
    5-6, so it's solving a strictly harder problem, not regressing on the
    same one — but it means this script's numbers are not yet matched.
  - phase6 (full 8-division, 132 sessions): NOT reproduced. The production
    engine's best full-scale run (seed=7, max_generations=8000,
    MAX_RESTARTS=8) stagnated at generation 6333 with 1 remaining violation
    (teacher_outside_availability), 655.8s. This script's own full-scale
    result is the only existing proof that this exact problem is solvable
    at all with a GA, and it remains useful as that reference point while
    engine.py's tuning keeps closing the gap.

Delete phase5/6 once a production run demonstrably matches or beats their
convergence at the same scale. Until then they stay, as reference
implementations only — nothing in app/ imports from this package.
"""
