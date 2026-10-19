"""Job intelligence for one JD: everything the job page needs to answer "should I apply, and what next?".

Rule-based (no AI), so a JD can never change its own verdict and nothing is invented:
- job facts come from the JD text; what is not there is "Not specified"
- your side comes only from the profile (= your CV); "strong" needs evidence in a CV bullet or project
- company-specific facts (interview process, reported questions) come only from logic/ai.py research, with sources
Every estimate is labelled as an estimate.
"""
import re

from app.defaults import ROLE_FAMILIES
from app.logic.cv import degree_text
from app.logic.interview import TOPICS, answer_guide, project_questions
from app.logic.jd_parser import simplify
from app.logic.learning import hindi_videos
from app.logic.skills import find_skills, related_skill, with_implied

# skill -> (days to reach working knowledge, difficulty 1-3, interview weight 1-3). Rough guides, shown as estimates.
LEARNING = {
    "PostgreSQL": (5, 1, 3), "SQL": (5, 1, 3), "Docker": (5, 1, 2), "Kubernetes": (14, 3, 2), "AWS": (10, 2, 2),
    "Azure": (10, 2, 2), "GCP": (10, 2, 1), "Terraform": (7, 2, 1), "CI/CD": (4, 1, 2), "Linux": (5, 1, 1), "Git": (2, 1, 1),
    "Unit Testing": (4, 1, 3), "Microservices": (7, 2, 2), "Kafka": (7, 2, 2), "RabbitMQ": (5, 2, 1), "Redis": (3, 1, 2),
    "GraphQL": (4, 1, 1), "Go": (21, 3, 2), "Java": (30, 3, 3), "C#": (30, 3, 3), "C++": (45, 3, 3), ".NET": (30, 3, 2),
    "TypeScript": (5, 1, 2), "JavaScript": (7, 1, 2), "React": (10, 2, 2), "Vue.js": (7, 2, 1), "Node.js": (7, 2, 2),
    "FastAPI": (5, 1, 3), "Django": (7, 2, 2), "Flask": (3, 1, 1), "MQTT": (3, 1, 2), "OPC UA": (7, 2, 2), "PROFINET": (10, 3, 1),
    "Siemens S7 / TIA": (21, 3, 2), "InfluxDB": (3, 1, 1), "Node-RED": (3, 1, 1), "MongoDB": (4, 1, 1), "OAuth": (3, 1, 2),
    "Machine Learning": (60, 3, 2), "HMI": (7, 2, 1), "MES": (10, 2, 2), "Industrial Automation": (14, 2, 1), "Industry 4.0": (5, 1, 1),
    "Agile": (2, 1, 1), "HTML": (2, 1, 1), "CSS": (3, 1, 1), "REST APIs": (3, 1, 3), "Microsoft SQL": (5, 1, 2),
}
DEFAULT_LEARNING = (10, 2, 1)
CANNOT_FAKE = {"Java", "C#", "C++", ".NET", "Go", "Machine Learning", "Siemens S7 / TIA"}  # need real production experience
CLOUD_DEVOPS = {"AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "CI/CD", "Linux"}

SOFT_SKILLS = {
    "Communication": r"communicat", "Teamwork": r"team ?player|teamwork|collaborat", "Leadership / mentoring": r"lead(?:ing|ership)? (?:a |the )?team|mentor",
    "Problem solving": r"problem[- ]solving|analytical", "Ownership": r"ownership|take responsibility|end[- ]to[- ]end",
    "Agile": r"agile|scrum|kanban", "Stakeholders": r"stakeholder", "Self-driven": r"self[- ](?:driven|motivated|starter)|proactive",
}
DOMAINS = {
    "Industrial automation / manufacturing": r"industrial|manufactur|factory|automation|scada|\bplc|\bmes\b|production line",
    "IoT / IIoT": r"\biot\b|iiot|connected devices|edge computing",
    "Pharma / life sciences": r"pharma|life science|\bgmp\b|gxp|medical device",
    "FinTech / banking": r"fintech|banking|payments?|financial services|trading|brokerage|insurance",
    "E-commerce": r"e-?commerce|marketplace|online shop|retail",
    "SaaS / B2B software": r"\bsaas\b|b2b software|platform for (?:businesses|teams)",
    "Cloud / infrastructure": r"cloud[- ]native|infrastructure|platform engineering|devops",
    "Cybersecurity": r"cyber ?security|security operations|threat",
    "Energy / climate": r"energy|solar|battery|climate|grid|heat pump",
    "Mobility / automotive": r"automotive|mobility|vehicle|autonomous driving",
    "Aerospace / defence": r"aerospace|defen[cs]e|aircraft|satellite|rocket",
    "Healthcare": r"health ?care|patient|clinic|hospital",
    "Logistics": r"logistics|supply chain|freight|warehouse",
}
MY_DOMAINS = {"Industrial automation / manufacturing": "strong", "Pharma / life sciences": "strong", "IoT / IIoT": "partial",
              "SaaS / B2B software": "partial", "E-commerce": "partial"}

BIG_TECH = {"google", "amazon", "aws", "microsoft", "meta", "apple", "netflix", "uber", "booking", "spotify", "bytedance",
            "tiktok", "stripe", "datadog", "salesforce", "oracle", "airbnb", "nvidia", "linkedin"}
SCALE_UPS = {"celonis", "n26", "trade republic", "traderepublic", "helsing", "getyourguide", "contentful", "raisin", "sumup",
             "hellofresh", "flix", "staffbase", "parloa", "delivery hero", "deliveryhero", "zalando", "personio", "scout24",
             "autoscout24", "doctolib", "wolt", "freenow", "free now", "qonto", "moss", "upvest", "n8n", "deepl", "black forest labs",
             "enpal", "adyen", "solaris", "trivago", "babbel", "isar aerospace", "mobileye", "commercetools", "tier", "gorillas", "flink"}
INDUSTRIAL_COMPANIES = {"bosch", "continental", "siemens", "kuka", "festo", "beckhoff", "sick", "trumpf", "wandelbots", "magazino",
                        "sereact", "konux", "tulip", "envelio", "kiwigrid", "1komma5", "abb", "schneider", "wago", "phoenix contact",
                        "pilz", "ifm", "harting", "zeiss", "infineon", "brainlab", "stark"}

DSA_LEVELS = {
    "Low–Medium": {"required": ["Arrays and lists", "Strings", "Hash maps / dictionaries", "Basic Big-O (time and space)",
                                "Sorting and searching basics", "Practical coding and debugging"],
                   "optional": ["Stacks and queues", "Two pointers"], "problems": 15},
    "Medium": {"required": ["Arrays and strings", "Hash maps / sets", "Stacks and queues", "Two pointers and sliding window",
                            "Binary search", "Recursion", "Trees (traversal, BFS/DFS)", "Big-O analysis"],
               "optional": ["Graphs (BFS/DFS)", "Heaps / priority queue", "Intervals"], "problems": 40},
    "Medium–High": {"required": ["Arrays, strings, hash maps", "Stacks, queues, two pointers, sliding window", "Binary search",
                                 "Trees and graphs (BFS/DFS)", "Heaps / priority queue", "Intervals", "Big-O analysis"],
                    "optional": ["Dynamic programming basics", "Tries", "Union-find"], "problems": 75},
    "Very High": {"required": ["All Medium–High topics", "Dynamic programming", "Advanced graphs (shortest path, topological sort)",
                               "Tries, union-find", "Backtracking"],
                  "optional": ["Segment trees", "Bit manipulation"], "problems": 150},
}
PROBABILITY_ORDER = {"Very High": 0, "High": 1, "Medium": 2, "Low": 3}
LEVELS = ["Low", "Medium", "High", "Very High"]


# ------------------------------------------------------------------ helpers


def jd_text(job) -> str:
    return job.parsed.get("text") or job.original_description or ""


def cv_bullets(profile) -> list[tuple[str, str]]:
    """(where, bullet) for every CV bullet."""
    return [(p["name"], b) for p in profile.projects for b in p.get("bullets", [])] + \
           [(f"{e['role']} at {e['company']}", b) for e in profile.experience or [] for b in e.get("bullets", [])]


def skill_evidence(profile) -> set[str]:
    """Skills your CV PROVES (named in a bullet or a project's tech list), not only listed."""
    found = set()
    for _, bullet in cv_bullets(profile):
        found.update(find_skills(bullet))
    for p in profile.projects:
        found.update(p.get("skills", []))
        found.update(find_skills(p.get("tech", "")))
    return with_implied(found)


def my_skill_status(skill: str, profile) -> tuple[str, str]:
    """('strong' | 'partial' | 'missing', explanation)."""
    mine = with_implied({s["name"] for s in profile.skills})
    if skill in mine:
        if skill in skill_evidence(profile):
            return "strong", "On your CV with project evidence"
        return "partial", "Listed in your skills, but no CV project shows it yet"
    other = related_skill(skill, mine)
    if other:
        return "partial", f"Related: you know {other}"
    return "missing", "Not on your CV"


def german_level(profile) -> str:
    return next((str(l.get("level", "")).upper() for l in profile.languages or [] if l.get("language", "").lower() == "german"), "")


def level_down(level: str, steps: int = 1) -> str:
    return LEVELS[max(0, LEVELS.index(level) - steps)]


def company_type(job) -> str:
    name = simplify(job.company)
    if any(b == name or name.startswith(b + " ") for b in BIG_TECH):
        return "big_tech"
    if any(s in name for s in SCALE_UPS):
        return "scale_up"
    if any(c in name for c in INDUSTRIAL_COMPANIES) or is_industrial(job):
        return "industrial"
    if job.source in ("berlinstartupjobs", "munichstartup", "startupcityhamburg", "personio", "ashby"):
        return "startup"
    return "general"


COMPANY_TYPE_LABEL = {"big_tech": "Big Tech", "scale_up": "Scale-up / well-funded tech company", "industrial": "Industrial / engineering company",
                      "startup": "Startup / small company", "general": "Mid-size or unknown company"}


OT_SIGNALS = re.compile(r"scada|plc|opc|modbus|\bmes\b|iiot|industrial|manufactur|factory|production|\bhmi\b|pharma|gmp|process control")


def ot_signals(signals: list | None) -> int:
    """How many of the JD's industrial signals are real OT/factory words (not just 'energy' or 'automotive')."""
    return sum(bool(OT_SIGNALS.search(s)) for s in signals or [])


def is_industrial(job) -> bool:
    return ot_signals(job.parsed.get("industrial_signals")) >= 2


def role_family(title: str, industrial_signals: list | None = None) -> str:
    t = f" {simplify(title)} "
    if any(w in t for w in ROLE_FAMILIES["iiot"]["words"]):
        return "iiot"
    title_industrial = any(w in t for w in ROLE_FAMILIES["industrial"]["words"] if w != "automation")
    if title_industrial or ot_signals(industrial_signals) >= 3 or ("automation" in t and ot_signals(industrial_signals) >= 2):
        return "industrial"
    if any(w in t for w in ROLE_FAMILIES["fullstack"]["words"]):
        return "fullstack"
    if any(w in t for w in ROLE_FAMILIES["backend"]["words"]):
        return "backend"
    return "general"


# ------------------------------------------------------------------ 1. JD facts


def job_information(job) -> dict:
    text = simplify(jd_text(job))
    salary = job.parsed.get("salary") or {}
    lang = job.language_requirement
    evidence = job.parsed.get("visa_evidence", [])
    relocation = re.search(r"relocation (?:assistance|support|package|budget|bonus)|help (?:you )?relocat|relocate to germany", text)
    return {
        "Company": job.company,
        "Job title": job.title,
        "Location": job.location or "Not specified",
        "Work mode": {"remote": "Remote", "hybrid": "Hybrid", "onsite": "On-site"}.get(job.remote_type, "Not specified"),
        "Employment type": job.employment_type or "Not specified",
        "Experience required": f"{job.experience_required:g}+ years" if job.experience_required else "Not specified",
        "Salary": f"€{salary['min']:,} – €{salary['max']:,}" if salary.get("min") else "Not specified",
        "Visa sponsorship": ("Mentioned: " + "; ".join(evidence)) if job.visa_status == "confirmed"
        else ("Probably not: " + "; ".join(evidence)) if job.visa_status == "unlikely" else "Not specified",
        "Relocation support": f"Mentioned: “{relocation.group(0)}”" if relocation else "Not specified",
        "German requirement": {"german_required": "Required: " + "; ".join(job.parsed.get("language_evidence", [])),
                               "german_plus": "A plus, not required", "german_jd": "JD is written in German (German likely needed)"}
        .get(lang, "Not specified"),
        "English requirement": "Yes (mentioned in the JD)" if re.search(r"\benglish\b", text) else "Not specified",
    }


# ------------------------------------------------------------------ 2+3. requirements vs your CV


def requirements(profile, job) -> dict:
    text = simplify(jd_text(job))
    groups = {"must": [], "preferred": [], "nice": []}
    for s in job.parsed.get("skills", []):
        group = "nice" if not s["required"] else "must" if s["importance"] >= 0.8 else "preferred"
        status, why = my_skill_status(s["skill"], profile)
        groups[group].append({"item": s["skill"], "status": status, "why": why})

    soft = []
    mine = " ".join([*profile.domain_experience, *(b for _, b in cv_bullets(profile))]).lower()
    for label, pattern in SOFT_SKILLS.items():
        if re.search(pattern, text):
            proven = (label == "Leadership / mentoring" and re.search(r"lead|mentor|junior", mine)) or \
                     (label == "Agile" and "agile" in mine) or (label == "Ownership" and "end-to-end" in mine)
            soft.append({"item": label, "status": "strong" if proven else "not_relevant",
                         "why": "Shown on your CV" if proven else "Can't be proven on paper: show it with a story in the interview"})

    domains = []
    for label, pattern in DOMAINS.items():
        if re.search(pattern, text):
            status = MY_DOMAINS.get(label, "missing")
            domains.append({"item": label, "status": status,
                            "why": {"strong": "Your industrial / pharma work", "partial": "Related experience (production web apps / machine data)"}
                            .get(status, "New domain for you: read up on it, not a blocker for most roles")})

    education = []
    if re.search(r"ph\.?d|doctorate", text):
        education.append({"item": "PhD", "status": "missing", "why": "You have an MSc"})
    elif re.search(r"bachelor|master|degree|diploma|b\.?sc|m\.?sc|studium|university|hochschul", text):
        education.append({"item": "Degree in Computer Science or related", "status": "strong",
                          "why": "; ".join(degree_text(e) for e in profile.education or []) or "Not on profile"})

    experience = []
    need, have = job.experience_required, profile.years_experience
    if need:
        status = "strong" if have and have >= need else "partial" if have and have >= need - 1.5 else "missing"
        experience.append({"item": f"{need:g}+ years", "status": status,
                           "why": f"You have ~{have:g} years" + (" (cannot be faked: show ownership instead)" if status != "strong" else "")})

    language = [{"item": "English", "status": "strong", "why": "Professional English, MSc in the UK"}]
    g = german_level(profile)
    if job.language_requirement == "german_required":
        language.append({"item": "German (required)", "status": "strong" if g in ("B2", "C1", "C2", "NATIVE") else "missing",
                         "why": f"Your German: {g or 'none'}. Months to learn, can't be fixed before applying"})
    elif job.language_requirement == "german_plus":
        language.append({"item": "German (a plus)", "status": "partial" if not g else "strong", "why": f"Your German: {g or 'none'}. Not required"})
    elif job.language_requirement == "german_jd":
        language.append({"item": "German (JD in German)", "status": "missing", "why": "The team likely works in German"})

    return {"must": groups["must"], "preferred": groups["preferred"], "nice": groups["nice"], "soft": soft,
            "domain": domains, "education": education, "experience": experience, "language": language}


# ------------------------------------------------------------------ 4. scores


def match_scores(job, score, reqs: dict) -> dict:
    parts = score.parts if score else {}
    overall = score.overall if score else (job.ats_score or 0)
    known = len(job.parsed.get("skills", []))
    margin = 3 + (4 if known < 4 else 0) + (3 if job.description_incomplete else 0) + (2 if not job.parsed.get("requirements") else 0)
    cloud = [r for g in ("must", "preferred", "nice") for r in reqs[g] if r["item"] in CLOUD_DEVOPS]
    cloud_score = round(100 * sum({"strong": 1, "partial": 0.5}.get(r["status"], 0) for r in cloud) / len(cloud)) if cloud else None
    return {
        "overall": round(overall),
        "range": [max(0, round(overall - margin)), min(100, round(overall + margin))],
        "uncertain": margin > 5,
        "parts": {
            "Technical skills": parts.get("skills"), "Experience": parts.get("experience"), "Role fit": parts.get("role"),
            "Domain": parts.get("industrial"), "Education": 100 if all(e["status"] == "strong" for e in reqs["education"]) else 60,
            "Language": parts.get("language"), "Cloud / DevOps": cloud_score, "Visa": parts.get("sponsorship"), "Location": parts.get("location"),
        },
    }


def germany_fit(scores: dict) -> dict:
    p = scores["parts"]
    weights = {"Technical skills": 0.3, "Experience": 0.2, "Domain": 0.1, "Language": 0.15, "Visa": 0.15, "Location": 0.1}
    have = {k: p[k] for k in weights if p.get(k) is not None}
    overall = round(sum(have[k] * weights[k] for k in have) / (sum(weights[k] for k in have) or 1))
    tier = ("🔥 APPLY IMMEDIATELY" if overall >= 85 else "🟢 STRONG APPLICATION" if overall >= 78
            else "🟡 APPLY IF TIME ALLOWS" if overall >= 68 else "🔴 LOW PRIORITY")
    return {"parts": have, "overall": overall, "tier": tier}


# ------------------------------------------------------------------ 5+6. skill gaps + learning ROI


def roi(skill: str, importance_here: float, share: float) -> dict:
    days, difficulty, interview = LEARNING.get(skill, DEFAULT_LEARNING)
    demand = min(1.0, share / 0.5)                      # 50%+ of your target jobs = full demand
    speed = max(0.0, 1 - days / 60)
    value = 10 * (0.35 * demand + 0.2 * importance_here + 0.2 * interview / 3 + 0.25 * speed)
    if skill in CANNOT_FAKE:
        value *= 0.6
    return {"days": days, "time": f"{days} days" if days < 14 else f"{round(days / 7)} weeks",
            "difficulty": ["", "Easy", "Medium", "Hard"][difficulty], "interview": ["", "Low", "Medium", "High"][interview],
            "roi": round(value, 1)}


def skill_gaps(reqs: dict, market: dict) -> list[dict]:
    weight = {"must": 1.0, "preferred": 0.7, "nice": 0.4}
    gaps = []
    for group in ("must", "preferred", "nice"):
        for r in reqs[group]:
            if r["status"] == "strong":
                continue
            share = market.get("shares", {}).get(r["item"], 0)
            info = roi(r["item"], weight[group], share)
            gaps.append({
                "skill": r["item"], "group": group, "status": r["status"], "current": "None" if r["status"] == "missing" else r["why"],
                "target": "Working knowledge: build one small project" if group == "must" else "Overview: be able to talk about it",
                "importance": {"must": "Very High", "preferred": "High", "nice": "Medium"}[group],
                "jobs_share": round(100 * share), "cannot_fake": r["item"] in CANNOT_FAKE, **info,
                "learn_hindi": hindi_videos(r["item"]),
                "cv_importance": "High" if group == "must" else "Medium",
            })
    gaps.sort(key=lambda g: -g["roi"])
    for i, g in enumerate(gaps, 1):
        g["priority"] = i
    return gaps


# ------------------------------------------------------------------ 7. DSA


def dsa(job, research: dict | None) -> dict:
    kind = company_type(job)
    level = {"big_tech": "Very High", "scale_up": "Medium–High", "industrial": "Low–Medium", "startup": "Low–Medium", "general": "Medium"}[kind]
    if kind == "scale_up" and job.seniority in ("junior",):
        level = "Medium"
    why = {
        "big_tech": "Big Tech interviews are built around algorithm rounds (LeetCode-style, often 2+ rounds).",
        "scale_up": "Scale-ups usually have one live-coding or algorithm round plus practical/system-design rounds.",
        "industrial": "Industrial companies usually test practical coding, debugging and your domain knowledge more than algorithms.",
        "startup": "Small companies usually test practical coding (often a take-home or pair programming), rarely hard algorithms.",
        "general": "Typical software role: expect one practical coding exercise with basic data structures.",
    }[kind]
    reported = (research or {}).get("dsa") or {}
    result = {"level": level, "company_type": COMPANY_TYPE_LABEL[kind], "why": why, "basis": "Estimated from the company type",
              "learn_hindi": hindi_videos("DSA"),
              **{k: DSA_LEVELS[level][k] for k in ("required", "optional", "problems")}}
    if reported.get("level") and reported.get("source_url"):
        result.update({"reported_level": reported["level"], "reported_evidence": reported.get("evidence"),
                       "reported_source": reported["source_url"], "basis": "Reported by candidates (see source) + company type"})
    return result


# ------------------------------------------------------------------ 11+12. predicted questions + questions to ask


def predicted_questions(profile, job, reqs: dict, dsa_info: dict, research: dict | None) -> list[dict]:
    qs: list[dict] = []
    add = lambda q, cat, prob, why, **extra: qs.append({"question": q, "category": cat, "probability": prob, "why": why, "basis": "Estimated", **extra})
    abroad = "germany" not in (profile.location or "").lower()
    strong = [r["item"] for g in ("must", "preferred") for r in reqs[g] if r["status"] == "strong"]
    missing_must = [r["item"] for r in reqs["must"] if r["status"] == "missing"]

    add("Tell me about yourself.", "HR", "Very High", "Opens almost every interview")
    add(f"Why do you want to work at {job.company}, and why this role?", "HR", "Very High", "Asked in almost every first call")
    for i, q in enumerate(project_questions(profile, set(strong))[:4]):
        add(q["question"], "Project deep dive", "Very High" if i == 0 else "High", f"From your CV: {q['where']}", where=q["where"])
    if abroad:
        add("Why Germany? Are you ready to relocate, and when could you start?", "Germany / relocation", "Very High", "You apply from abroad")
    if profile.visa_required is not False:
        add("Do you need visa sponsorship?", "Visa", "High", "Asked early for non-EU candidates; answer clearly")
    add("What salary are you expecting?", "Salary", "High", "Usually asked in the recruiter call (in Germany: yearly gross)")
    for r in reqs["must"][:5]:
        if r["item"] in TOPICS:
            add(f"{r['item']}: {TOPICS[r['item']][0]}?", "Technical", "High", "Must-have in the JD", skill=r["item"])
    for skill in missing_must[:2]:
        add(f"Have you worked with {skill}? How would you get up to speed?", "Technical", "High",
            "Missing must-have: answer honestly and show how you learn", skill=skill)
    if dsa_info["level"] != "Low–Medium":
        add("Solve a coding problem live (arrays / hash maps / strings).", "DSA", "High" if dsa_info["level"] != "Medium" else "Medium",
            f"DSA level {dsa_info['level']}")
    else:
        add("Fix or extend a small piece of code (practical coding).", "DSA", "Medium", "Practical coding is typical here")
    text = simplify(jd_text(job))
    if job.seniority in ("mid", "senior") or re.search(r"architect|scalab|distributed|system design|high[- ]availability", text):
        add("Design a system: e.g. a service that collects data from many machines/users and serves it via an API.",
            "System design", "High" if job.seniority == "senior" else "Medium", "Mid/senior level or architecture in the JD")
    add("Tell me about a hard bug or production problem you solved.", "Behavioral", "High", "Common behavioral question")
    add("Tell me about a disagreement in your team and how you handled it.", "Behavioral", "Medium", "Common behavioral question")
    add("Why are you leaving your current company?", "HR", "Medium", "Common in the recruiter call")
    for r in reqs["preferred"][:2]:
        if r["item"] in TOPICS:
            add(f"{r['item']}: {TOPICS[r['item']][0]}?", "Technical", "Medium", "Mentioned in the JD", skill=r["item"])
    for item in (research or {}).get("reported_questions", [])[:5]:
        qs.append({"question": item["question"], "category": item.get("category", "Reported"), "probability": "High",
                   "why": f"Reported by candidates ({item.get('published') or 'date unknown'})", "basis": "Reported",
                   "source_url": item.get("source_url"), "confidence": item.get("confidence")})
    seen, unique = set(), []
    for q in sorted(qs, key=lambda q: PROBABILITY_ORDER[q["probability"]]):
        if q["question"] not in seen:
            seen.add(q["question"])
            unique.append(q)
    matched = [r["item"] for g in ("must", "preferred", "nice") for r in reqs[g] if r["status"] == "strong"]
    for q in unique[:20]:
        q["guide"] = answer_guide(q, profile, job, matched)
    return unique[:20]


def questions_to_ask(job, reqs: dict, research: dict | None) -> list[str]:
    text = simplify(jd_text(job))
    top = [r["item"] for r in reqs["must"][:2]]
    asks = [f"What would success look like in the first six months for this {job.title} role?"]
    if is_industrial(job):
        asks.append("Which machines, PLCs and protocols does the team integrate with today (OPC UA, MQTT, Modbus…), and how is machine data stored?")
    if top:
        asks.append(f"How is {' and '.join(top)} used in your system today, and which part would I work on first?")
    if re.search(r"kubernetes|aws|azure|gcp|cloud|microservice", text):
        asks.append("How are your services deployed and released today, and how much does the team own operations?")
    asks.append("How does the team approach testing, code review and deployment?")
    asks.append("What are the biggest technical challenges the team is solving this year?")
    if job.visa_status == "confirmed":
        asks.append(f"How does relocation and the EU Blue Card process work at {job.company}, and how long does it usually take?")
    else:
        asks.append(f"Does {job.company} support visa sponsorship (EU Blue Card) and relocation for this role?")
    if job.language_requirement in ("german_plus",):
        asks.append("How much German is used day to day in the team and with customers?")
    asks.append("How big is the team, and who would I work with most closely?")
    products = [f["value"] for f in (research or {}).get("facts", []) if f.get("topic") == "products" and f.get("status") != "not_found"]
    if products:
        asks.append(f"How does this team contribute to {products[0][:80]}?")
    return asks[:10]


# ------------------------------------------------------------------ 13+14. readiness, shortlist, risks


def readiness(profile, job, scores: dict, reqs: dict, gaps: list[dict], dsa_info: dict) -> dict:
    overall = scores["overall"]
    learnable = [g for g in gaps if g["group"] in ("must", "preferred") and g["days"] <= 21 and not g["cannot_fake"]]
    # Learning can only raise the skills part of the score (30% weight), in proportion to the gaps you can close.
    skills_part = (scores["parts"].get("Technical skills") or overall)
    gain = (100 - skills_part) * 0.30 * (len(learnable) / len(gaps)) if gaps else 0
    strong_must = [r["item"] for r in reqs["must"] if r["status"] == "strong"]
    reasons_yes = []
    if strong_must:
        reasons_yes.append(f"You have the core skills: {', '.join(strong_must[:5])}")
    if is_industrial(job) and any(d["status"] == "strong" for d in reqs["domain"]):
        reasons_yes.append("Industrial / production software experience (rare among backend candidates)")
    if any(e["status"] == "strong" for e in reqs["experience"]) or not reqs["experience"]:
        reasons_yes.append("Your experience level fits the requirement")
    if reqs["education"] and reqs["education"][0]["status"] == "strong":
        reasons_yes.append("MSc Computer Science (UK) meets the degree requirement")
    if job.language_requirement == "english":
        reasons_yes.append("English is enough for this role")
    if job.visa_status == "confirmed":
        reasons_yes.append("The JD mentions visa / relocation support")

    risks = []  # (severity 1-5, text)
    for r in reqs["language"]:
        if r["status"] == "missing":
            risks.append((5, f"{r['item']}: your German is not at that level"))
    if job.visa_status == "unlikely" and profile.visa_required is not False:
        risks.append((5, "The JD asks for an existing work permit"))
    elif job.visa_status == "unclear" and profile.visa_required is not False:
        risks.append((3, "Visa sponsorship not mentioned (many companies still sponsor the Blue Card; ask early)"))
    for e in reqs["experience"]:
        if e["status"] != "strong":
            risks.append((4 if e["status"] == "missing" else 2, f"Experience: they ask {e['item']}, {e['why']}"))
    for g in gaps:
        if g["group"] == "must" and g["status"] == "missing":
            risks.append((4 if g["cannot_fake"] else 3, f"Missing must-have: {g['skill']}"))
    if job.seniority in ("senior", "lead", "principal", "head"):
        risks.append((3, f"Seniority is '{job.seniority}', above your ~{profile.years_experience:g} years"))
    if dsa_info["level"] in ("Medium–High", "Very High"):
        risks.append((2, f"Algorithm round likely (DSA {dsa_info['level']})"))
    risks.sort(key=lambda r: -r[0])

    hard_block = any(sev == 5 for sev, _ in risks)
    shortlist = "Very High" if overall >= 88 else "High" if overall >= 80 else "Medium" if overall >= 70 else "Low"
    if hard_block:
        shortlist = "Low"
    elif job.visa_status == "unclear" and profile.visa_required is not False and overall < 88:
        shortlist = level_down(shortlist) if shortlist == "Very High" else shortlist
    tech = "High" if overall >= 82 else "Medium" if overall >= 70 else "Low"
    if dsa_info["level"] in ("Medium–High", "Very High"):
        tech = level_down(tech)
    final = LEVELS[min(LEVELS.index(shortlist), LEVELS.index(tech))]
    if job.visa_status != "confirmed" and profile.visa_required is not False and final != "Low":
        final = level_down(final)
    return {
        "current": round(overall), "after_preparation": round(min(100, overall + gain)),
        "learnable_gaps": [g["skill"] for g in learnable],
        "why_shortlist": reasons_yes, "why_reject": [text for _, text in risks],
        "risks": [{"severity": sev, "risk": text} for sev, text in risks],
        "shortlist": shortlist, "technical": tech, "final": final,
        "note": "Estimated hiring readiness from your CV vs this JD, not a real statistical probability.",
    }


# ------------------------------------------------------------------ 15+16. ATS + CV plan


def ats(profile, job) -> dict:
    cv_text = " ".join([profile.summary or "", profile.headline or "", *(b for _, b in cv_bullets(profile)),
                        *(p.get("tech", "") for p in profile.projects)])
    in_cv = with_implied(set(find_skills(cv_text)))
    mine = with_implied({s["name"] for s in profile.skills})
    present, can_add, never = [], [], []
    for s in job.parsed.get("skills", []):
        k = s["skill"]
        if k in in_cv:
            present.append(k)
        elif k in mine:
            can_add.append({"keyword": k, "how": "You list it: name it in the bullet where you really used it"})
        else:
            other = related_skill(k, mine)
            never.append({"keyword": k, "how": f"Not your experience. Write your real skill instead ({other})" if other
                          else "Not your experience: do not add it"})
    total = len(job.parsed.get("skills", [])) or 1
    return {"present": present, "can_add": can_add, "must_not_add": never,
            "match_now": round(100 * len(present) / total), "match_possible": round(100 * (len(present) + len(can_add)) / total)}


def cv_plan(profile, job, reqs: dict, ats_info: dict) -> dict:
    wanted = {r["item"] for g in ("must", "preferred", "nice") for r in reqs[g]}
    order = [r["item"] for g in ("must", "preferred", "nice") for r in reqs[g] if r["status"] != "missing"]
    projects = sorted(profile.projects, key=lambda p: -len(set(p.get("skills", [])) & wanted))
    emphasize = [p["name"] for p in projects if set(p.get("skills", [])) & wanted][:2]
    shorten = [p["name"] for p in projects if not set(p.get("skills", [])) & wanted]
    weak = []
    for where, bullet in cv_bullets(profile):
        if not re.search(r"\d", bullet) and set(find_skills(bullet)) & wanted:
            weak.append({"where": where, "bullet": bullet,
                         "tip": "Add a real number if you know it (machines, tags, users, response time). If you don't know it, leave it."})
    return {"skills_first": order[:10], "emphasize_projects": emphasize, "shorten_projects": shorten, "weak_bullets": weak[:4],
            "add_keywords": [k["keyword"] for k in ats_info["can_add"]], "never_add": [k["keyword"] for k in ats_info["must_not_add"]],
            "cv_version": "STANDARD", "cv_version_name": "Standard CV"}  # one CV for every application


# ------------------------------------------------------------------ 26. Germany-specific


def germany_check(profile, job, research: dict | None) -> dict:
    text = simplify(jd_text(job))
    facts = {f.get("topic"): f for f in (research or {}).get("facts", [])}
    intl = facts.get("international_hiring")
    city = simplify(job.location or "")
    hub = any(c in city for c in ("berlin", "munich", "munchen", "hamburg", "frankfurt"))
    checks = [
        {"q": "Does the company hire internationally?",
         "a": (f"{intl['value']} ({intl['status']})" if intl and intl.get("status") != "not_found" else
               "JD welcomes international candidates" if re.search(r"international (?:candidates|applicants|team)", text) else "Not found")},
        {"q": "Relocation mentioned?", "a": "Yes" if re.search(r"relocat", text) else "Not specified"},
        {"q": "Visa sponsorship mentioned?", "a": {"confirmed": "Yes", "unlikely": "No: asks for an existing work permit"}.get(job.visa_status, "Not specified")},
        {"q": "EU Blue Card mentioned?", "a": "Yes" if re.search(r"blue card|blaue karte", text) else "Not specified"},
        {"q": "German required?", "a": {"german_required": "Yes", "german_plus": "No (a plus)", "german_jd": "Probably (JD in German)"}.get(job.language_requirement, "No")},
        {"q": "Is English enough?", "a": "Yes" if job.language_requirement in ("english", "german_plus") else "Probably not"},
        {"q": "Location effect", "a": "International tech hub: more English-speaking teams (estimate)" if hub
         else "Outside the big hubs: German is used more often (estimate)"},
    ]
    if job.visa_status == "unlikely" or job.language_requirement in ("german_required", "german_jd"):
        label, why = "🔴 Probably difficult for overseas applicants", "Asks for a work permit or German"
    elif job.visa_status == "confirmed" or (job.language_requirement == "english" and (hub or re.search(r"international", text))):
        label, why = "🟢 International-friendly", "Sponsorship/relocation mentioned, or English team in an international hub"
    else:
        label, why = "🟡 Possibly international-friendly", "No sponsorship language. Not a reason to skip: ask early"
    return {"label": label, "why": why, "checks": checks}


# ------------------------------------------------------------------ 40. final recommendation


def final_recommendation(profile, job, scores, reqs, gaps, dsa_info, ready, plan, contacts, threshold: float) -> dict:
    overall = scores["overall"]
    blocked = [r["risk"] for r in ready["risks"] if r["severity"] == 5]
    learnable_must = [g for g in gaps if g["group"] == "must" and g["status"] == "missing" and not g["cannot_fake"] and g["days"] <= 21]
    student_role = job.employment_type in ("Internship", "Working student")
    if student_role:
        decision, label = "SKIP", "LOW PRIORITY — SKIP (student role)"
    elif blocked or overall < threshold - 15 or job.seniority in ("principal", "head"):
        decision, label = "SKIP", "LOW PRIORITY — SKIP"
    elif overall >= threshold and not (job.seniority == "lead"):
        decision, label = "APPLY", "APPLY NOW"
    elif learnable_must:
        decision, label = "LEARN", f"LEARN {learnable_must[0]['skill'].upper()} FIRST"
    elif overall >= threshold - 5:
        decision, label = "APPLY", "APPLY NOW (stretch)"
    else:
        decision, label = "SKIP", "LOW PRIORITY — SKIP"
    prep_low = sum(g["days"] * (1 if g["status"] == "missing" else 0.4) for g in gaps if g["group"] == "must")
    dsa_days = {"Low–Medium": 2, "Medium": 5, "Medium–High": 10, "Very High": 21}[dsa_info["level"]]
    prep = min(30, max(2, round(0.5 * prep_low) + dsa_days))
    recruiter = next((c for c in sorted(contacts, key=lambda c: c["tier"])), None)
    actions = ["Download the standard CV", "Apply on the official careers page",
               (f"Contact {recruiter['name']} ({recruiter['role']})" if recruiter else "Find 1 recruiter with the search links and contact them")]
    actions += [f"Prepare {g['skill']}" for g in gaps[:2] if g["group"] in ("must", "preferred")]
    actions.append(f"Practice ~{min(20, dsa_info['problems'] // 4)} {dsa_info['level']} DSA problems")
    if decision == "LEARN":
        actions.insert(0, f"Learn {learnable_must[0]['skill']} first (~{learnable_must[0]['time']}), then apply")
    return {
        "decision": decision, "label": label, "match": overall, "shortlist": ready["shortlist"],
        "visa": {"confirmed": "Mentioned in the JD", "unlikely": "Probably not possible", "unclear": "Not specified: ask early"}[job.visa_status],
        "german": {"german_required": "Required", "german_plus": "A plus", "german_jd": "Probably needed"}.get(job.language_requirement, "Not required"),
        "dsa": dsa_info["level"], "biggest_gap": gaps[0]["skill"] if gaps else "None",
        "biggest_risk": ready["risks"][0]["risk"] if ready["risks"] else "None found",
        "preparation": f"{prep}–{prep + 4} days", "cv": plan["cv_version_name"],
        "contact": f"{recruiter['name']} ({recruiter['role']})" if recruiter else "Not identified yet",
        "next_actions": actions,
    }


# ------------------------------------------------------------------ everything for one job


def analyze_job(profile, job, score, settings: dict, market: dict, research: dict | None, contacts: list[dict]) -> dict:
    reqs = requirements(profile, job)
    scores = match_scores(job, score, reqs)
    gaps = skill_gaps(reqs, market)
    dsa_info = dsa(job, research)
    ready = readiness(profile, job, scores, reqs, gaps, dsa_info)
    fit = germany_fit(scores)
    blockers = [r["risk"] for r in ready["risks"] if r["severity"] == 5]
    if job.employment_type in ("Internship", "Working student"):
        blockers.append(f"{job.employment_type}: meant for enrolled students, not a professional role (and not a Blue Card job)")
        ready["risks"].insert(0, {"severity": 5, "risk": blockers[-1]})
    if blockers:
        fit["tier"] = "🔴 LOW PRIORITY"
        fit["blocker"] = blockers[0]
    ats_info = ats(profile, job)
    plan = cv_plan(profile, job, reqs, ats_info)
    return {
        "job_information": job_information(job),
        "requirements": reqs,
        "scores": scores,
        "germany_fit": fit,
        "germany": germany_check(profile, job, research),
        "skill_gaps": gaps,
        "dsa": dsa_info,
        "predicted_questions": predicted_questions(profile, job, reqs, dsa_info, research),
        "questions_to_ask": questions_to_ask(job, reqs, research),
        "readiness": ready,
        "ats": ats_info,
        "cv_plan": plan,
        "recommendation": final_recommendation(profile, job, scores, reqs, gaps, dsa_info, ready, plan, contacts, settings["min_score"]),
        "company_type": COMPANY_TYPE_LABEL[company_type(job)],
        "role_family": ROLE_FAMILIES[role_family(job.title, job.parsed.get("industrial_signals"))]["label"],
    }
