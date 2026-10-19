"""Where jobs come from. Only official, public job-board APIs are used.

Each source has one function:  search(query, companies) -> list of job dicts
A job dict has: source, title, company, description, location, source_url, application_url, posted_at

Rules:
- one request per second per source (polite)
- HTTP 429 (too many requests): wait and retry up to 3 times
- HTTP 401/403 or a CAPTCHA page: stop and raise SourceBlocked. We never try to get around it.
- LinkedIn / Indeed / StepStone / XING / Glassdoor / Wellfound... are NOT scraped. They get search links
  (Job boards page) and you paste interesting jobs with "Import job".
"""
import gzip
import html
import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.logic.jd_parser import detect_country, html_to_text, simplify

USER_AGENT = "JobApplication/1.0 (personal job search)"


class SourceBlocked(Exception):
    """The website blocked us (403 / CAPTCHA). Needs a human; never bypassed."""


_last_request: dict[str, float] = {}
_cache: dict[str, tuple[float, httpx.Response | None]] = {}
CACHE_SECONDS = 20 * 60  # a company's job list is downloaded at most every 20 minutes


def get_cached(source: str, url: str, params: dict | None = None, json_body: dict | None = None) -> httpx.Response | None:
    """Same as get(), but reuses the answer for 20 minutes (one download per company, not one per keyword)."""
    key = url + str(sorted((params or {}).items())) + json.dumps(json_body, sort_keys=True)
    if key in _cache and time.monotonic() - _cache[key][0] < CACHE_SECONDS:
        return _cache[key][1]
    response = get(source, url, params, json_body)
    _cache[key] = (time.monotonic(), response)
    return response


def get(source: str, url: str, params: dict | None = None, json_body: dict | None = None) -> httpx.Response | None:
    """Polite GET (POST when json_body is given: some job APIs search by POST). None if missing or keeps failing."""
    for attempt in range(4):
        wait = 1.0 - (time.monotonic() - _last_request.get(source, 0))
        if wait > 0:
            time.sleep(wait)
        _last_request[source] = time.monotonic()
        try:
            r = httpx.request("POST" if json_body is not None else "GET", url, params=params, json=json_body, timeout=40,
                              follow_redirects=True, headers={"User-Agent": USER_AGENT})
        except httpx.HTTPError:
            time.sleep(2 ** attempt)
            continue
        if r.status_code in (401, 403) or "captcha" in r.text[:3000].lower():
            raise SourceBlocked(f"{source}: blocked (HTTP {r.status_code}). Manual action required.")
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(int(r.headers.get("retry-after", 2 ** attempt)))
            continue
        return r if r.status_code == 200 else None
    return None


# Words that say little about the role: "Sales Engineer" must not match the keyword "Software Engineer".
GENERIC_WORDS = {"engineer", "developer", "specialist", "consultant", "manager", "senior", "junior", "lead",
                 "mid", "level", "medior"}


def matches(query: str, title: str, description: str) -> bool:
    """Feeds have no search, so we filter: a meaningful keyword word in the title, half of the words overall."""
    words = [w for w in simplify(query).split() if len(w) > 2 and w not in ("germany", "and", "the")]
    if query == "*" or not words:
        return True
    title_s = simplify(title)
    must = [w for w in words if w not in GENERIC_WORDS] or words
    if not any(w in title_s for w in must):
        return False
    text = title_s + " " + simplify(description[:4000])
    return sum(w in text for w in words) >= max(1, (len(words) + 1) // 2)


def in_germany(location: str | None) -> bool:
    return detect_country(location) == "Germany"


def parse_date(value) -> datetime | None:
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value / 1000 if value > 1e11 else value, UTC)  # milliseconds or seconds
        date = datetime.fromisoformat(str(value).replace("Z", "+00:00")) if value else None
        return date.replace(tzinfo=UTC) if date and date.tzinfo is None else date  # "2026-09-14" -> UTC
    except (ValueError, OSError):
        return None


# ------------------------------------------------------------------ Greenhouse


def greenhouse(query: str, boards: list[str]) -> list[dict]:
    """boards.greenhouse.io/<board> -> public Job Board API"""
    jobs = []
    for board in boards:
        r = get_cached("greenhouse", f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs", {"content": "true"})
        for j in (r.json().get("jobs", []) if r else []):
            location = (j.get("location") or {}).get("name")
            if in_germany(location) and matches(query, j.get("title", ""), j.get("content", "")):
                jobs.append({
                    "source": "greenhouse", "title": j["title"], "company": j.get("company_name") or board,
                    "description": j.get("content", ""), "location": location,
                    "source_url": j.get("absolute_url"), "application_url": j.get("absolute_url"),
                    "posted_at": parse_date(j.get("first_published") or j.get("updated_at")),
                })
    return jobs


# ------------------------------------------------------------------ Lever


def lever(query: str, companies: list[str]) -> list[dict]:
    """jobs.lever.co/<company> -> public Postings API (US and EU servers)"""
    jobs = []
    for company in companies:
        postings = []
        for host in ("https://api.lever.co", "https://api.eu.lever.co"):
            r = get_cached("lever", f"{host}/v0/postings/{company}", {"mode": "json"})
            if r and r.json():
                postings = r.json()
                break
        for p in postings:
            location = (p.get("categories") or {}).get("location")
            lists = "\n".join(f"<h3>{x.get('text', '')}</h3>{x.get('content', '')}" for x in p.get("lists", []))
            description = f"{p.get('description', '')}\n{lists}\n{p.get('additional', '')}"
            if in_germany(location) and matches(query, p.get("text", ""), description):
                jobs.append({
                    "source": "lever", "title": p["text"], "company": company, "description": description,
                    "location": location, "source_url": p.get("hostedUrl"),
                    "application_url": p.get("applyUrl") or p.get("hostedUrl"), "posted_at": parse_date(p.get("createdAt")),
                })
    return jobs


# ------------------------------------------------------------------ SmartRecruiters


def smartrecruiters(query: str, companies: list[str]) -> list[dict]:
    """jobs.smartrecruiters.com/<Company> -> public Posting API (has real search + country filter)"""
    jobs = []
    for company in companies:
        r = get("smartrecruiters", f"https://api.smartrecruiters.com/v1/companies/{company}/postings",
                {"q": "" if query == "*" else query, "country": "de", "limit": 25})
        for item in (r.json().get("content", []) if r else []):
            d = get_cached("smartrecruiters", f"https://api.smartrecruiters.com/v1/companies/{company}/postings/{item['id']}")
            if not d:
                continue
            d = d.json()
            sections = (d.get("jobAd") or {}).get("sections") or {}
            description = "".join(f"<h3>{s.get('title', '')}</h3>{s.get('text', '')}" for s in sections.values() if isinstance(s, dict) and s.get("text"))
            if not matches(query, d.get("name", ""), description):
                continue  # their search is full-text: "Prompt Engineer" also returns a PHP job that mentions "prompt"
            jobs.append({
                "source": "smartrecruiters", "title": d.get("name", ""), "company": (d.get("company") or {}).get("name", company),
                "description": description, "location": (d.get("location") or {}).get("fullLocation"),
                "source_url": d.get("postingUrl"), "application_url": d.get("applyUrl") or d.get("postingUrl"),
                "posted_at": parse_date(d.get("releasedDate")),
            })
    return jobs


# ------------------------------------------------------------------ Personio


def personio(query: str, companies: list[str]) -> list[dict]:
    """<company>.jobs.personio.de/xml -> public XML feed"""
    jobs = []
    for company in companies:
        r = get_cached("personio", f"https://{company}.jobs.personio.de/xml")
        if not r:
            continue
        for pos in ET.fromstring(r.content).iter("position"):
            title = (pos.findtext("name") or "").strip()
            location = (pos.findtext("office") or "").strip()
            description = "".join(f"<h3>{d.findtext('name') or ''}</h3>{d.findtext('value') or ''}" for d in pos.iter("jobDescription"))
            url = f"https://{company}.jobs.personio.de/job/{pos.findtext('id')}"
            if in_germany(location) and matches(query, title, description):
                jobs.append({
                    "source": "personio", "title": title, "company": (pos.findtext("subcompany") or company).strip(),
                    "description": description, "location": location, "source_url": url, "application_url": url,
                    "posted_at": parse_date(pos.findtext("createdAt")),
                })
    return jobs


# ------------------------------------------------------------------ Ashby


def ashby(query: str, boards: list[str]) -> list[dict]:
    """jobs.ashbyhq.com/<board> -> public Job Posting API (used by many startups' own careers pages)"""
    jobs = []
    for board in boards:
        r = get_cached("ashby", f"https://api.ashbyhq.com/posting-api/job-board/{board}")
        for j in (r.json().get("jobs", []) if r else []):
            places = [j.get("location") or ""] + [x.get("location") or "" for x in j.get("secondaryLocations") or []]
            country = ((j.get("address") or {}).get("postalAddress") or {}).get("addressCountry")
            german = [p for p in places if in_germany(p)]
            if not j.get("isListed", True) or not (german or country == "Germany"):
                continue
            if matches(query, j.get("title", ""), j.get("descriptionPlain") or ""):
                jobs.append({
                    "source": "ashby", "title": j["title"], "company": board.replace("-", " ").title(),
                    "description": j.get("descriptionHtml") or j.get("descriptionPlain") or "",
                    "location": (german or places)[0] + (" (remote)" if j.get("isRemote") else ""),
                    "source_url": j.get("jobUrl"), "application_url": j.get("applyUrl") or j.get("jobUrl"),
                    "posted_at": parse_date(j.get("publishedAt")),
                })
    return jobs


# ------------------------------------------------------------------ Workday (big companies' own career sites)


def _germany_facet(facets: list) -> tuple[str, str] | None:
    """Workday's country filter: (facet parameter, id of "Germany"). Its name differs per company; some nest it."""
    for facet in facets or []:
        for value in facet.get("values", []):
            if value.get("descriptor") in ("Germany", "Deutschland") and "id" in value:
                return facet["facetParameter"], value["id"]
            found = _germany_facet([value]) if "values" in value else None
            if found:
                return found
    return None


def company_name(legal: str) -> str:
    """'DE01 NVIDIA Germany' / 'Amazon Web Services ... GmbH - R28' → without the internal entity codes."""
    return re.sub(r"\s+-\s+R\d+$", "", re.sub(r"^[A-Z]{2}\d{2,3}\s+", "", legal.strip()))


def workday(query: str, sites: list[str]) -> list[dict]:
    """<host>/<tenant>/<site>, e.g. db.wd3.myworkdayjobs.com/db/DBWebSite: the public JSON behind the company's own
    Workday careers page (robots.txt allows the site; checked 2026-10-19). Only jobs in Germany (Workday's country
    filter), the first 20 search results per keyword; job details are read only for titles that match."""
    jobs = []
    for site in sites:
        host, tenant, name = site.split("/")
        base = f"https://{host}/wday/cxs/{tenant}/{name}"
        r = get_cached("workday", f"{base}/jobs", json_body={"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""})
        germany = _germany_facet(r.json().get("facets")) if r else None
        if not germany:
            continue  # no jobs in Germany right now
        r = get_cached("workday", f"{base}/jobs", json_body={"appliedFacets": {germany[0]: [germany[1]]}, "limit": 20, "offset": 0,
                                                             "searchText": "" if query == "*" else query})
        for posting in (r.json().get("jobPostings", []) if r else []):
            if not matches(query, posting.get("title", ""), posting.get("title", "")):
                continue  # title check first, so we don't open every job
            detail = get_cached("workday", base + posting["externalPath"])
            info = (detail.json() if detail else {}).get("jobPostingInfo") or {}
            if not info or not matches(query, info.get("title", ""), info.get("jobDescription", "")):
                continue
            places = [info.get("location") or posting.get("locationsText") or ""] + list(info.get("additionalLocations") or [])
            location = next((p for p in places if in_germany(p)), f"{places[0]}, Germany")  # the country filter said Germany
            url = info.get("externalUrl") or f"https://{host}/{name}{posting['externalPath']}"
            jobs.append({
                "source": "workday", "title": info["title"],
                "company": company_name((detail.json().get("hiringOrganization") or {}).get("name") or tenant),
                "description": info.get("jobDescription", ""), "location": location,
                "source_url": url, "application_url": url, "posted_at": parse_date(info.get("startDate")),
            })
    return jobs


# ------------------------------------------------------------------ Amazon


def amazon(query: str, _companies: list[str]) -> list[dict]:
    """amazon.jobs search JSON (the API behind their careers site; robots.txt allows it). Jobs in Germany only."""
    r = get_cached("amazon", "https://www.amazon.jobs/en/search.json",
                   {"normalized_country_code[]": "DEU", "base_query": "" if query == "*" else query, "result_limit": 50, "sort": "recent"})
    jobs = []
    for j in (r.json().get("jobs", []) if r else []):
        description = "\n".join(f"<h3>{head}</h3>{j.get(key) or ''}" for head, key in (
            ("Description", "description"), ("Basic qualifications", "basic_qualifications"), ("Preferred qualifications", "preferred_qualifications")))
        if matches(query, j.get("title", ""), description):
            url = "https://www.amazon.jobs" + j["job_path"]
            jobs.append({
                "source": "amazon", "title": j["title"], "company": company_name(j.get("company_name") or "Amazon"),
                "description": description, "location": j.get("normalized_location", "").replace(", DEU", ", Germany"),
                "source_url": url, "application_url": url,
                "posted_at": parse_date(datetime.strptime(" ".join(j["posted_date"].split()), "%B %d, %Y").date().isoformat()) if j.get("posted_date") else None,
            })
    return jobs


# ------------------------------------------------------------------ Arbeitnow


def arbeitnow(query: str, _companies: list[str], pages: int = 4) -> list[dict]:
    """arbeitnow.com free public job API (many English-speaking jobs in Germany).
    Their terms: "free public API, please do not abuse, link back". We read at most 4 pages, cached 20 min."""
    jobs = []
    for page in range(1, pages + 1):
        r = get_cached("arbeitnow", "https://www.arbeitnow.com/api/job-board-api", {"page": page})
        if not r:
            break
        data = r.json()
        for j in data.get("data", []):
            location = j.get("location") or ""
            if not (in_germany(location) or (j.get("remote") and "germany" in location.lower())):
                continue
            if matches(query, j.get("title", ""), j.get("description", "")):
                jobs.append({
                    "source": "arbeitnow", "title": j["title"], "company": j.get("company_name", ""),
                    "description": j.get("description", ""), "location": location + (" (remote)" if j.get("remote") else ""),
                    "source_url": j.get("url"), "application_url": j.get("url"),
                    "posted_at": parse_date(int(j["created_at"])) if str(j.get("created_at", "")).isdigit() else None,
                })
        if not (data.get("links") or {}).get("next"):
            break
    return jobs


# ------------------------------------------------------------------ City startup job boards
# Checked 2026-10-04: robots.txt allows these pages, we read 1 page per second and cache 20 minutes.


def rss_items(r: httpx.Response | None) -> list[ET.Element]:
    return list(ET.fromstring(r.content).iter("item")) if r else []


def rss_date(item: ET.Element) -> datetime | None:
    try:
        return parsedate_to_datetime(item.findtext("pubDate") or "")
    except (TypeError, ValueError):
        return None


def job_posting(page: str) -> dict:
    """The schema.org JobPosting block many job pages include for search engines (full text, date, company)."""
    for block in re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', page, re.S):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        if isinstance(data, dict) and data.get("@type") == "JobPosting":
            return data
    return {}


def berlinstartupjobs(query: str, _companies: list[str], pages: int = 2) -> list[dict]:
    """berlinstartupjobs.com: its own RSS feed (with site search). The feed has only a teaser, so for jobs
    whose title matches we open the job page and read its JobPosting block."""
    jobs = []
    for page in range(1, pages + 1):
        params = {"paged": page} if query == "*" else {"s": query, "paged": page}
        items = rss_items(get_cached("berlinstartupjobs", "https://berlinstartupjobs.com/feed/", params))
        for item in items:
            title, _, company = html.unescape(item.findtext("title") or "").rpartition(" // ")
            title, company = (title or company).strip(), company.strip() if title else ""
            link = item.findtext("link")
            if not matches(query, title, item.findtext("description") or ""):
                continue
            detail = get_cached("berlinstartupjobs", link)
            posting = job_posting(detail.text) if detail else {}
            description = posting.get("description") or item.findtext("description") or ""
            if not matches(query, title, description):
                continue
            jobs.append({
                "source": "berlinstartupjobs", "title": title,
                "company": (posting.get("hiringOrganization") or {}).get("name") or company or "Unknown (Berlin startup)",
                "description": description, "location": "Berlin, Germany", "source_url": link, "application_url": link,
                "posted_at": parse_date(posting.get("datePosted")) or rss_date(item),
            })
        if len(items) < 10:
            break  # last page
    return jobs


def startupcityhamburg(query: str, _companies: list[str]) -> list[dict]:
    """startupcity.hamburg (the city's startup portal): its official jobs RSS feed, full job text included.
    The feed has no company name, so for matching jobs we read it from the job page's JobPosting block."""
    jobs = []
    for item in rss_items(get_cached("startupcityhamburg", "https://startupcity.hamburg/feed/jobs")):
        title, description = html.unescape(item.findtext("title") or "").strip(), item.findtext("description") or ""
        link = item.findtext("link")
        if matches(query, title, description):
            detail = get_cached("startupcityhamburg", link)
            company = (job_posting(detail.text if detail else "").get("hiringOrganization") or {}).get("name")
            jobs.append({
                "source": "startupcityhamburg", "title": title, "company": company or "Unknown (Hamburg startup)",
                "description": description, "location": "Hamburg, Germany", "source_url": link,
                "application_url": link, "posted_at": rss_date(item),  # the page's datePosted is wrong (in the future)
            })
    return jobs


def ago(text: str) -> datetime | None:
    """German "vor 5 Wochen" / "vor 3 Tagen" / "vor 2 Monaten" -> a date."""
    m = re.search(r"vor (\d+|einer?|einem) (Stunde|Tag|Woche|Monat)", text)
    if not m:
        return None
    n = int(m.group(1)) if m.group(1).isdigit() else 1
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return today - timedelta(days=n * {"Stunde": 0, "Tag": 1, "Woche": 7, "Monat": 30}[m.group(2)])


def munichstartup(query: str, _companies: list[str], pages: int = 3) -> list[dict]:
    """munich-startup.de/jobs (the city's startup portal). No feed, so we read the job list page
    (company + title per card) and open only the jobs whose title matches."""
    jobs, seen = [], set()
    for page in range(1, pages + 1):
        r = get_cached("munichstartup", "https://www.munich-startup.de/jobs", {"page": page} if page > 1 else None)
        cards = re.findall(r'href="(/jobs/anzeige/\d+)".*?<p class="text-card-meta[^"]*">(.*?)</p>.*?<h3[^>]*>(.*?)</h3>',
                           r.text if r else "", re.S)
        new = [c for c in cards if c[0] not in seen]
        for path, company, title in new:
            seen.add(path)
            title, company = html.unescape(title).strip(), html.unescape(company).strip()
            if not matches(query, title, title):  # title check first, so we don't open every job
                continue
            url = "https://www.munich-startup.de" + path
            detail = get_cached("munichstartup", url)
            body = re.search(r'<div class="pinboard-prose[^"]*">(.*?)</article>', detail.text, re.S) if detail else None
            description = body.group(1) if body else ""
            if matches(query, title, description):
                jobs.append({"source": "munichstartup", "title": title, "company": company or "Unknown (Munich startup)",
                             "description": description, "location": "Munich, Germany", "source_url": url,
                             "application_url": url, "posted_at": ago(detail.text[detail.text.find("<h1"):][:3000]) if detail else None})
        if not new:
            break  # no more pages
    return jobs


# ------------------------------------------------------------------ Recruitment agencies' own job pages
# Checked 2026-10-19: these recruiters list their job pages in the sitemap named in robots.txt, robots.txt allows them,
# and each job page carries a schema.org JobPosting block (title, employer, location, date, full text). We read the
# sitemaps (cached), open only jobs whose URL words match your role (max PER_QUERY per site and role, 1 request/s),
# keep jobs in Germany, and never read pages robots.txt disallows. Hays / Amadeus Fire / Huxley / Computer Futures
# have no job data in their pages (built in the browser) and stay manual (links on the Recruiter jobs page).
RECRUITER_SITES = {
    "randstad": ("Randstad Germany", "https://www.randstad.de", r"/jobs/[^/]+_c\d+/?$"),
    "brunel": ("Brunel", "https://www.brunel.net", r"/jobs/[^/]+-pr-\d+/?$"),
    "vesterling": ("Vesterling", "https://www.vesterling.com", r"/job/\d+-[^/]+/?$"),
    "jac": ("JAC Recruitment Germany", "https://www.jac-recruitment.de", r"/job/[^/]+-\d+/?$"),
    "dekra": ("DEKRA Arbeit", "https://www.dekra-arbeit.de", r"/stellenmarkt/[^/]+-job-in-[^/]+/[0-9a-f-]{20,}/?$"),
    "persona": ("persona service", "https://www.persona.de", r"/jobs/[^/]+/[0-9a-f-]{36}/?$"),
    "tempton": ("TEMPTON", "https://www.tempton.de", r"/jobs/[a-z0-9-]+-[a-z0-9-]+/?$"),
    "orizon": ("Orizon", "https://www.orizon.de", r"/job/[^/]+-t\d+/?$"),
    "hofmann": ("I.K. Hofmann", "https://www.hofmann.info", r"/jobs/stellenanzeige/[^/]+/?$"),
}
PER_QUERY = 8                       # job pages opened per site and role (the sitemaps list thousands of jobs)
_robots: dict[str, RobotFileParser] = {}


def _allowed(base: str, url: str) -> bool:
    if base not in _robots:
        rp = RobotFileParser()
        r = get_cached("recruiters", f"{base}/robots.txt")
        rp.parse((r.text if r else "").splitlines())
        _robots[base] = rp
    return _robots[base].can_fetch(USER_AGENT, url)


def _sitemap_job_urls(base: str, pattern: str) -> list[str]:
    """Job-page URLs from the sitemaps named in robots.txt (sitemap indexes followed, job sitemaps first)."""
    robots = get_cached("recruiters", f"{base}/robots.txt")
    queue = re.findall(r"(?im)^sitemap:\s*(\S+)", robots.text if robots else "") or [f"{base}/sitemap.xml"]
    urls, seen, job = [], set(), re.compile(pattern)
    while queue and len(seen) < 30:
        sitemap = queue.pop(0)
        if sitemap in seen or not _allowed(base, sitemap):
            continue
        seen.add(sitemap)
        r = get_cached("recruiters", sitemap)
        body = r.content if r else b""
        if sitemap.endswith(".gz"):
            try:
                body = gzip.decompress(body)
            except OSError:
                pass
        text = body.decode("utf-8", "ignore")
        locs = re.findall(r"<loc>\s*(.*?)\s*</loc>", text)
        if "<sitemapindex" in text:
            queue = sorted(locs, key=lambda u: 0 if re.search(r"job|stell|vacanc", u, re.I) else 1) + queue
        else:
            urls += [html.unescape(u) for u in locs if job.search(urlparse(u).path)]
    return list(dict.fromkeys(urls))


def _job_posting_any(page: str) -> dict:
    """schema.org JobPosting from JSON-LD (also inside @graph or with @type as a list)."""
    for block in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', page, re.S):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        items = data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []
        for item in items:
            kind = item.get("@type") if isinstance(item, dict) else None
            if kind == "JobPosting" or (isinstance(kind, list) and "JobPosting" in kind):
                return item
    return {}


def _place(posting: dict) -> tuple[str, str]:
    """(city, country) from jobLocation.address (lists and plain strings allowed)."""
    loc = posting.get("jobLocation")
    loc = loc[0] if isinstance(loc, list) and loc else loc
    address = loc.get("address", {}) if isinstance(loc, dict) else {}
    address = address[0] if isinstance(address, list) and address else address
    if not isinstance(address, dict):
        return "", ""
    country = address.get("addressCountry")
    country = country.get("name", "") if isinstance(country, dict) else (country or "")
    return address.get("addressLocality") or "", country


def recruiters(query: str, sites: list[str]) -> list[dict]:
    jobs = []
    for key in sites:
        if key not in RECRUITER_SITES:
            continue
        agency, base, pattern = RECRUITER_SITES[key]
        seen = set()  # the same job in two languages (Vesterling /job and /en/job) counts once
        try:
            candidates = [u for u in _sitemap_job_urls(base, pattern)
                          if query == "*" or matches(query, " ".join(urlparse(u).path.split("/")[-2:]).replace("-", " "), "")]
            for url in candidates[:PER_QUERY]:
                if not _allowed(base, url):
                    continue
                page = get_cached("recruiters", url)
                posting = _job_posting_any(page.text) if page else {}
                city, country = _place(posting)
                title = html.unescape(posting.get("title") or "").strip()
                description = posting.get("description") or ""
                expires = parse_date(posting.get("validThrough"))
                if not title or country.strip().lower() not in ("de", "deu", "germany", "deutschland") \
                        or (expires and expires < datetime.now(UTC)) or not matches(query, title, html_to_text(description)):
                    continue
                if (title, city) in seen:
                    continue
                seen.add((title, city))
                org = posting.get("hiringOrganization")
                employer = (org.get("name") if isinstance(org, dict) else org) or agency
                jobs.append({
                    "source": "recruiters", "agency": agency, "title": title, "company": " ".join(str(employer).split()),
                    "description": description, "location": f"{city}, Germany" if city else "Germany",
                    "source_url": url, "application_url": posting.get("url") or url, "posted_at": parse_date(posting.get("datePosted")),
                })
        except SourceBlocked:
            continue  # this recruiter blocks automatic reading right now: skip it, never get around it
    return jobs


# ------------------------------------------------------------------ Demo (fictional, for trying the app)

DEMO_JOBS = [
    ("Industrial Software Engineer (m/w/d)", "Demo Automation GmbH", "Stuttgart, Germany",
     "We build SCADA and MES software for factories. Requirements: 2+ years of experience with Python and FastAPI, "
     "OPC UA, Modbus, PLC integration, Docker, PostgreSQL. Angular frontend. English is our working language. "
     "We offer visa sponsorship and relocation assistance. Full-time, permanent."),
    ("Python Backend Engineer", "Demo Cloud SE", "Berlin, Germany",
     "Requirements: 3+ years of experience with Python, Django or FastAPI, REST APIs, MySQL or PostgreSQL, Docker, AWS. "
     "Nice to have: Kubernetes. English-speaking team, hybrid work. Full-time, permanent contract."),
    ("IIoT Engineer", "Demo Machines AG", "Munich, Germany",
     "Connect machines to the cloud. Requirements: Python, MQTT, OPC UA, Docker, Linux. At least 2 years of experience. "
     "International candidates welcome, EU Blue Card support. Full-time."),
    ("Senior Full Stack Engineer", "Demo Commerce GmbH", "Hamburg, Germany",
     "Requirements: 6+ years of experience with React, Node.js, TypeScript and GraphQL. "
     "You must already have a valid EU work permit. Full-time."),
    ("Softwareentwickler (m/w/d)", "Demo Mittelstand GmbH", "Leipzig",
     "Ihr Profil: Mindestens 3 Jahre Berufserfahrung, sehr gute Deutschkenntnisse (C1), Java, SQL. "
     "Wir bieten eine unbefristete Vollzeitstelle."),
    ("Automation Software Engineer", "Demo Robotics GmbH", "Karlsruhe, Germany",
     "Develop automation software for robot cells. Requirements: Python, C++, PLC, Linux, Docker. "
     "2+ years of experience. English required. Full-time."),
]


def demo(query: str, _companies: list[str]) -> list[dict]:
    now = datetime.now(UTC)
    return [{
        "source": "demo", "title": title, "company": company, "location": location,
        "description": f"{company} is a fictional demo employer. You will join a small product team. {text}",
        "source_url": f"https://demo.example.com/jobs/{i}", "application_url": f"https://demo.example.com/jobs/{i}/apply",
        "company_url": "https://demo.example.com", "posted_at": now - timedelta(days=i),
    } for i, (title, company, location, text) in enumerate(DEMO_JOBS) if matches(query, title, text)]


# name -> (function, settings key holding the company list, or None)
SOURCES = {
    "greenhouse": (greenhouse, "greenhouse_boards"),
    "lever": (lever, "lever_companies"),
    "smartrecruiters": (smartrecruiters, "smartrecruiters_companies"),
    "personio": (personio, "personio_companies"),
    "ashby": (ashby, "ashby_boards"),
    "workday": (workday, "workday_sites"),
    "amazon": (amazon, None),
    "recruiters": (recruiters, "recruiter_sites"),
    "arbeitnow": (arbeitnow, None),
    "berlinstartupjobs": (berlinstartupjobs, None),
    "munichstartup": (munichstartup, None),
    "startupcityhamburg": (startupcityhamburg, None),
    "demo": (demo, None),
}


def search(source_name: str, query: str, user_settings: dict) -> list[dict]:
    function, companies_key = SOURCES[source_name]
    companies = user_settings.get(companies_key, []) if companies_key else []
    if companies_key and not companies:
        return []  # nothing configured for this source
    return function(query, companies)
