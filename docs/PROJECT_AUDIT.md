# IMCS Scheduler — Project Audit

**Snapshot date:** 2026-09-18, at the end of the cleanup/pivot phase that
removed the One Max scaffolding, ruled out OR-Tools/hybrid permanently,
adopted `docs/timetable.json` as the GA's reference data, and documented
every scheduling constraint decided so far in `docs/CONSTRAINTS.md`.

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
│       └── ef3f9e008a22_..._classroom_.py   real — the ONLY migration so far: creates departments,
│                                            programs, classrooms, teachers, course_schemes, courses.
│                                            No divisions or timetables table yet.
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
│   │   └── rematerialize.py              real — rebuilds Course rows from a scheme's stored content
│   ├── models/
│   │   ├── program.py                    real — Department, Program, ProgramLevel enum
│   │   ├── classroom.py                  real — Classroom, ClassroomType enum
│   │   ├── teacher.py                    real — Teacher (no auth fields, by design)
│   │   ├── course.py                     real — Course (materialized from CourseScheme.content)
│   │   ├── course_scheme.py              real — CourseScheme (JSONB content column)
│   │   ├── division.py                   placeholder — Division/LabBatch model, not built
│   │   └── timetable.py                  placeholder — Timetable/TimetableSession model, not built
│   ├── schemas/
│   │   ├── program.py                    real — Pydantic schemas for the programs endpoint
│   │   ├── course_scheme.py              real — Pydantic schemas for course scheme upload/list/detail
│   │   └── dashboard.py                  real — Pydantic schema for the stats endpoint
│   ├── api/
│   │   ├── deps.py                       real — shared DbSession dependency
│   │   └── v1/
│   │       ├── router.py                 real — mounts programs, course_schemes, dashboard routers
│   │       └── endpoints/
│   │           ├── programs.py           real — GET /api/v1/programs
│   │           ├── course_schemes.py     real — extract/save/list/detail/delete endpoints
│   │           ├── dashboard.py          real — GET /api/v1/dashboard/stats
│   │           ├── classrooms.py         placeholder — no Classroom endpoint yet
│   │           ├── divisions.py          placeholder — no Division endpoint yet
│   │           ├── teachers.py           placeholder — no Teacher endpoint yet
│   │           └── timetables.py         placeholder — no Timetable endpoint yet (this is where GA
│   │                                        generation would eventually be triggered from)
│   ├── services/
│   │   ├── course_scheme_service.py      real — PDF/Word text extraction (+ OCR fallback), Supabase
│   │   │                                    Storage upload/delete, lab-pairing materialization logic
│   │   ├── dashboard_service.py          real — the counts query behind the stats endpoint
│   │   └── export_service.py             placeholder — Word/PDF timetable export, not built
│   └── scheduler/                        **the GA package — see §5 "Genetic Algorithm file map" below**
│       ├── chromosome.py                 placeholder — docstring only
│       ├── fitness.py                    placeholder — docstring only
│       ├── engine.py                     placeholder — docstring only
│       ├── operators.py                  placeholder — docstring only
│       ├── constraints/
│       │   ├── hard.py                   placeholder — docstring only
│       │   └── soft.py                   placeholder — docstring only
│       └── dev_scripts/                  dev-script — real, tested, standalone GA work
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
│   └── dashboard/page.tsx                real — stats overview page (Phase 3), counts only
├── components/
│   ├── ui/                               real — Button, Alert, ConfirmDialog, Spinner, form fields,
│   │                                        SiteHeader — shared primitives, no GA content
│   ├── scheme-upload/                    real — the 4-step upload wizard + saved-scheme list
│   │                                        (upload-step, text-review-step, course-form-step,
│   │                                        preview-step, scheme-list, semester-table, step-indicator)
│   └── dashboard/
│       └── stat-card.tsx                 real — the stat tile + its loading skeleton
├── lib/
│   ├── api-client.ts                     real — fetch wrapper, readable error messages
│   ├── schemes.ts                        real — Course Scheme types, lab-pairing helper, API calls
│   ├── scheme-text-parser.ts             real — parses the university portal's table layout for
│   │                                        the "Fill rows from extracted text" button
│   └── dashboard.ts                      real — stats types + API call
└── public/imcs-logo.png                  real — the IMCS crest used in the header and homepage
```

**Nothing in `frontend/` calls or displays anything GA-related.** Confirmed
by search: every "generation"/"genetic"/"chromosome" match in the frontend
source is either page copy ("Timetable generation and scheduling for the
Institute of..." — descriptive text, not a function call) or a Tailwind
`gap-*` utility class matching the regex by accident. No frontend file
imports from, fetches from, or references `backend/app/scheduler/` in any
way.

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

---

## 3. Current database state

Confirmed by direct query against the live Supabase database on 2026-09-18
(commands and output in §8 below):

| Table | Row count | Populated with |
|---|---|---|
| `departments` | 3 | Computer Science, Artificial Intelligence, Mathematics |
| `programs` | 18 | All levels for all 3 departments; 3 are `is_schedulable=true` (the BS programs) |
| `classrooms` | **0** | Empty — no Classroom rows have ever been created |
| `teachers` | **0** | Empty — no Teacher rows have ever been created |
| `course_schemes` | 1 (active) | BS Computer Science, scheme year 2024, from the real university PDF |
| `courses` | 45 | Materialized from that one scheme, after Phase 3's lab-pairing fix (20 have `has_lab=true`) |

No `divisions` or `timetables` table exists yet — those models are still
placeholders (§1).

**Worth noting:** `classrooms` and `teachers` being 0 is not a bug — nothing
has built a UI or seed step for them yet. The GA dev scripts (Phase 4-6) use
their own hardcoded room/teacher data and are completely disconnected from
these (empty) tables.

---

## 4. Genetic Algorithm — current state

### What's proven (Phase 4-6 findings)
- The chromosome design (one gene per session, course+teacher fixed per gene
  position, mutation only re-rolls room/day/time) holds up from 1 division
  (Phase 4) to 8 divisions (Phase 6) with no redesign needed.
- All 6 implemented hard constraints (see `docs/CONSTRAINTS.md`) work
  correctly at every scale tested, including cross-division teacher clashes
  and shared-room contention (Part-III/Part-IV sharing rooms 03/04).
- Tournament selection + elitism + blame-carrying targeted mutation reliably
  converges to zero hard violations: 5/5 (Phase 4), 10/10 (Phase 5), 10/10
  (Phase 6) across independent random seeds.
- Real course and teacher data was used throughout — no invented names in
  Phase 5-6 (Phase 4 used plausible-but-unconfirmed teacher assignments,
  since the real BSCS 2024 course scheme didn't have teacher names attached
  yet at that point).

### What's known to be fragile
- **Generation count grows worse than linearly with problem size.** Phase 5
  (79 sessions) averaged 172 generations to converge; Phase 6 (133 sessions,
  1.7x the sessions) averaged 1206 generations — a ~7x jump. Scaling to the
  full department (both shifts, both CS and AI, ~250+ sessions) at that rate
  is a real risk to interactive use.
- **Violation messages are built in the fitness hot path.** Every violation
  constructs an f-string during evaluation even though fitness only needs a
  *count* — this was measured as the likely reason Phase 6's early
  (high-violation) generations cost roughly double Phase 5's per-generation
  cost for only 1.7x the genes. Making messages lazy is flagged as probably
  the cheapest next performance win.
- **No stagnation detection or restart.** A run can spend hundreds or
  thousands of generations without improving (Phase 6 run 4 took 2080
  generations; a population-250 experiment left one run stuck at exactly 1
  violation for the full 3000-generation cap). Nothing currently detects
  that and restarts or perturbs the population.
- **No infeasibility pre-check.** The GA can only report "hit the generation
  cap" — it cannot distinguish a run that would converge given more time
  from one that's asking for something genuinely impossible (e.g. more
  sessions than a teacher's available days can hold).
- **Real declared availability hasn't been tested.** Every phase so far
  derived teacher availability from days they appear in a *published*
  timetable, which guarantees the problem is solvable. Real availability
  (collected independently) could easily be tighter and infeasible, and the
  GA has no way to say so cleanly yet.

### The 9 constraints (full detail in `docs/CONSTRAINTS.md`)

| # | Constraint | Implemented? |
|---|---|---|
| 1 | Teacher double-booking | Yes (Phase 4) |
| 2 | Room double-booking | Yes (Phase 4) |
| 3 | Teacher availability | Yes (Phase 4) |
| 4 | Lab session rules (separate slot, lab room, no self-clash) | Yes (Phase 4) |
| 5 | Division double-booking (joint sessions excluded) | Yes (Phase 4, refined Phase 5) |
| 6 | Cross-division teacher clash | Yes (Phase 4, verified Phase 5-6) |
| 7 | Same-subject daily spread (max 2 sessions/day, theory only) | **No** — decided this phase, not coded |
| 8 | Teacher daily load limit (max 3 sessions/day) | **No** — decided this phase, not coded |
| 9 | One subject per teacher per Part per semester run | **No** — decided this phase, not coded |

---

## 5. Genetic Algorithm file map

Every file that currently contains GA-related code lives under
`backend/app/scheduler/`. There are two completely separate layers here —
don't confuse them:

**The production skeleton** (`chromosome.py`, `fitness.py`, `engine.py`,
`operators.py`, `constraints/hard.py`, `constraints/soft.py`) — **all six
are still docstring-only**, exactly as they were left after Phase 0's
scaffold. Nothing has been implemented in any of them. They describe what
they'll eventually hold (per `docs/PROJECT_ARCHITECTURE.md` §6) but contain
zero working code.

**The dev scripts** (`scheduler/dev_scripts/`) — three real, tested,
**standalone** Python files, each a complete self-contained GA:

- **`phase4_bscs_part1_ga.py`** — the starting point. One division (BSCS
  Part-I Morning, semester 1), 6 real courses pulled from the database's
  Course Scheme #6, plausible teacher assignments (Phase 4 predates real
  teacher-timetable data). Defines the gene shape, the first 5 hard
  constraints, and the GA loop (tournament selection, elitism, two-point
  crossover, uniform mutation) from scratch.
- **`phase5_multi_division_ga.py`** — extends Phase 4's chromosome to cover
  4 divisions (BSCS Part-I + Part-II, each split PM/PE) in one combined
  chromosome, so cross-division teacher clashes can actually be tested. Adds
  blame-carrying violations and targeted mutation (re-place the genes
  actually causing a violation, not a uniform random subset) because uniform
  mutation stopped reliably converging at this size. Real teacher data, read
  directly off the official timetable PDF for the first time.
- **`phase6_full_bscs_morning_ga.py`** — extends Phase 5's approach to all 8
  BSCS Morning divisions (adds Part-III and Part-IV, both PM/PE). Same GA
  machinery as Phase 5, unchanged. Adds shared-room contention (Part-III and
  Part-IV are printed on the same room numbers) and generalizes the
  cross-division check from "2 shared teachers" to "however many teachers
  turn out to be shared" (5, in this data).

Each file is fully self-contained (the GA loop is copied into each one
rather than imported from a shared module) so any one of them can be read
and run on its own without needing the others.

**The current relationship between this GA code and the rest of the system
is: none.** The dev scripts are not imported by, called from, or in any way
connected to the database, the API layer, or the frontend. They run as
`python -m app.scheduler.dev_scripts.phase6_full_bscs_morning_ga` from a
terminal and print their result to stdout. Nothing about generating,
storing, or displaying a real timetable through the app exists yet — that
integration work has not started.

---

## 6. What is NOT yet started

- **Database integration of the GA** — no code reads Division/Teacher/Room
  data from the real database to build a chromosome, and no code writes a
  GA result back as `Timetable`/`TimetableSession` rows (those tables don't
  exist yet either — see §1, §3).
- **API endpoints for triggering generation** — `timetables.py` is a
  docstring-only placeholder; there is no `POST /api/v1/timetables/generate`
  or equivalent.
- **Frontend for viewing/generating a timetable** — no page or component
  exists for this anywhere in `frontend/`.
- **Authentication** — faculty-only Google sign-in via Supabase Auth is
  planned (per `docs/PROJECT_ARCHITECTURE.md` §13) but not started; no auth
  fields exist on any model, by design.
- **Word/PDF export of a generated timetable** — `export_service.py` is a
  docstring-only placeholder.
- **The live/soft-constraint dashboard** (teacher/room availability derived
  from real generated timetables) — the current stats page is counts-only
  and explicitly does not claim to show availability (per Phase 3's scope
  correction).
- **Soft constraints** — not designed or implemented; only hard constraints
  exist anywhere in the GA work so far.
- **Constraints 7, 8, 9** from `docs/CONSTRAINTS.md` — decided, not coded.
- **Classroom and Teacher data entry** — no seed data, no admin UI, no API
  endpoint; both tables are empty (§3).
- **Division model** — placeholder only; no PM/PE group, no lab-batch
  support built against the real schema yet (the dev scripts model this in
  Python data structures, not database rows).

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
