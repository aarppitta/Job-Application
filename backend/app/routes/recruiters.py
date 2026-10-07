"""Recruiters page: companies with good jobs, by city, with LinkedIn/XING search links and pitches.

Nothing is scraped and nothing is sent: you open the search links yourself and send the pitch yourself.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import current_profile
from app.database import get_db
from app.defaults import user_settings
from app.logic.jd_parser import simplify
from app.logic.pitch import search_links, write_pitch
from app.models import Application, Job, Profile
from app.routes.jobs import get_job
from app.services.jobs import latest_score

router = APIRouter(prefix="/api", tags=["recruiters"])

# City filter -> spellings that can appear in a job's location
CITIES = {
    "Berlin": ["berlin"], "Munich": ["munich", "munchen"], "Stuttgart": ["stuttgart"], "Hamburg": ["hamburg"],
    "Frankfurt": ["frankfurt"], "Nuremberg": ["nuremberg", "nurnberg", "nuernberg"],
}


def in_city(job: Job, city: str | None) -> bool:
    if not city:
        return True
    if city == "Remote":
        return job.remote_type == "remote" or "remote" in simplify(job.location or "")
    return any(name in simplify(job.location or "") for name in CITIES.get(city, []))


@router.get("/recruiters")
def recruiters(city: str | None = None, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    """Companies that have good or near-good jobs for you (score ≥ threshold − 10), optionally in one city."""
    threshold = user_settings(profile)["min_score"]
    jobs = db.query(Job).filter(Job.user_id == profile.user_id, Job.ats_score >= threshold - 10, Job.status != "RISK")\
        .order_by(Job.ats_score.desc()).all()
    applied = {a.job_id for a in db.query(Application).filter_by(user_id=profile.user_id)}
    companies: dict[str, dict] = {}
    for job in jobs:
        if not in_city(job, city):
            continue
        entry = companies.setdefault(job.company, {"company": job.company, "jobs": [],
                                                   "links": search_links(job.company, city if city not in (None, "Remote") else None)})
        entry["jobs"].append({"id": job.id, "title": job.title, "location": job.location, "score": job.ats_score,
                              "good": (job.ats_score or 0) >= threshold, "applied": job.id in applied})
    return {"cities": [*CITIES, "Remote"], "companies": list(companies.values())}


class PitchRequest(BaseModel):
    contact_name: str | None = None


@router.post("/jobs/{job_id}/pitch")
def pitch(job_id: int, body: PitchRequest, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    job = get_job(db, profile, job_id)
    score = latest_score(db, job)
    applied = db.query(Application).filter_by(user_id=profile.user_id, job_id=job.id).first() is not None
    return write_pitch(profile, job, score.matched_skills if score else [], body.contact_name, applied)
