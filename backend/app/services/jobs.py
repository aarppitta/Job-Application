"""Saving jobs (with duplicate check + JD versions) and scoring them."""
import time
from datetime import date

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.defaults import user_settings
from app.logic import dedup
from app.logic.jd_parser import parse_job
from app.logic.scoring import score_job
from app.models import Company, JDVersion, Job, JobSource, Profile, Score, SourceStatus, now
from app.services import agencies
from app.sources import SOURCES, SourceBlocked, search


def find_duplicate(db: Session, user_id: int, info: dict, company_key: str) -> tuple[Job | None, str]:
    """Look at jobs that could be the same vacancy and compare them."""
    candidates = (
        db.query(Job).join(Company, Company.id == Job.company_id, isouter=True)
        .filter(Job.user_id == user_id)
        .filter(or_(Job.jd_hash == info["jd_hash"], Company.key == company_key,
                    Job.source_url == info["url"], Job.application_url == info["application_url"]))
        .limit(200).all()
    )
    for job in candidates:
        # job.jd_hash = the latest version's hash; the full text is loaded only if the comparison really needs it
        old = {"title": job.title, "company": job.company, "text": lambda job=job: latest_version(db, job).text,
               "jd_hash": job.jd_hash, "url": job.source_url, "application_url": job.application_url, "location": job.location}
        same, reason = dedup.is_same_job(info, old)
        if same:
            return job, reason
    return None, ""


def latest_version(db: Session, job: Job) -> JDVersion:
    return db.query(JDVersion).filter_by(job_id=job.id).order_by(JDVersion.version.desc()).first()


def save_job(db: Session, user_id: int, raw: dict) -> tuple[Job, str, str]:
    """Save a job found by a source or pasted by the user.

    Returns (job, outcome, reason). outcome is:
      "new"       - first time we see this vacancy
      "duplicate" - already saved; we only add the new source link
      "updated"   - already saved, but the JD text changed -> new JD version stored
    """
    raw = {**raw, "title": " ".join(raw["title"].split()), "company": " ".join(raw["company"].split())}  # tidy spaces
    info = parse_job(raw["title"], raw.get("description", ""), raw.get("location"), raw.get("application_url"))
    key = dedup.company_key(raw["company"]) or raw["company"].lower()
    compare = {"title": raw["title"], "company": raw["company"], "text": info["text"], "jd_hash": info["jd_hash"],
               "url": raw.get("source_url"), "application_url": raw.get("application_url"), "location": raw.get("location")}
    existing, reason = find_duplicate(db, user_id, compare, key)

    # posted by a recruitment company? (the recruiter sources say so; otherwise: is the company itself a recruiter?)
    matched = agencies.match_agency(db, user_id, raw["company"])
    agency_name = raw.get("agency") or (matched.name if matched else None)
    if existing:
        existing.last_seen_at, existing.closed_at = now(), None  # listed again by a source = still open
        existing.agency = existing.agency or agency_name
        link = db.query(JobSource).filter_by(job_id=existing.id, source=raw["source"], url=raw.get("source_url")).first()
        if link:
            link.last_seen = now()
        else:
            db.add(JobSource(job_id=existing.id, source=raw["source"], url=raw.get("source_url")))
        known = {v.jd_hash for v in db.query(JDVersion).filter_by(job_id=existing.id)}
        if info["jd_hash"] in known or info["description_incomplete"]:
            db.flush()
            return existing, "duplicate", reason
        # The JD changed: keep the old versions, store the new one, update parsed facts.
        version = latest_version(db, existing).version + 1
        db.add(JDVersion(job_id=existing.id, version=version, text=info["text"], jd_hash=info["jd_hash"], source=raw["source"]))
        apply_parsed_info(existing, info)
        db.flush()
        return existing, "updated", f"{reason}; JD changed (version {version})"

    company = db.query(Company).filter_by(user_id=user_id, key=key).first()
    if company is None:
        company = Company(user_id=user_id, name=raw["company"], key=key, website=raw.get("company_url"), locations=[])
        db.add(company)
        db.flush()
    if raw.get("location") and info["country"] == "Germany" and raw["location"] not in company.locations:
        company.locations = [*company.locations, raw["location"]]

    job = Job(
        user_id=user_id, company_id=company.id, title=raw["title"][:300], company=raw["company"][:300],
        location=raw.get("location"), source=raw["source"], source_url=raw.get("source_url"),
        application_url=raw.get("application_url") or raw.get("source_url"), company_url=raw.get("company_url"),
        posted_at=raw.get("posted_at"), original_description=info["text"], last_seen_at=now(),
        agency=agency_name,
    )
    apply_parsed_info(job, info)
    db.add(job)
    db.flush()
    db.add(JobSource(job_id=job.id, source=raw["source"], url=raw.get("source_url")))
    db.add(JDVersion(job_id=job.id, version=1, text=info["text"], jd_hash=info["jd_hash"], source=raw["source"]))
    db.flush()
    return job, "new", ""


def apply_parsed_info(job: Job, info: dict) -> None:
    for field in ("jd_hash", "country", "remote_type", "employment_type", "experience_required", "seniority",
                  "visa_status", "language_requirement", "risk_flags", "description_incomplete", "parsed"):
        setattr(job, field, info[field])
    job.skills_text = "," + ",".join(s["skill"].lower() for s in info["parsed"]["skills"]) + ","
    if info["parsed"].get("deadline") and job.deadline is None:  # a deadline you typed yourself wins
        job.deadline = date.fromisoformat(info["parsed"]["deadline"])


def score(db: Session, job: Job, profile: Profile) -> Score:
    """Score the job, store the result, update the job's status."""
    s = user_settings(profile)
    result = score_job(profile, job, s["weights"], s["min_score"], s["search_queries"])
    row = Score(job_id=job.id, jd_version=latest_version(db, job).version, overall=result["overall"], parts=result["parts"],
                matched_skills=result["matched_skills"], missing_skills=result["missing_skills"], reasons=result["reasons"],
                concerns=result["concerns"], recommendation=result["recommendation"], threshold=result["threshold"])
    db.add(row)
    job.ats_score = result["overall"]
    if job.status != "APPLIED":
        job.status = {"APPLY": "QUALIFIED", "REVIEW": "REVIEW", "SKIP": "NOT_QUALIFIED", "RISK": "RISK"}[result["recommendation"]]
    db.flush()
    return row


def latest_score(db: Session, job: Job) -> Score | None:
    return db.query(Score).filter_by(job_id=job.id).order_by(Score.id.desc()).first()


def record_source(db: Session, user_id: int, source: str, error: str | None = None, blocked: bool = False) -> None:
    """Source health: remember when a source was searched and whether it worked (Source health page)."""
    row = db.query(SourceStatus).filter_by(user_id=user_id, source=source).first()
    if row is None:
        row = SourceStatus(user_id=user_id, source=source)
        db.add(row)
    row.last_checked_at, row.last_error, row.blocked = now(), error, blocked
    if error is None:
        row.last_ok_at = now()


def search_now(db: Session, profile: Profile, source_names: list[str], queries: list[str]) -> dict:
    """Run every query on every source once. Used by the 'Search now' button."""
    summary = {"found": 0, "new": 0, "duplicates": 0, "errors": []}
    s = user_settings(profile)
    for source_name in source_names:
        for query in queries:
            try:
                raws = search(source_name, query, s)
            except SourceBlocked as exc:
                summary["errors"].append(str(exc))
                record_source(db, profile.user_id, source_name, str(exc), blocked=True)
                db.commit()
                break
            record_source(db, profile.user_id, source_name)
            for raw in raws:
                summary["found"] += 1
                job, outcome, _ = save_job(db, profile.user_id, raw)
                if outcome == "duplicate":
                    summary["duplicates"] += 1
                else:
                    summary["new"] += outcome == "new"
                    score(db, job, profile)
            db.commit()
    return summary


# ------------------------------------------------------------------ step-by-step search (serverless, resumable)


def search_pairs(s: dict, only: list[str] | None = None) -> list[tuple[str, str]]:
    """Every (source, role) to search, source by source so a company list is downloaded once and then cached."""
    return [(src, q) for src in s["sources"] if src in SOURCES and (not only or src in only) for q in s["search_queries"]]


def search_step(db: Session, profile: Profile, cursor: int, seconds: float, blocked: list[str] | None = None,
                on_job=None, on_log=None, only: list[str] | None = None) -> dict:
    """Search from `cursor` until `seconds` are used up. Call again with the returned cursor to continue.
    Works the same locally and on Vercel (where one call may run at most a few minutes)."""
    blocked = blocked if blocked is not None else []
    pairs = search_pairs(user_settings(profile), only)
    started = time.monotonic()
    out = {"found": 0, "new": 0, "duplicates": 0, "errors": []}
    while cursor < len(pairs) and time.monotonic() - started < seconds:
        source, query = pairs[cursor]
        cursor += 1
        if source in blocked:
            continue
        if on_log:
            on_log(f"Searching {source}: {query}")
        try:
            raws = search(source, query, user_settings(profile))
        except SourceBlocked as exc:
            blocked.append(source)
            out["errors"].append(str(exc))
            record_source(db, profile.user_id, source, str(exc), blocked=True)
            db.commit()
            continue
        except Exception as exc:  # one broken source must not stop the search
            out["errors"].append(f"{source} failed: {exc}")
            record_source(db, profile.user_id, source, f"{source} failed: {exc}")
            db.commit()
            continue
        record_source(db, profile.user_id, source)
        for raw in raws:
            out["found"] += 1
            job, outcome, why = save_job(db, profile.user_id, raw)
            if outcome == "duplicate":
                out["duplicates"] += 1
            else:
                out["new"] += outcome == "new"
                score(db, job, profile)
            if on_job:
                on_job(job, outcome, why)
        db.commit()
    return {**out, "cursor": cursor, "total": len(pairs), "done": cursor >= len(pairs), "blocked": blocked}
