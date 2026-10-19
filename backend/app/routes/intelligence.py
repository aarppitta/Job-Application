"""Job intelligence API: analysis, company research, interview package, mock interview, contacts, strategy."""
import time
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import current_profile
from app.config import settings as app_config
from app.database import get_db
from app.defaults import user_settings
from app.logic import ai, market, outreach
from app.logic.analysis import analyze_job
from app.logic.dedup import company_key
from app.logic.interview import ANSWER_STRUCTURES, interview_prep
from app.logic.jd_parser import detect_city
from app.logic.pitch import search_links
from app.logic.writer import find_invented_claims
from app.models import Application, CompanyResearch, Job, MockSession, OutreachContact, Profile, now
from app.routes.jobs import get_job
from app.serialize import to_dict
from app.services.jobs import latest_score

router = APIRouter(prefix="/api", tags=["intelligence"])
RESEARCH_MAX_AGE = timedelta(days=30)

_market_cache: dict[int, tuple[float, dict]] = {}


def market_data(db: Session, profile: Profile) -> dict:
    """Skill demand across your target jobs (cached 5 minutes; it reads every job)."""
    hit = _market_cache.get(profile.user_id)
    if hit and time.monotonic() - hit[0] < 300:
        return hit[1]
    threshold = user_settings(profile)["min_score"]
    jobs = market.target_jobs(db.query(Job).filter(Job.user_id == profile.user_id, Job.ats_score.isnot(None)).all(), threshold)
    data = {"jobs": jobs, "demand": market.skill_demand(profile, jobs)}
    _market_cache[profile.user_id] = (time.monotonic(), data)
    return data


def research_for(db: Session, profile: Profile, job: Job) -> CompanyResearch | None:
    return db.query(CompanyResearch).filter_by(user_id=profile.user_id, company_key=company_key(job.company) or job.company.lower())\
        .order_by(CompanyResearch.id.desc()).first()


def contacts_for(db: Session, profile: Profile, job: Job) -> list[OutreachContact]:
    return db.query(OutreachContact).filter_by(user_id=profile.user_id, job_id=job.id).order_by(OutreachContact.id).all()


def contact_dict(c: OutreachContact) -> dict:
    return {**to_dict(c), "tier": outreach.tier(c.kind), "kind_label": outreach.KINDS.get(c.kind, (4, c.kind))[1]}


def full_analysis(db: Session, profile: Profile, job: Job) -> dict:
    settings = user_settings(profile)
    research = research_for(db, profile, job)
    contacts = contacts_for(db, profile, job)
    data = analyze_job(profile, job, latest_score(db, job), settings, {"shares": market_data(db, profile)["demand"]["shares"]},
                       research.data if research else None, [contact_dict(c) for c in contacts])
    app = db.query(Application).filter_by(user_id=profile.user_id, job_id=job.id).first()
    data["research"] = ({**research.data, "researched_at": research.created_at.isoformat(), "model": research.model} if research else None)
    data["ai_available"] = ai.available()
    data["contacts"] = [contact_dict(c) for c in contacts]
    data["outreach_plan"] = outreach.outreach_plan(app is not None, contacts)
    data["health"] = outreach.health(app, job, contacts, settings["min_score"])
    data["follow_ups"] = outreach.follow_ups(app, contacts, now())
    data["application"] = {"id": app.id, "status": app.status, "cv_version": app.cv_version} if app else None
    data["search_links"] = search_links(job.company, detect_city(job.location))
    return data


@router.get("/jobs/{job_id}/analysis")
def analysis(job_id: int, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    return full_analysis(db, profile, get_job(db, profile, job_id))


@router.post("/jobs/{job_id}/research")
def research(job_id: int, refresh: bool = False, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    """Company + interview-process research with AI web search (cached 30 days per company)."""
    job = get_job(db, profile, job_id)
    existing = research_for(db, profile, job)
    if existing and not refresh and now() - existing.created_at < RESEARCH_MAX_AGE:
        return {"cached": True, **existing.data}
    try:
        data, urls = ai.research_company(job.company, job.title, job.location, job.original_description)
    except ai.AIError as exc:
        raise HTTPException(400, str(exc)) from None
    row = CompanyResearch(user_id=profile.user_id, company_key=company_key(job.company) or job.company.lower(), company=job.company,
                          data=data, searched_urls=urls, model=app_config.ai_model)
    db.add(row)
    db.commit()
    return {"cached": False, **data}


# ------------------------------------------------------------------ interview mode


@router.get("/jobs/{job_id}/interview-package")
def interview_package(job_id: int, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    """Everything to prepare for this job's interview, in one place."""
    job = get_job(db, profile, job_id)
    a = full_analysis(db, profile, job)
    score = latest_score(db, job)
    prep = interview_prep(profile, job, score.matched_skills if score else [], score.missing_skills if score else [])
    by_category: dict[str, list] = {}
    for q in a["predicted_questions"]:
        by_category.setdefault(q["category"], []).append(q)
    research_data = a["research"] or {}
    return {
        "company": {"name": job.company, "type": a["company_type"], "facts": research_data.get("facts", []),
                    "summary": research_data.get("summary")},
        "role": {"title": job.title, "family": a["role_family"], "information": a["job_information"]},
        "strengths": a["readiness"]["why_shortlist"], "weaknesses": a["readiness"]["why_reject"],
        "stages": research_data.get("interview_rounds", []), "process_conclusion": research_data.get("process_conclusion"),
        "conflicts": research_data.get("conflicts", []),
        "questions": by_category, "dsa": a["dsa"], "topics": prep["technical"], "stories": prep["stories"], "gaps": prep["gaps"],
        "questions_to_ask": a["questions_to_ask"], "readiness": interview_readiness(a, prep),
        "answer_structures": ANSWER_STRUCTURES, "ai_available": a["ai_available"],
    }


def interview_readiness(a: dict, prep: dict) -> dict:
    """Readiness per area (estimate): CV evidence for skills, plus your mock-interview scores later."""
    areas = {}
    for group in ("must", "preferred"):
        for r in a["requirements"][group][:6]:
            areas[r["item"]] = {"strong": 85, "partial": 55, "missing": 20}[r["status"]]
    areas["DSA"] = {"Low–Medium": 70, "Medium": 55, "Medium–High": 45, "Very High": 30}[a["dsa"]["level"]]
    areas["Behavioral"] = 65
    if a["job_information"]["Experience required"] != "Not specified" or a["dsa"]["level"] != "Low–Medium":
        areas["System design"] = 50
    weakest = sorted(areas, key=areas.get)[:3]
    days = sum(5 if areas[w] < 40 else 3 if areas[w] < 60 else 1 for w in weakest)
    return {"areas": areas, "weakest": weakest, "days": days, "note": "Estimate from your CV evidence; improves with mock-interview scores."}


class MockStart(BaseModel):
    categories: list[str] | None = None


@router.post("/jobs/{job_id}/mock")
def mock_start(job_id: int, body: MockStart, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    job = get_job(db, profile, job_id)
    questions = full_analysis(db, profile, job)["predicted_questions"]
    if body.categories:
        questions = [q for q in questions if q["category"] in body.categories] or questions
    session = MockSession(user_id=profile.user_id, job_id=job.id, answers=[],
                          questions=[{k: q.get(k) for k in ("question", "category", "probability")} for q in questions[:10]])
    db.add(session)
    db.commit()
    return mock_dict(session)


def mock_dict(s: MockSession) -> dict:
    done = len(s.answers)
    graded = [a["grade"]["overall"] for a in s.answers if a.get("grade") and a["grade"].get("overall") is not None]
    return {"id": s.id, "job_id": s.job_id, "total": len(s.questions), "answered": done, "answers": s.answers,
            "next": s.questions[done] if done < len(s.questions) else None,
            "average": round(sum(graded) / len(graded)) if graded else None, "ai_available": ai.available()}


@router.get("/mock/{session_id}")
def mock_get(session_id: int, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    return mock_dict(get_session(db, profile, session_id))


def get_session(db: Session, profile: Profile, session_id: int) -> MockSession:
    s = db.query(MockSession).filter_by(id=session_id, user_id=profile.user_id).first()
    if s is None:
        raise HTTPException(404, "Mock interview not found.")
    return s


class MockAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=8000)
    self_score: int | None = Field(default=None, ge=0, le=100)   # used when AI is not configured


@router.post("/mock/{session_id}/answer")
def mock_answer(session_id: int, body: MockAnswer, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    s = get_session(db, profile, session_id)
    if len(s.answers) >= len(s.questions):
        raise HTTPException(409, "This mock interview is finished.")
    q = s.questions[len(s.answers)]
    job = db.get(Job, s.job_id)
    structure = ANSWER_STRUCTURES.get(q["category"], ANSWER_STRUCTURES["Technical"])
    if ai.available():
        cv = {"experience": profile.experience, "projects": profile.projects, "skills": [x["name"] for x in profile.skills],
              "education": profile.education, "years_experience": profile.years_experience}
        try:
            grade = ai.grade_answer(q["question"], q["category"], body.answer, cv,
                                    {"title": job.title, "company": job.company, "skills": [x["skill"] for x in job.parsed.get("skills", [])]})
            grade["by"] = "claude"
        except ai.AIError as exc:
            raise HTTPException(400, str(exc)) from None
    else:
        grade = {"by": "self", "overall": body.self_score, "scores": {}, "good": [], "missing": [], "improve": [],
                 "ideal_structure": structure, "invented_claims": [],
                 "note": "AI is not configured: compare your answer with the ideal structure and rate yourself."}
    s.answers = [*s.answers, {"question": q["question"], "category": q["category"], "answer": body.answer, "grade": grade}]
    db.commit()
    return mock_dict(s)


class DraftRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


@router.post("/jobs/{job_id}/answer-draft")
def answer_draft(job_id: int, body: DraftRequest, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    """AI sample answer for one predicted question, built only from your CV, checked for invented claims."""
    job = get_job(db, profile, job_id)
    q = next((q for q in full_analysis(db, profile, job)["predicted_questions"] if q["question"] == body.question), None)
    if q is None:
        raise HTTPException(404, "Question not found for this job.")
    cv = {"name": profile.name, "location": profile.location, "years_experience": profile.years_experience,
          "summary": profile.summary, "experience": profile.experience, "projects": profile.projects,
          "skills": [x["name"] for x in profile.skills], "education": profile.education, "visa_required": profile.visa_required}
    try:
        text = ai.draft_answer(q["question"], q["category"], q["guide"], cv,
                               {"title": job.title, "company": job.company, "skills": [x["skill"] for x in job.parsed.get("skills", [])]})
    except ai.AIError as exc:
        raise HTTPException(400, str(exc)) from None
    return {"draft": text, "warnings": find_invented_claims(text, profile, job),
            "note": "Draft from your CV only. Fill the [brackets] and say it in your own words; don't memorise it."}


# ------------------------------------------------------------------ contacts (you find them; the app manages them)


class ContactIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    role: str = Field(min_length=2, max_length=200)
    kind: str
    linkedin_url: str | None = None
    email: str | None = None
    source_url: str | None = None
    relevance: str | None = None
    confidence: str = "Medium"
    notes: str | None = None


@router.post("/jobs/{job_id}/contacts")
def add_contact(job_id: int, body: ContactIn, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    job = get_job(db, profile, job_id)
    if body.kind not in outreach.KINDS:
        raise HTTPException(422, f"kind must be one of {list(outreach.KINDS)}")
    if body.linkedin_url and "linkedin.com/" not in body.linkedin_url:
        raise HTTPException(422, "LinkedIn link must be a linkedin.com URL.")
    if len(contacts_for(db, profile, job)) >= outreach.MAX_CONTACTS_PER_JOB:
        raise HTTPException(409, f"Quality over quantity: max {outreach.MAX_CONTACTS_PER_JOB} people per job "
                                 "(1 recruiter, 1 hiring manager, 1 referral). Remove one first.")
    c = OutreachContact(user_id=profile.user_id, job_id=job.id, **body.model_dump())
    db.add(c)
    db.commit()
    return contact_dict(c)


class ContactUpdate(BaseModel):
    contacted: bool | None = None
    replied: bool | None = None
    followed_up: bool | None = None
    notes: str | None = None


@router.patch("/contacts/{contact_id}")
def update_contact(contact_id: int, body: ContactUpdate, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    c = db.query(OutreachContact).filter_by(id=contact_id, user_id=profile.user_id).first()
    if c is None:
        raise HTTPException(404, "Contact not found.")
    for field, column in (("contacted", "contacted_at"), ("replied", "replied_at"), ("followed_up", "followed_up_at")):
        value = getattr(body, field)
        if value is not None:
            setattr(c, column, now() if value else None)
    if body.notes is not None:
        c.notes = body.notes
    app = db.query(Application).filter_by(user_id=profile.user_id, job_id=c.job_id).first()
    if app:  # keep the application pipeline in step with your outreach
        if body.contacted and app.status == "APPLIED":
            set_status(app, "RECRUITER_CONTACTED")
        if body.replied and app.status in ("APPLIED", "RECRUITER_CONTACTED"):
            set_status(app, "RECRUITER_REPLIED")
        if body.contacted or body.replied or body.followed_up:
            app.last_contact_at = now()
            app.next_follow_up = None if body.replied else now() + timedelta(days=outreach.FOLLOW_UP_DAYS)
    db.commit()
    return contact_dict(c)


def set_status(app: Application, status: str) -> None:
    app.status = status
    app.history = [*app.history, {"status": status, "at": now().isoformat()}]


@router.delete("/contacts/{contact_id}")
def delete_contact(contact_id: int, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    c = db.query(OutreachContact).filter_by(id=contact_id, user_id=profile.user_id).first()
    if c is None:
        raise HTTPException(404, "Contact not found.")
    db.delete(c)
    db.commit()
    return {"deleted": True}


@router.get("/contacts/{contact_id}/message")
def contact_message(contact_id: int, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    c = db.query(OutreachContact).filter_by(id=contact_id, user_id=profile.user_id).first()
    if c is None:
        raise HTTPException(404, "Contact not found.")
    job = db.get(Job, c.job_id)
    score = latest_score(db, job)
    applied = db.query(Application).filter_by(user_id=profile.user_id, job_id=job.id).first() is not None
    return outreach.contact_message(profile, job, score.matched_skills if score else [], c, applied)


# ------------------------------------------------------------------ strategy (January 2027 goal)


@router.get("/strategy")
def strategy(profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    settings = user_settings(profile)
    threshold = settings["min_score"]
    m = market_data(db, profile)
    jobs = db.query(Job.status, Job.ats_score).filter(Job.user_id == profile.user_id).all()
    apps = db.query(Application).filter_by(user_id=profile.user_id).all()
    contacts = db.query(OutreachContact).filter_by(user_id=profile.user_id).all()
    f = market.funnel(apps, contacts, sum(1 for j in jobs if j.ats_score is not None),
                      sum(1 for j in jobs if j.status in ("QUALIFIED", "APPLIED")))
    dsa_info = market.dsa_market([j for j in m["jobs"] if (j.ats_score or 0) >= threshold - 10] or m["jobs"])
    learning = market.rejection_learning(apps)
    demand = {k: v for k, v in m["demand"].items() if k != "shares"}
    return {
        "goal": market.goal(settings), "funnel": f, "rejections": learning,
        "weekly": market.weekly_strategy(f, learning, m["demand"], dsa_info, float(settings.get("study_hours_per_week") or 15)),
        "skills": demand, "dsa": dsa_info, "roles": market.role_ranking(m["jobs"]),
        "follow_ups_due": follow_ups_due(db, profile, apps),
    }


def follow_ups_due(db: Session, profile: Profile, apps: list[Application]) -> list[dict]:
    out = []
    for app in apps:
        if app.status in ("REJECTED", "WITHDRAWN", "OFFER"):
            continue
        job = db.get(Job, app.job_id)
        for item in outreach.follow_ups(app, [c for c in db.query(OutreachContact).filter_by(job_id=job.id)], now()):
            if item.get("overdue"):
                out.append({**item, "job_id": job.id, "job": f"{job.title} · {job.company}"})
    return out[:10]
