"""Starts the automation by itself once a day (no button needed).

Every minute it checks: is daily auto-start on, is it past the start time (e.g. 08:00), and has
nothing run today yet? Then it starts a normal automation run. If the computer was off at 08:00,
the run starts as soon as the backend is running again that day.
"""
import threading
import time
from datetime import datetime

from app.config import settings
from app.database import SessionLocal
from app.defaults import user_settings
from app.models import AutomationRun, Profile
from app.services import automation


def should_start(cfg: dict, now: datetime, last_start: datetime | None, running: bool) -> bool:
    """Pure decision (easy to test). now and last_start are in local time."""
    if not cfg.get("daily_auto_start") or running:
        return False
    hour, minute = (int(x) for x in str(cfg.get("daily_start_time", "08:00")).split(":"))
    if (now.hour, now.minute) < (hour, minute):
        return False
    return last_start is None or last_start.date() < now.date()


def check_once() -> None:
    with SessionLocal() as db:
        for profile in db.query(Profile).all():
            runs = db.query(AutomationRun).filter_by(user_id=profile.user_id)
            last = runs.order_by(AutomationRun.started_at.desc()).first()
            running = runs.filter(AutomationRun.status.in_(("RUNNING", "PAUSED"))).first() is not None
            last_start = last.started_at.astimezone() if last else None
            if should_start(user_settings(profile), datetime.now().astimezone(), last_start, running):
                automation.start(db, profile, {})


def _loop() -> None:
    while True:
        try:
            check_once()
        except Exception as exc:  # never let the scheduler die
            print(f"[scheduler] {exc}")
        time.sleep(60)


def start_scheduler() -> None:
    if settings.daily_scheduler:
        threading.Thread(target=_loop, daemon=True).start()
