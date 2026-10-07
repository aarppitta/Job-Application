"""Intelligence across ALL your target jobs, plus the January 2027 goal and the weekly strategy.

- skill demand: how often each skill appears in the jobs you actually target -> what to learn first
- DSA: how much algorithm prep your target companies need -> the minimum curriculum
- roles: which role families fit your CV best
- funnel: applications -> interviews -> offers, and what the results say about your strategy
Everything is computed from your own data. Percentages are counts, not predictions.
"""
from collections import Counter
from datetime import date, datetime, timedelta

from app.defaults import ROLE_FAMILIES
from app.logic.learning import hindi_videos
from app.logic.analysis import (CANNOT_FAKE, COMPANY_TYPE_LABEL, DSA_LEVELS, company_type, my_skill_status, roi, role_family)

# Pipeline order: reaching a later stage means you passed the earlier ones.
STAGES = ["APPLIED", "RECRUITER_CONTACTED", "RECRUITER_REPLIED", "HR_SCREEN", "TECHNICAL", "TAKE_HOME", "HIRING_MANAGER", "FINAL", "OFFER"]
REJECTION_STAGES = ["CV_SCREENING", "HR", "TECHNICAL", "TAKE_HOME", "HIRING_MANAGER", "FINAL", "UNKNOWN"]
REJECTED_AT = {"HR": "HR_SCREEN", "TECHNICAL": "TECHNICAL", "TAKE_HOME": "TAKE_HOME", "HIRING_MANAGER": "HIRING_MANAGER", "FINAL": "FINAL"}


def target_jobs(jobs: list, threshold: float) -> list:
    """The jobs that represent YOUR market: genuine, in Germany, and at least loosely matching your CV."""
    return [j for j in jobs if j.status != "RISK" and j.country == "Germany" and (j.ats_score or 0) >= threshold - 25]


def skill_demand(profile, jobs: list) -> dict:
    n = len(jobs) or 1
    counts = Counter(s["skill"] for j in jobs for s in j.parsed.get("skills", []))
    required = Counter(s["skill"] for j in jobs for s in j.parsed.get("skills", []) if s["required"])
    shares = {k: v / n for k, v in counts.items()}
    rows = []
    for skill, count in counts.most_common():
        status, why = my_skill_status(skill, profile)
        share = count / n
        info = roi(skill, required[skill] / count, share)
        rows.append({"skill": skill, "share": round(100 * share), "jobs": count, "status": status, "why": why, **info,
                     "learn_hindi": hindi_videos(skill)})
    have = [r for r in rows if r["status"] == "strong" and r["share"] >= 10]
    improve = sorted([r for r in rows if r["status"] != "strong" and r["share"] >= 10 and r["skill"] not in CANNOT_FAKE], key=lambda r: -r["roi"])
    needs_experience = [r for r in rows if r["status"] != "strong" and r["share"] >= 10 and r["skill"] in CANNOT_FAKE]
    skip = [r for r in rows if r["status"] == "missing" and r["share"] < 8][:15]
    return {"jobs_analyzed": len(jobs), "shares": shares, "skills": rows[:30], "have": have[:12], "improve": improve[:10],
            "needs_experience": needs_experience, "skip": skip}


def dsa_market(jobs: list) -> dict:
    kinds = Counter(company_type(j) for j in jobs)
    n = sum(kinds.values()) or 1
    level_of = {"big_tech": "Very High", "scale_up": "Medium–High", "industrial": "Low–Medium", "startup": "Low–Medium", "general": "Medium"}
    by_level = Counter()
    for kind, count in kinds.items():
        by_level[level_of[kind]] += count
    # minimum curriculum = the level that covers at least 70% of your target jobs
    covered, chosen = 0, "Low–Medium"
    for level in ["Low–Medium", "Medium", "Medium–High", "Very High"]:
        covered += by_level[level]
        chosen = level
        if covered / n >= 0.7:
            break
    return {
        "by_company_type": [{"type": COMPANY_TYPE_LABEL[k], "level": level_of[k], "share": round(100 * v / n), "jobs": v} for k, v in kinds.most_common()],
        "curriculum_level": chosen, "curriculum": DSA_LEVELS[chosen], "learn_hindi": hindi_videos("DSA"),
        "skip": ([] if by_level["Very High"] / n > 0.15 else ["Dynamic programming beyond basics", "Advanced graph algorithms", "Competitive programming"]),
    }


def role_ranking(jobs: list) -> list[dict]:
    groups: dict[str, list] = {k: [] for k in ROLE_FAMILIES}
    for j in jobs:
        groups[role_family(j.title, j.parsed.get("industrial_signals"))].append(j.ats_score or 0)
    ranking = []
    for key, scores in groups.items():
        top = sorted(scores, reverse=True)[:10]
        avg = round(sum(top) / len(top)) if top else 0
        ranking.append({"family": ROLE_FAMILIES[key]["label"], "primary": ROLE_FAMILIES[key]["primary"], "jobs": len(scores),
                        "good": sum(s >= 80 for s in scores), "avg_top10": avg,
                        "advice": "Focus" if avg >= 80 else "Also apply" if avg >= 72 else "Low fit right now"})
    ranking.sort(key=lambda r: (-r["avg_top10"], -r["good"]))
    return ranking


# ------------------------------------------------------------------ funnel + goal


def reached(app) -> set[str]:
    stages = {h["status"] for h in app.history or []} | {app.status}
    if app.status == "REJECTED" and app.rejection_stage in REJECTED_AT:
        idx = STAGES.index(REJECTED_AT[app.rejection_stage])
        stages |= set(STAGES[: idx + 1])
    top = max((STAGES.index(s) for s in stages if s in STAGES), default=0)
    return set(STAGES[: top + 1])


def funnel(apps: list, contacts: list, jobs_scored: int, shortlisted: int) -> dict:
    stage_sets = [reached(a) for a in apps]
    count = lambda stage: sum(stage in s for s in stage_sets)
    interviews = count("HR_SCREEN")
    technical = count("TECHNICAL")
    final = sum(bool({"HIRING_MANAGER", "FINAL"} & s) or "OFFER" in s for s in stage_sets)
    offers = count("OFFER")
    replies = sum(bool({"RECRUITER_REPLIED", "HR_SCREEN"} & s) for s in stage_sets) + sum(1 for c in contacts if c.replied_at)
    pct = lambda a, b: round(100 * a / b) if b else None
    return {
        "jobs_analyzed": jobs_scored, "jobs_shortlisted": shortlisted, "applications": len(apps),
        "recruiters_contacted": len({c.job_id for c in contacts if c.contacted_at}), "hr_responses": replies,
        "interviews": interviews, "technical_rounds": technical, "final_rounds": final, "offers": offers,
        "rejected": sum(a.status == "REJECTED" for a in apps),
        "conversion": {"application_to_interview": pct(interviews, len(apps)), "interview_to_final": pct(final, interviews),
                       "final_to_offer": pct(offers, final)},
    }


def rejection_learning(apps: list) -> dict:
    stages = Counter(a.rejection_stage or "UNKNOWN" for a in apps if a.status == "REJECTED")
    lessons = []
    if stages["CV_SCREENING"] >= 3:
        lessons.append(f"{stages['CV_SCREENING']} rejections at CV screening → improve CV targeting: use the recommended CV version, "
                       "add legitimate keywords, apply to higher-match jobs, contact a recruiter for each application.")
    if stages["TECHNICAL"] + stages["TAKE_HOME"] >= 2:
        lessons.append(f"{stages['TECHNICAL'] + stages['TAKE_HOME']} rejections in technical rounds → more DSA and system design practice, "
                       "and mock interviews on your weakest JD skills.")
    if stages["HR"] >= 2:
        lessons.append(f"{stages['HR']} rejections after the HR call → practice 'Tell me about yourself', 'Why Germany', visa and salary answers.")
    if stages["HIRING_MANAGER"] + stages["FINAL"] >= 2:
        lessons.append("Rejections in late rounds → prepare project deep dives and questions about the team; ask for feedback.")
    return {"by_stage": dict(stages), "lessons": lessons}


def weekly_strategy(f: dict, learning: dict, demand: dict, dsa_info: dict, hours: float) -> dict:
    """This week's targets, adjusted to your real results."""
    apps, interviews = f["applications"], f["interviews"]
    stages = learning["by_stage"]
    diagnosis, focus = [], "volume"
    targets = {"applications": "10–15 high-quality jobs", "recruiter_outreach": "5–10 (1 per application)",
               "dsa_problems": max(5, dsa_info["curriculum"]["problems"] // 8), "interview_practice_hours": 2, "german_hours": 0}
    if f["offers"]:
        focus = "offer"
        diagnosis.append("You have an offer: focus on visa (EU Blue Card), relocation and salary negotiation.")
        targets.update(applications="3–5 (keep options open)", recruiter_outreach="as needed", dsa_problems=0, interview_practice_hours=1)
    elif apps >= 10 and interviews == 0:
        focus = "cv"
        diagnosis.append(f"{apps} applications but no interview yet → the problem is getting seen: tighter targeting "
                         "(only ≥ 80 matches), CV version per role, and a recruiter message for every application.")
        targets.update(applications="8–12 (higher match only)", recruiter_outreach="8–12")
    elif stages.get("TECHNICAL", 0) + stages.get("TAKE_HOME", 0) >= 2:
        focus = "technical"
        diagnosis.append("You get interviews but technical rounds fail → more technical preparation this week.")
        targets.update(dsa_problems=targets["dsa_problems"] * 2, interview_practice_hours=4, applications="6–10")
    elif stages.get("HR", 0) >= 2:
        focus = "behavioral"
        diagnosis.append("You pass CV screening but not the HR call → practice behavioral answers and your Germany/visa story.")
        targets.update(interview_practice_hours=4)
    elif apps < 5:
        diagnosis.append("Few applications so far → volume first: apply to every 🔥/🟢 match this week.")
    else:
        diagnosis.append("Steady progress: keep the volume and contact a recruiter for every application.")

    # Split study hours over the highest-ROI skills from your market
    study = [s for s in demand["improve"][:3]]
    tech_hours = max(0.0, hours - targets["interview_practice_hours"] - 3)  # ~3 h for DSA
    plan = [{"skill": s["skill"], "hours": round(tech_hours / len(study), 1), "why": f"In {s['share']}% of your target jobs"} for s in study] if study else []
    plan.append({"skill": f"DSA ({dsa_info['curriculum_level']})", "hours": 3, "why": f"{targets['dsa_problems']} problems"})
    plan.append({"skill": "Interview practice (mock interviews)", "hours": targets["interview_practice_hours"], "why": "Answer out loud, get graded"})
    return {"focus": focus, "diagnosis": diagnosis, "targets": targets, "study_plan": plan}


def goal(settings: dict) -> dict:
    try:
        end = date.fromisoformat(settings.get("goal_date") or "2027-01-31")
    except ValueError:
        end = date(2027, 1, 31)
    today = datetime.now().date()
    return {"goal_date": end.isoformat(), "days_remaining": max(0, (end - today).days), "weeks_remaining": max(0, (end - today).days // 7)}


def follow_up_due(sent_at: datetime | None, days: int = 7) -> datetime | None:
    return sent_at + timedelta(days=days) if sent_at else None
