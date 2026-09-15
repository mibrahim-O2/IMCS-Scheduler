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

---

## 2. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Python 3.11+, FastAPI | Async, typed, clean separation of routes vs. logic |
| Scheduling engine | Pure Python (DEAP-style custom GA, no framework lock-in) | Full control over chromosome/fitness design |
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

### 3.1 Program
```
Program
- id
- name            e.g. "BS Computer Science"
- short_code      "BSCS" | "BSAI" | "MATH"
- has_shift_split  bool   (True for CS/AI, False for Math)
- has_pm_pe_split_from_part  int | null   (2 for CS/AI, null for Math — unconfirmed, kept overridable)
- total_semesters  int (8)
- level           "BS" | "Masters" | "MPhil"   (for homepage hierarchy: BSCS shows all its levels first)
```

### 3.2 Division (a.k.a. Section)
The unit an actual timetable is generated for: one Program + Part + Shift
(+ Group where applicable).
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
The flexible piece — one row per Program + scheme (admission) year.
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
│   │   ├── engine.py              # the generation loop (population -> iterate -> result)
│   │   └── onemax_sanity_check.py # scaffolding-only GA machinery test
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
│   ├── page.tsx                   # homepage — hierarchy: BSCS -> BSAI -> Math
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

---

## 6. Genetic Algorithm Design

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

### 6.4 Sanity Check First
`scheduler/onemax_sanity_check.py` implements the classic One Max problem
(evolve a random bit-string to all 1s) purely to prove the
selection/crossover/mutation loop in `operators.py` is mechanically correct,
in isolation from the timetabling domain. This file is scaffolding, not a
feature, and is expected to be deleted or moved to `tests/` once the real
chromosome/fitness function is wired in and passing its own tests.

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

---

## 12. Explicitly Out of Scope (do not build unless asked)

- Events management (seminars, viva panels, invigilation duty, academic
  calendar sync).
- Faculty leave/substitute suggestions, room/resource inventory, RBAC,
  notifications, audit logs, utilization reports.
- Any RAG-based chatbot for live schedule data (see §8).
- Hybrid GA + OR-Tools CP-SAT — noted as a possible future upgrade if pure
  GA convergence proves too slow, not part of the current build.

---

## 13. Immediate Next Step

Minimal scaffold only (this phase): empty/starter FastAPI app with a health
endpoint, empty/starter Next.js app with a homepage stub, correct folder
structure per §4/§5, no models/GA/features implemented yet. Real
implementation begins in a later, explicitly confirmed phase.
