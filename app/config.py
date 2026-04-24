"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    Loaded from environment variables or `.env` file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Nytia Recommender"
    app_version: str = "0.1.0"
    environment: str = "development"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000


settings = Settings()