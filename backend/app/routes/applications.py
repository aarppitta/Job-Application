"""Applications = jobs you applied to. Each one keeps the exact CV, cover letter, JD version and score used."""
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.auth import current_profile
from app.database import get_db
from app.defaults import user_settings
from app.logic import outreach
from app.logic.cv import docx_response, text_docx
from app.logic.market import REJECTION_STAGES, STAGES
from app.models import Application, Job, OutreachContact, Profile, RecruitmentCompany, now
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
    data["cv_version_name"] = "Standard CV" if app.cv_version == "STANDARD" else app.cv_version  # older rows: CV-001…
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


@router.get("/calendar")
def calendar(days: int = 60, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    """Upcoming dates: interviews, follow-ups (applications) and deadlines of jobs you have not applied to yet."""
    start = now() - timedelta(days=1)
    end = now() + timedelta(days=days)
    events = []
    for app, job in db.query(Application, Job).join(Job, Job.id == Application.job_id).filter(Application.user_id == profile.user_id):
        for i in app.interviews or []:
            if start <= datetime.fromisoformat(i["at"]) <= end:
                events.append({"at": i["at"], "type": "interview", "title": f"{i['kind']}: {job.title}", "company": job.company,
                               "job_id": job.id, "note": i.get("note") or ""})
        if app.next_follow_up and app.status not in ("REJECTED", "WITHDRAWN", "OFFER") and app.next_follow_up <= end:
            events.append({"at": app.next_follow_up.isoformat(), "type": "follow_up", "title": f"Follow up: {job.title}",
                           "company": job.company, "job_id": job.id, "note": "", "overdue": app.next_follow_up < now()})
    applied = db.query(Application.job_id).filter_by(user_id=profile.user_id)
    for job in db.query(Job).filter(Job.user_id == profile.user_id, Job.deadline.isnot(None), Job.closed_at.is_(None),
                                    Job.id.not_in(applied), Job.deadline >= start.date(), Job.deadline <= end.date()):
        events.append({"at": datetime.combine(job.deadline, datetime.min.time(), UTC).isoformat(), "type": "deadline",
                       "title": f"Deadline: {job.title}", "company": job.company, "job_id": job.id, "note": ""})
    for agency in db.query(RecruitmentCompany).filter(RecruitmentCompany.user_id == profile.user_id,
                                                      RecruitmentCompany.next_follow_up.isnot(None), RecruitmentCompany.next_follow_up <= end):
        events.append({"at": agency.next_follow_up.isoformat(), "type": "follow_up", "title": f"Follow up with recruiter {agency.name}",
                       "company": agency.name, "job_id": None, "agency_id": agency.id, "note": "", "overdue": agency.next_follow_up < now()})
    return sorted(events, key=lambda e: e["at"])


@router.get("/options")
def options():
    return {"statuses": STATUSES, "rejection_stages": REJECTION_STAGES}


class Interview(BaseModel):
    at: datetime                        # date + time of the interview
    kind: str = Field("Interview", max_length=60)  # "HR screen", "Technical", "Final"…
    note: str = Field("", max_length=500)

    @field_validator("at")
    @classmethod
    def with_time_zone(cls, value: datetime) -> datetime:  # the app sends UTC; a bare time counts as UTC too
        return value if value.tzinfo else value.replace(tzinfo=UTC)


class ApplicationUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None
    rejection_stage: str | None = None     # asked when you mark REJECTED: where did it stop?
    next_follow_up: datetime | None = None
    referral: bool | None = None
    interviews: list[Interview] | None = None  # the whole list (add / edit / remove = send the new list)


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
    if body.interviews is not None:
        app.interviews = sorted((i.model_dump(mode="json") for i in body.interviews), key=lambda i: i["at"])
    db.commit()
    contacts = db.query(OutreachContact).filter_by(user_id=profile.user_id, job_id=job.id).all()
    return app_dict(app, job, contacts, user_settings(profile)["min_score"])


@router.get("/{app_id}/cv.docx")
def cv_used(app_id: int, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    """The exact CV you applied with."""
    app, job = get_app(db, profile, app_id)
    if app.tailored_cv is None:
        raise HTTPException(404, "No CV saved for this application.")
    return docx_response(app.tailored_cv, profile, None, "CV")


@router.get("/{app_id}/cover-letter.docx")
def letter_used(app_id: int, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    app, job = get_app(db, profile, app_id)
    if not app.cover_letter:
        raise HTTPException(404, "No cover letter saved for this application.")
    return docx_response(text_docx(app.cover_letter), profile, job, "Cover_Letter")

