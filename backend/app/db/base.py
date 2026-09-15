"""Declarative base and model registry.

Will define the SQLAlchemy `Base` and import every model in app/models/ so
Alembic autogenerate sees the full schema. See docs/PROJECT_ARCHITECTURE.md §3–§4.
"""
