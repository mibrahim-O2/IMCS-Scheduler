# Project Context: IMCS Scheduler

## Goal
Build a full-stack, AI-assisted timetable generation and academic scheduling
system for the Institute of Mathematics & Computer Science (IMCS), University
of Sindh. The system generates conflict-free class timetables using a Genetic
Algorithm, manages course schemes per program per admission year, and gives
students/teachers/admins a live view of schedules and room/teacher
availability. This is a real Final Year Project — build the actual system
from day one, not a throwaway prototype.

## Tech Stack
- **Backend**: Python (FastAPI), running the Genetic Algorithm scheduling engine
- **Frontend**: Next.js / React
- **Database**: PostgreSQL or MongoDB (decide per data shape — relational
  entities like Program/Teacher/Room/Course favor PostgreSQL; flexible
  per-scheme-year documents may favor MongoDB — confirm before scaffolding)
- **Repo**: github.com/mibrahim-O2/IMCS-Scheduler
- **Local path**: `D:\FYP\IMCS Scheduler`

## Current Focus
Backend and Genetic Algorithm logic first. Get the scheduling engine correct
and tested before investing in frontend polish. Everything built is part of
the final codebase — no disposable/throwaway scaffolding.

## Institutional Structure (do not re-derive — treat as given)
- **3 programs** under IMCS: BS Computer Science (BSCS), BS Artificial
  Intelligence (BSAI), BS Mathematics.
- CS and AI each run **Morning + Evening shifts**. Mathematics has no shift split.
- From **Part-II onward, CS and AI split into Pre-Medical (PM) and
  Pre-Engineering (PE) groups** — separate rooms, separate teachers per group.
  Mathematics has no PM/PE split (unconfirmed with department — verify before
  hardcoding this assumption).
- **Physical resources**: ~14 spaces — Rooms 01–10, Multimedia-1, Hall-1/2/3.
- **~50 teachers**, several teaching across BOTH BSCS and BSAI at once —
  cross-program clash-checking is mandatory, not optional.
- **Lab-batch pattern**: a single lab subject can run as multiple parallel
  sub-batches with different teachers at the exact same time slot (e.g. one
  lab split 3 ways). The data model must support a Division/Section having
  multiple independently-assigned lab batches.
- **Data-quality rule**: teacher initials (e.g. A.B, H.B, A.A, S.S, K.B)
  collide across different sheets/programs and refer to different people.
  Always resolve teachers by full name, never by initials alone. Original
  scanned timetable PDFs are the source of truth — never trust a prior
  digitized dataset over the original scan.

## Course Scheme Rules
- A **Course Scheme** is defined per program, per **admission/scheme year**
  (not calendar year) — course code, name, credit hours, marks, lab/theory flag.
- A student's applicable scheme is fixed at their admission year and followed
  for all 8 semesters (a Part-III student in 2026 follows a different scheme
  year than a Part-I student in 2026).
- **The Course Scheme must be entirely frontend-manageable**: admin uploads a
  PDF/Word file, sees a **preview before confirming upload**, can delete an
  old scheme or add a new one with a **proper warning/confirmation dialog on
  delete**, and the **scheme year is always clearly labeled** in the UI.
- **Design goal**: adding a new year's course scheme must never require a
  database schema change or backend redeploy — the storage model must be
  generic enough (e.g. a flexible course-list-per-scheme-year document/table)
  that the frontend alone manages new/old scheme data.
- Before deleting a scheme year, check whether it's referenced by any
  active/published timetable — warn and block/confirm accordingly, don't
  silently corrupt history.

## Genetic Algorithm Rules
- **Chromosome** = one full candidate timetable, encoded as an array of
  session assignments: `[subject, teacher, room, day, time]` per gene.
- **Population** = many candidate timetables evaluated per generation.
- **Fitness function** = the department's "cost function":
  - Heavy penalty: teacher double-booking, room double-booking, a teacher
    getting two different Parts/sections at the same time slot.
  - Lighter penalty: unmet teacher time preferences, uneven daily/weekly load,
    poor gap distribution.
- **Selection → Crossover → Mutation → Iterate** across generations until an
  acceptable (low-violation) timetable emerges.
- Scheduling is **feasibility-based, not a rigid fixed grid** — if a teacher
  is unavailable at a given slot, the algorithm assigns another slot rather
  than forcing a template. Each teacher's own stated availability is an input
  constraint, not something the system overrides.
- Start with a minimal **One Max sanity-check** (a classic simple bit-string
  GA test) purely to confirm the selection/crossover/mutation loop is
  implemented correctly, before wiring in the real timetable chromosome and
  fitness function. This is a scaffolding step, not a feature.

## Architecture & Code Rules
1. Keep the GA engine (`scheduler`/`ga_engine` module) isolated from the API
   layer — the FastAPI routes should call into pure scheduling functions, not
   contain scheduling logic inline.
2. Isolate all hard constraints (teacher clash, room clash, cross-part clash)
   and soft constraints (preferences, load balance) as separately testable
   functions — do not hardcode them inline in the fitness function body.
3. Data model must include, as first-class entities: Program, Division/Section
   (with PM/PE group and multiple lab batches), Classroom/Room (with type —
   lecture/lab/hall — and capacity), Teacher (with availability and
   cross-program load), Course (sourced from the active Course Scheme), and
   Timetable (versioned, with a generation-status and conflict list).
4. Write concise, self-documenting functions. Do not create redundant utility
   files. Keep each module focused on one responsibility.
5. Do not introduce Abstract Syntax Tree / Genetic Programming approaches —
   this was considered and explicitly rejected as the wrong fit for a
   fixed-structure assignment problem like timetabling.

## Features to Implement (in rough priority order)
1. **Core GA scheduling engine** (current focus) — generate a valid timetable
   for a given program/part/shift given teachers, rooms, and course-scheme subjects.
2. **Course Scheme management** — upload, preview, delete-with-warning,
   year-labeled, frontend-driven (no schema change per new year).
3. **Homepage hierarchy** — BSCS (and its levels: BS/Masters/MPhil) first,
   then BSAI (and its programs), then BS Mathematics (and its programs).
4. **Live Dashboard** — which teachers are available/unavailable right now,
   which rooms are free, derived by matching current day+time against the
   generated timetable data (a simple "get current status" API).
5. **Resource counts** — total rooms, labs, halls shown on the dashboard.
6. **Export** — generated timetable downloadable as Word and PDF, with the
   IMCS logo.

## Explicitly Out of Scope For Now (do not build unless asked)
- Events management (seminars, viva scheduling, invigilation duty) — discussed
  as future scope, not part of the current build.
- Faculty leave/substitute-suggestion system, room inventory, audit logs,
  role-based dashboards — future scope, not current build.
- Any RAG-based chatbot. If a natural-language query feature is added later,
  it should use function-calling (e.g. Gemini) against real DB queries — never
  vector-similarity retrieval for live schedule/room-status questions.

---

Before writing any code, read everything above and tell me back, in your own
words, what you understand this project to be — the department structure, the
algorithm approach, the tech stack decision, and what the immediate next step
is. Do not start implementation yet. Once I confirm your understanding is
correct, we begin.
