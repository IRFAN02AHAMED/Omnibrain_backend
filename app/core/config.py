"""
config.py — Application Configuration
======================================
All environment-driven settings are loaded here using Pydantic BaseSettings.
Values are read from the .env file automatically.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central settings class.

    Values come from .env.
    Default values are used only when .env does not provide them.
    """

    # ── Application ──────────────────────────────────────────────────
    APP_NAME: str = "Ask Docs"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # ── Server ───────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── Database ─────────────────────────────────────────────────────
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    @property
    def DATABASE_URL(self) -> str:
        """
        Async PostgreSQL connection string used by FastAPI + SQLAlchemy.
        """
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # ── JWT ──────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── CORS ─────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    # ── Google OAuth ─────────────────────────────────────────────────
    # These values are used for Google login and Google APIs.
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"
    FRONTEND_URL: str = "http://localhost:5173"


    # ── Jira / Atlassian OAuth ───────────────────────────────────────
    ATLASSIAN_CLIENT_ID: str = ""
    ATLASSIAN_CLIENT_SECRET: str = ""
    ATLASSIAN_REDIRECT_URI: str = "http://localhost:8000/connectors/jira/callback"

    # ── GitHub OAuth ─────────────────────────────────────────────────
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_REDIRECT_URI: str = "http://localhost:8000/connectors/github/callback"

    # ── Gemini AI ────────────────────────────────────────────────────
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "models/gemini-embedding-001"
    GEMINI_MAX_RETRIES: int = 3
    GEMINI_TIMEOUT_SECONDS: int = 60

    # ── Hugging Face backup embedding ────────────────────────────────
    HUGGINGFACE_CHAT_MODEL: str = "Qwen/Qwen3-8B"
    HUGGINGFACE_API_KEY: str | None = None
    HUGGINGFACE_EMBEDDING_MODEL: str = "sentence-transformers/all-mpnet-base-v2"

    # ── Embeddings / Vector Search ───────────────────────────────────
    EMBEDDING_DIMENSIONS: int = 768
    VECTOR_SEARCH_TOP_K: int = 5

    # ── File Upload ──────────────────────────────────────────────────
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 20
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "docx", "txt"]

    # ── Chunking ─────────────────────────────────────────────────────
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100

    # ── Logging ──────────────────────────────────────────────────────
    LOG_FILE: str = "app.log"
    LOG_LEVEL: str = "DEBUG"

    # Pydantic Settings config
    # extra="ignore" prevents crash when .env has extra variables.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


"""
lru_cache is used to cache the settings object.

The .env file is read once when the backend starts, and the same settings object
is reused throughout the application. This avoids repeatedly loading
configuration values.
"""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Creates the Settings object once and reuses it.

    Returns:
        Settings: Loaded application settings.
    """
    return Settings()


settings: Settings = get_settings()