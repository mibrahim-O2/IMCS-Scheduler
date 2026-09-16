"""Department and Program models.

Department is the stable top-level grouping (Computer Science, Artificial
Intelligence, Mathematics) used for the homepage hierarchy. Program is one
department + level pair (BS, Master, M.Phil, M.Phil Bioinformatics, Ph.D,
M.Sc. Pass, PGD), carrying `is_schedulable` — true for BS-level programs
only today, and the flag that decides which programs get Divisions and
Timetables at all. Shift-split and PM/PE-split flags apply only to
schedulable programs.

See docs/PROJECT_ARCHITECTURE.md §3.1. Whether Mathematics has a PM/PE split
is open question §11.1.
"""
