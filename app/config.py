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

    # Database
    db_host: str = "localhost"
    db_port: int = 5433
    db_name: str = "nytia_dev"
    db_user: str = "nytia_user"
    db_password: str = "local_dev_password"

    @property
    def database_url(self) -> str:
        """Build the SQLAlchemy database URL from settings."""
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()