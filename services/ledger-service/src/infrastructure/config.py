"""Typed application settings, loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", frozen=True)

    # Required on purpose: fail fast instead of silently using a default database.
    database_url: str  # postgresql+asyncpg://user:password@host:port/dbname
    service_name: str = "ledger-service"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10
    health_check_timeout_seconds: float = 2.0


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # values come from the environment
