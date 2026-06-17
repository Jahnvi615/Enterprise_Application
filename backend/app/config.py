from pydantic_settings import BaseSettings
from pydantic import field_validator
from enum import Enum
from pathlib import Path
import json


class StorageProvider(str, Enum):
    LOCAL = "local"
    AZURE = "azure"


class JobRunner(str, Enum):
    SYNC = "sync"
    CELERY = "celery"


class Settings(BaseSettings):
    app_name: str = "BalanceIQ"
    app_env: str = "local"
    debug: bool = True

    # Security
    secret_key: str = "change-me-in-production"
    jwt_secret_key: str = "change-me-jwt-secret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # Database
    database_url: str = "sqlite:///./data/balanceiq.db"

    # Storage
    storage_provider: StorageProvider = StorageProvider.LOCAL
    storage_local_path: str = "./data/storage"

    # Job Runner
    job_runner: JobRunner = JobRunner.SYNC
    redis_url: str = "redis://localhost:6379/0"

    # CORS
    cors_origins: list[str] = ["http://localhost:4200"]

    # Logging
    log_level: str = "DEBUG"

    # Data directory
    data_dir: Path = Path("./data")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }

    @property
    def is_local(self) -> bool:
        return self.app_env == "local"

    def ensure_directories(self):
        dirs = [
            self.data_dir,
            self.data_dir / "uploads",
            self.data_dir / "outputs",
            self.data_dir / "storage",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
