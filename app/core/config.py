from dataclasses import dataclass
from functools import lru_cache
from os import getenv

from dotenv import load_dotenv


load_dotenv()


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    project_name: str = getenv("PROJECT_NAME", "SillicoBio API")
    api_version: str = getenv("API_VERSION", "1.0.0")
    database_url: str = getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/sillicobio",
    )
    cors_origins: list[str] = None
    cors_origin_regex: str | None = getenv(
        "CORS_ORIGIN_REGEX",
        r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    )
    session_secret_key: str = getenv("SESSION_SECRET_KEY", "change-me-in-local-env")
    session_cookie_name: str = getenv("SESSION_COOKIE_NAME", "SESSION")
    session_https_only: bool = getenv("SESSION_HTTPS_ONLY", "false").lower() == "true"
    upload_dir: str = getenv("UPLOAD_DIR", "uploads")

    def __post_init__(self) -> None:
        if self.cors_origins is None:
            origins = getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
            object.__setattr__(self, "cors_origins", _csv(origins))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
