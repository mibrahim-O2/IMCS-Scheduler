# IMCS Scheduler — Scheduling Constraints

**This is a living document.** It lists every scheduling rule the Genetic
Algorithm (GA) has to respect, in the order each one was decided. New
constraints get added here as they're decided — this file should always be
the up-to-date single list, not something you have to reconstruct from old
conversation history or old phase reports.

Every constraint below is a **hard constraint**: the GA is not allowed to
produce a timetable that breaks one. (There are no soft/preference-style
constraints yet — those come later, once hard constraints are solid. When
soft constraints are added, this file gets a second section for them.)

For each constraint: what it actually means in plain language, and where it
was decided. "Implemented" means there's a working, tested function for it in
the production scheduler, `backend/app/scheduler/constraints/hard.py` — that
is the code the real `POST /api/v1/timetables/generate` endpoint runs. (The
older standalone dev scripts under `backend/app/scheduler/dev_scripts/` proved
constraints 1-6 out first; they are reference only now.)

The rules below describe **what a valid timetable is**. How the search finds
one (Phase 8's greedy starting population, mutation, restarts) lives in
`docs/PROJECT_AUDIT.md` §4-5 and never relaxes any of these rules — the greedy
seeder reads the same limits (max 2 same-subject sessions a day, max 3 teacher
sessions a day) from `hard.py`, and every candidate is still scored by the
functions in that file.

---

## Implemented and verified (constraints 1-6)

These six were first proven in `phase4_bscs_part1_ga.py`,
`phase5_multi_division_ga.py` and `phase6_full_bscs_morning_ga.py`, and were
ported to the production `constraints/hard.py` in Phase 7. Each one has its own
function (never buried inline in the fitness calculation), and each has been
proven two ways in every phase report: (a) a clean, GA-produced
timetable shows zero violations of it, and (b) the timetable is deliberately
broken in exactly the way that constraint should catch, and the check fires.

### 1. Teacher double-booking
**A teacher cannot be in two different sessions at the same day and time
slot.** If Dr. Fida Chandio is teaching Programming Fundamentals on Tuesday
at 9:20, they cannot also be teaching Applied Physics at that same time —
anywhere, not just in the same division (see constraint 6 below).
*Decided: Phase 4.*

### 2. Room double-booking
**A room cannot host two different sessions at the same day and time slot.**
If Room 01 is booked for Object Oriented Programming on Wednesday at 8:30, no
other session can also be placed in Room 01 at that same time.
*Decided: Phase 4.*

### 3. Teacher availability
**A teacher can only be scheduled on the days they've actually declared
themselves available.** Availability is an input the GA works around, not
something it's allowed to override — if a teacher says they only teach
Tuesday and Thursday, the GA can never place them on a Monday, no matter how
convenient that would be for the rest of the timetable.
*Decided: Phase 4.*

### 4. Lab session rules
**A lab session is its own separate slot from its subject's theory session,
must be placed in a room actually suited for a lab (not an ordinary
lecture room), and must never land on the same day/time as that subject's own
theory session.** For example, "Object Oriented Programming" (theory) and
"Object Oriented Programming (LAB)" are two different sessions that must sit
at two different times, and the lab one has to be in a computer lab.
*Decided: Phase 4.*
*Implementation note (Phase 7): "a room actually suited for a lab" is enforced
by construction, not by a detector — a lab session's only candidate room is its
division's own lab room, so the search can't put it anywhere else. The
`lab_session_rules` detector itself checks the remaining half: the lab never
lands on the same slot as its own subject's theory session.*

### 5. Division double-booking
**One division (a specific class/section of students — e.g. "BSCS Part-I,
Pre-Medical") cannot have two different sessions scheduled at the same
day/time**, because those are the same group of students and they can only
physically sit in one classroom at once. The one deliberate exception: if a
single session is explicitly shared by two divisions on purpose (a joint
class both groups sit together, like History-II being taught to both
Pre-Medical and Pre-Engineering Part-I students in the same room at the same
time), that is **not** treated as a violation — it's one session that just
happens to belong to two divisions at once, not two different sessions
competing for the same slot.
*Decided: Phase 4. Refined in Phase 5 to explicitly handle joint/shared
sessions once real data showed they exist.*

### 6. Cross-division teacher clash
**A teacher who teaches in more than one division (or more than one Part —
e.g. someone teaching both BSCS Part-I and BSCS Part-II) cannot be
double-booked across those divisions at the same day/time.** This isn't a
separate rule with its own function — it's a direct consequence of
constraint 1 (teacher double-booking) being checked globally across *every*
division in one combined chromosome, rather than checking each division in
isolation. Phases 5 and 6 exist specifically to prove this actually works:
Phase 5 verified it for 2 shared teachers across BSCS Part-I/Part-II, and
Phase 6 verified it for 5 shared teachers across all four BSCS Parts, each
one checked individually (clean-solution evidence + a deliberate break that
gets detected).
*Decided: Phase 4 (as a consequence of constraint 1). Explicitly verified in
Phase 5, then again at larger scale in Phase 6.*

---

## Implemented and verified (constraints 7-9)

These three were decided in the cleanup/pivot phase and implemented for the
first time in Phase 7, directly in the production `constraints/hard.py` — the
dev scripts phase4/5/6 do not check them. Each was verified the same two ways
as 1-6, again in Phase 8 on the full 8-division timetable: a clean solution
shows zero violations, and a deliberately broken one is caught by exactly that
constraint's detector.

### 7. Same-subject daily spread
**A theory subject's weekly sessions can never have more than 2 of them
scheduled on the same day.** The number of weekly sessions for a subject
comes from its credit hours in the course scheme (e.g. a 3-credit-hour
subject has exactly 3 sessions a week) — this constraint doesn't add or
remove sessions, it only limits how those sessions can be spread across the
days a division actually has class. So a 3-credit subject could be Mon+Mon+
Wed, or Mon+Wed+Fri, but never Mon+Mon+Mon.
Two things this explicitly does **not** do:
- It does not apply to lab sessions — a lab is a single separate session, not
  part of this weekly-spread count.
- It does not force a subject onto a day the division has zero classes on
  (e.g. it won't create a Friday session for a division that never meets on
  Fridays) — it only constrains how the sessions that already need to exist,
  per the course scheme, get distributed across the days that division is
  actually in session.
*Decided: this cleanup phase.*

### 8. Teacher daily load limit
**A teacher cannot be scheduled for more than 3 sessions on any single
day**, across every division they teach. Even if a teacher is available five
days a week and teaches in multiple divisions, no single day can stack more
than 3 of their sessions back to back.
*Decided: this cleanup phase.*

### 9. One subject per teacher per Part per semester
**Within one specific timetable-generation run (one Part, one semester being
scheduled), a teacher is assigned exactly one subject — never two different
subjects in that same division/semester.** For example, if Dr. Gulsher
Laghari teaches Object Oriented Programming for BSCS Part-I this semester,
they cannot also be assigned a second, different subject for that same
Part-I semester run.
This does **not** restrict the same teacher across *different* semesters
generated as separate runs — the same person can teach a different subject
when, say, Part-II's other semester is generated on its own later. This was
checked against the real data and the pattern already holds there (e.g. a
teacher can appear with one subject in a Part-I dataset and a different
subject in a Part-II dataset without conflict, because those are separate
generation runs, not the same run).
*Decided: this cleanup phase, confirmed against real data.*
*Implementation note (Phase 7): the search never changes which teacher takes
which subject — that pairing is fixed by the seeded assignments before the
search starts — so this can't be broken by placement. It is still checked, so a
bad assignment in the seed data (or a deliberate test) is caught rather than
silently scheduled.*

---

## Quick reference table

| # | Constraint | Hard? | Status | Decided |
|---|---|---|---|---|
| 1 | Teacher double-booking | Yes | Implemented & verified | Phase 4 |
| 2 | Room double-booking | Yes | Implemented & verified | Phase 4 |
| 3 | Teacher availability | Yes | Implemented & verified | Phase 4 |
| 4 | Lab session rules | Yes | Implemented & verified | Phase 4 |
| 5 | Division double-booking (joint sessions excluded) | Yes | Implemented & verified | Phase 4, refined Phase 5 |
| 6 | Cross-division teacher clash | Yes | Implemented & verified | Phase 4, verified Phase 5-6 |
| 7 | Same-subject daily spread (max 2/day, theory only) | Yes | Implemented & verified | Decided cleanup phase, built Phase 7 |
| 8 | Teacher daily load limit (max 3 sessions/day) | Yes | Implemented & verified | Decided cleanup phase, built Phase 7 |
| 9 | One subject per teacher per Part per semester run | Yes | Implemented & verified | Decided cleanup phase, built Phase 7 |
