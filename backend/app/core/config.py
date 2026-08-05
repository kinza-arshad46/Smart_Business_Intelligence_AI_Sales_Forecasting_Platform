"""
Central application configuration.
All values can be overridden using environment variables or a .env file.
"""
import os
from pathlib import Path
from typing import List

try:
    from pydantic_settings import BaseSettings
    from pydantic import field_validator
except ImportError:
    # Fallback shim so the module still imports if pydantic-settings
    # is not installed yet (e.g. before `pip install -r requirements.txt`)
    class BaseSettings:  # type: ignore
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    def field_validator(*args, **kwargs):  # type: ignore
        def wrapper(f):
            return f
        return wrapper

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # --- General ---
    PROJECT_NAME: str = "Smart Business Intelligence & AI Sales Forecasting Platform"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")  # development | staging | production
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # --- Security / Auth ---
    SECRET_KEY: str = os.getenv("SECRET_KEY", "CHANGE_THIS_SECRET_KEY_IN_PRODUCTION_1234567890")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # --- Database ---
    # Default: local SQLite file (zero setup, works out of the box).
    # For production, set DATABASE_URL to a PostgreSQL DSN, e.g.:
    #   postgresql+psycopg2://user:password@localhost:5432/sales_bi
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'storage' / 'app.db'}"
    )

    # --- Redis (optional, used for caching / background jobs) ---
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    USE_REDIS: bool = os.getenv("USE_REDIS", "false").lower() == "true"

    # --- File storage ---
    UPLOAD_DIR: str = str(BASE_DIR / "storage" / "uploads")
    MODEL_DIR: str = str(BASE_DIR / "storage" / "models")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = [".csv", ".xlsx", ".xls"]

    # --- CORS ---
    CORS_ORIGINS: List[str] = ["*"]

    # --- Logging ---
    LOG_DIR: str = str(BASE_DIR / "logs")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # --- ML ---
    DEFAULT_FORECAST_HORIZON_DAYS: int = 30
    MODEL_RETRAIN_CRON: str = os.getenv("MODEL_RETRAIN_CRON", "0 2 * * *")  # 2 AM daily

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# Ensure required directories exist at import time
for _dir in (settings.UPLOAD_DIR, settings.MODEL_DIR, settings.LOG_DIR):
    Path(_dir).mkdir(parents=True, exist_ok=True)
