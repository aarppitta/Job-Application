"""Is a job still open? Re-open its page and look for "gone" signs. Closed jobs are hidden (and never applied to).

Polite: one page per second, only the jobs that matter (good matches you have not applied to), oldest check first.
A page that blocks us (403/429) counts as "unknown", never as closed.
"""
import re
import time

import httpx
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.defaults import user_settings
from app.models import Application, Job, JobSource, Profile, now
from app.sources import USER_AGENT

GONE = re.compile(r"no longer (available|accepting|open|active)|(position|job|role|vacancy) (has been |is )?(filled|closed|expired)"
                  r"|job (posting )?(not found|expired)|this job is no longer|nicht mehr (verfügbar|aktiv|besetzbar)"
                  r"|stelle (ist )?(bereits )?(besetzt|vergeben)|stellenanzeige (ist )?(abgelaufen|nicht mehr)", re.I)


NOT_CHECKED = ("manual", "demo")  # pasted jobs (their link may be anything) and the fictional demo jobs


def is_closed(url: str) -> bool | None:
    """True = gone (404/410, redirected to an error page, or the page says so); False = still there; None = unknown."""
    try:
        r = httpx.get(url, timeout=30, follow_redirects=True, headers={"User-Agent": USER_AGENT})
    except httpx.HTTPError:
        return None
    if r.status_code in (404, 410):
        return True
    if r.status_code != 200:
        return None  # 403 / 429 / 5xx: we can't tell, so we don't guess
    if "error=true" in str(r.url):  # Greenhouse sends closed jobs back to the board with ?error=true
        return True
    return bool(GONE.search(r.text[:200_000]))


def recheck_jobs(db: Session, profile: Profile, limit: int = 25, seconds: float = 120) -> dict:
    """Re-check the most relevant open jobs (score ≥ threshold−10, not applied), least recently checked first."""
    threshold = user_settings(profile)["min_score"]
    applied = db.query(Application.job_id).filter_by(user_id=profile.user_id)
    jobs = (db.query(Job).filter(Job.user_id == profile.user_id, Job.closed_at.is_(None), Job.dismissed_at.is_(None),
                                 Job.ats_score >= threshold - 10,
                                 Job.id.not_in(applied), or_(Job.source_url.isnot(None), Job.application_url.isnot(None)),
                                 Job.source.notin_(NOT_CHECKED))
            .order_by(Job.checked_at.asc().nulls_first(), Job.ats_score.desc()).limit(limit).all())
    out, started = {"checked": 0, "closed": [], "unknown": 0}, time.monotonic()
    for job in jobs:
        if time.monotonic() - started > seconds:
            break
        # Closed only if EVERY place we saw it says so (an Arbeitnow copy can expire while the company page is open).
        urls = [u for u in dict.fromkeys([job.source_url, *(s.url for s in db.query(JobSource).filter_by(job_id=job.id)),
                                          job.application_url]) if u]
        results = []
        for url in urls:
            results.append(is_closed(url))
            if results[-1] is False:
                break  # one open page is enough
            time.sleep(1)
        closed = True if results and all(r is True for r in results) else (False if False in results else None)
        job.checked_at = now()
        out["checked"] += 1
        if closed:
            job.closed_at = now()
            out["closed"].append({"id": job.id, "title": job.title, "company": job.company})
        elif closed is None:
            out["unknown"] += 1
        db.commit()
    return out
