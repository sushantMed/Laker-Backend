from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    # ── Application ───────────────────────────────────────────────
    app_env: str = "development"
    app_debug: bool = False
    app_version: str = "1.0.0"

    # ── Database ──────────────────────────────────────────────────
    db_driver: str
    db_user: str
    db_password: str
    db_host: str
    db_port: int
    db_name: str

    # ── Redis / Cache ─────────────────────────────────────────────
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    cache_enabled: bool = True
    cache_default_ttl_seconds: int = 300

    # ── Security ──────────────────────────────────────────────────
    jwt_secret_key: str

    # ── Rate Limiting ─────────────────────────────────────────────
    rate_limit_enabled: bool = False
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    @property
    def database_url(self) -> str:
        user = quote_plus(self.db_user)
        password = quote_plus(self.db_password)
        if self.db_driver.startswith("oracle"):
            return (
                f"{self.db_driver}://{user}:{password}"
                f"@{self.db_host}:{self.db_port}/?service_name={self.db_name}"
            )
        return (
            f"{self.db_driver}://{user}:{password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
