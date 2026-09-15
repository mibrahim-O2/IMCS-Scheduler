"""SQLAlchemy 2.0 engine and session factory.

Will build the engine from `Settings.database_url` (app/core/config.py) and
expose a request-scoped session dependency for FastAPI routes. Not connected
in Phase 0. See docs/PROJECT_ARCHITECTURE.md §2 and §4.
"""
