# IMCS Timetable Generator — Project Architecture

**Team:** AbstractMinds — Ibrahim (lead), Arsal, Ali
**Supervisor:** Prof. Dr. Ayaz Keerio · **Co-supervisor:** Sir Rajesh Kumar
**Institution:** Institute of Mathematics & Computer Science, University of Sindh

This document is the complete blueprint of the final system. Only a small
slice of it is implemented at any given stage — this file exists so every
future phase has a fixed target to build toward, and so nothing gets
reinvented differently halfway through the project.

---

## 1. System Overview

A full-stack, constraint-based timetable generation and department-scheduling
platform for IMCS. Core pieces:

1. A **Genetic Algorithm scheduling engine** that produces conflict-free
   timetables per Program/Part/Shift/Group from a Course Scheme, a teacher
   pool, and a room pool.
2. **Course Scheme management** — admin-uploaded, year-labeled, versioned,
   schema-flexible.
3. A **live dashboard** — real-time teacher/room availability derived from
   generated timetables.
4. **Export** — Word/PDF timetable output with the IMCS crest.

**Scope of scheduling:** IMCS is organized as three departments (Computer
Science, Artificial Intelligence, Mathematics), and each department offers
several program levels (BS, Master, M.Phil, Ph.D, M.Sc. (Pass), Post Graduate
Diploma). Every level is represented in the data model and listed in
navigation, but **only BS-level programs are scheduled in the current build** —
see §3.1.

---

## 2. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Python 3.11+, FastAPI | Async, typed, clean separation of routes vs. logic |
| Scheduling engine | Pure Python custom Genetic Algorithm (DEAP-style, no framework lock-in) — the sole, permanent scheduling approach; no OR-Tools/CP-SAT hybrid, see §6 | Full control over chromosome/fitness design |
| Database | PostgreSQL | Core entities (Program, Division, Classroom, Teacher, Course, Timetable) are relational — FKs, joins, and referential integrity (e.g. blocking scheme deletion when referenced) matter here |
| Flexible data | JSONB column on a `course_schemes` table | Each scheme year's subject list varies in shape; JSONB avoids a migration per new scheme year while keeping it inside the relational DB (no second datastore to sync) |
| ORM | SQLAlchemy 2.0 + Alembic | Typed models, migrations for the relational core (schemes stay migration-free via JSONB) |
| Frontend | Next.js (App Router) + React + Tailwind | Matches reference-project UI patterns already reviewed; Tailwind maps cleanly onto the fixed color palette |
| Auth (later) | Not yet scoped | RBAC is explicitly future work |
| AI query feature (later) | Gemini free tier, function-calling only | Structured DB queries, not RAG — see §8 |

**Why Postgres + JSONB instead of Mongo:** almost everything in this domain
is relational — a Division belongs to a Program, a Course belongs to a
Scheme, a Timetable session references a Teacher/Room/Course/Division all at
once, and clash-detection queries are exactly the kind of multi-table joins
Postgres is built for. The one part of the domain that's genuinely
schema-variable — course scheme documents — gets a JSONB `content` column
instead of a full second database, so scheme flexibility doesn't cost us
relational integrity everywhere else.

---

## 3. Data Models

All models live conceptually in `backend/app/models/`. Types below are
descriptive, not final column-level DDL — exact constraints get pinned down
when the models are actually implemented.

### 3.1 Department and Program
A department offers several program levels, so a `Program` is one
(department + level) pair — not a department on its own. `Department` is the
stable top-level grouping used for the homepage hierarchy.

```
Department        -- exactly 3 rows
- id
- name             "Computer Science" | "Artificial Intelligence" | "Mathematics"
- short_code       "CS" | "AI" | "MATH"
- display_order    int   (homepage order: CS -> AI -> Math)
```

```
Program           -- one (department + level) combination
- id
- department_id    -> Department
- level            "BS" | "Master" | "MPhil" | "MPhilBioinformatics"
                     | "PhD" | "MScPass" | "PGD"
- display_name     e.g. "BS Computer Science",
                        "M.Phil (Bioinformatics) — Artificial Intelligence"
- total_semesters  int | null   (only where semester-by-semester structure is
                                  tracked — 8 for BS, null for levels we do
                                  not model that way yet)
- is_schedulable   bool  -- TRUE only for BS-level programs today. This flag is
                            how the system knows which programs get Divisions
                            and Timetables generated, versus which are listed
                            in navigation but not scheduled.
- has_shift_split            bool        (Morning/Evening — true for CS/AI BS, false for Math)
- has_pm_pe_split_from_part  int | null  (2 for CS/AI BS, null for Math — unconfirmed, kept overridable)
```

`has_shift_split` and `has_pm_pe_split_from_part` are only meaningful when
`is_schedulable` is true (BS level today) and are ignored for other levels.

Levels offered today, per the university's course scheme portal:

| Department | Levels |
|---|---|
| Computer Science | BS, Master of Computer Science (MCS), M.Phil, M.Phil (Bioinformatics), Ph.D, M.Sc. (Pass), Post Graduate Diploma |
| Artificial Intelligence | BS, Master of Artificial Intelligence, M.Phil, M.Phil (Bioinformatics), Ph.D, M.Sc. (Pass), Post Graduate Diploma |
| Mathematics | BS, M.Sc. (Pass), M.Phil, Ph.D |

**Current build scope:** no Divisions, Course Schemes or Timetables are created
for non-BS levels. Carrying every level in the model now is a data-model and
navigation accommodation, so that scheduling another level later is a new
`Program` row with `is_schedulable = true` rather than a breaking schema
change. Whether Mathematics has a PM/PE split is open question §11.1.

### 3.2 Division (a.k.a. Section)
The unit an actual timetable is generated for: one Program + Part + Shift
(+ Group where applicable). Divisions exist only for programs with
`is_schedulable = true` (BS level today — see §3.1).
```
Division
- id
- program_id        -> Program
- part              1-8 (maps to "Part-I".."Part-IV" naming per semester pair)
- semester           1-8, the actual semester within the part
- shift             "Morning" | "Evening" | null (Math)
- group             "PM" | "PE" | null (Part-I and Math)
- scheme_year_id     -> CourseScheme (which scheme this division follows)
- student_count      int | null

LabBatch  (child of Division, supports the "one lab, N parallel sub-batches" pattern)
- id
- division_id       -> Division
- course_id         -> Course (the lab course being split)
- batch_label       e.g. "Batch A" / "Batch B" / "Batch C"
- teacher_id        -> Teacher (independent per batch)
- room_id           -> Classroom (independent per batch)
```

### 3.3 Classroom
```
Classroom
- id
- name              "Room 01" | "Multimedia-1" | "Hall-1" ...
- type              "lecture" | "lab" | "hall" | "multimedia"
- capacity          int | null
- features          jsonb  (projector, AC, etc. — free-form, future-proofed)
```

### 3.4 Teacher
```
Teacher
- id
- full_name          -- resolution key; NEVER resolve by initials
- designation
- home_program_id     -> Program (primary affiliation; teacher may still be
                         assigned sessions in other programs — cross-program
                         load is tracked via the Timetable session table, not
                         restricted here)
- max_hours_per_week  int | null
- availability        jsonb  -- per-day preferred/available time windows,
                                teacher-declared, treated as an input
                                constraint, not overridden by the algorithm
- cannot_teach_with    Teacher[]  (future: team-teaching conflicts)
- must_teach_with      Teacher[]  (future: confirmed co-teaching, e.g. the
                                    real IOT section case with two teachers)
```

### 3.5 Course
Sourced from the active Course Scheme for a given Program + scheme year —
not entered by hand per-timetable.
```
Course
- id
- scheme_id          -> CourseScheme
- code                e.g. "CSOO303"
- name                e.g. "OBJECT ORIENTED PROGRAMMING"
- credit_hours        int (or "NC" for non-credit — stored as nullable/flag)
- has_lab             bool
- lab_credit_hours    int | null
- min_marks / max_marks
```

### 3.6 CourseScheme
The flexible piece — one row per Program + scheme (admission) year, for
schedulable programs (BS level today — see §3.1).
```
CourseScheme
- id
- program_id          -> Program
- scheme_year          int  (e.g. 2023, 2024, 2025 — admission year, NOT calendar year)
- source_filename      original uploaded PDF/Word filename, kept for audit
- uploaded_at
- is_active            bool (soft-delete flag — never hard-delete a scheme
                         referenced by a published timetable)
- content              jsonb  -- the full semester-by-semester course list,
                                 shape intentionally not fixed at the SQL
                                 level; frontend renders/validates structure
```
Why `content` is JSONB and not a normalized `courses` table alone: the
per-semester grouping, non-credit markers, and any future per-scheme quirk
(the department already customizes what's actually taught vs. the official
scheme — see open question in §9) can change shape without a migration. A
normalized `Course` table (3.5) is still derived/materialized from this JSON
for the GA engine and for querying — `content` is the source-of-record,
`Course` rows are a queryable projection of it, rebuilt on upload.

### 3.7 Timetable
```
Timetable
- id
- division_id          -> Division
- status               "draft" | "generating" | "published" | "archived"
- algorithm_version     string (for reproducibility)
- generation_params     jsonb (population size, generations run, etc.)
- fitness_score         float
- conflict_list         jsonb[]  -- unresolved soft-constraint misses at time of publish
- version               int
- created_at / published_at

TimetableSession  (child — one row per placed class = one GA gene, materialized)
- id
- timetable_id         -> Timetable
- course_id            -> Course
- teacher_id           -> Teacher
- room_id               -> Classroom
- day                   "Mon".."Fri"
- start_time / end_time
- is_lab                bool
- lab_batch_id           -> LabBatch | null
```

### 3.8 Relationships at a glance
```
Department 1---N Program          (one Program row per department + level;
                                   only is_schedulable programs go further)
Program 1---N Division 1---N TimetableSession N---1 Timetable
Program 1---N CourseScheme 1---N Course
Division N---1 CourseScheme
Teacher 1---N TimetableSession   (cross-program: query by teacher_id alone,
                                   never scoped to one Program — this is how
                                   cross-program clash detection works)
Classroom 1---N TimetableSession
Division 1---N LabBatch N---1 Course
```

---

## 4. Backend Folder Structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI app entrypoint
│   ├── core/
│   │   ├── config.py             # settings (env-driven: DB URL, CORS, etc.)
│   │   └── security.py           # (future — RBAC/auth)
│   ├── db/
│   │   ├── session.py            # SQLAlchemy engine/session
│   │   └── base.py               # declarative base + model registry
│   ├── models/                   # SQLAlchemy ORM models
│   │   ├── program.py
│   │   ├── division.py
│   │   ├── classroom.py
│   │   ├── teacher.py
│   │   ├── course.py
│   │   ├── course_scheme.py
│   │   └── timetable.py
│   ├── schemas/                  # Pydantic request/response models
│   │   └── (mirrors models/, one file per entity)
│   ├── scheduler/                # THE GA ENGINE — isolated from API layer
│   │   ├── chromosome.py          # encode/decode a timetable <-> gene array
│   │   ├── fitness.py             # calls constraints/, aggregates penalty score
│   │   ├── constraints/
│   │   │   ├── hard.py             # teacher clash, room clash, cross-part clash
│   │   │   └── soft.py             # preference misses, load balance, gaps
│   │   ├── operators.py           # selection, crossover, mutation
│   │   └── engine.py              # the generation loop (population -> iterate -> result)
│   ├── api/
│   │   └── v1/
│   │       ├── router.py          # aggregates all endpoint routers
│   │       └── endpoints/
│   │           ├── programs.py
│   │           ├── divisions.py
│   │           ├── teachers.py
│   │           ├── classrooms.py
│   │           ├── course_schemes.py   # upload/preview/delete-with-warning
│   │           ├── timetables.py        # generate/publish/export
│   │           └── dashboard.py         # live availability endpoint
│   └── services/
│       ├── course_scheme_service.py     # parse uploaded PDF/Word -> content jsonb
│       ├── dashboard_service.py          # "what's happening right now" query
│       └── export_service.py             # Word/PDF rendering with IMCS logo
├── tests/
│   ├── scheduler/                 # constraint + fitness + GA-loop tests
│   └── api/
├── alembic/                       # DB migrations (core relational tables only)
├── requirements.txt
└── .env.example
```

**Rule enforced by this layout:** `api/endpoints/timetables.py` calls
`scheduler/engine.py`; it never contains scheduling logic inline. Every hard
and soft constraint is its own testable function in `constraints/hard.py` /
`constraints/soft.py`, not embedded in `fitness.py`.

---

## 5. Frontend Folder Structure

```
frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx                   # homepage — departments CS -> AI -> Math, each listing its levels
│   ├── (programs)/
│   │   └── [programCode]/
│   │       └── [part]/page.tsx    # division timetable view
│   ├── dashboard/page.tsx         # live availability dashboard
│   ├── schemes/page.tsx           # course scheme upload/preview/delete
│   └── api/                       # (only if BFF routes are ever needed)
├── components/
│   ├── ui/                        # buttons, cards, dialogs — palette-driven
│   ├── timetable/                 # grid/continuous-list rendering
│   ├── dashboard/                 # availability cards, status pills
│   └── scheme-upload/             # upload + preview + delete-confirm dialog
├── lib/
│   ├── api-client.ts              # typed fetch wrapper to backend
│   └── theme.ts                   # color tokens (see §7), light/dark
├── public/
│   └── imcs-logo.png
├── tailwind.config.ts
├── next.config.js
└── package.json
```

**Homepage hierarchy:** the three Departments render in order (Computer
Science → Artificial Intelligence → Mathematics), and each lists **all** of
its program levels, not only BS. Only programs with `is_schedulable = true`
(BS today) link through to a timetable view at `[programCode]/[part]`; every
other level is listed as an informational / "coming soon" entry with no
timetable route behind it. See §3.1.

---

## 6. Genetic Algorithm Design

**Genetic Algorithm is the sole, permanent scheduling approach for this
project.** This was evaluated and decided early on and is not revisited: no
OR-Tools, no CP-SAT, no constraint-programming solver, and no "GA now,
hybridize later" plan. Everything in this section, and everything built in
`scheduler/dev_scripts/` (Phases 4-6, see `docs/CONSTRAINTS.md`), assumes
pure GA end to end.

### 6.1 Chromosome
One chromosome = one full candidate `Timetable` for a given Division.
Each **gene** = one session assignment:
```
gene = (course_id, teacher_id, room_id, day, start_time)
```
A chromosome is an array of genes, one per required session (theory +
lab-batches) for that Division's active Course Scheme.

### 6.2 Fitness Function
`fitness(chromosome) = -( Σ hard_violations * HARD_WEIGHT + Σ soft_violations * SOFT_WEIGHT )`

**Hard constraints** (heavy penalty — from `constraints/hard.py`):
- Teacher double-booked (same teacher, overlapping day/time, any Division —
  cross-program included, since Teacher is queried globally, not per-Program).
- Room double-booked.
- A teacher assigned two different Parts/sections at the same slot
  (cross-part clash — the specific case the co-supervisor flagged).
- Teacher assigned outside their declared `availability` window.
- Lab batches of the same course scheduled with conflicting teacher/room
  within their own split.

**Soft constraints** (light penalty — from `constraints/soft.py`):
- Unmet *preferred* (not hard-blocked) time slots.
- Uneven daily/weekly load across the week for one teacher or one Division.
- Poor gap distribution (e.g. large idle gaps in a student's day).

### 6.3 Loop
```
Selection  -> tournament or roulette over population, favor higher fitness
Crossover  -> single/two-point crossover over the gene array, repaired if it
              creates a duplicate hard-slot assignment
Mutation   -> re-roll one gene's (room, day, start_time) — never re-roll
              course/teacher pairing, that's fixed by the Course Scheme
Iterate    -> until fitness plateau or max_generations reached
```

### 6.4 How the GA loop was actually validated
The original plan was a One Max bit-string sanity check before touching the
real chromosome. That step was skipped: Phases 4-6
(`scheduler/dev_scripts/phase4_bscs_part1_ga.py`,
`phase5_multi_division_ga.py`, `phase6_full_bscs_morning_ga.py`) went
straight to the real timetable chromosome and fitness function on real
department data, and validated selection/crossover/mutation by running the
GA to convergence (0 hard violations) across 10+ seeds per phase, plus a
deliberate "break one rule, confirm the detector fires" test per constraint.
That proved the loop mechanically works without a separate toy problem. See
`docs/CONSTRAINTS.md` for the constraint list these dev scripts implement
and verify, and `docs/PROJECT_AUDIT.md` for what is proven versus still
fragile.

---

## 7. Course Scheme Management

1. Admin uploads a PDF/Word file via `schemes/page.tsx`.
2. Frontend shows a **preview** (parsed table: semester → course rows) before
   confirming upload — nothing is written until confirmed.
3. On confirm, `course_scheme_service.py` parses the file and stores it as
   `CourseScheme.content` (JSONB), stamped with `scheme_year` and
   `program_id`. A normalized `Course` row set is materialized from `content`
   for querying/GA use.
4. Deleting a scheme first checks (`course_scheme_service.py`) whether any
   `Division` referencing it has a `published` `Timetable`. If so, the
   frontend shows a blocking warning instead of a silent delete —
   `is_active = false` (soft-delete) is used instead of a hard delete so
   history is never corrupted.
5. **No backend schema change is ever required for a new scheme year** —
   a new year is just a new `CourseScheme` row with its own `content` blob.

**Confirmed starting point for Phase 2:** the `course_schemes` and `courses`
tables exist from Phase 1 but are empty. Phase 2 populates **BSCS only, scheme
year 2024** — the scheme we already hold the PDF for. Other programs and years
follow once their documents are collected (§11.3).

---

## 8. Live Dashboard

Not a separately maintained state — **derived** on request:
`dashboard_service.py` takes "now" (current day + time), queries
`TimetableSession` rows for all `published` Timetables, and returns:
- Which teachers currently have a session (busy) vs. not (available).
- Which rooms are currently occupied vs. free.
- Aggregate counts: total rooms, total labs, total halls (from `Classroom`).

Exposed via a single `GET /api/v1/dashboard/status` endpoint. No caching
layer or background job needed at this scale — it's a filtered query per
request.

**Future AI query layer** (explicitly not RAG): Gemini free tier with
function-calling. Gemini maps a natural-language question ("who's teaching
right now", "is Room 05 free") to one of `getCurrentClass`,
`getTeacherSchedule`, `getRoomStatus`, `getFreeRooms`, the backend runs the
real DB query, Gemini phrases the result. RAG is reserved only for genuinely
unstructured content added later (policy docs, FAQs) — never for live
schedule/room-status facts.

---

## 9. Export (Word / PDF)

`export_service.py` renders a `published` Timetable to:
- **Word (.docx)** — python-docx, with the IMCS logo (`public/imcs-logo.png`
  / a backend-side copy) placed in the document header.
- **PDF** — either rendered directly (e.g. via a PDF library) or generated
  by converting the same Word output, to guarantee both exports stay
  visually consistent.

Layout follows the "general/continuous" timetable format the department
described (Class 1 → last class in sequence) rather than a rigid fixed-grid
image, matching how the real department timetables actually read.

---

## 10. Color Palette (reference)

Full source: `docs/color-palette.md`. Summary for implementers:

- Primary blue (buttons/links/active-nav only, never a background):
  `#16324F` light · `#3D6E9E` dark
- Light theme: bg `#F5F5F5`, cards `#FFFFFF`, text `#1A1A1A`
- Dark theme: bg `#0A0A0A`, cards `#171717`, text `#F5F5F5`
- Status pills (dashboard only, deliberately outside brand palette):
  available `#22C55E`, busy `#F59E0B`, conflict `#EF4444`

---

## 11. Open Questions (track, don't silently resolve)

1. Does BS Mathematics have a PM/PE split from Part-II like CS/AI, or none
   at all? Currently modeled as `has_pm_pe_split_from_part = null` for Math
   — needs department confirmation.
2. The official Course Scheme documents don't perfectly match what's
   actually taught in a given real semester (e.g. IOT, Mathematics-II,
   UHQ-II appear in real timetables but not the matching scheme doc). Needs
   clarification with the supervisor on whether the department customizes
   the official scheme, and if so, where that customization should live in
   the data model.
3. BSCS 2022 & 2025 schemes, and all BSAI/Math scheme years, are still to be
   collected.
4. Which non-BS levels (Master, M.Phil, Ph.D, M.Sc. Pass, PGD) will eventually
   need real timetables, and do they use the same Division / Shift / Group
   structure as BS? Deferred until a level beyond BS is actually scheduled —
   until then those programs carry `is_schedulable = false` (§3.1).

---

## 12. Explicitly Out of Scope (do not build unless asked)

- Events management (seminars, viva panels, invigilation duty, academic
  calendar sync).
- Faculty leave/substitute suggestions, room/resource inventory, RBAC,
  notifications, audit logs, utilization reports.
- Any RAG-based chatbot for live schedule data (see §8).
- Divisions, Course Schemes and Timetables for non-BS program levels. Those
  levels are modeled and listed only; scheduling them is future work (§3.1).

---

## 13. Phase Status

- **Phase 0 — done.** FastAPI + Next.js scaffold with the folder structure in
  §4/§5, a health endpoint and a homepage stub.
- **Phase 1 — done.** SQLAlchemy models for Department, Program, Classroom,
  Teacher, CourseScheme and Course; Alembic wired to the app settings and the
  first migration applied to Supabase; the three departments and all their
  program levels seeded (BS only is schedulable); `GET /api/v1/programs`
  serving real data.
- **Phase 2 — done.** Course Scheme management per §7 — upload, preview,
  delete-with-warning — starting with **BSCS, scheme year 2024**, saved in
  the database from the real university scheme document.
- **Phase 3 — done.** Lab pairing fixed (a lab is `has_lab` + `lab_credit_hours`
  on its theory course, never a course of its own), demo polish on the
  Course Scheme flow, and a real-data stats overview page/endpoint
  (`GET /api/v1/dashboard/stats` — counts only, not teacher/room
  availability, which needs generated timetables).
- **Phases 4-6 — done, standalone dev scripts only.** The GA in
  `backend/app/scheduler/dev_scripts/` (`phase4_bscs_part1_ga.py`,
  `phase5_multi_division_ga.py`, `phase6_full_bscs_morning_ga.py`) was
  built and proven directly against real timetable data — one division,
  then four, then all eight BSCS Morning divisions (Part-I through
  Part-IV, PM/PE). **These scripts are not wired into the database, the
  API, or the frontend** — they run standalone and print their result to
  the terminal. See `docs/CONSTRAINTS.md` for the constraint list they
  implement and `docs/PROJECT_AUDIT.md` for the full file map and
  fragility notes.
- **Reference data for GA development, from this cleanup phase onward:**
  `docs/timetable.json` is now the source of truth for real
  BSCS/BSAI Morning-shift timetable data used to build and test the GA —
  course names, full teacher names, rooms, days, times and PM/PE sections
  for every department/program, already resolved into one clean structured
  file. It **replaces the manual PDF-extraction approach Phases 4-6 used**
  (reading scanned timetable PDFs by hand and typing the data into each
  dev script), which was error-prone — see the initials collisions found
  in Phases 5-6 (e.g. `A.B` meant three different people on three
  different sheets). This is a GA-development data source only; it is
  unrelated to and does not change the Course Scheme upload feature (§7),
  which still parses admin-uploaded PDF/Word files at runtime.
- **After the GA is trusted:** wire it to the database (Division/Timetable
  models), add generate/publish endpoints, build a frontend to trigger and
  view a generated timetable, then authentication (faculty-only Google
  sign-in via Supabase Auth; students read without logging in — no auth
  fields exist on any model yet, by design), then the live dashboard (§8)
  and export (§9).
