"""SQLAlchemy engine and session factory for the API.

Runtime traffic goes through the transaction pooler (port 6543); Alembic uses
the session pooler instead. See docs/PROJECT_ARCHITECTURE.md §2 and §4.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# pgbouncer in transaction mode cannot reuse prepared statements across checkouts,
# so psycopg is told never to create them.
engine = create_engine(
    settings.runtime_database_url,
    pool_pre_ping=True,
    connect_args={"prepare_threshold": None},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    # FastAPI dependency: lends a session to one request and closes it when the request ends.
    with SessionLocal() as session:
        yield session
