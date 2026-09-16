"""Shared FastAPI dependencies for the API layer.

See docs/PROJECT_ARCHITECTURE.md §4.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db

# Every endpoint that touches the database takes this instead of repeating Depends(get_db).
DbSession = Annotated[Session, Depends(get_db)]
