"""Jobs: list with filters, details, import, search, score, JD versions, standard CV, cover letter, mark as applied."""
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.auth import current_profile
from app.config import settings as app_config
from app.database import get_db
from app.defaults import user_settings
from app.logic import writer
from app.logic.cv import docx_response, standard_cv_docx, text_docx
from app.logic.interview import interview_prep
from app.logic.scoring import match_label
from app.models import Application, JDVersion, Job, JobSource, Profile, now
from app.serialize import to_dict
from app.services import agencies, freshness
from app.services import jobs as job_service
from app.sources import SOURCES

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

KEYWORDS = {  # filter chip -> skills
    "iiot": ["iiot", "mqtt", "opc ua"], "scada": ["scada", "webscada", "hmi"], "python": ["python"],
    "fastapi": ["fastapi"], "angular": ["angular"], "react": ["react"],
}


def get_job(db: Session, profile: Profile, job_id: int) -> Job:
    job = db.query(Job).filter_by(id=job_id, user_id=profile.user_id).first()
    if job is None:
        raise HTTPException(404, "Job not found.")
    return job


def job_summary(job: Job, threshold: float, app_status: str | None = None, updated_at=None) -> dict:
    data = to_dict(job, skip=("original_description", "parsed", "skills_text"))
    data["top_skills"] = [s["skill"] for s in job.parsed.get("skills", [])][:5]
    data["application_status"] = app_status
    data["match"] = match_label(job.ats_score, threshold, job.status)
    data["updated_at"] = updated_at  # set when the JD changed after we first saved it
    return data


def start_of_today() -> datetime:
    """Midnight in this computer's time zone."""
    return datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)


@router.get("")
def list_jobs(
    q: str = "", min_score: float | None = None, visa: bool = False, remote: bool = False, hybrid: bool = False,
    germany_only: bool = False, english_only: bool = False, days: int | None = None, keyword: list[str] = Query([]),
    view: str = "week", sort: str = "score", page: int = 1, show_scams: bool = False, show_closed: bool = False,
    saved: bool = False, agency: str = "", profile: Profile = Depends(current_profile), db: Session = Depends(get_db),
):
    """view: today = posted today · week = posted in the last 7 days · older = posted more than 7 days ago · all
    Closed jobs (page gone / position filled) are hidden unless show_closed; saved = only your bookmarks."""
    threshold = user_settings(profile)["min_score"]
    query = db.query(Job, Application.status).outerjoin(
        Application, (Application.job_id == Job.id) & (Application.user_id == profile.user_id)).filter(Job.user_id == profile.user_id)
    if not show_scams:
        query = query.filter(Job.status != "RISK")  # only genuine postings
    if not show_closed:
        query = query.filter(Job.closed_at.is_(None))
    if saved:
        query = query.filter(Job.is_saved.is_(True))
    if agency:
        query = query.filter(Job.agency == agency)
    posted = func.coalesce(Job.posted_at, Job.discovered_at)  # posting date; if the site gives none, the day we found it
    week_ago = start_of_today() - timedelta(days=6)
    if view == "today":
        query = query.filter(posted >= start_of_today())
    elif view == "week":
        query = query.filter(posted >= week_ago)
    elif view == "older":
        query = query.filter(posted < week_ago)
    if q:
        query = query.filter(or_(Job.title.ilike(f"%{q}%"), Job.company.ilike(f"%{q}%"), Job.location.ilike(f"%{q}%")))
    if min_score is not None:
        query = query.filter(Job.ats_score >= min_score)
        if min_score >= threshold:
            query = query.filter(Job.status != "REVIEW")  # held back: internship, part-time, lead role, German…
    if visa:
        query = query.filter(Job.visa_status == "confirmed")
    if remote or hybrid:
        query = query.filter(Job.remote_type.in_([t for t, on in (("remote", remote), ("hybrid", hybrid)) if on]))
    if germany_only:
        query = query.filter(Job.country == "Germany")
    if english_only:
        query = query.filter(Job.language_requirement.in_(("english", "german_plus")))
    if days is not None:
        since = datetime.now(UTC) - timedelta(days=days)
        query = query.filter(func.coalesce(Job.posted_at, Job.discovered_at) >= since)
    for k in keyword:
        if k == "industrial":
            query = query.filter(Job.parsed["industrial_signals"].as_string() != "[]")
        else:
            query = query.filter(or_(*[Job.skills_text.ilike(f"%,{s},%") for s in KEYWORDS.get(k, [k])]))
    order = {"score": Job.ats_score.desc().nulls_last(), "date": posted.desc(), "company": Job.company}[sort if sort in ("score", "date", "company") else "score"]
    total = query.count()
    rows = query.order_by(order, Job.id.desc()).offset((page - 1) * 50).limit(50).all()
    # JD changed after we first saved it? -> "Updated" date
    ids = [job.id for job, _ in rows]
    updated = dict(db.query(JDVersion.job_id, func.max(JDVersion.captured_at))
                   .filter(JDVersion.job_id.in_(ids), JDVersion.version > 1).group_by(JDVersion.job_id).all()) if ids else {}
    return {"total": total, "page": page,
            "items": [job_summary(job, threshold, status, updated.get(job.id)) for job, status in rows]}


@router.get("/{job_id}")
def job_details(job_id: int, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    job = get_job(db, profile, job_id)
    app = db.query(Application).filter_by(user_id=profile.user_id, job_id=job.id).first()
    data = job_summary(job, user_settings(profile)["min_score"], app.status if app else None)
    data["description"] = job.original_description
    data["parsed"] = job.parsed
    score = job_service.latest_score(db, job)
    data["score"] = to_dict(score) if score else None
    data["sources"] = [to_dict(s) for s in db.query(JobSource).filter_by(job_id=job.id)]
    data["versions"] = db.query(JDVersion).filter_by(job_id=job.id).count()
    data["application_id"] = app.id if app else None
    return data


@router.patch("/{job_id}")
def update_job(job_id: int, body: dict, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    job = get_job(db, profile, job_id)
    if "is_saved" in body:
        job.is_saved = bool(body["is_saved"])
    if "deadline" in body:  # "2026-11-30" or null
        try:
            job.deadline = date.fromisoformat(body["deadline"]) if body["deadline"] else None
        except (TypeError, ValueError):
            raise HTTPException(422, "deadline must look like 2026-11-30") from None
    if body.get("reopen"):  # "this job is still open" (the recheck was wrong)
        job.closed_at = None
    db.commit()
    return job_summary(job, user_settings(profile)["min_score"])


@router.post("/recheck")
def recheck(profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    """Re-open the pages of your best open jobs; the ones that are gone get hidden (and are never applied to)."""
    return freshness.recheck_jobs(db, profile, limit=25, seconds=min(120, app_config.step_seconds))


class ImportJob(BaseModel):
    title: str = Field(min_length=2)
    company: str = Field(min_length=1)
    description: str = Field(min_length=50)
    location: str | None = None
    source: str = "manual"
    source_url: str | None = None
    application_url: str | None = None
    company_url: str | None = None
    posted_at: datetime | None = None   # when the job was posted (for the Today / This week tabs)


@router.post("/import")
def import_job(body: ImportJob, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    """For jobs you found on LinkedIn, Indeed, StepStone... (those sites are never scraped)."""
    job, outcome, reason = job_service.save_job(db, profile.user_id, body.model_dump())
    if outcome != "duplicate":
        job_service.score(db, job, profile)
    db.commit()
    return {"id": job.id, "outcome": outcome, "reason": reason}


class SearchRequest(BaseModel):
    sources: list[str] | None = None
    queries: list[str] | None = None


@router.post("/search")
def search_now(body: SearchRequest, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    settings = user_settings(profile)
    sources = [s for s in (body.sources or settings["sources"]) if s in SOURCES]
    return job_service.search_now(db, profile, sources, body.queries or settings["search_queries"])


class SearchStep(BaseModel):
    cursor: int = 0
    blocked: list[str] = []
    seconds: float = 50


@router.post("/search-step")
def search_step(body: SearchStep, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    """One part of "Search now" (≤ `seconds`). The page calls it again with the returned cursor until done."""
    return job_service.search_step(db, profile, body.cursor, min(body.seconds, app_config.step_seconds), list(body.blocked))


@router.post("/rescore-all")
def rescore_all(profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    """Score every saved job again (e.g. after you changed weights or your profile)."""
    jobs = db.query(Job).filter_by(user_id=profile.user_id).all()
    for job in jobs:
        job_service.score(db, job, profile)
    db.commit()
    return {"rescored": len(jobs), "matching": sum(1 for j in jobs if j.status == "QUALIFIED")}


@router.post("/{job_id}/score")
def rescore(job_id: int, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    score = job_service.score(db, get_job(db, profile, job_id), profile)
    db.commit()
    return to_dict(score)


@router.get("/{job_id}/versions")
def versions(job_id: int, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    job = get_job(db, profile, job_id)
    return [to_dict(v) for v in db.query(JDVersion).filter_by(job_id=job.id).order_by(JDVersion.version)]


# ------------------------------------------------------------------ CV, cover letter, applied


def matched_skills(db: Session, job: Job) -> list[str]:
    score = job_service.latest_score(db, job)
    return score.matched_skills if score else []


@router.get("/{job_id}/interview-prep")
def interview(job_id: int, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    """What to study and which of your CV stories to tell, for this job's interview."""
    job = get_job(db, profile, job_id)
    score = job_service.latest_score(db, job)
    return interview_prep(profile, job, score.matched_skills if score else [], score.missing_skills if score else [])


@router.get("/{job_id}/cv.docx")
def job_cv(job_id: int, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    """The CV for this job = the standard CV (the same file for every application)."""
    job = get_job(db, profile, job_id)
    job.cv_prepared_at = job.cv_prepared_at or now()
    db.commit()
    return docx_response(standard_cv_docx(profile), profile, None, "CV")


@router.post("/{job_id}/cover-letter")
def cover_letter(job_id: int, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    job = get_job(db, profile, job_id)
    text, made_by, warnings = writer.cover_letter(profile, job, matched_skills(db, job))
    return {"text": text, "made_by": made_by, "warnings": warnings}


class LetterText(BaseModel):
    text: str = Field(min_length=20)


@router.post("/{job_id}/cover-letter.docx")
def cover_letter_docx(job_id: int, body: LetterText, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    """The cover letter as a Word file (the text you see, including your edits)."""
    return docx_response(text_docx(body.text), profile, get_job(db, profile, job_id), "Cover_Letter")


class AppliedRequest(BaseModel):
    cover_letter: str | None = None   # the letter you sent (your edited version); generated if empty


@router.post("/{job_id}/applied")
def mark_applied(job_id: int, body: AppliedRequest, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    """Record that you applied. Saves the exact CV, cover letter, JD version and score."""
    job = get_job(db, profile, job_id)
    if db.query(Application).filter_by(user_id=profile.user_id, job_id=job.id).first():
        raise HTTPException(409, "You already applied to this job.")
    letter = body.cover_letter or writer.cover_letter(profile, job, matched_skills(db, job))[0]
    from app.routes.intelligence import full_analysis  # (late import: intelligence imports this module)

    analysis = full_analysis(db, profile, job)
    snapshot = {k: analysis[k] for k in ("recommendation", "scores", "skill_gaps", "dsa", "readiness", "predicted_questions", "germany")}
    app = Application(
        user_id=profile.user_id, job_id=job.id, status="APPLIED", score=job.ats_score,
        jd_version=job_service.latest_version(db, job).version, cover_letter=letter,
        tailored_cv=standard_cv_docx(profile), cv_version="STANDARD", analysis=snapshot,
        next_follow_up=now() + timedelta(days=2),  # day 2: contact a recruiter
        history=[{"status": "APPLIED", "at": now().isoformat()}],
    )
    db.add(app)
    job.status = "APPLIED"
    agencies.on_applied(db, profile.user_id, job)  # advertised by a recruiter → its status becomes Applied
    db.commit()
    return {"id": app.id, "status": app.status}
