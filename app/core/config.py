from functools import lru_cache

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

    # ── Security ──────────────────────────────────────────────────
    jwt_secret_key: str

    # ── Rate Limiting ─────────────────────────────────────────────
    rate_limit_enabled: bool = False
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    @property
    def database_url(self) -> str:
        return (
            f"{self.db_driver}://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"



@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
