# IMCS Scheduler — Project Audit

**Snapshot date:** 2026-09-22, at the end of Phase 9 — a general-purpose data-entry
dashboard (`/build-timetable`) so an admin can build up the course/teacher/room
assignments the GA needs for ANY program/shift/part/semester/group by hand, not just
BSCS Morning (which still gets its data from the Phase 7 seed script). On top of Phase
8.1 (lab room identity fixed to the five real labs, Lab A-E) and Phase 8 — full
8-division GA convergence. Phase 7 wired the real GA end to end (database models, seed data
from `docs/timetable.json`, the production scheduler package with all 9 hard
constraints, the `/api/v1/timetables` endpoints, a real frontend page) but the
full BSCS Part-I to Part-IV problem stalled 1-20 violations short of zero.
Phase 8 fixed that with a greedy (constructive) starting population: the full
problem now converges in 100/100 seeded runs, in under a second of search time.

This file exists so a fresh conversation (or a new person) can pick the
project up without re-reading every prior phase report. It answers: what
exists, what actually works (tested, not assumed), what's still a
docstring, and what hasn't been started.

---

## 1. Full file tree, with current state per file

State key: **real** = working code that does something; **placeholder** =
docstring only, no logic; **dev-script** = real, tested code, but standalone
— not called by the database/API/frontend.

### backend/

```
backend/
├── .env.example                          real — env template (Supabase URL, DB URLs, CORS)
├── alembic.ini                           real — no DB URL in the file itself; env.py reads it from app settings
├── alembic/
│   ├── env.py                            real — wired to app.core.config, autogenerate-ready
│   ├── script.py.mako                    real — the template new migrations are generated from
│   └── versions/
│       ├── ef3f9e008a22_..._classroom_.py   real — departments, programs, classrooms, teachers,
│       │                                       course_schemes, courses.
│       ├── 722044599067_..._lab_....py      real (Phase 7) — divisions, division_courses, lab_batches,
│       │                                       timetables, timetable_sessions.
│       ├── 2ef363712bc6_drop_division_lab_room_id_...py   real (Phase 8.1) — drops divisions.lab_room_id
│       │                                      (labs are a shared pool, not per-division)
│       └── 6546114ebf29_phase9_course_semester_....py     real (Phase 9) — courses.semester (+ backfill),
│                                              division_courses.lecture_room_id/lab_room_id,
│                                              divisions.assignments_locked_at, divisions' unique key
│                                              widened to include semester
├── requirements.txt                      real — pinned deps (fastapi, sqlalchemy, alembic, psycopg,
│                                            pdfplumber, python-docx, httpx, pytesseract, pdf2image)
├── app/
│   ├── main.py                           real — FastAPI app, mounts /api/v1, / and /health routes
│   ├── core/
│   │   ├── config.py                     real — pydantic-settings, reads backend/.env
│   │   └── security.py                   placeholder — auth/RBAC, not started
│   ├── db/
│   │   ├── base.py                       real — SQLAlchemy declarative base + TimestampMixin
│   │   ├── session.py                    real — engine/session factory, get_db dependency
│   │   ├── seed.py                       real — seeds the 3 departments + 18 programs (idempotent)
│   │   ├── seed_bscs_timetable.py        real (Phase 7, fixed Phase 8.1) — reads docs/timetable.json and
│   │   │                                    creates real Teacher / lecture Classroom / Division /
│   │   │                                    DivisionCourse rows for BSCS Part-I to Part-IV, Morning shift,
│   │   │                                    plus the five shared labs Lab A-E (idempotent); also clears the
│   │   │                                    old placeholder "Room NN (Lab)" rooms
│   │   └── rematerialize.py              real — rebuilds Course rows from a scheme's stored content
│   ├── models/
│   │   ├── program.py                    real — Department, Program, ProgramLevel enum
│   │   ├── classroom.py                  real — Classroom, ClassroomType enum
│   │   ├── teacher.py                    real — Teacher (no auth fields, by design)
│   │   ├── course.py                     real — Course (materialized from CourseScheme.content), plus
│   │   │                                    a Phase 9 `semester` column for the dashboard's course filter
│   │   ├── course_scheme.py              real — CourseScheme (JSONB content column)
│   │   ├── division.py                   real (Phase 7, extended Phase 9) — Division (now with
│   │   │                                    `assignments_locked_at`), LabBatch, DivisionCourse (now with
│   │   │                                    per-assignment `lecture_room_id`/`lab_room_id`)
│   │   └── timetable.py                  real (Phase 7) — TimetableStatus, Timetable, TimetableSession
│   ├── schemas/
│   │   ├── program.py                    real — Pydantic schemas for the programs endpoint
│   │   ├── course_scheme.py              real — scheme upload/list/detail + Phase 9 course-list/add-subject
│   │   ├── dashboard.py                  real — Pydantic schema for the stats endpoint
│   │   ├── timetable.py                  real (Phase 7) — generate/list/detail schemas
│   │   ├── teacher.py                    real (Phase 9) — TeacherCreate/TeacherRead
│   │   ├── classroom.py                  real (Phase 9) — ClassroomCreate/ClassroomRead
│   │   └── division.py                   real (Phase 9) — Division/CourseAssignment create/read/update
│   ├── api/
│   │   ├── deps.py                       real — shared DbSession dependency
│   │   └── v1/
│   │       ├── router.py                 real — mounts every endpoint router below
│   │       └── endpoints/
│   │           ├── programs.py           real — GET /api/v1/programs
│   │           ├── course_schemes.py     real — extract/save/list/detail/delete, plus Phase 9's
│   │           │                            /courses (list-by-semester, add-a-new-subject)
│   │           ├── dashboard.py          real — GET /api/v1/dashboard/stats
│   │           ├── classrooms.py         real (Phase 9) — list/create Classroom
│   │           ├── divisions.py          real (Phase 9) — create/list/get Division; list/add/edit/remove
│   │           │                            a draft DivisionCourse; live constraint-9 check; finalize
│   │           ├── teachers.py           real (Phase 9) — list/create/get Teacher
│   │           └── timetables.py         real (Phase 7) — POST /generate, GET "", GET /{id},
│   │                                        GET /{id}/export (Phase 9, Word .docx)
│   ├── services/
│   │   ├── course_scheme_service.py      real — PDF/Word text extraction (+ OCR fallback), Supabase
│   │   │                                    Storage upload/delete, lab-pairing materialization logic
│   │   ├── dashboard_service.py          real — the counts query behind the stats endpoint
│   │   └── export_service.py             real (Phase 9) — renders a saved Timetable to a .docx
│   │                                        (IMCS logo header, one weekly-grid table per division)
│   └── scheduler/                        **the GA package — see §5 "Genetic Algorithm file map" below**
│       ├── chromosome.py                 real (Phase 7, extended Phase 9) — Gene, SessionRequirement,
│       │                                    DivisionInfo, build_session_requirements now honours a
│       │                                    per-assignment pre-assigned lecture/lab room when set
│       ├── fitness.py                    real (Phase 7) — fitness_from_violations
│       ├── engine.py                     real (Phase 7, extended Phase 8) — evolve() loop, stagnation
│       │                                    detection + partial-population restarts, half-greedy /
│       │                                    half-random starting population, generate_timetable() entry point
│       ├── seeding.py                    real (Phase 8) — constructive_chromosome(): greedy clash-free
│       │                                    placement, most-constrained teachers first
│       ├── operators.py                  real (Phase 7) — tournament_select, two_point_crossover,
│       │                                    mutate_targeted (blame-carrying targeted mutation)
│       ├── constraints/
│       │   ├── hard.py                   real (Phase 7) — all 9 hard constraints, lazy Violation.describe()
│       │   └── soft.py                   placeholder — docstring only, out of scope this phase
│       └── dev_scripts/                  dev-script — reference only; deletion condition now met (see §5)
│           ├── phase4_bscs_part1_ga.py   dev-script — single-division GA, BSCS Part-I Morning
│           ├── phase5_multi_division_ga.py  dev-script — 4-division GA, BSCS Part-I + Part-II
│           └── phase6_full_bscs_morning_ga.py  dev-script — 8-division GA, full BSCS Morning shift
└── tests/                                placeholder — empty test package (no tests written yet)
```

### frontend/

```
frontend/
├── package.json / tsconfig.json / next.config.js / tailwind.config.ts / postcss.config.js   real — config
├── app/
│   ├── layout.tsx                        real — root layout, renders SiteHeader on every page
│   ├── page.tsx                          real — homepage, links to Course schemes and Stats overview
│   ├── schemes/page.tsx                  real — Course Scheme upload/list/delete flow (Phase 2-3)
│   ├── dashboard/page.tsx                real — stats overview page (Phase 3), counts only
│   └── timetables/page.tsx               real (Phase 7) — generate button + live elapsed timer, saved-
│                                            timetable list, per-division weekly detail view
├── components/
│   ├── ui/                               real — Button, Alert, ConfirmDialog, Spinner, form fields,
│   │                                        SiteHeader (now links to /timetables too)
│   ├── scheme-upload/                    real — the 4-step upload wizard + saved-scheme list
│   │                                        (upload-step, text-review-step, course-form-step,
│   │                                        preview-step, scheme-list, semester-table, step-indicator)
│   ├── dashboard/
│   │   └── stat-card.tsx                 real — the stat tile + its loading skeleton
│   └── timetables/                       real (Phase 7)
│       ├── division-schedule.tsx         real — one division's weekly schedule as a table
│       └── timetable-list.tsx            real — saved-timetable cards with converged/draft status
├── lib/
│   ├── api-client.ts                     real — fetch wrapper; API_BASE_URL now resolves to the
│   │                                        page's own host at runtime on the client (falls back to
│   │                                        localhost only during SSR) so it works over the LAN too
│   ├── schemes.ts                        real — Course Scheme types, lab-pairing helper, API calls
│   ├── scheme-text-parser.ts             real — parses the university portal's table layout for
│   │                                        the "Fill rows from extracted text" button
│   ├── dashboard.ts                      real — stats types + API call
│   ├── timetables.ts                     real (Phase 7) — generate/list/detail types + API calls
│   └── build-timetable.ts                real (Phase 9) — Teacher/Classroom/Division/CourseAssignment
│                                            types + every /teachers, /classrooms, /divisions, /courses call
└── public/imcs-logo.png                  real — the IMCS crest used in the header and homepage
```

**As of Phase 7, `frontend/timetables/` is real and wired to the GA.** The
page calls `POST /api/v1/timetables/generate`, lists saved runs via
`GET /api/v1/timetables`, and renders one run's full per-division schedule
via `GET /api/v1/timetables/{id}` — confirmed end to end in §8 below,
including from a phone over the real local network, not just localhost.

---

## 2. Phase summary

| Phase | What was built | Status |
|---|---|---|
| 0 | FastAPI + Next.js scaffold, folder structure, `/` and `/health` | Done |
| 1 | SQLAlchemy models (Department, Program, Classroom, Teacher, CourseScheme, Course), first Alembic migration, seed data, `GET /api/v1/programs` | Done |
| 2 | Course Scheme upload flow: PDF/Word text extraction with OCR fallback, Supabase Storage, 4-step wizard, list/delete | Done |
| 3 | Fixed lab pairing (a lab is `has_lab` on its theory course, not its own course), demo polish, stats overview page/endpoint | Done |
| 4 | Standalone GA, single division (BSCS Part-I Morning), real course data + real teachers, 5 hard constraints | Done (dev script only) |
| 5 | Standalone GA, 4 divisions (BSCS Part-I + Part-II, PM/PE), cross-division teacher clash proven | Done (dev script only) |
| 6 | Standalone GA, 8 divisions (full BSCS Morning, Part-I through IV), shared-room contention proven, super-linear generation growth identified as a risk | Done (dev script only) |
| This cleanup | Removed One Max scaffolding and OR-Tools/hybrid references; adopted `docs/timetable.json` as GA reference data; documented all 9 constraints in `docs/CONSTRAINTS.md`; full regression test of everything above; this audit | Done |
| 7 | Real GA integration: Division/Timetable DB models + migration, seed from `docs/timetable.json`, production scheduler package (all 9 hard constraints, lazy violation messages, stagnation detection + restarts), `/api/v1/timetables` endpoints, `/timetables` frontend page, tested end to end incl. over LAN from a phone | Done — see §4, §8 for honest results at full scale |
| 8 | Full 8-division convergence: greedy constructive seeding for half of every fresh population (Technique 1 of 3; Techniques 2-3 deliberately not needed). Full BSCS problem 100/100 converged at generation 1 | Done — see §4, §11 |
| 8.1 | Lab room identity: the department's five real labs (Lab A-E, shared by every division) replace six invented "Room NN (Lab)" rooms; labs are a shared pool the GA assigns per session; stale timetables removed. Convergence unchanged (100/100, generation 1) | Done — see §4, §12 |
| 9 | General-purpose data-entry dashboard (`/build-timetable`): real Teacher/Classroom CRUD, per-course room pre-assignment (fixes the GA's search, not just a UI nicety), a live constraint-9 warning at data-entry time, finalize-and-generate, real Word export, a dashboard clock widget | Done — see §13 |

---

## 3. Current database state

Confirmed by direct query against the live Supabase database on 2026-09-22,
after Phases 7-9 (Phase 9 added no new BSCS rows — its own test data was
created and then deleted again as part of its own testing, §13):

| Table | Row count | Populated with |
|---|---|---|
| `departments` | 3 | Computer Science, Artificial Intelligence, Mathematics |
| `programs` | 18 | All levels for all 3 departments; 3 are `is_schedulable=true` (the BS programs) |
| `classrooms` | 11 | 6 lecture rooms (Room 01-06, from `docs/timetable.json`) + the 5 real labs **Lab A, Lab B, Lab C, Lab D, Lab E** (type `lab`, shared by every division). Phase 9 added `POST /api/v1/classrooms` to create more of either type through the dashboard, but none were kept in this snapshot |
| `teachers` | 29 | Real full names, `availability.days` derived from actual teaching days in the JSON. Phase 9 added `POST /api/v1/teachers` to add more through the dashboard |
| `course_schemes` | 2 (1 active) | The original BSCS 2024 upload (active, 45 courses, `applies_to_part` not yet added — that's Phase 10 scope), plus a synthetic `scheme_year=2026, is_active=false` scheme holding real-timetable-derived Course rows |
| `courses` | 68 | 45 from the 2024 scheme (`semester` backfilled from the scheme's own semester grouping, Phase 9) + 23 from the synthetic scheme (`semester` left null — see §4/§9 history). Phase 9 added `POST /api/v1/courses` ("add a new subject") for programs with no upload yet |
| `divisions` | 8 | BSCS Part-I to Part-IV, Morning shift, PM/PE split each. Phase 9's `POST /api/v1/divisions` can create more for any program/part/semester/shift/group (its own test divisions for BS(AI) and Mathematics were deleted after testing, §13) |
| `division_courses` | 43 | Real course/teacher assignments per division, incl. joint PM/PE subjects. Two columns added in Phase 9, both null for all 43 existing rows (BSCS still relies on `Division.home_room_id` and the shared lab pool, unchanged): `lecture_room_id` (a per-course room pre-assignment) and `lab_room_id` (a per-course fixed lab) |
| `timetables` / `timetable_sessions` | 4 / 528 | Four independently-generated full 8-division BSCS runs, all converged (132 sessions each); none from Phase 9 testing remain |

`Division.assignments_locked_at` (Phase 9) is null on all 8 BSCS divisions —
they were seeded directly, never built through the `/build-timetable` flow,
so nothing has ever locked them.

---

## 4. Genetic Algorithm — current state

### What's proven (Phase 7, through the real production code and real API)
- The production chromosome/constraint/operator/engine package
  (`app/scheduler/`) reproduces Phase 4's single-division result: calling
  the real `POST /api/v1/timetables/generate` with BSCS Part-I's two real
  divisions (42 sessions) **converged in 74-84 generations, 3.0-3.2 seconds,
  fitness 0.0, zero conflicts** — run twice, both through the actual HTTP
  endpoint against the actual database, not a script.
- All 9 hard constraints from `docs/CONSTRAINTS.md` are implemented and
  individually verified, including constraints 7, 8, 9 which did not exist
  before this phase — each was deliberately broken and confirmed to be
  detected (see §8), not just "no violations found" on a clean run.
- Lazy violation messages and stagnation detection with partial-population
  restarts (both flagged as the top two fragility risks in the previous
  audit) are now implemented (`Violation.describe()` builds nothing until
  asked; `engine.evolve()` restarts part of the population after 400
  generations without improvement, up to `MAX_RESTARTS` times).

### Phase 8 result — the full 8-division problem now converges

The Phase 7 problem: the real engine on all 8 BSCS Morning divisions (132
sessions, all 9 constraints) never reached zero violations. Phase 8 tried
Technique 1 (greedy constructive seeding) first, it worked, and Techniques 2
(two-stage decomposition) and 3 (honest-partial-result fallback) were
deliberately not built. Full runs are in §11; the headline comparison:

| Run | Setup | Result |
|---|---|---|
| Phase 7 baseline | seed=1, 3000 gens, 3 restarts | did not converge, 7 violations left, 645.7s |
| Phase 7 baseline | seed=7, 8000 gens, 3 restarts | did not converge, 20 violations left, 381.0s |
| Phase 7 baseline | seed=7, 8000 gens, 8 restarts | did not converge, 1 violation left (`teacher_outside_availability`), 655.8s |
| **Phase 8** | seeds 1,2,3,4,5,7 (same engine, same settings, 50% constructive) | **6/6 converged at generation 1, 0.2-0.3s each** |
| **Phase 8** | 100 seeds (1000-1099), full problem | **100/100 converged, all at generation 1, mean 0.35s, max 0.61s, 100 distinct timetables** |

Why it works: the load analysis (§11) showed several teachers with exactly as
many sessions as their available days can hold (6 sessions on 2 days at the
3/day cap), a near-zero-slack packing that random repair almost never
finishes. The greedy placer (`scheduler/seeding.py`) places the least-flexible
teachers first and takes only clash-free slots. On its own it produces a
violation-free timetable 143 times in 200 tries (a random individual: 0 in 200,
mean 137.6 violations), so half a starting population contains a clean answer
immediately.

The smaller cases did not regress: BSCS Part-I (2 divisions) and the
Phase-5-sized Part-I+II (4 divisions, 78 sessions) both converge 100/100 at
generation 1. With seeding switched off (`constructive_fraction=0.0`) the
evolutionary loop is bit-for-bit unchanged: seed 1 on Part-I still takes 84
generations, exactly its Phase 7 number, and all 8 tried seeds converge.

### What's still fragile — read this before trusting a timetable

- **Resolved in Phase 8.1: lab rooms.** Phase 8 found that the seed modelled
  "Room 03" and a placeholder "Room 03 (Lab)" as two rooms, so 91 of 100
  generated timetables had a lab and a same-numbered lecture room in use at
  the same time (a clash, had they been one room). The real labs are five shared rooms, Lab A-E; the placeholders are
  gone and every lab session now chooses among the real five, so the room-clash
  rule compares real identities. **What is still only inferred, not sourced:**
  `docs/timetable.json` never says which physical lab a session uses (it writes
  "Lab / Room No: 01".."06", numbered like the lecture rooms), so the lab shown
  for any generated session is the GA's choice, not a fact from the department's
  timetable. Any of the five is treated as interchangeable (same capacity and
  equipment) — that came from the department and hasn't been tested against a
  session that needs a particular lab.
- **The evolutionary loop is no longer exercised on this data.** Everything
  converges at generation 1, from the greedy seeder alone, so the crossover /
  mutation / restart machinery is now a safety net rather than the workhorse.
  It is intact (see above) but only proven to work at these sizes.
- **The seeder repeats the constraint rules.** `seeding.py` re-states which
  slots are clean (teacher/room/division busy, daily caps) instead of asking
  `hard.py`. It imports the two cap constants, and every candidate is still
  scored by `hard.py`, so a stale seeder can only make convergence worse, never
  let a violation through — but a new constraint must be added in both places
  to keep the fast path fast.
- **Greedy seeding is proven on one dataset.** BS(AI), Evening shift or
  tighter real availability could be much harder; nothing here says the seeder
  would still hit zero.
- **The not-converged path is honest but thin.** If a run does not converge the
  API still saves it as `draft` with `converged=false` and a `conflict_list`,
  and the frontend shows a warning with the first 10 conflicts, never a
  success. But (a) messages name raw ids ("Teacher 31", "Course 428"), not
  people and subjects, and (b) there's no hard time budget — the worst case is
  4000 generations plus up to 8 restarts (~10+ minutes measured in Phase 7).
- **No infeasibility pre-check.** The engine can't tell "hard to solve" from
  "impossible"; feasibility was checked by hand in Phase 7.
- **Real declared availability still hasn't been tested.** Availability is
  still derived from days a teacher appears in the real published timetable, so
  the problem is guaranteed solvable — real availability could be tighter.
- **The API is slow because the database is remote, not because of the GA.**
  A generate call spends ~0.13s searching and 5-10s saving 132 rows to Supabase;
  the list endpoint takes ~12s once ~10 timetables exist (extra queries per
  timetable). Not touched in Phase 8.

### The 9 constraints (full detail in `docs/CONSTRAINTS.md`)

| # | Constraint | Implemented? |
|---|---|---|
| 1 | Teacher double-booking | Yes (Phase 4, ported to production Phase 7) |
| 2 | Room double-booking | Yes (Phase 4, ported to production Phase 7) |
| 3 | Teacher availability | Yes (Phase 4, ported to production Phase 7) |
| 4 | Lab session rules (separate slot, lab room, no self-clash) | Yes (Phase 4, ported Phase 7) |
| 5 | Division double-booking (joint sessions excluded) | Yes (Phase 4/5, ported Phase 7) |
| 6 | Cross-division teacher clash | Yes (Phase 4-6, ported Phase 7) |
| 7 | Same-subject daily spread (max 2 sessions/day, theory only) | **Yes — new in Phase 7** |
| 8 | Teacher daily load limit (max 3 sessions/day) | **Yes — new in Phase 7** |
| 9 | One subject per teacher per division | **Yes — new in Phase 7** |

---

## 5. Genetic Algorithm file map

Every file that currently contains GA-related code lives under
`backend/app/scheduler/`. As of Phase 7 the production package is real and
is what the API actually calls — the dev scripts are kept alongside it as
reference only, not as a second live implementation.

**The production package** (`chromosome.py`, `fitness.py`, `engine.py`,
`operators.py`, `constraints/hard.py`) — real, tested, and what
`POST /api/v1/timetables/generate` actually runs:

- **`chromosome.py`** — `Gene` (room, day, slot_index — course/teacher fixed
  per gene position, matching the dev scripts' original design),
  `SessionRequirement`, `DivisionInfo`, and DB-reading functions
  (`load_divisions`, `build_session_requirements`) that replace the dev
  scripts' hardcoded Python data with real `Division`/`DivisionCourse` rows.
- **`constraints/hard.py`** — all 9 constraints. 1-6 are the same logic as
  the dev scripts, ported to real DB-shaped data; 7, 8, 9 are new. Violation
  messages are lazy (`Violation` carries a raw context dict; `.describe()`
  builds the string only when asked), fixing the previous audit's flagged
  hot-path cost.
- **`fitness.py`** / **`operators.py`** — fitness derived from an
  already-computed violation set (never recomputed), tournament selection,
  two-point crossover, and blame-carrying targeted mutation — the Phase 5-6
  mutation strategy, not Phase 4's uniform mutation.
- **`engine.py`** — the generation loop, with stagnation detection and
  partial-population restarts, a starting population that is half greedy /
  half random (`constructive_fraction`, Phase 8; `fresh_individuals()` builds it
  and is also used to refill after a restart), and `generate_timetable()`, the
  real entry point the API calls.
- **`seeding.py`** (Phase 8) — `constructive_chromosome()`: places sessions one
  at a time, teachers with the fewest available days first, taking only slots
  that clash with nothing already placed and falling back to a random
  placement for a session with no clean slot. Greedy, not guaranteed clean —
  it just has to start the population close.

**The dev scripts** (`scheduler/dev_scripts/`) — three real, tested,
**standalone** Python files, kept as reference only. Production now does
everything they did and more: it converges on the full 8-division problem
(100/100, §4) where phase6's own result was 10/10, and it checks 9 constraints
where they checked 5-6. The condition Phase 7 set for deleting them ("once a
production run matches or beats their convergence at the same scale") is met.
They are still in the repo only because deleting them also means editing the
references in `PROJECT_ARCHITECTURE.md` and `CONSTRAINTS.md`; safe to delete.

- **`phase4_bscs_part1_ga.py`** — one division (BSCS Part-I Morning), 5 hard
  constraints, uniform mutation.
- **`phase5_multi_division_ga.py`** — 4 divisions, real teacher data,
  blame-carrying targeted mutation introduced here.
- **`phase6_full_bscs_morning_ga.py`** — all 8 BSCS Morning divisions.

Each dev script is fully self-contained (no shared imports between them or
with the production package). **They are not imported by, called from, or in any way connected to
the database, the API layer, or the frontend** — that connection now exists
only through the production package.

---

## 6. What is NOT yet started

- **Authentication** — faculty-only Google sign-in via Supabase Auth is
  planned (per `docs/PROJECT_ARCHITECTURE.md` §13) but not started; no auth
  fields exist on any model, by design.
- **PDF export of a generated timetable** — Phase 9 built Word (.docx) only,
  per that phase's explicit scope; `export_service.py` has no PDF path.
- **The live/soft-constraint dashboard** (teacher/room availability derived
  from real generated timetables) — the current stats page is counts-only
  and explicitly does not claim to show availability (per Phase 3's scope
  correction).
- **Soft constraints** — `constraints/soft.py` is still a docstring-only
  placeholder; only hard constraints exist anywhere in the GA work so far,
  by explicit scope for this phase.
- **BS(AI) and Evening-shift scheduling** — the *tool* to enter their data
  now exists (`/build-timetable`, Phase 9, tested against real BS(AI) and
  Mathematics divisions), but no one has entered their real course/teacher
  data yet, and Evening shift specifically still has no real
  teacher-availability data behind it at all — Phase 9 built the general
  mechanism, it did not fill either of these in, by explicit scope.
- **A defined time budget and readable conflict reporting for a run that
  doesn't converge** (this was "Technique 3" of Phase 8, deliberately not
  built because seeding made it unnecessary on current data). Today a
  non-converged run is saved honestly as a draft with its conflicts listed, but
  the conflicts are raw ids and the search can run ~10 minutes before giving
  up. Worth building before any harder dataset (BS(AI), Evening) is attempted.
- **`LabBatch` rows** — the model exists (`app/models/division.py`) but the
  Phase 7 seed does not populate it; lab sessions are scheduled per-division
  as a whole, not split into sub-batches.
- **Reviewing/publishing a draft timetable** — every generated `Timetable`
  is created with `status="draft"`; there's no UI or endpoint yet to move
  one to `published`, edit it, or compare versions. Phase 9's "Finalize"
  locks the *assignment list*, not the resulting timetable's status.
- **Browsing/editing Teachers and Classrooms after creation** — Phase 9
  added real `POST`/`GET` endpoints and inline quick-create from within
  `/build-timetable`, but there's still no standalone admin page to list,
  edit, or delete a Teacher or Classroom on its own.
- **Un-finalizing a division** — once `/build-timetable` locks a division's
  assignment list, nothing can unlock it again; fixing a mistake in a
  finalized division needs direct database access. Not built, not
  requested this phase.

---

## 7. Confirmation: Parts 1-4 completed

**Part 1 — One Max / N-Queens / GA-learning-demo remnants removed.**
Repository-wide search found exactly one such file and two doc mentions,
all now gone:
- Deleted `backend/app/scheduler/onemax_sanity_check.py` (docstring-only
  placeholder, never actually implemented).
- Rewrote the file-tree entry and §6.4 in `docs/PROJECT_ARCHITECTURE.md`
  that referenced it.
- Rewrote the One Max bullet in `docs/claude_instructions.md`.
- No N-Queens or "hello world" GA demo references were found anywhere.
- `phase4_bscs_part1_ga.py`, `phase5_multi_division_ga.py` and
  `phase6_full_bscs_morning_ga.py` were confirmed untouched by this removal
  (only later got an unrelated one-line docstring note, per Part 3).

**Part 2 — OR-Tools / CP-SAT / hybrid references removed.** Exactly one
mention existed, in `docs/PROJECT_ARCHITECTURE.md` §12 (Out of Scope),
describing "Hybrid GA + OR-Tools CP-SAT" as a possible future upgrade. It's
removed, not reworded as a still-open option. An explicit permanent-decision
statement was added at the top of §6 ("Genetic Algorithm is the sole,
permanent scheduling approach... no OR-Tools, no CP-SAT, no
constraint-programming solver, and no 'GA now, hybridize later' plan") and
the §2 Tech Stack row was strengthened to match, so the decision is
unambiguous wherever a reader in the doc encounters it.

**Part 3 — JSON adopted as the GA data source.** `docs/timetable.json` is in
place (confirmed: valid JSON, covers BS(CS) Part-I-IV and BS(AI) Part-I-III,
193 schedule rows, full teacher names throughout, no initials).
`docs/PROJECT_ARCHITECTURE.md` §13 now states it's the reference data source
for GA development going forward, replacing the manual PDF-extraction
approach, and is explicit that this doesn't touch the separate Course Scheme
upload feature. Each of the three dev scripts got one added docstring
paragraph pointing to it; no logic in any of them changed (confirmed by
re-running all three in §8 below and getting byte-identical generation
counts to their original phase reports).

**Part 4 — `docs/CONSTRAINTS.md` created.** Documents all 9 constraints,
marked as a living document, split into "implemented and verified" (1-6)
and "decided but not yet implemented" (7-9), each with a plain-language
explanation and the phase/decision it came from.

---

## 8. Full testing — commands run and actual results

All commands below were actually executed against the live Supabase
database and a locally running backend/frontend on 2026-09-18, after Parts
1-4 were committed. Nothing in this table is assumed.

| Step | Command / Action | Expected Output | Actual Result |
|---|---|---|---|
| 1 | `uvicorn app.main:app --port 8000` | Starts, no errors | Started cleanly |
| 2 | `curl http://127.0.0.1:8000/` | HTTP 200 | **HTTP 200** |
| 3 | `curl http://127.0.0.1:8000/health` | `{"status":"ok","environment":"development"}` | **Exact match, HTTP 200** |
| 4 | Query `departments`, `programs`, `classrooms`, `teachers`, `course_schemes`, `courses` row counts directly | Matches Phase 1-3 end state | **3 / 18 / 0 / 0 / 1 / 45** — matches |
| 5 | `curl http://127.0.0.1:8000/api/v1/course-schemes` (list) | One active scheme, BSCS 2024 | **HTTP 200**, `id:6, program_name:"BS Computer Science", scheme_year:2024, course_count:45, lab_course_count:20, is_active:true` |
| 6 | `curl http://127.0.0.1:8000/api/v1/course-schemes/6` (detail) | Full scheme with paired semesters | **HTTP 200**, 8 semesters, first course `CSPF302` shows `has_lab:true, lab_credit_hours:1` — lab pairing confirmed intact |
| 7 | `curl` the scheme's `file_url` directly | The stored PDF is reachable | **HTTP 200** |
| 8 | `curl http://127.0.0.1:8000/api/v1/dashboard/stats` | Counts matching step 4 | **HTTP 200**, `departments:3, programs:{total:18,schedulable:3,not_yet_schedulable:15}, course_schemes:1, courses:{total:45,with_lab:20}, classrooms:0, teachers:0` — all match |
| 9 | `python -m app.scheduler.dev_scripts.phase4_bscs_part1_ga --runs 3` | Converges, same generation counts as the original Phase 4 report (seeds 2/3/4 → 41/48/34) | **Converged 3/3. Seeds 2/3/4 → 41/48/34 generations — identical to the original report**, proving the cleanup changed no logic |
| 10 | `python -m app.scheduler.dev_scripts.phase5_multi_division_ga --runs 3` | Converges, same counts as Phase 5 (seeds 101/102/103 → 106/114/99) | **Converged 3/3. 106/114/99 — identical** |
| 11 | `python -m app.scheduler.dev_scripts.phase6_full_bscs_morning_ga --runs 2 --generations 3000` | Converges, same counts as Phase 6 (seeds 201/202 → 880/1749) | **Converged 2/2. 880/1749 — identical** |
| 12 | `npm run dev` (frontend) | Starts, no errors | Started cleanly |
| 13 | Load `/`, `/schemes`, `/dashboard` at 1280x900 (desktop) | HTTP 200, no console errors, no horizontal overflow | **All 3 pages: HTTP 200, 0 console errors, no overflow** |
| 14 | Load `/`, `/schemes`, `/dashboard` at 390x844 (mobile) | HTTP 200, no console errors, no horizontal overflow | **All 3 pages: HTTP 200, 0 console errors, no overflow** |
| 15 | Screenshot `/dashboard` after data loads | Six stat cards showing 3/18/1/45/0/0, plus a "BS Computer Science, Scheme year 2024" breakdown row | **Confirmed visually** — matches step 8's numbers exactly |

**Nothing was found broken by this cleanup.** Steps 9-11 in particular are
the important regression check: because they reproduce the *exact* original
generation counts from the Phase 4/5/6 reports (not just "still converges",
but the identical number for the identical seed), they prove the docstring
note added to each script in Part 3 changed nothing about how the GA
actually runs.

---

## 9. Open questions and ambiguities carried forward

These are unresolved from earlier phases. None of them block current work,
but none of them should be silently assumed away either — they need a
department/supervisor answer at some point.

- **Dr./Mr. title mismatch for Abdul Rehman Nangraj** (Phase 5-6): the
  Part-I sheet calls him "Dr.", the Part-II sheet calls him "Mr." Treated as
  the same person in the dev scripts; not confirmed with the department.
- **`A.P` in the BSCS Part-IV timetable is undefined** (Phase 6): the
  Part-IV legend defines `S.P = Speech Processing`, which never appears in
  the grid, while `A.P` appears in the grid but isn't in the legend. Most
  likely `A.P` *is* Speech Processing under a different abbreviation, but
  this was never assumed — it's carried in the Phase 6 data as
  "undefined in the Part-IV legend."
- **`R.K` teaching E.C(PM) on Part-IV isn't in the Part-IV legend** (Phase
  6): resolved to Mr. Rajesh Kumar by cross-referencing the Part-III
  legend, not confirmed independently.
- **Lab rooms were an assumption in Phases 4-6** — superseded by Phase 8.1: the labs are the five real
  rooms Lab A-E (see the lab-identity bullet below).
- **Two people with nearly identical surnames on different sheets** (Phase
  6): "Dr. Hameedullah Bhutto" (Part-I) and "Mr. Hammad Bhutto" (Part-III)
  are different people who share initials (`H.B`) and a surname — the kind
  of collision the project's own "never resolve by initials" rule exists to
  prevent, and a reminder of why `docs/timetable.json`'s full-name
  resolution matters.
- **Whether Mathematics has a PM/PE split from Part-II** (open since Phase
  1, `docs/PROJECT_ARCHITECTURE.md` §11.1) — still unconfirmed with the
  department.
- **Official Course Scheme documents vs. what's actually taught** (open
  since Phase 1, §11.2) — subjects like IOT, Mathematics-II and UHQ-II show
  up in real timetables but not in the matching official scheme document.
  Not clarified with the supervisor yet.
- **BSCS 2022 & 2025 schemes, and all BSAI/Math scheme years, are still to
  be collected** (open since Phase 1, §11.3) — only BSCS 2024 exists in the
  database.
- **Which non-BS levels will eventually need real scheduling** (open since
  Phase 1, §11.4) — Master/M.Phil/Ph.D/M.Sc./PGD are modeled and listed but
  deliberately not scheduled; no decision yet on if/when that changes.
- **Deleting and re-uploading a Course Scheme leaves the old PDF in Supabase
  Storage** (noted in Phase 3) — nothing currently cleans up an orphaned
  stored file when a scheme is replaced. Minor, not urgent, but real.
- **Lab identity is only partly resolved** (Phase 8.1, replaces two earlier
  lab bullets). Resolved: the department has exactly five labs, Lab A-E, shared
  by all BSCS Parts, and they are separate from the lecture rooms — the old
  "is Room 03 the same room as its lab?" question no longer applies. Still open:
  which lab each real session uses. `docs/timetable.json` doesn't say, so it
  can't be reproduced or checked; the real schedule needs at most 2 labs at
  once, so five is plenty, but a real lab assignment (if the department has
  one) should replace the GA's choice before timetables are used for booking.

---

## 10. Phase 7 testing — commands run and actual results

All commands below were actually executed on 2026-09-19 against the live
Supabase database and locally running backend/frontend. Nothing in this
table is assumed.

### Migration, seed, and scheduler correctness

| Step | Command | Expected | Actual Result |
|---|---|---|---|
| 1 | `alembic upgrade head` | Creates divisions, division_courses, lab_batches, timetables, timetable_sessions | **Succeeded** — all 5 tables confirmed present |
| 2 | `alembic downgrade -1` then `alembic upgrade head` | Round-trips cleanly, including dropping/recreating the `timetable_status` enum | **Succeeded**, no errors either direction |
| 3 | `python -m app.db.seed_bscs_timetable`, run twice | Idempotent — identical row counts both runs | **Identical both runs**: divisions 8, division_courses 43, teachers 29, classrooms 12, courses 23 (synthetic scheme) |
| 4 | Direct DB query: full row counts | Matches §3 | **8 / 43 / 29 / 12 / 68 total courses / 2 course_schemes / 2 timetables / 84 timetable_sessions** — matches |
| 5 | `POST /api/v1/timetables/generate {"division_ids":[1,2]}` (BSCS Part-I, 42 sessions) | Converges in a reasonable time | **Converged, 74 generations, 3.03s, fitness 0.0, 0 conflicts** (run twice: 74 gen/3.03s and 84 gen/3.23s) |
| 6 | `engine.evolve()` direct call, all 8 BSCS divisions (132 sessions), seed=7, `max_generations=8000`, `MAX_RESTARTS=8` | Best-effort result, reported honestly whether it converges or not | **Did not converge** — stagnated at generation 6333, 1 remaining violation (`teacher_outside_availability`), 655.8s, 8/8 restarts used. Down from 7 and 20 violations in earlier lower-restart-budget runs on the same/different seeds — see §4 |
| 7 | `verify_constraints.py` — deliberately break constraint 7 (3 same-course sessions on one day) | `same_subject_daily_spread` fires | **DETECTED**: "Course 428 has 3 sessions on Thu for division 1 (max 2)." (plus expected room/division double-booking side effects of the forced placement) |
| 8 | `verify_constraints.py` — deliberately pile 6 of one teacher's sessions onto one day | `teacher_daily_load` fires | **DETECTED**: "Teacher 34 has 5 sessions on Tue (max 3)." |
| 9 | `verify_constraints.py` — reassign a division's course to a teacher who already teaches another course in that division | `one_subject_per_teacher_per_division` fires | **DETECTED**: "Teacher 31 is assigned more than one subject ((428, 430)) in division 1." |
| 10 | `GET /api/v1/timetables/9999` (nonexistent) | 404 with a clear message | **HTTP 404**, `{"detail":"Timetable 9999 does not exist."}` |
| 11 | `POST /generate {"division_ids":[9999]}` (nonexistent division) | 400 with a clear message | **HTTP 400**, `{"detail":"Division id(s) not found: [9999]"}` |
| 12 | `GET /api/v1/timetables` (list) | Both saved runs, newest first | **HTTP 200**, both runs listed with correct session/generation counts |
| 13 | `GET /api/v1/timetables/2` (detail) | Grouped by division → day → time | **HTTP 200**, 2 divisions, sessions correctly grouped and sorted by start time |
| 14 | `ruff check` on every Phase 7 backend file | No errors | **All checks passed** (17 initial errors — line length, unused imports — all fixed) |
| 15 | AST comment audit across 12 backend files (45 functions) | Every function has a body-first-line comment | **44/45 had one; 1 missing (`_all_checks` in `hard.py`) found and fixed** |
| 16 | `npm run build` (production build) | Compiles clean, no TypeScript errors | **Succeeded** — `/timetables` included in the route list, 0 TypeScript errors |

**Spot-check against real data**: the converged BSCS Part-I result (step 5)
was checked against `docs/timetable.json` by inspection of the rendered
detail view (§10 desktop table, step D3) — real teacher names (Dr. Gulsher
Laghari, Ms. Madhia Khemtio, Dr. Abdul Rehman Nangraj, etc.), real subjects
(DLD, OOP, IOT, History-II, Ethics), real joint-session markers on
History-II and Ethics, and lab sessions correctly tagged and room-paired.

### Desktop manual testing (1280×900, headless Edge via Puppeteer + curl)

| Step | Action | Expected | Actual Result |
|---|---|---|---|
| D1 | Load `/timetables` | HTTP 200, list of 2 saved timetables, 0 console errors, no horizontal overflow | **HTTP 200, 0 console errors, no overflow** — both saved runs shown with correct status badges |
| D2 | Click "View" on a converged run | Detail view loads, grouped by division/day | **Loaded correctly** — 2 division tables, days in order, times sorted, joint sessions and Lab badges rendered |
| D3 | Visual spot-check of rendered schedule | Matches real course/teacher/room data | **Confirmed** — see screenshot; e.g. Mon 08:30 "History-II (joint session)" taught by Ms. Asma Mughal in Room 01 for both PM and PE, matching the JSON's joint-subject handling |
| D4 | `curl -X POST .../generate` (real generation, not a mock) | Real GA runs, returns a real result | **Confirmed real** — timing (3.0-3.2s), generation counts (74/84), and fitness (0.0) vary run to run, consistent with a real stochastic search, not a fixture |
| D5 | Error paths (steps 10-11 above) | Clean 4xx with readable messages, no 500s | **Confirmed**, no unhandled exceptions |

### Mobile manual testing — real local network via phone hotspot

Laptop connects to the phone's hotspot; commands run to confirm the setup:

```
ipconfig   →  Wireless LAN adapter Wi-Fi: IPv4 Address. . . : 172.20.10.14
```

Backend started with `uvicorn app.main:app --host 0.0.0.0 --port 8000`
(confirmed: `Uvicorn running on http://0.0.0.0:8000`). Frontend started with
`next dev -H 0.0.0.0 -p 3000` (confirmed: `Network: http://0.0.0.0:3000`).
`CORS_ORIGINS` in `backend/.env` updated to include
`http://172.20.10.14:3000` so the phone's browser isn't blocked by CORS.
`frontend/lib/api-client.ts`'s `API_BASE_URL` changed from a hardcoded
`http://localhost:8000` to resolving from `window.location.hostname` at
runtime on the client, so a phone loading the page from
`http://172.20.10.14:3000` calls the backend at `172.20.10.14:8000`
automatically instead of trying to reach itself.

Phone URL given: **`http://172.20.10.14:3000/timetables`**

| Step | Action | Expected | Actual Result |
|---|---|---|---|
| M1 | Open `http://172.20.10.14:3000/timetables` on the phone browser | Page loads | **Loaded** — header, generate button, and layout rendered |
| M2 | List of saved timetables | Loads the 2 saved runs | **Stuck on "Loading generated timetables…" indefinitely** |

**Root cause found**: the laptop's Wi-Fi (the phone's hotspot) is
classified by Windows as a **Public** network, and no inbound firewall rule
existed for ports 3000 or 8000 (`Get-NetFirewallRule` confirmed zero
matching rules). The frontend page itself loaded because the initial page
request/HTML is a normal HTTP response the OS didn't block in the same way,
but the phone's `fetch()` call to port 8000 (and potentially repeat
connections to 3000 for API routes) was very likely silently dropped by
Windows Firewall before reaching the Python process — this reproduces the
exact symptom observed (page renders, list request never resolves).

**Fix applied, not yet re-verified on the device**: since adding firewall
rules requires administrator privileges this session doesn't have, the
user was given the exact elevated-PowerShell commands to run:
```powershell
New-NetFirewallRule -DisplayName "IMCS Scheduler Frontend 3000" -Direction Inbound -Protocol TCP -LocalPort 3000 -Action Allow -Profile Any
New-NetFirewallRule -DisplayName "IMCS Scheduler Backend 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Any
```
The user has not yet re-tested on the physical phone after applying this
fix (they asked to defer that and have this report proceed without it).
**This is reported honestly as an open item, not glossed over**: the
LAN wiring (dynamic API URL, CORS origin, `0.0.0.0` binding) is confirmed
correct by direct `curl` calls to `172.20.10.14:8000` and
`172.20.10.14:3000` from the same machine (200 OK, correct CORS headers —
see step D-equivalent checks above), and by a real Windows Firewall
diagnosis explaining the one observed failure — but a live phone-browser
confirmation after the firewall fix is still outstanding.

---

## 11. Phase 8 testing — commands run and actual results

All of this was run on 2026-09-19 against the live Supabase database. "Engine
run" means `engine.evolve()` called directly on the real requirements loaded
from the database (the same code the API calls, without the HTTP/save step, so
many seeds can run in parallel). "API run" means a real HTTP call.

### Why the problem was hard (load analysis, before changing anything)

`inspect_load` over the 132 real sessions: three teachers (Dr. Hira Fatima,
Mr. Kamran Brohi, Prof. Dr. Ayaz Keerio) have exactly 6 sessions on 2
available days, and the daily cap is 3 — so each must get exactly 3 on both
days, zero slack. Several others (Prof. Dr. Fida Chandio 5 on 2 days; a dozen
with 4 on 2 days) are nearly as tight. Random repair almost never finishes a
packing like that, which is why Phase 7 stalled 1 violation short.

### Self-test results

| # | What was run | Result |
|---|---|---|
| 1 | Seeder sanity: 200 individuals each, random vs constructive, full problem, count violations | random: mean **137.6**, min 106, **0/200 clean**. constructive: mean **0.7**, max 6, **143/200 clean** |
| 2 | **Technique 1, engine run x6**, full 8-division, seeds 1,2,3,4,5,7, `max_generations=8000`, restarts 8 (Phase 7 values unchanged), `constructive_fraction=0.5` | seed 1: gens 1, 0.2s, **0 violations**. seed 2: 1, 0.3s, 0. seed 3: 1, 0.2s, 0. seed 4: 1, 0.3s, 0. seed 5: 1, 0.2s, 0. seed 7: 1, 0.3s, 0. **6/6 converged**, 0 restarts |
| 3 | Same setup vs the Phase 7 baseline (§4) | baseline: 7 violations/645.7s, 20/381.0s, 1/655.8s, **never zero**. Phase 8: **0 violations in 0.2-0.3s, every time** |
| 4 | 100 seeds (1000-1099), full 8-division | **100/100 converged, all at generation 1**, mean 0.35s, max 0.61s, **100/100 distinct timetables** |
| 5 | 100 seeds, 4-division Part-I+II (78 sessions, Phase-5-sized) | 100/100 converged, generation 1, mean 0.22s |
| 6 | 100 seeds, 2-division Part-I (42 sessions) | 100/100 converged, generation 1, mean 0.12s |
| 7 | **2-division regression via the real API**, 5 seeds | all 5: converged, generation 1, 0.04-0.10s (Phase 7: 74-84 generations, ~3s) |
| 8 | Evolutionary loop untouched? `constructive_fraction=0.0` (old all-random start), 2-division, seeds 1-8 | all 8 converge: 84, 124, 161, 47, 84, 465, 41, 52 generations. **Seed 1 = 84, identical to its Phase 7 number** |
| 9 | Deliberately break each of the **9 constraints** on a converged full 8-division timetable (`p8_verify_all9.py`) | **all 9 detectors fire**: teacher double-booked, room double-booked, teacher availability, lab-on-own-theory, division double-booked, cross-division teacher clash (divisions 1 vs 3), same-subject spread ("Course 428 has 3 sessions on Thu ... max 2"), teacher daily load ("Teacher 40 has 5 sessions on Fri, max 3"), one-subject-per-teacher |
| 10 | **Independent check of saved timetable #7** — reads the 132 `timetable_sessions` rows and re-checks with its own code (no scheduler imports) | teacher/room/division double-booking 0, teacher >3/day 0, same subject >2/day 0, availability OK, labs in lab rooms OK, no lab on its own theory slot. **All 59 (part, section, subject, lab?) groups match `docs/timetable.json` in session count and teacher — 0 mismatches** |
| 11 | Negative test of #10 (corrupt the loaded rows in memory) | flags availability, teacher/room/division double-booking and a missing session vs the JSON — 5 problems reported, so a clean pass in #10 is meaningful |
| 12 | `ruff check app/scheduler` (F,E,W,UP,SIM,B, line length 125); `npx tsc --noEmit` | both clean |
| 13 | Lecture-room vs lab-room identity check (found while testing) | real timetable: **0** same-physical-room overlaps; GA timetables: **91/100** contain >=1 (159 total) — see §4/§9. If enforced, 20/20 still converge at generation 1 (scratch test only, not committed) |

### Desktop manual testing (headless Edge, 1280x900, plus curl)

| Step | Command / Action | Expected | Actual |
|---|---|---|---|
| D1 | `uvicorn app.main:app --host 0.0.0.0 --port 8000` | Starts | `Uvicorn running on http://0.0.0.0:8000` |
| D2 | `npm run dev -- -H 0.0.0.0 -p 3000` | Starts on 3000 | **Failed: port 3000 is held by an unrelated project's Node process (`Bin-Khalid-Dairy-Farm-V2`), left untouched.** Used port **3001** instead (`Network: http://0.0.0.0:3001`), added its origins to the gitignored `backend/.env` CORS list |
| D3 | `curl -X POST http://localhost:8000/api/v1/timetables/generate -H "Content-Type: application/json" -d '{}'` (default = all 8 BSCS divisions, through the real API) | 201, converged, 132 sessions, no conflicts | **HTTP 201**, `timetable_id:7, converged:true, stagnated:false, fitness_score:0.0, generation_count:1, wall_seconds:0.129, session_count:132, conflict_list:[]` (whole HTTP call 9.0s — nearly all of it remote-database inserts) |
| D4 | `curl http://localhost:8000/api/v1/timetables/7` | Grouped by division -> day -> time | **HTTP 200**, 8 divisions (Part-I PE 21, PM 24; Part-II 18/18; Part-III 18/18; Part-IV 9/9 — 135 rows because 3 joint PM/PE sessions show in both groups), days in Mon-Fri order |
| D5 | `curl .../timetables/9999`; `curl -X POST .../generate -d '{"division_ids":[9999]}'`; `-d '{"population_size":"lots"}'` | Clean 4xx with a readable reason | **404** "Timetable 9999 does not exist."; **400** "Division id(s) not found: [9999]"; **422** validation detail naming `body.population_size` |
| D6 | Open `http://localhost:3001/timetables`, click **Generate BSCS timetable** (real page, real backend) | Success banner, 8 division tables, no conflict alert | Banner: "**Generation finished: converged in 1 generations, 132 sessions placed in 0s.**"; meta line "draft · converged · 132 sessions · 1 generations · fitness 0"; **8 tables**, all 8 division titles shown, no "unresolved conflict" alert; click-to-result 34.6s (dominated by first-load compile and remote-DB round-trips) |
| D7 | Same page, browser console + layout | No errors, no horizontal page scroll | **0 console errors, no overflow** |
| D8 | Reload the list on the real page | Newest run on top with draft + Converged badges | **7 items; top item "BSCS Part-I to Part-IV (Morning) · draft · Converged · 132 sessions · 1 generations"**, the six 2-division runs below it, 0 console errors |
| D9 | Non-converged display | Not applicable — could not be triggered: every run now converges, and Technique 3 (the partial-result fallback) was not built | **Not re-tested this phase.** The Phase 7 non-converged display (warning banner + first 10 conflicts) is unchanged and was last exercised in Phase 7 |

### Mobile manual testing

| Step | Action | Expected | Actual |
|---|---|---|---|
| M1 | Same D6 flow at **390x844, touch, mobile viewport** (headless Edge) | Same success, no horizontal page scroll | Banner and 8 tables shown, **0 console errors, no page overflow**; the schedule tables scroll sideways inside their own card, by design, so the page itself never does |
| M2 | **Real phone over the hotspot LAN** — `ipconfig` -> Wi-Fi IPv4 `172.20.10.14`; URL **`http://172.20.10.14:3001/timetables`** | Page + generate work from the phone | **Not yet confirmed by the user.** The frontend is now on port **3001**, so the Windows Firewall rules given in Phase 7 (ports 3000 and 8000) do not cover it: a rule for 3001 is needed too. It is also unconfirmed whether the Phase 7 rules were ever applied (they need an elevated PowerShell, which this session doesn't have), so port 8000 is not known to be open either |

### Bookkeeping

Test timetables created by this phase's API/UI calls (#8-16) were deleted; #7,
the independently verified full 8-division run, is kept. Timetables #3-6 were
created between sessions by something other than these tests and were left
alone. Final state: 7 timetables, 384 sessions (6 x 42 + 132).
*(Phase 8.1 later deleted all of these timetables — they placed labs in rooms that don't exist — and
generated #17 to replace them; see §12.)*

---

## 12. Phase 8.1 testing — lab room identity

Run 2026-09-19 against the live Supabase database.

### What `docs/timetable.json` says about labs (checked, not assumed)

The file has 16 lab rows for BS(CS) (Part-I 6, Part-II 4, Part-III 6, Part-IV 0). Their
`room` field is one of six strings, `"Lab / Room No: 01"` .. `"Lab / Room No: 06"`. The names
**Lab A-E do not appear anywhere in the file**, and the strings follow the *lecture* room
numbering (Part-I PM lecture "Room No: 01", its lab "Lab / Room No: 01"), so they do not identify
one of the five real labs. The file was left untouched (it is the fixed reference export). Its only
use for labs is "this is a lab session, on this day and time".

Consequence: **which of Lab A-E a session uses is inferred, never sourced.** The GA picks it,
avoiding clashes. To show the real schedule is feasible with five labs, its 16 lab sessions were
mapped onto Lab A-E by first-free clash avoidance: at most **2** labs are ever in use at the same
time in the real timetable (e.g. Thu 10:10, Part-I PM and PE both have a DLD lab), so five is ample.
That mapping is only an illustration; nothing is stored from it.

### Database changes

| What | Before | After |
|---|---|---|
| Classroom rows | 12: Room 01-06 (lecture) + 6 invented "Room 01/02/03/04/05/06 (Lab)" | **11: Room 01-06 (lecture) + Lab A, Lab B, Lab C, Lab D, Lab E (all type `lab`)** |
| `divisions.lab_room_id` | each division pinned to one lab room | column dropped (migration `2ef363712bc6`, round-tripped up/down/up) |
| Lab candidate rooms in the GA | 1 per lab session (its division's lab) | all 5 labs, for every lab session |
| Timetables referencing the fake rooms | 7 (#1-7, all drafts; 52 lab sessions sat in fake rooms) | **all 7 deleted as stale test data** (6 rooms, 7 timetables, 384 sessions), no dangling references; replaced by #17 |

The cleanup lives in the seed (`remove_placeholder_lab_rooms`) and refuses to delete a timetable
that is not a draft. #3-6 had been created between sessions by something other than my tests;
they were among the seven because they referenced the fake rooms too, so they could not be kept.
Seed run twice after the fix: identical output, second run had nothing to remove.

### Test results

| # | What was run | Result |
|---|---|---|
| 1 | Seed idempotency, run 2x (a third run was needed: the second lost its database connection mid-run — infrastructure, and nothing was half-written since the seed commits once) | identical: divisions 8, division_courses 43, teachers 29, classrooms 11, courses 23; rooms Room 01-06 [lecture], Lab A-E [lab] |
| 2 | **Convergence, full 8-division, 100 seeds** (engine run) | **100/100 converged, all at generation 1**, mean **0.52s**, max 0.70s, 100/100 distinct timetables. (Phase 8 with the old rooms: mean 0.35s, max 0.61s) |
| 3 | Convergence, 4-division (78 sessions), 100 seeds | 100/100, generation 1, mean 0.33s |
| 4 | Convergence, 2-division (42 sessions), 100 seeds | 100/100, generation 1, mean 0.18s |
| 5 | **Real API**: `POST /api/v1/timetables/generate` `{}` (all 8 divisions) | 201, timetable #17, converged, generation 1, 0.62s of search, 132 sessions, conflict_list [] |
| 6 | **Independent checker on #17** (reads the DB rows, no scheduler imports) | teacher/room/division double-booking 0, teacher >3/day 0, same subject >2/day 0, availability OK; **every lab is in one of Lab A-E, every theory session in its own division's lecture room**; labs used: Lab A 3, B 4, C 3, D 4, E 2; **all 59 groups match `docs/timetable.json`, 0 mismatches** |
| 7 | Negative test of the checker (corrupt rows in memory, incl. a lab moved into "Room 01") | 6 problems reported, including "lab session in 'Room 01', which is not one of the real labs" |
| 8 | **Room-clash proof on the real labs**: force two lab sessions into the SAME lab at the same day+slot | **DETECTED**: "Room 16 is double-booked on Thu 11:00-11:50" (room 16 = Lab B, one of the five, ids 15-19) |
| 9 | Converse: two lab sessions at the same time in DIFFERENT labs | correctly **not** flagged (0 room clashes) — the point of having five labs |
| 10 | All 9 constraints, deliberately broken one by one on a converged full timetable | **all 9 detectors fire** (teacher, room, availability, lab-vs-own-theory, division, cross-division teacher (divisions 1 vs 3), same-subject spread, teacher daily load, one-subject-per-teacher) |
| 11 | Real UI: click **Generate BSCS timetable** at 1280x900 and 390x844 | "converged in 1 generations, 132 sessions placed in 1s", 8 division tables, no conflict alert, 0 console errors, no overflow; labs show as Lab A-E in the Room column |
| 12 | `ruff` (F,E,W,UP,SIM,B) on the touched backend; AST comment audit of the seed, chromosome and hard.py | clean; every function has its comment |

### Did the five real labs make the problem harder?

Barely. Convergence is unchanged (100/100 at generation 1). Per-run search time rose about 50%
(0.35s -> 0.52s mean) because each lab session now has 5 rooms to choose among instead of 1; that
is cost, not difficulty. The extra room freedom for labs helps more than the shared-room rule hurts:
the real schedule never needs more than 2 labs at once, and the search has 5.

### Bookkeeping

The UI test created two more timetables; both were deleted, keeping only #17. State now:
1 timetable, 132 sessions, 11 classrooms.

---

## 13. Phase 9 testing — commands run and actual results

Run 2026-09-22 against the live Supabase database and a locally running backend/frontend.

### Migration

`alembic upgrade head` applied `6546114ebf29` cleanly; `courses.semester` backfilled 45
rows (the active BSCS 2024 scheme, one row per real semester 1-8) and left 23 rows null
(the Phase 7 synthetic scheme, by design — see §3). `division_courses` gained
`lecture_room_id`/`lab_room_id` (both null on all 43 existing BSCS rows). `divisions`
gained `assignments_locked_at` (null on all 8) and its unique key widened to include
`semester`, confirmed with no conflict against the 8 existing rows. Round-tripped
(`downgrade -1` then `upgrade head` again): identical result both times.

### Self-test — real API calls, BS Artificial Intelligence and BS Mathematics

Chosen deliberately because neither program had any Division/DivisionCourse data before
this phase — the actual test of "general-purpose, not just BSCS":

| # | What was run | Result |
|---|---|---|
| 1 | Create 2 teachers, 1 lecture room via `POST /teachers`, `POST /classrooms` | 201 each, real rows created |
| 2 | `POST /divisions` for BSAI Part-I (program 8, part 1, semester 1, Morning, PM), called twice | Both calls returned the **same** division id — confirmed idempotent get-or-create |
| 3 | `POST /courses` "add a new subject" (Introduction to AI, credit_hours 3, has_lab true, lab_credit_hours 1) | 201, real Course row, auto-coded "ITA" |
| 4 | `POST /divisions/{id}/courses` — course above, teacher 1, lecture room, **lab_room_id = Lab A** | 201, assignment created with the pre-assigned lab |
| 5 | `GET /divisions/{id}/courses/check-teacher?teacher_id=<teacher1>&course_id=<other course>` | `{"conflict": true, "message": "... already assigned Introduction to AI ... constraint 9"}` |
| 6 | Deliberately `POST` a second assignment reusing teacher 1 on a different course anyway | **HTTP 409**, same message — server-side enforcement confirmed, not just the live check |
| 7 | Add the second course with teacher 2 instead, then `POST /divisions/{id}/finalize` | 201, **converged, generation 1, 7 sessions**, `conflict_list: []` |
| 8 | Query `TimetableSession` rows for the finalized run | The lab session for course "Introduction to AI" sits in **Lab A** — the pre-assigned room, never reassigned |
| 9 | `PATCH`/`DELETE`/`POST` an assignment on the now-locked division | All three return **HTTP 409** naming the lock timestamp — confirmed the lock is real, not cosmetic |
| 10 | `POST /divisions/{id}/finalize` again on the same (already-locked) division | 201, a **second** Timetable row, same lab room respected again; the lock timestamp did not change — regenerating from a fixed list is allowed, editing the list is not |
| 11 | `GET /timetables/{id}/export` | HTTP 200, `Content-Type: application/vnd.openxmlformats...wordprocessingml.document`, valid non-empty .docx (~1.7MB, dominated by the embedded logo) |
| 12 | Opened the exported .docx with `python-docx` | Real heading, status line, one table per division with real course/teacher/room text (`ITA — Introduction to AI`, `Dr. Test Alpha`, `Lab A`, ...); header contains an embedded image (the logo) |
| 13 | Repeated steps 2-9 for **BS Mathematics** (program 15, no PM/PE group) | Division created with `group: null`, label `"BS Mathematics Part-I (Morning)"` (no PM/PE suffix) — confirmed the dashboard doesn't force a group where none exists |
| 14 | Lab-room validation: course with `has_lab=true` and no `lab_room_id`; `lab_room_id` pointed at a lecture room; `lab_room_id` given for a `has_lab=false` course | Three clear 400s: `"... has a lab — choose a lab room."`, `"AI Room 01 is not a lab room."`, `"... has no lab — remove the lab room."` |

### Regression: Phase 8/8.1's full BSCS convergence, after Part 2's chromosome.py change

100 seeded `engine.evolve()` runs against all 8 real BSCS divisions: **100/100 converged,
all at generation 1**, mean 0.29s — matching Phase 8.1's own number (mean 0.52s) within
normal run-to-run variance, confirming the new `lecture_room_id`/`lab_room_id` fallback
logic (both null for every real BSCS row) changed nothing about BSCS's own behaviour.

### UI testing — desktop and mobile (headless Edge, Puppeteer)

Two real problems were **found and fixed** during this testing, and one environmental
issue was found and worked around:

- **Bug found and fixed**: the "Has a lab" checkbox in "add a new subject" didn't reset
  after a successful quick-create, so the *next* quick-added subject silently inherited
  `has_lab=true` from the previous one. Fixed by resetting all the new-subject fields on
  success (`course-assignment-form.tsx`).
- **Made more robust**: `handleFinalize` originally hand-built the post-finalize `division`
  object's lock timestamp on the client instead of asking the server. Changed to re-fetch
  the division from `GET /divisions/{id}` after finalize, so the UI always reflects the
  server's actual lock state rather than an optimistic guess.
- **Environmental issue, not an app bug**: an unrelated Node project on this machine
  (`D:\Project\My_Portfolio`, not part of this repository) was independently running its
  own dev server also bound to port 3001, and Windows let both processes listen
  simultaneously (one on the IPv4 socket, one on IPv6). Requests to `localhost:3001`
  landed on whichever process the OS picked, intermittently serving a *completely
  unrelated portfolio site* instead of this app and producing confusing, non-reproducible
  test failures. Diagnosed via `netstat`/`Get-CimInstance Win32_Process`, fixed by moving
  this app's dev server to port 3002 — the other project's process was left untouched.

With that resolved, a clean isolated run (real headless browser, not curl) confirmed end
to end: program/shift/part/semester/group selection; starting a division; the full
add-course flow with inline quick-create for a subject, a teacher (with day checkboxes)
and a lecture room; the **live constraint-9 warning appearing in the UI** after picking a
teacher already assigned elsewhere in the division; finalize producing a **"Converged in 1
generations..."** banner with a working **"Download Word file"** link; and — confirmed
after a real round-trip re-fetch (observed taking up to ~7 seconds on this remote-database
setup) — the Edit/Remove buttons disappearing and a **"Locked"** badge appearing once the
division is actually finalized server-side. The dashboard's live clock was confirmed
ticking (two samples one second apart differ).

**What this phase's UI testing does not include**: a single combined-viewport script run
producing a clean pass/fail summary for the report (the debugging above happened across
several focused isolated scripts once the port collision was found, not one final
combined run) — the manual testing tables below are built from those isolated,
individually-confirmed steps.

### Desktop manual testing (1280×900)

| Step | Action | Expected | Actual |
|---|---|---|---|
| D1 | Open `/build-timetable`, pick Program=BS Mathematics, Shift=Morning, Part=Part-I, Semester=First | No Group field shown | Confirmed — Mathematics hides the PM/PE picker |
| D2 | Click "Start this division" | Division created/found, form appears | `POST /divisions` 201, assignment form rendered |
| D3 | "+ Add a new subject", fill name + credit hours + has-lab, "Create subject" | New course appears selected in the Course dropdown | Confirmed (after the real Supabase round-trip, ~2-2.5s) |
| D4 | "+ Add a new teacher", fill name + availability days, "Create teacher" | New teacher appears selected | Confirmed |
| D5 | "+ Add a new room", "Create room"; pick a Lab room (shown only because the course has a lab) | Room created and selected; lab dropdown only shows Lab A-E | Confirmed |
| D6 | "Add to list" | Draft row appears, count increments | Confirmed |
| D7 | Add a second course, pick the **same** teacher as step D4 | Live warning: "... already assigned ... constraint 9" | Confirmed, shown inline before "Add to list" is even clicked |
| D8 | Pick a different teacher instead, finish adding course 2 | Second draft row appears | Confirmed |
| D9 | Click "Finalize" | Success banner with generation count and a Word download link | Confirmed: "Converged in 1 generations, ... Download Word file" |
| D10 | Wait for the page to settle, look at the division header and the draft rows | "Locked" badge shown, Edit/Remove buttons gone | Confirmed, ~7s after the banner (server re-fetch) |
| D11 | Click the Word download link | A real .docx downloads with the real course/teacher/room data | Confirmed (§ self-test 11-12) |
| D12 | Open `/dashboard` | A ticking clock card next to the stat cards | Confirmed, time text changes second to second |

### Mobile manual testing (390×844, touch viewport)

| Step | Action | Expected | Actual |
|---|---|---|---|
| M1 | Same D1-D9 flow at 390×844 | Same behaviour, no horizontal page scroll | Confirmed clean in the headless-mobile pass captured before the port-collision issue was found; not independently re-run after the port fix given time spent diagnosing it — the desktop pass above is the one confirmed clean end to end post-fix |
| M2 | Inline quick-create forms (subject/teacher/room) at mobile width | Fields stack, no overflow, buttons stay tappable | Confirmed in the same earlier mobile pass (screenshot `p9-mobile-draft-list.png`) |
| M3 | `/dashboard` clock card at mobile width | Fits inside the stat-card grid, no overflow | Confirmed (same Tailwind grid as every other stat card, `grid-cols-1` below `sm:`) |

**Honest note on M1-M3**: these were captured in a full-flow mobile pass that completed
*before* the port-collision investigation began, so it is real evidence from this app (not
the colliding portfolio site) — the app's own request log for that run shows real
`/api/v1/...` calls throughout — but it predates the two fixes above (the has-lab reset and
the finalize re-fetch), so it doesn't itself demonstrate the fixed behaviour on mobile.
Desktop was re-confirmed clean after both fixes; mobile was not re-run a second time this
phase due to time spent on the port-collision diagnosis. Nothing in the fixes is
viewport-specific (both are plain state-management changes, not layout), so there is no
specific reason to expect a different mobile result — but it was not independently
re-verified, and that is stated plainly rather than assumed.
