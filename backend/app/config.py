"""App settings. Every value comes from an environment variable (or the `.env` file locally).

The full list with explanations is in `.env.example`. On Vercel, set them in Project → Settings → Environment Variables.
"""
import os
from urllib.parse import quote, unquote

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET = "change-me-in-the-env-file-to-a-long-random-text"
DEFAULT_PASSWORD = "JobHunt@2026"


def encode_password(url: str) -> str:
    """'postgresql://user:p@ss@host/db' -> 'postgresql://user:p%40ss@host/db'.
    Database passwords often contain @ : / # (Supabase, Neon); pasted unencoded they break the link. Idempotent."""
    if "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    slash = rest.find("/", rest.rfind("@") + 1) if "@" in rest else -1
    netloc, tail = (rest[:slash], rest[slash:]) if slash != -1 else (rest, "")
    if "@" not in netloc:
        return url
    userinfo, host = netloc.rsplit("@", 1)
    if ":" not in userinfo:
        return url
    user, password = userinfo.split(":", 1)
    return f"{scheme}://{user}:{quote(unquote(password), safe='')}@{host}{tail}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    # Database. Neon / Vercel give "postgresql://…?sslmode=require": it is converted for SQLAlchemy automatically.
    # The Neon integration on Vercel sets POSTGRES_URL / DATABASE_URL; both names work.
    # APP_DATABASE_URL wins over both: use it to point the app at another database (e.g. Supabase) without
    # touching the variables a Vercel integration manages.
    database_url: str = Field("postgresql+psycopg://localhost:5432/germany_jobs",
                              validation_alias=AliasChoices("APP_DATABASE_URL", "DATABASE_URL", "POSTGRES_URL"))
    db_pool_size: int = 5
    auto_migrate: bool = True          # create tables + apply NEW_COLUMNS on start-up

    secret_key: str = DEFAULT_SECRET   # signs login tokens
    token_days: int = 7                # how long a login stays valid

    # The only login. Created automatically on start-up. Change it (required on Vercel).
    master_username: str = "arpita"
    master_password: str = DEFAULT_PASSWORD
    cors_origins: list[str] = ["http://localhost:5001"]

    # "server" = background threads (local ./start.sh); "serverless" = work in steps (Vercel); "auto" = serverless on Vercel.
    run_mode: str = "auto"
    step_seconds: int = 240            # how long one serverless search step may run (Vercel Hobby limit is 300 s)
    cron_secret: str = ""              # Vercel Cron sends "Authorization: Bearer <CRON_SECRET>"

    # Start the automation by itself every day (server mode; on Vercel the crons in vercel.json do it). Tests turn this off.
    daily_scheduler: bool = True

    # Job roles to search for, comma-separated, e.g. "Data Analyst, BI Developer".
    # Empty = Arpita's roles. Only the default: whatever is saved on the Settings page wins.
    job_keywords: str = ""

    # Your CV as JSON (same shape as DEFAULT_PROFILE in defaults.py), to run the app for someone else.
    # PROFILE_JSON = the JSON text itself (handy on Vercel), PROFILE_FILE = path to a .json file. Used when the profile is created.
    profile_json: str = ""
    profile_file: str = ""

    # Optional AI: research, mock-interview grading, answer drafts, cover letters.
    ai_api_key: str = ""
    ai_model: str = "claude-opus-5-5"

    @field_validator("database_url")
    @classmethod
    def sqlalchemy_url(cls, url: str) -> str:
        url = encode_password(url.strip())
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix):]
        return url

    @property
    def serverless(self) -> bool:
        return self.run_mode == "serverless" or (self.run_mode == "auto" and bool(os.environ.get("VERCEL")))

    def check_for_production(self) -> None:
        """A public deployment must not run with the default password or token secret."""
        if not self.serverless:
            return
        problems = [name for name, bad in (("DATABASE_URL", "@localhost" in self.database_url or "//localhost" in self.database_url),
                                           ("SECRET_KEY", self.secret_key == DEFAULT_SECRET or len(self.secret_key) < 32),
                                           ("MASTER_PASSWORD", self.master_password == DEFAULT_PASSWORD or len(self.master_password) < 10))
                    if bad]
        if problems:
            raise RuntimeError(f"Set {' and '.join(problems)} in the Vercel environment variables (see .env.example).")


settings = Settings()
