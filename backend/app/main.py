"""FastAPI application entrypoint.

Phase 0 exposes only `/` and `/health`. The versioned router in
app/api/v1/router.py is mounted here once real endpoints exist.
See docs/PROJECT_ARCHITECTURE.md §4.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="IMCS Scheduler API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {"name": app.title, "version": app.version, "docs": "/docs"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}
