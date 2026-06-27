"""
Centralised application settings.

All runtime configuration is read from environment variables (or a .env file)
via a single Pydantic Settings class.  Every module that previously used
``os.getenv`` should import ``settings`` from here instead.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Single source of truth for every runtime knob."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── General ──────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # ── Database ─────────────────────────────────────────────────────────
    # Must be a PostgreSQL URL, e.g.
    #   postgresql://user:pass@host:5432/dbname
    DATABASE_URL: str  # required – no default

    # ── LLM (provider‑agnostic) ──────────────────────────────────────────
    # Supported providers: "openai", "gemini", "groq"
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o"
    LLM_API_KEY: str  # required – no default

    # ── Optional service keys ────────────────────────────────────────────
    SCRAPER_API_KEY: Optional[str] = None
    ENRICHMENT_API_KEY: Optional[str] = None

    # ── Operational tunables ─────────────────────────────────────────────
    MAX_RETRIES: int = 3
    HITL_TIMEOUT_SECONDS: int = 86400  # 24 h

    # ── Helpers ──────────────────────────────────────────────────────────
    def get_async_db_url(self) -> str:
        """Return the DATABASE_URL with the ``asyncpg`` driver for SQLAlchemy async."""
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgresql+asyncpg://"):
            return url
        # Already has a driver qualifier – return as‑is
        return url

    def get_sync_db_url(self) -> str:
        """Return a synchronous URL suitable for Alembic (uses ``psycopg`` driver)."""
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
        return url

    def get_checkpoint_db_url(self) -> str:
        """Return a raw ``postgresql://`` URL for LangGraph's AsyncPostgresSaver.

        The LangGraph postgres checkpointer uses ``psycopg`` internally and
        expects a plain ``postgresql://`` connection string (no SQLAlchemy
        driver suffix).
        """
        url = self.DATABASE_URL
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql://", 1)
        if url.startswith("postgresql+psycopg://"):
            return url.replace("postgresql+psycopg://", "postgresql://", 1)
        return url


# ── Global singleton ─────────────────────────────────────────────────────
settings = Settings()
