"""Application settings loaded from environment variables and backend/.env.

See docs/PROJECT_ARCHITECTURE.md §2 and §4.
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "staging", "production"] = "development"

    # Session-pooler URL (port 5432). Used by Alembic, which needs a connection
    # that supports DDL and prepared statements.
    database_url: str = "postgresql+psycopg://imcs:imcs@localhost:5432/imcs_scheduler"

    # Transaction-pooler URL (port 6543) for app runtime. Falls back to
    # database_url when unset, e.g. against a plain local Postgres.
    database_url_pooled: str = ""

    supabase_url: str = ""
    supabase_service_role_key: str = ""

    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_comma_separated(cls, value: object) -> object:
        # CORS_ORIGINS is written as a comma-separated string in .env, so turn it into a list.
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def runtime_database_url(self) -> str:
        # What the API actually connects with: the pooled URL if we have one, else the plain one.
        return self.database_url_pooled or self.database_url


@lru_cache
def get_settings() -> Settings:
    # Cached so every caller shares one Settings instance instead of re-reading .env.
    return Settings()
