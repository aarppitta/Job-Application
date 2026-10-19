"""Recruitment companies: link job postings to the agency that advertised them, check agency websites, and keep
your recruiter status up to date when you apply.

The website check only proves the official site answers (and where it ends up). It never marks India eligibility,
visa sponsorship or relocation as verified: you confirm those yourself, with a source URL (PATCH /api/agencies/{id}).
"""
import re
import time

import httpx
from sqlalchemy.orm import Session

from app.logic.jd_parser import simplify
from app.models import RecruitmentCompany, now
from app.sources import USER_AGENT

STATUSES = ["NOT_REVIEWED", "REVIEWED", "PROFILE_REGISTERED", "RELEVANT_JOB_FOUND", "APPLICATION_PREPARED", "APPLIED",
            "FOLLOW_UP_NEEDED", "NO_RELEVANT_OPENINGS"]


def _key(name: str) -> str:
    """'ALTEN GmbH' / 'Hays AG' → 'alten' / 'hays' (legal forms dropped)."""
    words = [w for w in re.sub(r"[^a-z0-9 ]", " ", simplify(name)).split()
             if w not in ("gmbh", "ag", "se", "kg", "co", "mbh", "inc", "ltd", "germany", "deutschland", "group")]
    return " ".join(words)


def match_agency(db: Session, user_id: int, company: str) -> RecruitmentCompany | None:
    """The directory entry whose name or alias IS this company name (exact after normalising, never a guess)."""
    key = _key(company)
    if not key:
        return None
    for agency in db.query(RecruitmentCompany).filter_by(user_id=user_id):
        if key in {_key(n) for n in [agency.name, *(agency.aliases or [])]}:
            return agency
    return None


def check_website(url: str) -> tuple[str, str]:
    """→ (status, note). website_ok = answered 2xx; blocked = 401/403/429 or a bot check (unknown, never bypassed)."""
    try:
        r = httpx.get(url, timeout=25, follow_redirects=True, headers={"User-Agent": USER_AGENT})
    except httpx.HTTPError as exc:
        return "website_unreachable", f"No answer ({type(exc).__name__})"
    final = str(r.url)
    if r.status_code in (401, 403, 429) or "captcha" in r.text[:5000].lower() or "just a moment" in r.text[:3000].lower():
        return "website_blocked", f"HTTP {r.status_code}: the site blocks automatic checks; open it yourself"
    if r.status_code >= 400:
        return "website_unreachable", f"HTTP {r.status_code} at {final}"
    moved = "" if _host(final) == _host(url) else f" (moved to another domain: {_host(final)})"
    return "website_ok", f"HTTP {r.status_code} → {final}{moved}"


def _host(url: str) -> str:
    return re.sub(r"^www\.", "", url.split("://", 1)[-1].split("/", 1)[0].lower())


def check_websites(db: Session, user_id: int, limit: int = 50, seconds: float = 100) -> dict:
    """Check the official websites, least recently checked first (1 per second). Your confirmations are kept."""
    agencies = (db.query(RecruitmentCompany).filter_by(user_id=user_id)
                .order_by(RecruitmentCompany.last_verified_at.asc().nulls_first(), RecruitmentCompany.seed_id).limit(limit).all())
    out, started = {"checked": 0, "ok": 0, "problems": []}, time.monotonic()
    for agency in agencies:
        if time.monotonic() - started > seconds:
            break
        status, note = check_website(agency.website_url)
        out["checked"] += 1
        if agency.verification_status != "confirmed":  # never downgrade what you confirmed with a source
            agency.verification_status = status
        agency.verification_note, agency.last_verified_at = note, now()
        agency.source_url = agency.source_url if agency.verification_status == "confirmed" else agency.website_url
        if status == "website_ok":
            out["ok"] += 1
        else:
            out["problems"].append({"id": agency.id, "name": agency.name, "status": status, "note": note})
        db.commit()
        time.sleep(1)
    out["remaining"] = max(0, db.query(RecruitmentCompany).filter_by(user_id=user_id).count() - out["checked"])
    return out


def on_applied(db: Session, user_id: int, job) -> None:
    """You applied to a job a recruiter advertised: that recruiter's status becomes Applied (saved in the database)."""
    agency = match_agency(db, user_id, job.agency) if job.agency else None
    if agency:
        agency.status, agency.last_contact_at = "APPLIED", now()
