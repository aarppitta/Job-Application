"""Tests for the pure logic (no database)."""
from types import SimpleNamespace

from app.defaults import DEFAULT_PROFILE
from app.logic import dedup, writer
from app.logic.jd_parser import (
    detect_country, detect_language, detect_risks, detect_sponsorship, extract_experience_years, extract_salary, parse_job,
)
from app.logic.scoring import score_job
from app.logic.skills import canonical_skill, find_skills

SCADA_JD = """<h2>SCADA Software Developer</h2><p>We build industrial automation systems for manufacturing plants.</p>
<h3>Your profile</h3><ul><li>3+ years of experience in software development</li><li>Python and FastAPI</li>
<li>OPC UA, Modbus and PLC communication</li><li>Docker and PostgreSQL</li><li>Kubernetes is a plus</li></ul>
<h3>What we offer</h3><ul><li>Visa sponsorship and relocation assistance</li><li>English is our working language. Full-time.</li></ul>"""


def arpita(**changes):
    data = {**DEFAULT_PROFILE, "visa_required": True, "email": None, "phone": None}
    return SimpleNamespace(**{**data, **changes})


def job_from(title, description, location="Stuttgart, Germany"):
    info = parse_job(title, description, location)
    return SimpleNamespace(title=title, company="Test GmbH", location=location, original_description=info["text"], **{
        k: info[k] for k in ("parsed", "country", "remote_type", "employment_type", "visa_status",
                             "language_requirement", "experience_required", "seniority", "risk_flags")})


# ---- parsing


def test_sponsorship():
    assert detect_sponsorship("We offer visa sponsorship.")[0] == "confirmed"
    assert detect_sponsorship("We support EU Blue Card applications.")[0] == "confirmed"
    assert detect_sponsorship("No relocation support is provided.")[0] == "unclear"
    assert detect_sponsorship("Relocation help. You must already have a valid EU work permit.")[0] == "unlikely"
    assert detect_sponsorship("Nothing about visas here.")[0] == "unclear"


def test_language():
    assert detect_language("English speaking team")[0] == "english"
    assert detect_language("Fluent German and English are required.")[0] == "german_required"
    assert detect_language("German is a plus.")[0] == "german_plus"
    assert detect_language("Wir suchen einen Entwickler für unser Team und sind ein tolles Team mit der Cloud.")[0] == "german_jd"


def test_experience_salary_country():
    assert extract_experience_years("3+ years of experience with Python") == 3
    assert extract_experience_years("Mindestens 5 Jahre Berufserfahrung") == 5
    assert extract_experience_years("We have 25 years of experience as a company") is None
    assert extract_salary("Salary: €60,000 - €75,000") == {"min": 60000, "max": 75000, "currency": "EUR"}
    assert detect_country("München, Bayern") == "Germany"
    assert detect_country("Vienna, Austria") == "Austria"


def test_skills():
    assert "Java" not in find_skills("JavaScript and TypeScript")
    assert "OPC" not in find_skills("OPC UA server")
    assert canonical_skill("nodejs") == "Node.js"
    skills = {s["skill"]: s for s in parse_job("x", SCADA_JD, "Berlin")["parsed"]["skills"]}
    assert skills["Kubernetes"]["required"] is False and skills["Python"]["required"] is True


def test_scam_detection():
    assert detect_risks("Pay a refundable deposit and send a copy of your passport via Telegram")


# ---- duplicates


def test_duplicates():
    text = "ABC builds software for factories with Python, FastAPI, Docker and OPC UA in Munich. " * 3
    base = {"title": "Python Engineer", "company": "ABC GmbH", "text": text, "jd_hash": "h1", "url": None,
            "application_url": None, "location": "Munich"}
    assert dedup.is_same_job({**base, "title": "Backend Engineer", "company": "ABC Deutschland GmbH", "jd_hash": "h2"}, base)[0]
    assert dedup.is_same_job({**base, "url": "https://x.com/1?utm_source=a", "jd_hash": "x"}, {**base, "url": "https://x.com/1"})[0]
    assert not dedup.is_same_job({**base, "company": "XYZ AG", "jd_hash": "h3", "text": text + "x"}, base)[0]
    assert not dedup.is_same_job({**base, "location": "Berlin", "jd_hash": "h4"}, base)[0]  # other city = other job


# ---- scoring


def test_strong_match_is_apply_and_honest():
    result = score_job(arpita(), job_from("SCADA Software Developer", SCADA_JD))
    assert result["overall"] >= 85 and result["recommendation"] == "APPLY"
    assert any("3+ years" in c for c in result["concerns"])       # 2.5 vs 3 years is flagged
    assert "Kubernetes" in result["missing_skills"] and "PostgreSQL" not in result["missing_skills"]   # PostgreSQL: Job Application project


def test_german_required_and_unlikely_sponsorship_are_not_apply():
    german = job_from("Softwareentwickler Python", "Ihr Profil: Python, Django. Sehr gute Deutschkenntnisse (C1).", "Leipzig")
    assert score_job(arpita(), german)["recommendation"] != "APPLY"
    no_visa = job_from("Python Developer", "Python, FastAPI. You must already have a valid EU work permit. Full-time.")
    assert score_job(arpita(), no_visa)["recommendation"] == "SKIP"


def test_weights_change_score():
    job = job_from("SCADA Software Developer", SCADA_JD)
    only_location = {k: 0 for k in ("skills", "experience", "role", "industrial", "language", "sponsorship", "seniority")}
    assert score_job(arpita(), job, {**only_location, "location": 1})["overall"] == 100


# ---- writing



def test_cover_letter_and_fabrication_check():
    job = job_from("SCADA Software Developer", SCADA_JD)
    job.company = "Muster GmbH"
    text, made_by, warnings = writer.cover_letter(arpita(), job, ["SCADA", "OPC UA", "Python"])
    assert made_by == "template" and not warnings
    assert "Muster GmbH" in text and not writer.find_invented_claims(text, arpita(), job)
    assert writer.find_invented_claims("I have 5 years of Kubernetes experience and am AWS certified.", arpita(), job)



def test_non_software_engineering_job_is_not_a_match():
    rocket = job_from("Fluid Systems Engineer (f/m/d)", "Design fluid systems for rockets. Python for analysis is a plus. "
                      "3 years of experience in propulsion. English speaking team. Full-time.", "Munich, Germany")
    result = score_job(arpita(), rocket)
    assert result["parts"]["role"] == 0
    assert result["overall"] < 80 and result["recommendation"] != "APPLY"


def test_daily_scheduler_decision():
    from datetime import datetime

    from app.logic.scoring import match_label
    from app.services.scheduler import should_start

    cfg = {"daily_auto_start": True, "daily_start_time": "08:00"}
    morning = datetime(2026, 9, 30, 7, 59)
    later = datetime(2026, 9, 30, 9, 0)
    yesterday = datetime(2026, 9, 29, 8, 0)
    assert not should_start(cfg, morning, yesterday, running=False)       # too early
    assert should_start(cfg, later, yesterday, running=False)             # due today
    assert not should_start(cfg, later, later, running=False)             # already ran today
    assert not should_start(cfg, later, yesterday, running=True)          # one is running
    assert not should_start({**cfg, "daily_auto_start": False}, later, yesterday, running=False)
    assert match_label(79)["level"] == "stretch" and match_label(69)["level"] == "low" and match_label(80)["level"] == "good"


def test_lead_and_architect_roles_are_not_apply():
    for title in ("Lead Software Engineer (m/f/d)", "Software Architect (m/f/d)"):
        job = job_from(title, SCADA_JD, "Berlin, Germany")
        result = score_job(arpita(), job)
        assert result["recommendation"] != "APPLY", title


def test_keyword_needs_a_meaningful_title_word():
    from app.sources import matches

    assert matches("Software Engineer", "Software Engineer (m/w/d)", "")
    assert not matches("Software Engineer", "Sales Engineer", "We sell software")   # "engineer" alone is not enough
    assert matches("Data Analyst", "Senior Data Analyst", "SQL, data analysis")
    assert not matches("Data Analyst", "Python Developer", "data analyst team")


def test_hindi_learning_links():
    from app.logic.learning import CHANNELS, hindi_videos

    docker = hindi_videos("Docker")
    assert [l["channel"] for l in docker][:2] == ["TrainWithShubham", "CloudFolks HUB Hindi"]
    assert all(l["url"].startswith("https://www.youtube.com/results?search_query=") for l in docker)
    assert docker[-1]["channel"] == "YouTube search" and "Hindi" in docker[-1]["url"]
    assert [l["channel"] for l in hindi_videos("OPC UA")] == ["YouTube search"]        # no verified channel -> only a search
    assert all(c in CHANNELS for s in ("FastAPI", "PostgreSQL", "DSA", "React") for c in [l["channel"] for l in hindi_videos(s)][:-1])


def test_workday_country_filter_and_company_names():
    from app.sources import _germany_facet, company_name
    flat = [{"facetParameter": "Country", "values": [{"descriptor": "India", "id": "in"}, {"descriptor": "Germany", "id": "de"}]}]
    nested = [{"facetParameter": "locationMainGroup", "values": [{"facetParameter": "locationHierarchy1",
                                                                  "values": [{"descriptor": "Germany", "id": "x1"}]}]}]
    assert _germany_facet(flat) == ("Country", "de")
    assert _germany_facet(nested) == ("locationHierarchy1", "x1")            # NVIDIA nests it one level deeper
    assert _germany_facet([{"facetParameter": "Country", "values": [{"descriptor": "France", "id": "fr"}]}]) is None
    assert company_name("DE01 NVIDIA Germany") == "NVIDIA Germany"
    assert company_name("Amazon Web Services Development Center Germany GmbH - R28") == "Amazon Web Services Development Center Germany GmbH"


def test_deadline_and_closed_page_detection():
    from app.logic.jd_parser import find_deadline
    from app.services.freshness import GONE
    assert find_deadline("Application deadline: 15.11.2026. We look forward") == "2026-11-15"
    assert find_deadline("Bewerbungsfrist: 30. November 2026") == "2026-11-30"
    assert find_deadline("Please apply by November 30, 2026.") == "2026-11-30"
    assert find_deadline("We review applications continuously.") is None
    assert GONE.search("Sorry, this job is no longer available.") and GONE.search("Die Stelle ist bereits besetzt")
    assert not GONE.search("The position will be filled as soon as possible. Apply now!")


def test_recruiter_job_pages(monkeypatch):
    """Recruiter source: sitemap → only role-matching job URLs → JobPosting → Germany only, duplicates once."""
    from app import sources

    class R:
        def __init__(self, text): self.text, self.content = text, text.encode()
    posting = lambda title, country: R('<script type="application/ld+json">' + __import__("json").dumps({
        "@type": "JobPosting", "title": title, "description": "Python FastAPI developer for SCADA. " * 10,
        "hiringOrganization": {"name": "Orizon GmbH"}, "datePosted": "2026-10-01",
        "jobLocation": {"address": {"addressLocality": "Munich", "addressCountry": country}}}) + "</script>")
    pages = {
        "https://www.orizon.de/robots.txt": R("User-agent: *\nDisallow: /intern/\nSitemap: https://www.orizon.de/sitemap.xml"),
        "https://www.orizon.de/sitemap.xml": R("<urlset><loc>https://www.orizon.de/de/job/python-developer-munich-t1</loc>"
                                                "<loc>https://www.orizon.de/de/job/staplerfahrer-essen-t2</loc>"
                                                "<loc>https://www.orizon.de/de/job/python-developer-zurich-t3</loc>"
                                                "<loc>https://www.orizon.de/en/job/python-developer-munich-t4</loc></urlset>"),
        "https://www.orizon.de/de/job/python-developer-munich-t1": posting("Python Developer (m/w/d)", "DE"),
        "https://www.orizon.de/de/job/python-developer-zurich-t3": posting("Python Developer (m/w/d)", "CH"),
        "https://www.orizon.de/en/job/python-developer-munich-t4": posting("Python Developer (m/w/d)", "DE"),
    }
    opened = []
    monkeypatch.setattr(sources, "get_cached", lambda source, url, *a, **k: opened.append(url) or pages.get(url))
    sources._robots.clear()
    [job] = sources.recruiters("Python Developer", ["orizon"])
    assert job["agency"] == "Orizon" and job["company"] == "Orizon GmbH" and job["location"] == "Munich, Germany"
    assert "https://www.orizon.de/de/job/staplerfahrer-essen-t2" not in opened          # title doesn't match: never opened


def test_skills_you_have_are_never_gaps():
    from types import SimpleNamespace
    from app.logic.analysis import requirements, skill_gaps
    from app.logic.skills import with_implied
    assert {"Node.js", "JavaScript"} <= with_implied({"Express.js"}) and "JavaScript" in with_implied({"Angular"})   # chains
    job = job_from("Full Stack Developer", "Requirements: JavaScript, React, Kubernetes and Python. Full-time, English.")
    gaps = {g["skill"] for g in skill_gaps(requirements(arpita(), job), {})}
    assert "JavaScript" not in gaps and "React" not in gaps and "Kubernetes" in gaps


def test_database_url_password_with_special_characters():
    from app.config import encode_password
    raw = "postgresql://postgres.abc:Pa@ss/w#rd@aws-0-eu-central-1.pooler.supabase.com:5432/postgres?sslmode=require"
    fixed = encode_password(raw)
    assert fixed == "postgresql://postgres.abc:Pa%40ss%2Fw%23rd@aws-0-eu-central-1.pooler.supabase.com:5432/postgres?sslmode=require"
    assert encode_password(fixed) == fixed                     # already encoded: unchanged
    plain = "postgresql://user:simple@host.neon.tech/db?sslmode=require"
    assert encode_password(plain) == plain
    assert encode_password("postgresql+psycopg://localhost:5432/germany_jobs") == "postgresql+psycopg://localhost:5432/germany_jobs"


def test_remote_jobs_anywhere_in_the_eu_are_wanted():
    from app.logic.jd_parser import is_eu_remote
    from app.sources import wanted
    assert wanted("Berlin, Germany") and wanted("Munich (hybrid)")
    assert wanted("Remote - Europe") and wanted("EU Remote") and wanted("Remote, EMEA")
    assert wanted("Amsterdam, Netherlands", remote=True) and wanted("Lisbon, Portugal (remote)")
    assert not wanted("Amsterdam, Netherlands")            # on-site outside Germany
    assert not wanted("Remote - United States") and not wanted("London (remote)") and not wanted("Remote")
    assert detect_country("Neu-Ulm") != "Europe" and is_eu_remote("Warsaw, Poland", True)
