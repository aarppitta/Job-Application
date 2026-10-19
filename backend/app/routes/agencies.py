"""Recruitment companies directory: list + filters, your status / notes / follow-up per recruiter, website checks,
and the jobs each recruiter advertised (scored against your CV like every other job)."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.auth import current_profile
from app.config import settings as app_config
from app.data.recruitment_companies import CATEGORIES
from app.database import get_db
from app.defaults import user_settings
from app.logic.scoring import match_label
from app.models import Application, Job, Profile, RecruitmentCompany
from app.serialize import to_dict
from app.services import agencies
from app.sources import RECRUITER_SITES

READ_SITES = {name for name, _, _ in RECRUITER_SITES.values()}  # recruiters whose own job pages are read

router = APIRouter(prefix="/api/agencies", tags=["recruitment companies"])
VERIFIED_FIELDS = ("international_recruitment_supported", "india_candidate_support_verified",
                   "visa_sponsorship_support_verified", "relocation_support_verified")


def get_agency(db: Session, profile: Profile, agency_id: int) -> RecruitmentCompany:
    agency = db.query(RecruitmentCompany).filter_by(id=agency_id, user_id=profile.user_id).first()
    if agency is None:
        raise HTTPException(404, "Recruitment company not found.")
    return agency


def agency_dict(a: RecruitmentCompany, jobs: int = 0, good: int = 0, applied: int = 0) -> dict:
    data = to_dict(a, skip=("user_id", "aliases"))
    data["category_label"] = CATEGORIES.get(a.recruitment_category, a.recruitment_category)
    data["jobs"], data["good_matches"], data["applied"] = jobs, good, applied
    data["ingestion"] = "automatic" if a.job_feed or a.name in READ_SITES else "manual"
    return data


@router.get("/options")
def options(profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    rows = db.query(RecruitmentCompany).filter_by(user_id=profile.user_id).all()
    return {"categories": CATEGORIES, "statuses": agencies.STATUSES,
            "industries": sorted({i for r in rows for i in r.industry_specializations}),
            "job_families": sorted({f for r in rows for f in r.job_family_specializations}),
            "countries": sorted({r.country for r in rows if r.country})}


@router.get("")
def list_agencies(q: str = "", category: str = "", industry: str = "", family: str = "", country: str = "", status: str = "",
                  saved: bool = False, sort: str = "id", profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    query = db.query(RecruitmentCompany).filter_by(user_id=profile.user_id)
    if q:
        query = query.filter(or_(RecruitmentCompany.name.ilike(f"%{q}%"), RecruitmentCompany.focus.ilike(f"%{q}%")))
    if category:
        query = query.filter(RecruitmentCompany.recruitment_category == category)
    if country:
        query = query.filter(RecruitmentCompany.country == country)
    if status:
        query = query.filter(RecruitmentCompany.status == status)
    if saved:
        query = query.filter(RecruitmentCompany.is_saved.is_(True))
    rows = [r for r in query.all() if (not industry or industry in r.industry_specializations)
            and (not family or family in r.job_family_specializations)]
    threshold = user_settings(profile)["min_score"]
    open_jobs = Job.closed_at.is_(None)
    counts = dict(db.query(Job.agency, func.count()).filter(Job.user_id == profile.user_id, Job.agency.isnot(None), open_jobs).group_by(Job.agency).all())
    good = dict(db.query(Job.agency, func.count()).filter(Job.user_id == profile.user_id, Job.agency.isnot(None), open_jobs,
                                                          Job.ats_score >= threshold, Job.status == "QUALIFIED").group_by(Job.agency).all())
    applied = dict(db.query(Job.agency, func.count()).join(Application, Application.job_id == Job.id)
                   .filter(Application.user_id == profile.user_id, Job.agency.isnot(None)).group_by(Job.agency).all())
    items = [agency_dict(r, counts.get(r.name, 0), good.get(r.name, 0), applied.get(r.name, 0)) for r in rows]
    key = {"name": lambda a: a["name"].lower(), "jobs": lambda a: (-a["good_matches"], -a["jobs"], a["seed_id"]),
           "status": lambda a: (agencies.STATUSES.index(a["status"]), a["seed_id"])}.get(sort, lambda a: a["seed_id"])
    return {"total": len(items), "items": sorted(items, key=key)}


class AgencyUpdate(BaseModel):
    status: str | None = None
    notes: str | None = Field(None, max_length=5000)
    is_saved: bool | None = None
    last_contact_at: datetime | None = None
    next_follow_up: datetime | None = None
    clear_follow_up: bool = False
    # Verification by YOU: setting any of these to true needs the page that says so (source_url).
    international_recruitment_supported: bool | None = None
    india_candidate_support_verified: bool | None = None
    visa_sponsorship_support_verified: bool | None = None
    relocation_support_verified: bool | None = None
    german_language_requirements: str | None = Field(None, max_length=200)
    source_url: str | None = Field(None, max_length=500)
    website_url: str | None = Field(None, max_length=500)                 # corrected official site (needs source_url)
    candidate_registration_url: str | None = Field(None, max_length=500)


@router.patch("/{agency_id}")
def update_agency(agency_id: int, body: AgencyUpdate, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    agency = get_agency(db, profile, agency_id)
    changes = body.model_dump(exclude_unset=True)
    if "status" in changes and changes["status"] not in agencies.STATUSES:
        raise HTTPException(422, f"status must be one of {agencies.STATUSES}")
    for url_field in ("source_url", "website_url", "candidate_registration_url"):
        if changes.get(url_field) and not str(changes[url_field]).startswith("https://"):
            raise HTTPException(422, f"{url_field} must be an https:// link")
    confirms = [f for f in VERIFIED_FIELDS if changes.get(f) is True] + (["website_url"] if changes.get("website_url") else [])
    if confirms and not changes.get("source_url"):
        raise HTTPException(422, "Add the page that confirms it (source_url): nothing is marked verified without a source.")
    for field in ("status", "notes", "is_saved", "last_contact_at", "next_follow_up", "german_language_requirements",
                  "candidate_registration_url", "website_url", *VERIFIED_FIELDS):
        if field in changes:
            setattr(agency, field, changes[field])
    if body.clear_follow_up:
        agency.next_follow_up = None
    if confirms:
        agency.verification_status, agency.source_url = "confirmed", changes["source_url"]
        agency.last_verified_at = datetime.now().astimezone()
        agency.verification_note = "Confirmed by you: " + ", ".join(f.replace("_", " ") for f in confirms)
    db.commit()
    return agency_dict(agency)


@router.post("/check-websites")
def check_websites(profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    """Open each official website (oldest check first, 1 per second, within one request's time budget)."""
    return agencies.check_websites(db, profile.user_id, seconds=min(100, app_config.step_seconds - 20))


@router.get("/{agency_id}/jobs")
def agency_jobs(agency_id: int, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    """Jobs this recruiter advertised, best match first (company = the employer if the ad names one)."""
    agency = get_agency(db, profile, agency_id)
    threshold = user_settings(profile)["min_score"]
    rows = (db.query(Job, Application.status).outerjoin(Application, (Application.job_id == Job.id) & (Application.user_id == profile.user_id))
            .filter(Job.user_id == profile.user_id, Job.agency == agency.name, Job.closed_at.is_(None))
            .order_by(Job.ats_score.desc().nulls_last()).limit(100).all())
    return [{"id": j.id, "title": j.title, "employer": j.company if agencies._key(j.company) != agencies._key(agency.name) else None,
             "location": j.location, "score": j.ats_score, "match": match_label(j.ats_score, threshold, j.status),
             "application_status": status, "source_url": j.source_url, "checked_at": j.checked_at or j.last_seen_at,
             "visa_status": j.visa_status, "language": j.language_requirement, "seniority": j.seniority} for j, status in rows]
