"""All database tables in one place."""
from datetime import UTC, date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def now():
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Profile(Base):
    """The candidate (from the CV). The ONLY source of facts for the standard CV and cover letters."""
    __tablename__ = "profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    location: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(50))
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    github_url: Mapped[str | None] = mapped_column(String(500))
    headline: Mapped[str | None] = mapped_column(String(300))
    summary: Mapped[str | None] = mapped_column(Text)
    education: Mapped[list] = mapped_column(JSON, default=list)       # ["MSc Computer Science, University of Greenwich, London"]
    experience: Mapped[list] = mapped_column(JSON, default=list)      # [{"company", "role", "location", "dates"}]
    years_experience: Mapped[float | None] = mapped_column(Float)
    target_country: Mapped[str] = mapped_column(String(100), default="Germany")
    target_roles: Mapped[list] = mapped_column(JSON, default=list)
    skills: Mapped[list] = mapped_column(JSON, default=list)          # [{"name": "Python", "years": 2.5 or None}]
    languages: Mapped[list] = mapped_column(JSON, default=list)       # [{"language": "English", "level": "Professional"}]
    domain_experience: Mapped[list] = mapped_column(JSON, default=list)
    projects: Mapped[list] = mapped_column(JSON, default=list)        # [{"name", "description", "skills"}]
    # Used by the score (sponsorship part). None = not set yet.
    visa_required: Mapped[bool | None] = mapped_column(Boolean)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)        # thresholds, weights, sources...



class Company(Base):
    __tablename__ = "companies"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(300))
    key: Mapped[str] = mapped_column(String(300))     # normalized name, e.g. "siemens" for "Siemens AG"
    website: Mapped[str | None] = mapped_column(String(500))
    locations: Mapped[list] = mapped_column(JSON, default=list)
    last_contact_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(300))
    company: Mapped[str] = mapped_column(String(300))
    location: Mapped[str | None] = mapped_column(String(300))
    country: Mapped[str | None] = mapped_column(String(100))
    remote_type: Mapped[str] = mapped_column(String(20), default="unknown")  # remote / hybrid / onsite / unknown
    employment_type: Mapped[str | None] = mapped_column(String(50))
    source: Mapped[str] = mapped_column(String(50))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    application_url: Mapped[str | None] = mapped_column(String(1000))
    company_url: Mapped[str | None] = mapped_column(String(1000))
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    original_description: Mapped[str] = mapped_column(Text, deferred=True)   # first JD ever seen, never changed (loaded only when used)
    jd_hash: Mapped[str] = mapped_column(String(64), index=True)
    parsed: Mapped[dict] = mapped_column(JSON, default=dict)   # skills, requirements, salary, evidence...
    skills_text: Mapped[str] = mapped_column(Text, default="")  # ",python,fastapi," for simple filtering
    visa_status: Mapped[str] = mapped_column(String(20), default="unclear")  # confirmed / unclear / unlikely
    language_requirement: Mapped[str] = mapped_column(String(30), default="english")
    experience_required: Mapped[float | None] = mapped_column(Float)
    seniority: Mapped[str | None] = mapped_column(String(30))
    risk_flags: Mapped[list] = mapped_column(JSON, default=list)
    description_incomplete: Mapped[bool] = mapped_column(Boolean, default=False)
    ats_score: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(30), default="NEW")  # NEW / QUALIFIED (score ≥ min) / REVIEW / NOT_QUALIFIED / RISK / APPLIED
    is_saved: Mapped[bool] = mapped_column(Boolean, default=False)
    cv_prepared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # CV downloaded for this job
    deadline: Mapped[date | None] = mapped_column(Date)                         # application deadline (from the JD or you)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # a source listed it (last time)
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))    # we re-opened the job page (freshness)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))     # page gone / "position filled" → hidden
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # you said "not for me" → hidden for good
    agency: Mapped[str | None] = mapped_column(String(200))  # recruitment company that advertised it (company = employer if named)


class JobSource(Base):
    """Every website where the same job was seen."""
    __tablename__ = "job_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(50))
    url: Mapped[str | None] = mapped_column(String(1000))
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class JDVersion(Base):
    """Every different text of a job description. Version 1 = original."""
    __tablename__ = "jd_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text, deferred=True)  # loaded only when used (lists and duplicate checks don't need it)
    jd_hash: Mapped[str] = mapped_column(String(64))
    source: Mapped[str | None] = mapped_column(String(50))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Score(Base):
    __tablename__ = "scores"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    jd_version: Mapped[int] = mapped_column(Integer, default=1)
    overall: Mapped[float] = mapped_column(Float)
    parts: Mapped[dict] = mapped_column(JSON)        # {"skills": 91, "experience": 84, ...}
    matched_skills: Mapped[list] = mapped_column(JSON, default=list)
    missing_skills: Mapped[list] = mapped_column(JSON, default=list)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    concerns: Mapped[list] = mapped_column(JSON, default=list)
    recommendation: Mapped[str] = mapped_column(String(20))  # APPLY / REVIEW / SKIP / RISK
    threshold: Mapped[float] = mapped_column(Float, default=80)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Application(Base):
    """A job you applied to, with the exact CV, cover letter, JD version and score you applied with."""
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("user_id", "job_id"),)  # never apply twice to the same job
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(30), default="APPLIED")  # see APP_STATUSES in routes/applications.py
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)  # when you applied
    cv_version: Mapped[str | None] = mapped_column(String(20))       # STANDARD (older rows: CV-001 …)
    rejection_stage: Mapped[str | None] = mapped_column(String(30))  # CV_SCREENING / HR / TECHNICAL / … (learning from rejections)
    next_follow_up: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_contact_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    referral: Mapped[bool] = mapped_column(Boolean, default=False)
    analysis: Mapped[dict] = mapped_column(JSON, default=dict)     # snapshot when you applied: match, gaps, interview prep
    jd_version: Mapped[int | None] = mapped_column(Integer)
    score: Mapped[float | None] = mapped_column(Float)
    cover_letter: Mapped[str | None] = mapped_column(Text)
    tailored_cv: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True)  # the exact CV (.docx) you applied with; loaded only for downloads
    notes: Mapped[str | None] = mapped_column(Text)
    history: Mapped[list] = mapped_column(JSON, default=list)   # [{"status", "at"}]
    interviews: Mapped[list] = mapped_column(JSON, default=list)  # [{"at": ISO datetime, "kind": "HR screen", "note"}]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class AutomationRun(Base):
    __tablename__ = "automation_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20), default="RUNNING")  # RUNNING / PAUSED / STOPPED / FINISHED / FAILED
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paused_seconds: Mapped[float] = mapped_column(Float, default=0)
    discovered: Mapped[int] = mapped_column(Integer, default=0)
    duplicates: Mapped[int] = mapped_column(Integer, default=0)
    qualified: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str | None] = mapped_column(Text)


class AutomationLog(Base):
    __tablename__ = "automation_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("automation_runs.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int | None] = mapped_column(Integer)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    level: Mapped[str] = mapped_column(String(10))   # INFO / WARNING / ERROR
    message: Mapped[str] = mapped_column(Text)


class OutreachContact(Base):
    """A recruiter / hiring manager YOU found (search links) for one job. Nothing is scraped or sent automatically."""
    __tablename__ = "outreach_contacts"   # not "contacts": that old table name is dropped on start-up
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(30))          # recruiter / talent_acquisition / hiring_manager / department_head / referral
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    email: Mapped[str | None] = mapped_column(String(320))  # only a publicly listed address
    source_url: Mapped[str | None] = mapped_column(String(1000))  # where you found the person
    relevance: Mapped[str | None] = mapped_column(String(300))    # e.g. "recruits backend engineers in Berlin"
    confidence: Mapped[str] = mapped_column(String(10), default="Medium")
    contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    followed_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CompanyResearch(Base):
    """Company + interview-process research done by AI with web search. Every fact has a source and confidence."""
    __tablename__ = "company_research"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    company_key: Mapped[str] = mapped_column(String(300), index=True)
    company: Mapped[str] = mapped_column(String(300))
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    searched_urls: Mapped[list] = mapped_column(JSON, default=list)   # every URL the web search really returned
    model: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MockSession(Base):
    """A mock interview for one job: one question at a time, each answer graded."""
    __tablename__ = "mock_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    questions: Mapped[list] = mapped_column(JSON, default=list)   # [{"question", "category", "probability"}]
    answers: Mapped[list] = mapped_column(JSON, default=list)     # [{"question", "answer", "grade"}]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SourceStatus(Base):
    """Source health: when each job source was last searched, and whether it worked."""
    __tablename__ = "source_status"
    __table_args__ = (UniqueConstraint("user_id", "source"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    source: Mapped[str] = mapped_column(String(50))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_ok_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)          # None = the last search worked
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)  # 403 / CAPTCHA: needs a human, never bypassed


class RecruitmentCompany(Base):
    """Recruitment directory (data/recruitment_companies.py) + YOUR interaction with each recruiter.
    Unknown = NULL. The *_verified fields are never assumed: only you set them, with a source URL."""
    __tablename__ = "recruitment_companies"
    __table_args__ = (UniqueConstraint("user_id", "seed_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    seed_id: Mapped[int] = mapped_column(Integer)                  # 1…50 from the starting list
    name: Mapped[str] = mapped_column(String(200))
    website_url: Mapped[str] = mapped_column(String(500))
    candidate_registration_url: Mapped[str | None] = mapped_column(String(500))
    country: Mapped[str | None] = mapped_column(String(100))
    recruitment_category: Mapped[str] = mapped_column(String(30))  # india / staffing / engineering / specialist
    focus: Mapped[str | None] = mapped_column(Text)
    industry_specializations: Mapped[list] = mapped_column(JSON, default=list)
    job_family_specializations: Mapped[list] = mapped_column(JSON, default=list)
    aliases: Mapped[list] = mapped_column(JSON, default=list)       # names used in job postings ("ALTEN")
    job_feed: Mapped[str | None] = mapped_column(String(100))      # "smartrecruiters:ALTEN" = read automatically; None = manual
    international_recruitment_supported: Mapped[bool | None] = mapped_column(Boolean)
    india_candidate_support_verified: Mapped[bool | None] = mapped_column(Boolean)
    visa_sponsorship_support_verified: Mapped[bool | None] = mapped_column(Boolean)
    relocation_support_verified: Mapped[bool | None] = mapped_column(Boolean)
    german_language_requirements: Mapped[str | None] = mapped_column(String(200))
    # unverified / website_ok (the app opened the site) / website_unreachable / website_blocked / confirmed (you, with a source)
    verification_status: Mapped[str] = mapped_column(String(30), default="unverified")
    source_url: Mapped[str | None] = mapped_column(String(500))     # evidence for the last verification
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_note: Mapped[str | None] = mapped_column(Text)     # what the check found ("HTTP 200 → https://…")
    # your workflow with this recruiter (not their decision about you)
    status: Mapped[str] = mapped_column(String(30), default="NOT_REVIEWED")
    is_saved: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)
    last_contact_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_follow_up: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
