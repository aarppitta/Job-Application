"""App settings. Values come from environment variables or the `.env` file."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str = "postgresql+psycopg://localhost:5432/germany_jobs"
    secret_key: str = "change-me-in-the-env-file-to-a-long-random-text"
    token_days: int = 7  # how long a login stays valid

    # The only login. Created automatically when the backend starts. Change it in .env.
    master_username: str = "arpita"
    master_password: str = "JobHunt@2026"
    cors_origins: list[str] = ["http://localhost:5001"]

    # Start the automation by itself every day (time is set in Settings). Tests turn this off.
    daily_scheduler: bool = True

    # Job roles to search for, comma-separated, e.g. "Data Analyst, BI Developer".
    # Empty = Arpita's roles. Only the default: whatever is saved on the Settings page wins.
    job_keywords: str = ""

    # Optional: set an Anthropic API key to let Claude write cover letters.
    # Without it, letters are built from templates (works offline).
    ai_api_key: str = ""
    ai_model: str = "claude-opus-5-5"


settings = Settings()
