"""ATS match score (0-100) between the candidate and one job.

Eight parts, each 0-100, combined with weights you can change in Settings.
Every rule writes a plain-English reason or concern, so the score is explainable.
No AI is used here, so a job description can never change its own score.
"""
import re

from app.logic.dedup import title_words
from app.logic.skills import related_skill, with_implied

DEFAULT_WEIGHTS = {
    "skills": 30, "experience": 20, "role": 15, "industrial": 10,
    "location": 10, "language": 5, "sponsorship": 5, "seniority": 5,
}
FULL_TIME = (None, "Full-time")
GOOD_GERMAN = {"B2", "C1", "C2", "NATIVE"}


def score_job(profile, job, weights: dict | None = None, threshold: float = 80, search_roles: list[str] = ()) -> dict:
    """profile: needs .skills, .years_experience, .target_roles, .domain_experience, .languages, .visa_required
    search_roles: the job keywords from Settings (count like target roles)
    job: needs .title, .parsed, .country, .location, .remote_type, .employment_type, .visa_status,
         .language_requirement, .experience_required, .seniority, .risk_flags
    """
    reasons, concerns = [], []
    my_skills = with_implied({s["name"] for s in profile.skills})
    german_level = next((str(l.get("level", "")).upper() for l in profile.languages if l.get("language", "").lower() == "german"), "")

    # 1. Skills ---------------------------------------------------------------------------
    job_skills = job.parsed.get("skills", [])
    matched, missing = [], []
    earned = possible = 0.0
    for s in job_skills:
        weight = s["importance"] * (1 if s["required"] else 0.5)
        possible += weight
        if s["skill"] in my_skills:
            earned += weight
            matched.append(s["skill"])
        else:
            missing.append(s["skill"])
            similar = related_skill(s["skill"], my_skills)
            if similar:
                earned += weight * 0.5
                concerns.append(f"Job asks for {s['skill']}; you have the similar {similar} (half credit).")
    if possible:
        # A JD that mentions only 1-2 skills we know is probably not a software job:
        # "1 of 1 matched" must not count as a perfect skills match.
        confidence = min(1.0, 0.4 + 0.15 * len(job_skills))
        skills = 100 * earned / possible * confidence
        if len(job_skills) < 3:
            concerns.append(f"The job description mentions only {len(job_skills)} technical skill(s) from your field.")
        if matched:
            reasons.append(f"Matches {len(matched)} of {len(job_skills)} skills: {', '.join(matched[:8])}.")
    else:
        skills = 50
        concerns.append("No known technical skills found in the job description (neutral 50).")

    # 2. Experience -----------------------------------------------------------------------
    need, have = job.experience_required, profile.years_experience
    if need is None:
        experience = 85
        reasons.append("No years-of-experience requirement found.")
    elif have is None:
        experience = 50
        concerns.append("Your years of experience are not set in your profile.")
    elif have >= need:
        experience = 100
        reasons.append(f"Experience {need:g}+ years required, you have {have:g}.")
    else:
        experience = max(0, 100 - 25 * (need - have))
        concerns.append(f"Job requests {need:g}+ years experience. You have approximately {have:g} years.")

    # 3. Role (job title vs your target roles) -----------------------------------------------
    # Only meaningful words count: "Fluid Systems Engineer" must NOT match "Software Engineer" just because of "engineer".
    generic = {"engineer", "developer", "specialist", "consultant"}
    title = title_words(job.title)
    best, best_role = 0.0, ""
    for role in [*profile.target_roles, *search_roles]:  # your search keywords count as target roles too
        words = title_words(role) - generic
        if words and len(words & title) / len(words) > best:
            best, best_role = len(words & title) / len(words), role
    role = 100 * best
    if best == 0:
        concerns.append(f"'{job.title}' does not match any of your target roles.")
    # Not one of your roles and not an engineering title at all -> half credit.
    if best < 0.66 and not title & {"engineer", "architect", "consultant", "specialist"} \
            and not any("ingenieur" in w or "entwickler" in w for w in title):
        role *= 0.5
        concerns.append(f"'{job.title}' does not look like an engineering role.")
    if best >= 0.66:
        reasons.append(f"Title matches your target role '{best_role}'.")

    # 4. Industrial domain ----------------------------------------------------------------
    signals = job.parsed.get("industrial_signals", [])
    industrial_background = any(re.search(r"industr|scada|plc|opc", d, re.I) for d in profile.domain_experience)
    if not signals:
        industrial = 70
        reasons.append("General software role (no industrial requirement).")
    elif industrial_background:
        industrial = 100 if len(set(signals)) >= 3 else 85
        reasons.append(f"Industrial match: {', '.join(sorted(set(signals))[:5])}.")
    else:
        industrial = 50

    # 5. Location -------------------------------------------------------------------------
    if job.country == "Germany":
        location = 100
        reasons.append(f"In Germany ({job.location or 'Germany'}).")
    elif job.country is None:
        location = 70 if job.remote_type == "remote" else 50
        concerns.append("Job location is unclear.")
    else:
        location = 0
        concerns.append(f"Job is in {job.country}, not Germany.")

    # 6. Language -------------------------------------------------------------------------
    lang = job.language_requirement
    if lang == "english":
        language = 100
        reasons.append("English-speaking role.")
    elif lang == "german_plus":
        language = 100 if german_level in GOOD_GERMAN else 80
        concerns.append("German is listed as a plus.")
    elif lang == "german_required":
        language = 90 if german_level in GOOD_GERMAN else 20
        if language == 20:
            concerns.append("German language is required.")
    else:  # german_jd
        language = 85 if german_level in GOOD_GERMAN else 35
        if language == 35:
            concerns.append("Job description is in German; German is probably expected.")

    # 7. Sponsorship ----------------------------------------------------------------------
    evidence = job.parsed.get("visa_evidence", [])
    if profile.visa_required is False:
        sponsorship = 100
    else:
        if profile.visa_required is None:
            concerns.append("Set 'visa required' in your profile; assuming you need sponsorship.")
        if job.visa_status == "confirmed":
            sponsorship = 100
            reasons.append(f"Sponsorship/relocation mentioned: \"{evidence[0] if evidence else ''}\".")
        elif job.visa_status == "unlikely":
            sponsorship = 0
            concerns.append(f"Requires existing work permit: \"{evidence[0] if evidence else ''}\".")
        else:
            sponsorship = 60
            concerns.append("Sponsorship not explicitly confirmed.")

    # 8. Seniority ------------------------------------------------------------------------
    seniority = {"junior": 90, "mid": 100, "senior": 55, "lead": 25, "principal": 20, "head": 10,
                 "intern": 20, "working_student": 20}.get(job.seniority or "mid", 80)
    if seniority < 60:
        concerns.append(f"Seniority is '{job.seniority}'.")

    # Combine -------------------------------------------------------------------------------
    parts = {"skills": skills, "experience": experience, "role": role, "industrial": industrial,
             "location": location, "language": language, "sponsorship": sponsorship, "seniority": seniority}
    weights = {**DEFAULT_WEIGHTS, **(weights or {})}
    total_weight = sum(weights.values()) or 1
    overall = round(sum(parts[k] * weights[k] for k in parts) / total_weight)
    parts = {k: round(v) for k, v in parts.items()}

    if lang in ("german_required", "german_jd") and german_level not in GOOD_GERMAN:
        missing.append("German")
    if job.employment_type not in FULL_TIME:
        concerns.append(f"Employment type is '{job.employment_type}', not full-time.")

    # Recommendation ----------------------------------------------------------------------
    # Lead / principal / head roles expect many more years than you have: never more than "stretch".
    blocked = job.employment_type not in FULL_TIME or language <= 35 or job.seniority in ("lead", "principal", "head")
    if job.risk_flags:
        recommendation = "RISK"
    elif location == 0 or (job.visa_status == "unlikely" and profile.visa_required is not False):
        recommendation = "SKIP"
    elif overall >= threshold and not blocked:
        recommendation = "APPLY"
    elif overall >= threshold - 10:
        recommendation = "REVIEW"
    else:
        recommendation = "SKIP"

    return {"overall": overall, "parts": parts, "matched_skills": matched, "missing_skills": missing,
            "reasons": reasons, "concerns": concerns, "recommendation": recommendation, "threshold": threshold}


def match_label(score: float | None, threshold: float = 80, status: str | None = None) -> dict:
    """Plain-English verdict shown next to every score.
    status REVIEW = high score but held back (internship, working student, part-time, lead role, German needed)."""
    if score is None:
        return {"level": "unknown", "text": "Not scored yet"}
    if score >= threshold and status != "REVIEW":
        return {"level": "good", "text": "Good match: apply"}
    if score >= threshold - 10:
        return {"level": "stretch", "text": "Stretch: apply only if you really like it"}
    return {"level": "low", "text": "Not a match: skip"}
