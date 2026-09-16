"""FastAPI application entrypoint.

Mounts the versioned API router under /api/v1 alongside the root and health
routes. See docs/PROJECT_ARCHITECTURE.md §4.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
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

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root() -> dict[str, str]:
    # Tiny landing payload so hitting the API root tells you what this service is.
    return {"name": app.title, "version": app.version, "docs": "/docs"}


@app.get("/health")
def health() -> dict[str, str]:
    # Liveness check; deliberately does not touch the database.
    return {"status": "ok", "environment": settings.app_env}
