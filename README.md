# IMCS Scheduler

AI-assisted timetable generation and academic scheduling for the **Institute of
Mathematics & Computer Science (IMCS), University of Sindh**, built as a Final
Year Project by team AbstractMinds.

The system generates conflict-free class timetables with a Genetic Algorithm,
manages course schemes per program and admission year, and shows live teacher
and room availability.

**Start here:** [docs/PROJECT_ARCHITECTURE.md](docs/PROJECT_ARCHITECTURE.md), the
master blueprint for structure and design decisions. Supporting docs:
[docs/claude_instructions.md](docs/claude_instructions.md) (project context and
rules) and [docs/color-palette.md](docs/color-palette.md) (UI palette).

## Status

**Phase 0: scaffold only.** The FastAPI backend exposes `/` and `/health`; the
Next.js frontend renders a homepage stub. No database models, GA engine, or
features are implemented yet.

## Repository layout

```
backend/    FastAPI app + GA scheduling engine   (PROJECT_ARCHITECTURE.md §4)
frontend/   Next.js App Router + TypeScript + Tailwind   (§5)
docs/       Architecture, project context, color palette
```

## Prerequisites

- Python 3.11+
- Node.js 20.9+ with npm

## Run the backend

From `backend/`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
Copy-Item .env.example .env           # optional, defaults work; macOS/Linux: cp .env.example .env
uvicorn app.main:app --reload
```

If PowerShell blocks `Activate.ps1`, skip activation and run
`.\.venv\Scripts\python -m uvicorn app.main:app --reload` instead.

| URL | Returns |
|---|---|
| http://localhost:8000/ | App name, version, docs link |
| http://localhost:8000/health | `{"status": "ok", "environment": "development"}` |
| http://localhost:8000/docs | Interactive OpenAPI docs |

## Run the frontend

From `frontend/`:

```powershell
npm install
Copy-Item .env.example .env.local     # optional, defaults work; macOS/Linux: cp .env.example .env.local
npm run dev
```

Open http://localhost:3000.

## Theming

Palette tokens (`primary`, `surface`, `card`, `content`, `status-available`,
`status-busy`, `status-conflict`) are defined once in
`frontend/tailwind.config.ts`, taken from `docs/color-palette.md`. No other
frontend file contains hex values. Light/dark mode follows the operating
system's `prefers-color-scheme` setting (Tailwind `darkMode: "media"`).
