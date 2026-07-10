import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


def default_database_url() -> str:
    if os.getenv("VERCEL"):
        return "sqlite:////tmp/rss_monitor.db"
    return "sqlite:///./rss_monitor.db"


class Settings(BaseSettings):
    app_name: str = "Economic RSS Monitor"
    database_url: str = default_database_url()
    fetch_interval_hours: int = 3
    scheduler_enabled: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
