"""Applications = jobs you applied to. Each one keeps the exact CV, cover letter, JD version and score used."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import current_profile
from app.database import get_db
from app.defaults import CV_VERSIONS, user_settings
from app.logic import outreach
from app.logic.cv_tailor import docx_response, text_docx
from app.logic.market import REJECTION_STAGES, STAGES
from app.models import Application, Job, OutreachContact, Profile, now
from app.serialize import to_dict

router = APIRouter(prefix="/api/applications", tags=["applications"])

STATUSES = [*STAGES, "REJECTED", "WITHDRAWN"]


def app_dict(app: Application, job: Job, contacts: list | None = None, threshold: float = 80) -> dict:
    data = to_dict(app, skip=("tailored_cv", "analysis"))
    data["job"] = {"id": job.id, "title": job.title, "company": job.company, "location": job.location,
                   "application_url": job.application_url, "salary": (job.parsed.get("salary") or {})}
    if contacts is not None:
        data["health"] = outreach.health(app, job, contacts, threshold)
        data["follow_ups"] = outreach.follow_ups(app, contacts, now())
        data["contacts"] = [{"name": c.name, "role": c.role, "kind": c.kind, "contacted": bool(c.contacted_at),
                             "replied": bool(c.replied_at)} for c in contacts]
    data["cv_version_name"] = CV_VERSIONS.get(app.cv_version or "", {}).get("name")
    data["snapshot"] = {k: (app.analysis or {}).get(k) for k in ("recommendation", "skill_gaps", "dsa")}
    return data


def get_app(db: Session, profile: Profile, app_id: int) -> tuple[Application, Job]:
    app = db.query(Application).filter_by(id=app_id, user_id=profile.user_id).first()
    if app is None:
        raise HTTPException(404, "Application not found.")
    return app, db.get(Job, app.job_id)


@router.get("")
def list_applications(profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    rows = db.query(Application, Job).join(Job, Job.id == Application.job_id)\
        .filter(Application.user_id == profile.user_id).order_by(Application.submitted_at.desc()).all()
    contacts: dict[int, list] = {}
    for c in db.query(OutreachContact).filter_by(user_id=profile.user_id):
        contacts.setdefault(c.job_id, []).append(c)
    threshold = user_settings(profile)["min_score"]
    return [app_dict(a, j, contacts.get(j.id, []), threshold) for a, j in rows]


@router.get("/options")
def options():
    return {"statuses": STATUSES, "rejection_stages": REJECTION_STAGES}


class ApplicationUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None
    rejection_stage: str | None = None     # asked when you mark REJECTED: where did it stop?
    next_follow_up: datetime | None = None
    referral: bool | None = None


@router.patch("/{app_id}")
def update_application(app_id: int, body: ApplicationUpdate, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    app, job = get_app(db, profile, app_id)
    if body.status:
        if body.status not in STATUSES:
            raise HTTPException(422, f"Status must be one of {STATUSES}")
        if body.status != app.status:
            app.status = body.status
            app.history = [*app.history, {"status": body.status, "at": now().isoformat()}]
    if body.rejection_stage is not None:
        if body.rejection_stage not in REJECTION_STAGES:
            raise HTTPException(422, f"rejection_stage must be one of {REJECTION_STAGES}")
        app.rejection_stage = body.rejection_stage
    if body.next_follow_up is not None:
        app.next_follow_up = body.next_follow_up
    if body.referral is not None:
        app.referral = body.referral
    if body.notes is not None:
        app.notes = body.notes
    db.commit()
    contacts = db.query(OutreachContact).filter_by(user_id=profile.user_id, job_id=job.id).all()
    return app_dict(app, job, contacts, user_settings(profile)["min_score"])


@router.get("/{app_id}/cv.docx")
def cv_used(app_id: int, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    """The exact tailored CV you applied with."""
    app, job = get_app(db, profile, app_id)
    if app.tailored_cv is None:
        raise HTTPException(404, "No CV saved for this application.")
    return docx_response(app.tailored_cv, profile, job, "CV")


@router.get("/{app_id}/cover-letter.docx")
def letter_used(app_id: int, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    app, job = get_app(db, profile, app_id)
    if not app.cover_letter:
        raise HTTPException(404, "No cover letter saved for this application.")
    return docx_response(text_docx(app.cover_letter), profile, job, "Cover_Letter")

