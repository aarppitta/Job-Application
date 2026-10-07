"""Start / pause / resume / stop the automation and read its live log."""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.auth import current_profile
from app.config import settings
from app.database import get_db
from app.defaults import user_settings
from app.models import AutomationLog, AutomationRun, Profile
from app.serialize import to_dict
from app.services import automation

router = APIRouter(prefix="/api/automation", tags=["automation"])


def latest_run(db: Session, profile: Profile) -> AutomationRun | None:
    return db.query(AutomationRun).filter_by(user_id=profile.user_id).order_by(AutomationRun.id.desc()).first()


def run_dict(run: AutomationRun) -> dict:
    return {**to_dict(run), "runtime_seconds": automation.runtime_seconds(run)}


@router.post("/start")
def start(body: dict | None = None, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    allowed = {"max_runtime_hours", "min_score", "repeat_every_minutes", "sources", "search_queries"}
    overrides = {k: v for k, v in (body or {}).items() if k in allowed}
    if float(overrides.get("max_runtime_hours", 6)) > 6:
        raise HTTPException(422, "Maximum runtime is 6 hours.")
    try:
        return run_dict(automation.start(db, profile, overrides))
    except ValueError as exc:
        raise HTTPException(409, str(exc))


def _set_status(db: Session, profile: Profile, new_status: str, allowed_from: tuple[str, ...]):
    run = latest_run(db, profile)
    if run is None or run.status not in allowed_from:
        raise HTTPException(409, "No automation to change.")
    run.status = new_status
    db.commit()
    return run_dict(run)


@router.post("/pause")
def pause(profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    return _set_status(db, profile, "PAUSED", ("RUNNING",))


@router.post("/resume")
def resume(profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    return _set_status(db, profile, "RUNNING", ("PAUSED",))


@router.post("/stop")
def stop(profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    return _set_status(db, profile, "STOPPED", ("RUNNING", "PAUSED"))


@router.get("/status")
def status(profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    run = latest_run(db, profile)
    return run_dict(run) if run else None


@router.get("/logs")
def logs(after_id: int = 0, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    """The page asks for new lines every 2 seconds (after_id = last line it has)."""
    run = latest_run(db, profile)
    if run is None:
        return []
    rows = db.query(AutomationLog).filter(AutomationLog.run_id == run.id, AutomationLog.id > after_id)\
        .order_by(AutomationLog.id).limit(500)
    return [to_dict(r) for r in rows]


@router.get("/runs")
def runs(profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    return [run_dict(r) for r in db.query(AutomationRun).filter_by(user_id=profile.user_id).order_by(AutomationRun.id.desc()).limit(20)]


@router.post("/step")
def step(profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    """Serverless mode: the Automation page calls this in a loop while the run is RUNNING (each call ≤ ~50 s)."""
    run = latest_run(db, profile)
    if run is None:
        raise HTTPException(409, "No automation run.")
    return run_dict(automation.step(db, run, min(50, settings.step_seconds)))


# ------------------------------------------------------------------ Vercel Cron (serverless daily run)

cron_router = APIRouter(prefix="/api/cron", tags=["cron"])


@cron_router.get("/daily")
def daily(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    """Called by Vercel Cron (several times each morning, see vercel.json). Starts today's run if needed, then works one step."""
    if not settings.cron_secret:
        raise HTTPException(503, "CRON_SECRET is not set.")
    if authorization != f"Bearer {settings.cron_secret}":
        raise HTTPException(401, "Wrong cron secret.")
    done = []
    for profile in db.query(Profile).all():
        cfg = user_settings(profile)
        run = latest_run(db, profile)
        today = datetime.now(UTC).date()
        if (run is None or run.status not in ("RUNNING", "PAUSED")) and cfg.get("daily_auto_start") \
                and (run is None or run.started_at.astimezone(UTC).date() < today):
            run = automation.start(db, profile, {})
        if run is not None and run.status == "RUNNING":
            run = automation.step(db, run, settings.step_seconds)
            done.append({"user_id": profile.user_id, "run": run.id, "status": run.status, "cursor": run.config.get("cursor")})
    return {"stepped": done}
