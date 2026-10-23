"""Job boards page (every platform, grouped like the source diagram) and Source health.

- "automatic": the app reads it by itself (official/free API)
- "link":      no public API, or scraping is forbidden -> a one-click search with your keyword;
               found something? use "Import job" so it gets saved, deduplicated and scored.
"""
from urllib.parse import quote, quote_plus

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import current_profile
from app.database import get_db
from app.defaults import user_settings
from app.models import Job, Profile, SourceStatus
from app.sources import SOURCES

router = APIRouter(prefix="/api", tags=["job boards"])


def google_site(site: str, q: str) -> str:
    """Always-working fallback: Google search limited to one site."""
    return "https://www.google.com/search?q=" + quote_plus(f"site:{site} {q} Germany")


def boards(q: str, enabled: set[str], settings: dict) -> list[dict]:
    slug = "-".join(q.lower().split())
    followed = len(settings["greenhouse_boards"]) + len(settings["smartrecruiters_companies"]) + \
        len(settings["lever_companies"]) + len(settings["personio_companies"]) + len(settings["ashby_boards"]) + len(settings["workday_sites"])

    def auto(source: str) -> str:
        return "automatic" if source in enabled else "off"

    germany = [
        {"name": "Company careers pages (Greenhouse, SmartRecruiters, Lever, Personio, Ashby, Workday)", "kind": "automatic",
         "why": f"Jobs often posted only on the company's own site. Official APIs of {followed} followed companies "
                "(Helsing, N26, Trade Republic, Bosch, Deutsche Bank, NVIDIA, Airbus, Softing, …). Add more in Settings.", "url": None},
        {"name": "Amazon / AWS", "kind": auto("amazon"), "why": "amazon.jobs search API, jobs in Germany (Berlin, Dresden, Munich…)",
         "url": f"https://www.amazon.jobs/en/search?base_query={quote(q)}&country=DEU"},
        {"name": "Arbeitnow", "kind": auto("arbeitnow"),
         "why": "Free public API, many English-speaking jobs in Germany (arbeitnow.com)", "url": f"https://www.arbeitnow.com/?search={quote(q)}"},
        {"name": "LinkedIn Jobs", "kind": "link", "why": "International tech jobs and recruiters (no API; bots forbidden)",
         "url": f"https://www.linkedin.com/jobs/search/?keywords={quote(q)}&location=Germany"},
        {"name": "StepStone", "kind": "link", "why": "Biggest German job board (no public API)", "url": f"https://www.stepstone.de/jobs/{quote(slug)}"},
        {"name": "Indeed Germany", "kind": "link", "why": "Very large volume (no public API; scraping forbidden)",
         "url": f"https://de.indeed.com/jobs?q={quote_plus(q)}&l=Deutschland"},
        {"name": "Bundesagentur für Arbeit (Jobbörse)", "kind": "link",
         "why": "Official federal job database; its API blocks apps that are not the official app (tested)",
         "url": f"https://www.arbeitsagentur.de/jobsuche/suche?angebotsart=1&was={quote(q)}&wo=Deutschland"},
        {"name": "Make it in Germany", "kind": "link", "why": "Government portal for international skilled workers (shows Bundesagentur jobs)",
         "url": "https://www.make-it-in-germany.com/en/working-in-germany/job-listings"},
        {"name": "XING Jobs", "kind": "link", "why": "DACH professional network (no public job API)",
         "url": f"https://www.xing.com/jobs/search?keywords={quote(q)}&location=Deutschland"},
        {"name": "JOIN", "kind": "link", "why": "European recruitment platform", "url": google_site("join.com/companies", q)},
        {"name": "Glassdoor Germany", "kind": "link", "why": "Jobs + salaries + company reviews", "url": google_site("glassdoor.de", q)},
        {"name": "Welcome to the Jungle (incl. Otta)", "kind": "link", "why": "Tech / startup / international companies",
         "url": google_site("welcometothejungle.com", q)},
    ]
    underscored = quote("_".join(q.lower().split()))
    cities = [  # checked 2026-10-04
        {"name": "Berlin Startup Jobs", "kind": auto("berlinstartupjobs"), "why": "Berlin startups; read via its RSS feed",
         "url": f"https://berlinstartupjobs.com/?s={quote_plus(q)}"},
        {"name": "Munich Startup", "kind": auto("munichstartup"), "why": "Munich's startup portal (munich-startup.de/jobs)",
         "url": "https://www.munich-startup.de/jobs"},
        {"name": "Startup City Hamburg", "kind": auto("startupcityhamburg"), "why": "Hamburg's startup portal; read via its jobs RSS feed",
         "url": "https://startupcity.hamburg/jobs-cofounder/startup-jobs"},
        {"name": "englishjobs.de", "kind": "link",
         "why": "English-speaking jobs, any city (collects ads from other boards; no feed, its job links forbid bots)",
         "url": f"https://englishjobs.de/jobs/{underscored}"},
        {"name": "SpinLab (Leipzig)", "kind": "link", "why": "Leipzig startup jobs, many English-speaking (no feed)",
         "url": "https://www.spinlab.co/jobs-in-leipzig"},
        {"name": "deutsche-startups.de jobs (Frankfurt, Cologne, Stuttgart, Düsseldorf…)", "kind": "link",
         "why": "Startup jobs with a city filter; only a few ads per city (no job feed)",
         "url": "https://www.deutsche-startups.de/startups-jobs/stellenangebote/filter/duesseldorf-frankfurtmain-koeln-stuttgart-muenchen/"},
        {"name": "GermanTechJobs", "kind": "link",
         "why": "Closed: germantechjobs.de now redirects to a JobCopilot sign-up page. Searched via Google instead.",
         "url": google_site("germantechjobs.de", q)},
    ]
    europe = [
        {"name": "EURES", "kind": "link", "why": "EU job mobility portal (EU + Norway, Iceland, Liechtenstein, Switzerland)",
         "url": google_site("eures.europa.eu", q)},
        {"name": "EuroJobs", "kind": "link", "why": "Europe-wide jobs", "url": google_site("eurojobs.com", q)},
        {"name": "EURAXESS", "kind": "link", "why": "Research / technical positions", "url": google_site("euraxess.ec.europa.eu", q)},
        {"name": "European (Online) Job Days", "kind": "link", "why": "European recruitment events",
         "url": "https://www.europeanjobdays.eu/en/events"},
        {"name": "Wellfound", "kind": "link", "why": "Startups (no API; bots forbidden)", "url": google_site("wellfound.com/jobs", q)},
    ]
    employers = []
    for company, site in [("Siemens", "jobs.siemens.com"), ("ABB", "careers.abb"), ("Schneider Electric", "careers.se.com"),
                          ("Beckhoff", "beckhoff.com"), ("KUKA", "kuka.com"), ("Festo", "festo.com")]:
        employers.append({"name": company, "kind": "link", "why": "Own careers portal (no public job API, checked)",
                          "url": google_site(site, q)})
    # Big banks and insurers: own careers portals (Workday / SAP SuccessFactors), no public job API
    for company, site in [("Commerzbank", "jobs.commerzbank.com"),
                          ("ING Deutschland", "ing.de/karriere"), ("DKB", "dkb.de/karriere"), ("KfW", "kfw.de/karriere"),
                          ("DZ Bank", "dzbank.de/karriere"), ("Allianz", "careers.allianz.com"), ("Munich Re", "munichre.com/careers")]:
        employers.append({"name": company, "kind": "link", "why": "Bank / insurer careers portal (no public job API)",
                          "url": google_site(site, q)})
    employers.insert(1, {"name": "Bosch", "kind": "automatic", "why": "Read automatically via its SmartRecruiters API", "url": None})
    employers.insert(2, {"name": "Deutsche Bank, NVIDIA, Airbus, Accenture, Morgan Stanley, Citi…", "kind": auto("workday"),
                         "why": "Read automatically from their Workday careers sites (Settings → Workday career sites)", "url": None})
    remote = [  # remote jobs open to the EU (user's list, 2026-10-23)
        {"name": "Himalayas", "kind": auto("himalayas"), "why": "Official job search API; only jobs open to Europe / worldwide",
         "url": f"https://himalayas.app/jobs/worldwide?q={quote(q)}"},
        {"name": "We Work Remotely", "kind": auto("weworkremotely"), "why": "Official RSS feed; only 'Anywhere' / Europe / EMEA jobs",
         "url": f"https://weworkremotely.com/remote-jobs/search?term={quote(q)}"},
        {"name": "workremotely.eu", "kind": auto("workremotely_eu"), "why": "Public job list with EU eligibility per job (no full job text)",
         "url": "https://workremotely.eu/"},
        {"name": "OpenJobsEU", "kind": auto("openjobseu"), "why": "EU remote job board, public feed with full job text", "url": "https://openjobseu.org/"},
        {"name": "RemoteBoard", "kind": auto("remoteboard"), "why": "Job pages from its sitemap (robots.txt allows them); only jobs open to Europe",
         "url": "https://remoteboard.com/"},
        {"name": "Wellfound (remote)", "kind": "link", "why": "Startups (no API; bots forbidden)", "url": "https://wellfound.com/candidates/remote"},
        {"name": "Hidden Remote", "kind": "link", "why": "Job data is behind robots-disallowed /api/: search it yourself", "url": "https://hiddenremote.io/"},
        {"name": "Psst Jobs (Europe)", "kind": "link", "why": "Job data is behind robots-disallowed /data/: search it yourself",
         "url": "https://psstjobs.com/remote-jobs/europe/"},
        {"name": "Rolefinder", "kind": "link", "why": "Blocks automatic access (HTTP 403): search it yourself", "url": "https://rolefinder.co/"},
    ]
    return [{"group": "Germany", "boards": germany}, {"group": "Cities (startup boards)", "boards": cities}, {"group": "Europe", "boards": europe},
            {"group": "Remote in Europe", "boards": remote}, {"group": "Direct employers", "boards": employers}]


@router.get("/job-boards")
def job_boards(q: str | None = None, profile: Profile = Depends(current_profile)):
    settings = user_settings(profile)
    keyword = (q or next(iter(settings["search_queries"]), "Software Engineer")).strip()
    return {"keyword": keyword, "keywords": settings["search_queries"], "groups": boards(keyword, set(settings["sources"]), settings)}


@router.get("/source-health")
def source_health(profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    """Which sources were searched, when, did it work, how many jobs each one gave (open / closed)."""
    settings = user_settings(profile)
    status = {s.source: s for s in db.query(SourceStatus).filter_by(user_id=profile.user_id)}
    counts = dict(db.query(Job.source, func.count()).filter(Job.user_id == profile.user_id).group_by(Job.source).all())
    closed = dict(db.query(Job.source, func.count()).filter(Job.user_id == profile.user_id, Job.closed_at.isnot(None))
                  .group_by(Job.source).all())
    newest = dict(db.query(Job.source, func.max(Job.discovered_at)).filter(Job.user_id == profile.user_id).group_by(Job.source).all())
    rows = []
    for name, (_, companies_key) in SOURCES.items():
        if name == "demo" and name not in settings["sources"]:
            continue
        s = status.get(name)
        rows.append({
            "source": name, "enabled": name in settings["sources"],
            "companies": len(settings.get(companies_key, [])) if companies_key else None,
            "last_checked_at": s.last_checked_at if s else None, "last_ok_at": s.last_ok_at if s else None,
            "last_error": s.last_error if s else None, "blocked": s.blocked if s else False,
            "jobs": counts.get(name, 0), "closed": closed.get(name, 0), "newest_job_at": newest.get(name),
        })
    checked = db.query(func.count(), func.max(Job.checked_at)).filter(Job.user_id == profile.user_id, Job.checked_at.isnot(None)).one()
    return {"sources": rows, "rechecked_jobs": checked[0], "last_recheck_at": checked[1]}
