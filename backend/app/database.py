"""Database connection. Tables are created automatically when the app starts."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

# Serverless (Vercel): each instance keeps only a tiny pool; Neon's pooled endpoint (-pooler) does the real pooling.
# Neon's pooled endpoint (PgBouncer, transaction mode) and psycopg's automatic prepared statements don't mix: turn them off there.
engine = create_engine(settings.database_url, pool_pre_ping=True, pool_recycle=300,
                       pool_size=1 if settings.serverless else settings.db_pool_size, max_overflow=2 if settings.serverless else 10,
                       connect_args={"prepare_threshold": None} if "-pooler" in settings.database_url else {})
SessionLocal = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: one database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Changes to existing tables (create_all() only creates NEW tables). Every line must be safe to run again.
NEW_COLUMNS = [
    "ALTER TABLE applications ADD COLUMN IF NOT EXISTS tailored_cv BYTEA",
    # 2026-09-29 simplification: applications = only jobs you actually applied to
    "DELETE FROM applications WHERE submitted_at IS NULL",
    "ALTER TABLE applications DROP COLUMN IF EXISTS cv_id, DROP COLUMN IF EXISTS cv_label, DROP COLUMN IF EXISTS cv_reason,"
    " DROP COLUMN IF EXISTS short_note, DROP COLUMN IF EXISTS answers, DROP COLUMN IF EXISTS checks,"
    " DROP COLUMN IF EXISTS manual_reason, DROP COLUMN IF EXISTS manual_detail, DROP COLUMN IF EXISTS response_received",
    "ALTER TABLE profiles DROP COLUMN IF EXISTS work_authorization_germany, DROP COLUMN IF EXISTS willing_to_relocate,"
    " DROP COLUMN IF EXISTS salary_expectation, DROP COLUMN IF EXISTS notice_period",
    "ALTER TABLE automation_runs DROP COLUMN IF EXISTS prepared",
    "DROP TABLE IF EXISTS messages, contacts, cvs",
    # 2026-10-07 job intelligence: richer application pipeline
    "ALTER TABLE applications ADD COLUMN IF NOT EXISTS cv_version VARCHAR(20), ADD COLUMN IF NOT EXISTS rejection_stage VARCHAR(30),"
    " ADD COLUMN IF NOT EXISTS next_follow_up TIMESTAMPTZ, ADD COLUMN IF NOT EXISTS last_contact_at TIMESTAMPTZ,"
    " ADD COLUMN IF NOT EXISTS referral BOOLEAN DEFAULT FALSE, ADD COLUMN IF NOT EXISTS analysis JSON DEFAULT '{}'",
    "UPDATE applications SET status = 'HR_SCREEN' WHERE status = 'INTERVIEW'",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS cv_prepared_at TIMESTAMPTZ",
    # 2026-10-19 freshness (closed jobs), deadlines, interview dates
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS deadline DATE, ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ,"
    " ADD COLUMN IF NOT EXISTS checked_at TIMESTAMPTZ, ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ",
    "UPDATE jobs SET last_seen_at = discovered_at WHERE last_seen_at IS NULL",
    "ALTER TABLE applications ADD COLUMN IF NOT EXISTS interviews JSON DEFAULT '[]'",
    # 2026-10-19 recruitment companies directory (table created by create_all)
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS agency VARCHAR(200)",
    # 2026-10-20 "not for me": hidden for good (a new scrape re-opens closed jobs, never dismissed ones)
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS dismissed_at TIMESTAMPTZ",
]


def create_tables():
    from sqlalchemy import text

    from app import models  # noqa: F401  (registers the tables)

    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        for statement in NEW_COLUMNS:
            conn.execute(text(statement))
