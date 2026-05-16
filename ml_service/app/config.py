from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


def normalize_database_url(url: str) -> str:
    """Compatibilité Django (postgres://) → SQLAlchemy (postgresql+psycopg2://)."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and "+psycopg2" not in url:
        return "postgresql+psycopg2://" + url[len("postgresql://") :]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./local.db"
    api_host: str = "0.0.0.0"
    api_port: int = 8001
    debug: bool = True
    log_level: str = "INFO"

    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000"
    jwt_enabled: bool = False
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    api_key: str = ""

    media_base_url: str = "http://127.0.0.1:8000"
    artifacts_dir: Path = BASE_DIR / "artifacts"
    default_top_n: int = 12
    recommendation_cache_ttl: int = 300
    rate_limit: str = "60/minute"

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        if isinstance(value, str):
            return normalize_database_url(value)
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def vectorizer_path(self) -> Path:
        return self.artifacts_dir / "vectorizer.pkl"

    @property
    def dataframe_path(self) -> Path:
        return self.artifacts_dir / "dataframe.pkl"

    @property
    def model_path(self) -> Path:
        return self.artifacts_dir / "model.pkl"


@lru_cache
def get_settings() -> Settings:
    return Settings()
