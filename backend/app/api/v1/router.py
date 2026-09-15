"""Aggregates all v1 endpoint routers into one APIRouter.

Will be mounted in app/main.py under /api/v1 once the first real endpoint
exists; Phase 0 exposes only `/` and `/health`. See docs/PROJECT_ARCHITECTURE.md §4.
"""
