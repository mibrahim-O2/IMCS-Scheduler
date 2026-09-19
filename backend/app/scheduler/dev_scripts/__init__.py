"""Throwaway exploration scripts for the scheduling engine.

Nothing here is production code. These scripts are for trying an approach out
end to end before any of it is promoted into app/scheduler/ proper.

KEPT, NOT DELETED, as of Phase 8 — and the reason to keep them is now gone:
Phase 7 kept these because production had reproduced phase4 but not phase5/6
(the full 8-division problem stalled at 1-20 leftover violations). Phase 8's
greedy starting population (scheduler/seeding.py) fixed that: the real engine
now converges on the full 8-division problem in 100/100 seeded runs, and on the
Phase-5-sized subset too, all under the stricter 9-constraint set these scripts
never checked. So production now matches or beats every one of these scripts.

They are still here only because deleting them means also editing the
references in docs/PROJECT_ARCHITECTURE.md and docs/CONSTRAINTS.md, which was
outside Phase 8's scope. Safe to delete (git history keeps them); nothing in
app/ imports from this package.
"""
