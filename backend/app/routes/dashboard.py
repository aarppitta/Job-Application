"""Numbers for the Dashboard page."""
from collections import Counter
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import current_profile
from app.database import get_db
from app.defaults import user_settings
from app.logic.market import reached
from app.models import Application, Job, Profile, Score

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard")
def dashboard(profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    midnight = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)  # local time
    threshold = user_settings(profile)["min_score"]
    jobs = db.query(Job.status, Job.ats_score, Job.discovered_at, Job.posted_at).filter(Job.user_id == profile.user_id).all()
    week_ago = midnight - timedelta(days=6)
    app_rows = db.query(Application).filter_by(user_id=profile.user_id).all()
    apps = [a.status for a in app_rows]
    top = db.query(Job).filter(Job.user_id == profile.user_id, Job.status == "QUALIFIED")\
        .order_by(Job.ats_score.desc()).limit(8).all()
    counts = {
        "Found today": sum(1 for j in jobs if j.discovered_at >= midnight),
        "Posted this week": sum(1 for j in jobs if (j.posted_at or j.discovered_at) >= week_ago and j.status != "RISK"),
        "Jobs found (total)": len(jobs),
        f"Matching (≥ {threshold}), not applied": sum(1 for j in jobs if j.status == "QUALIFIED"),
        "Skipped (low score)": sum(1 for j in jobs if j.status in ("NOT_QUALIFIED", "REVIEW", "RISK")),
        "Applied": len(apps),
        "Interview": sum(1 for a in app_rows if "HR_SCREEN" in reached(a)),   # reached HR screen or later
        "Rejected": sum(1 for a in apps if a == "REJECTED"),
    }
    # Skills to learn: what good and near-good jobs ask for that you don't have yet
    near = db.query(Score.missing_skills).join(Job, Job.id == Score.job_id)\
        .filter(Job.user_id == profile.user_id, Job.ats_score >= threshold - 10)\
        .order_by(Score.job_id, Score.id.desc()).distinct(Score.job_id).all()
    learn = Counter(skill for (missing,) in near for skill in missing)
    return {
        "skills_to_learn": [{"skill": s, "jobs": n} for s, n in learn.most_common(8)],
        "counts": counts,
        "top_matches": [{"id": j.id, "title": j.title, "company": j.company, "location": j.location,
                         "ats_score": j.ats_score, "visa_status": j.visa_status} for j in top],
    }
