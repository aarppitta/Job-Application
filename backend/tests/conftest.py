"""Tests use a separate database: germany_jobs_test (create it once with `createdb germany_jobs_test`)."""
import os

os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://localhost:5432/germany_jobs_test")
os.environ["AI_API_KEY"] = ""  # always use the offline templates in tests
os.environ["MASTER_USERNAME"] = "arpita"
os.environ["DAILY_SCHEDULER"] = "false"  # no automatic runs during tests
os.environ["MASTER_PASSWORD"] = "test-password"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from sqlalchemy import text  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_database():
    """Wipe the TEST database completely before each test (including tables from older app versions)."""
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        token = c.post("/api/auth/login", json={"username": "arpita", "password": "test-password"}).json()["token"]
        c.headers["Authorization"] = f"Bearer {token}"
        yield c
