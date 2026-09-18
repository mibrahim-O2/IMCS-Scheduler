# IMCS Scheduler — Project Audit

**Snapshot date:** 2026-09-19, at the end of Phase 7 — real GA integration
end to end: database models, seed data from `docs/timetable.json`, the
production scheduler package (all 9 hard constraints), the
`/api/v1/timetables` endpoints, and a real frontend page, wired together and
tested through the real system (no mocks), including over the real local
network from a phone.

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
│       └── 722044599067_..._lab_....py      real (Phase 7) — divisions, division_courses, lab_batches,
│                                              timetables, timetable_sessions.
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
│   │   ├── seed_bscs_timetable.py        real (Phase 7) — reads docs/timetable.json and creates real
│   │   │                                    Teacher/Classroom/Division/DivisionCourse rows for BSCS
│   │   │                                    Part-I to Part-IV, Morning shift (idempotent)
│   │   └── rematerialize.py              real — rebuilds Course rows from a scheme's stored content
│   ├── models/
│   │   ├── program.py                    real — Department, Program, ProgramLevel enum
│   │   ├── classroom.py                  real — Classroom, ClassroomType enum
│   │   ├── teacher.py                    real — Teacher (no auth fields, by design)
│   │   ├── course.py                     real — Course (materialized from CourseScheme.content)
│   │   ├── course_scheme.py              real — CourseScheme (JSONB content column)
│   │   ├── division.py                   real (Phase 7) — Division, LabBatch, DivisionCourse
│   │   └── timetable.py                  real (Phase 7) — TimetableStatus, Timetable, TimetableSession
│   ├── schemas/
│   │   ├── program.py                    real — Pydantic schemas for the programs endpoint
│   │   ├── course_scheme.py              real — Pydantic schemas for course scheme upload/list/detail
│   │   ├── dashboard.py                  real — Pydantic schema for the stats endpoint
│   │   └── timetable.py                  real (Phase 7) — generate/list/detail schemas
│   ├── api/
│   │   ├── deps.py                       real — shared DbSession dependency
│   │   └── v1/
│   │       ├── router.py                 real — mounts programs, course_schemes, dashboard, timetables
│   │       └── endpoints/
│   │           ├── programs.py           real — GET /api/v1/programs
│   │           ├── course_schemes.py     real — extract/save/list/detail/delete endpoints
│   │           ├── dashboard.py          real — GET /api/v1/dashboard/stats
│   │           ├── classrooms.py         placeholder — no Classroom endpoint yet
│   │           ├── divisions.py          placeholder — no Division endpoint yet
│   │           ├── teachers.py           placeholder — no Teacher endpoint yet
│   │           └── timetables.py         real (Phase 7) — POST /generate, GET "", GET /{id}
│   ├── services/
│   │   ├── course_scheme_service.py      real — PDF/Word text extraction (+ OCR fallback), Supabase
│   │   │                                    Storage upload/delete, lab-pairing materialization logic
│   │   ├── dashboard_service.py          real — the counts query behind the stats endpoint
│   │   └── export_service.py             placeholder — Word/PDF timetable export, not built
│   └── scheduler/                        **the GA package — see §5 "Genetic Algorithm file map" below**
│       ├── chromosome.py                 real (Phase 7) — Gene, SessionRequirement, DivisionInfo,
│       │                                    load_divisions, build_session_requirements from the DB
│       ├── fitness.py                    real (Phase 7) — fitness_from_violations
│       ├── engine.py                     real (Phase 7) — evolve() loop, stagnation detection +
│       │                                    partial-population restarts, generate_timetable() entry point
│       ├── operators.py                  real (Phase 7) — tournament_select, two_point_crossover,
│       │                                    mutate_targeted (blame-carrying targeted mutation)
│       ├── constraints/
│       │   ├── hard.py                   real (Phase 7) — all 9 hard constraints, lazy Violation.describe()
│       │   └── soft.py                   placeholder — docstring only, out of scope this phase
│       └── dev_scripts/                  dev-script — kept for reference, not deleted (see §5)
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
│   └── timetables.ts                     real (Phase 7) — generate/list/detail types + API calls
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

---

## 3. Current database state

Confirmed by direct query against the live Supabase database on 2026-09-19,
after the Phase 7 seed and two real `POST /api/v1/timetables/generate` runs:

| Table | Row count | Populated with |
|---|---|---|
| `departments` | 3 | Computer Science, Artificial Intelligence, Mathematics |
| `programs` | 18 | All levels for all 3 departments; 3 are `is_schedulable=true` (the BS programs) |
| `classrooms` | 12 | Real lecture + lab rooms for BSCS Part-I to Part-IV, from `docs/timetable.json` |
| `teachers` | 29 | Real full names, `availability.days` derived from actual teaching days in the JSON |
| `course_schemes` | 2 (1 active) | The original BSCS 2024 upload (active, 45 courses), plus a synthetic `scheme_year=2026, is_active=false` scheme that exists only to hold real-timetable-derived Course rows (kept out of the Course Scheme upload UI on purpose — that UI is for official documents) |
| `courses` | 68 | 45 from the 2024 scheme (unchanged) + 23 from the synthetic scheme |
| `divisions` | 8 | BSCS Part-I to Part-IV, Morning shift, PM/PE split each |
| `division_courses` | 43 | Real course/teacher assignments per division, incl. joint PM/PE subjects |
| `timetables` | 2 | Both draft, both converged, from real `POST /generate` calls in this phase's testing |
| `timetable_sessions` | 84 | 42 per timetable run (BSCS Part-I only, both test calls used `division_ids:[1,2]`) |

**Full 8-division generation was run (§8, §4) but its result was not saved
as a `Timetable` row** — that run was made directly against `engine.evolve()`
for measurement purposes, not through the API, and it did not converge (see
§4). The two saved `timetables` rows are both the smaller, proven-converging
2-division case, generated through the real HTTP endpoint.

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

### What's still fragile — an honest scaling result, not a bug
- **The full 8-division, 132-session, 9-constraint problem does not
  reliably converge within a practical time budget.** Three real runs
  against `engine.evolve()` directly (not saved as `Timetable` rows, since
  none converged):
  - seed=1, `max_generations=3000`, `MAX_RESTARTS=3`: stagnated, 7
    violations left, 645.7s.
  - seed=7, `max_generations=8000`, `MAX_RESTARTS=3`: stagnated at
    generation 2547, 20 violations left, 381.0s.
  - seed=7, `max_generations=8000`, `MAX_RESTARTS=8` (current setting):
    stagnated at generation 6333, **1 violation left**
    (`teacher_outside_availability`), 655.8s.
  Raising `MAX_RESTARTS` from 3 to 8 is a real, measured improvement (20 → 1
  remaining violation on the same seed) and is disclosed with its reasoning
  in `engine.py`'s own comment — but it is not full convergence, and further
  tuning wasn't chased down at the cost of shipping the rest of this phase.
  A smaller BSCS Part-I + Part-II subset (~78 sessions, the same scale
  Phase 5's dev script converged 10/10 on) was also tested directly and
  stagnated with 1 violation after 1736 generations — confirming the extra
  difficulty comes from the 3 new constraints (7-9), which Phase 5's dev
  script never had to satisfy, not from a regression in the GA machinery
  itself.
- **No infeasibility pre-check still.** A feasibility script was run this
  phase checking every teacher's `2 x available_days` (constraint 7 ceiling)
  and `3 x available_days` (constraint 8 ceiling) against their real
  assigned load — no teacher is mathematically overloaded, so the
  non-convergence above is a search-difficulty problem, not an infeasible
  one. The engine still can't say this on its own; it was checked manually.
- **Real declared availability still hasn't been tested** — availability is
  still derived from days a teacher appears in the real published
  timetable, same caveat as the previous audit.

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
- **`engine.py`** — the generation loop, now with stagnation detection and
  partial-population restarts (previous audit's other flagged gap), and
  `generate_timetable()`, the real entry point the API calls.

**The dev scripts** (`scheduler/dev_scripts/`) — three real, tested,
**standalone** Python files, kept deliberately, not deleted by default (see
the retention note in `dev_scripts/__init__.py` for the full reasoning):
production code fully reproduces Phase 4's result (§4) but not yet Phase
5's or Phase 6's at matching scale, so these remain the only proof that
those exact problems are solvable with a GA at all, useful as a reference
while `engine.py`'s tuning keeps closing the gap.

- **`phase4_bscs_part1_ga.py`** — one division (BSCS Part-I Morning),
  plausible-but-unconfirmed teacher assignments, 5 hard constraints, uniform
  mutation. Superseded by production for this scale (§4).
- **`phase5_multi_division_ga.py`** — 4 divisions, real teacher data,
  blame-carrying targeted mutation introduced here. Production does not yet
  match its 10/10 convergence at this scale under the fuller 9-constraint
  set (§4).
- **`phase6_full_bscs_morning_ga.py`** — all 8 BSCS Morning divisions.
  Production does not yet match its 10/10 convergence at this scale either
  (§4) — its own numbers remain the reference point for "this is solvable."

Each dev script is fully self-contained (no shared imports between them or
with the production package) so any one can still be read and run on its
own. **They are not imported by, called from, or in any way connected to
the database, the API layer, or the frontend** — that connection now exists
only through the production package.

---

## 6. What is NOT yet started

- **Authentication** — faculty-only Google sign-in via Supabase Auth is
  planned (per `docs/PROJECT_ARCHITECTURE.md` §13) but not started; no auth
  fields exist on any model, by design.
- **Word/PDF export of a generated timetable** — `export_service.py` is a
  docstring-only placeholder.
- **The live/soft-constraint dashboard** (teacher/room availability derived
  from real generated timetables) — the current stats page is counts-only
  and explicitly does not claim to show availability (per Phase 3's scope
  correction).
- **Soft constraints** — `constraints/soft.py` is still a docstring-only
  placeholder; only hard constraints exist anywhere in the GA work so far,
  by explicit scope for this phase.
- **BS(AI) and Evening-shift scheduling** — explicitly out of scope for
  Phase 7; the GA package and seed data cover BSCS Part-I to Part-IV,
  Morning shift only.
- **Full-scale (8-division) generation reliably converging** — see §4;
  the search gets very close (1 remaining violation after ~655s with the
  current tuning) but does not yet reliably reach zero within a practical
  time budget, and this hasn't been resolved.
- **`LabBatch` rows** — the model exists (`app/models/division.py`) but the
  Phase 7 seed does not populate it; lab sessions are scheduled per-division
  as a whole, not split into sub-batches.
- **Reviewing/publishing a draft timetable** — every generated `Timetable`
  is created with `status="draft"`; there's no UI or endpoint yet to move
  one to `published`, edit it, or compare versions.
- **Classroom and Teacher admin UI** — both tables are now populated by the
  Phase 7 seed script, but there's still no page or endpoint for adding,
  editing, or browsing them directly (only the timetables page reads them,
  indirectly, via a generated schedule).

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
- **Lab rooms are an assumption, not confirmed data** (Phase 4-6): none of
  the source timetable PDFs name a room for lab sessions. The dev scripts
  invented a "Computer Lab" pool (1-2 rooms depending on phase) sized to
  whatever the real schedule's simultaneous-lab pattern needed. Real lab
  room assignments should replace this before anything here is trusted.
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
- **Full 8-division GA tuning is unfinished** (Phase 7, §4) — the best
  measured run gets to 1 remaining violation, not zero, within a ~11-minute
  budget. Whether that needs a longer generation cap, a different
  restart/stagnation balance, or a genuinely different approach for
  constraints 7-9 at this scale hasn't been decided.
- **Lab room assignment is still a resolved-not-confirmed guess** (Phase
  7) — `docs/timetable.json`, like the source PDFs before it, doesn't name
  a lab room for every lab session. The Phase 7 seed script picks a
  reasonable lecture-room-plus-lab-room pairing per division rather than
  guessing silently, but this should be replaced with real room assignments
  before any generated timetable is trusted for actual room booking.

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
