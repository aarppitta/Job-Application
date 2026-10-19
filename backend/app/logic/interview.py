"""Interview preparation for one job.

Built from three things only:
1. the skills the JD asks for -> typical interview topics for each skill (TOPICS below)
2. your CV projects/bullets -> which real story to tell for each skill
3. the skills you are missing -> what to study before the interview
Nothing is said about the company except what is in the JD.
"""
import re

from app.logic.cv import degree_text
from app.logic.skills import find_skills, with_implied

# Typical interview topics per skill. Add a line to cover a new skill.
TOPICS: dict[str, list[str]] = {
    "Python": ["Lists vs tuples vs sets vs dicts, and their time complexity", "Generators, iterators and context managers",
               "The GIL; threads vs processes vs asyncio", "Decorators and type hints", "Error handling and writing tests with pytest"],
    "FastAPI": ["Dependency injection", "Pydantic models and validation", "async endpoints vs normal endpoints",
                "Authentication with JWT / OAuth2", "Background tasks, middleware and CORS"],
    "Django": ["ORM: select_related / prefetch_related, N+1 queries", "Migrations", "Class-based vs function views",
               "Django REST Framework serializers and permissions"],
    "REST APIs": ["HTTP methods, status codes and idempotency", "Designing resources and versioning", "Pagination, filtering, errors",
                  "Authentication vs authorization"],
    "SQL": ["JOIN types, GROUP BY / HAVING", "Indexes and when they help", "Transactions and isolation levels", "Normalisation"],
    "MySQL": ["Indexes, EXPLAIN, slow queries", "Transactions (InnoDB)", "Backup and restore"],
    "PostgreSQL": ["Indexes, EXPLAIN ANALYZE", "JSONB", "Transactions and locking", "Differences from MySQL (you know MySQL)"],
    "MongoDB": ["Document modelling vs relational", "Indexes and aggregation pipeline"],
    "Docker": ["Image vs container", "Writing a small Dockerfile, layers and caching", "docker-compose for multi-service apps",
               "Volumes, networks, environment variables"],
    "Kubernetes": ["Pods, Deployments, Services", "ConfigMaps and Secrets", "Health checks and rolling updates"],
    "AWS": ["EC2, security groups and SSH", "S3 basics", "IAM roles vs users", "Deploying a backend on EC2"],
    "Angular": ["Components, services and dependency injection", "RxJS Observables, subscribe/unsubscribe",
                "Change detection", "Routing, guards and HTTP interceptors", "Reactive forms"],
    "React": ["Hooks (useState, useEffect, custom hooks)", "Props vs state, lifting state up", "Rendering lists and keys",
              "Fetching data and loading/error states"],
    "TypeScript": ["Types vs interfaces, generics", "Union types and narrowing", "strict mode"],
    "JavaScript": ["Closures, this, promises and async/await", "Event loop", "== vs ==="],
    "Node.js": ["Event loop and non-blocking I/O", "Express middleware and error handling", "Streams"],
    "Express.js": ["Middleware order", "Routing and error handlers", "Auth middleware (JWT)"],
    "JWT": ["Structure of a JWT (header, payload, signature)", "Access vs refresh tokens", "Where to store tokens safely"],
    "RBAC": ["Roles vs permissions", "How you designed operator/supervisor/admin rights"],
    "SCADA": ["SCADA vs HMI vs PLC vs MES layers (ISA-95 levels)", "Alarms, trends, historian data", "Real-time data update strategies"],
    "WebSCADA": ["Pushing live values to the browser (polling vs WebSocket)", "Handling many tags efficiently"],
    "OPC UA": ["Address space, nodes, browsing", "Subscriptions and monitored items vs polling", "Security modes and certificates",
               "OPC UA vs classic OPC DA"],
    "OPC": ["Classic OPC (DA) vs OPC UA", "Why a custom OPC server: drivers, polling, storing data"],
    "Modbus": ["Coils, discrete inputs, input and holding registers", "Function codes (03, 06, 16)", "Modbus TCP vs RTU",
               "Byte/word order for 32-bit values"],
    "PLC": ["How PLC data reaches IT systems", "Scan cycle basics", "Handling connection loss and timeouts"],
    "FINS": ["FINS over Serial vs Ethernet", "Memory areas and addressing on Omron PLCs"],
    "MQTT": ["Publish/subscribe, topics and wildcards", "QoS levels 0/1/2, retained messages"],
    "IIoT": ["Edge vs cloud processing", "Collecting machine data reliably (buffering, reconnects)", "OT/IT security basics"],
    "MES": ["What an MES does (orders, recipes, traceability)", "ISA-95 and integration with ERP and SCADA"],
    "21 CFR Part 11": ["Audit trails, electronic signatures, data integrity (ALCOA+)", "How you implemented them in L2 LineSync"],
    "Git": ["Branching, rebase vs merge, pull requests", "Resolving conflicts"],
    "Linux": ["Processes, permissions, systemd services, logs"],
    "Unit Testing": ["Unit vs integration tests, mocking", "What you would test first in your projects"],
    "Microservices": ["Monolith vs microservices trade-offs", "Service communication (REST, queues)"],
    "Kafka": ["Topics, partitions, consumer groups"],
    "CI/CD": ["What a pipeline does: build, test, deploy"],
    "Agile": ["Sprints, stand-ups, estimation", "How you worked in Agile at Fortray"],
}

ALWAYS = [
    "Tell me about yourself (2 minutes: current role at Kevision, your industrial + full-stack mix, why Germany)",
    "Walk me through one project end to end (choose L2 LineSync or the OPC Server)",
    "A hard bug or problem you solved, and how",
    "How you lead / mentor junior developers (you do this at Kevision)",
    "Why this company and this role (read the JD and the company website first)",
    "Visa and relocation: be ready to answer clearly and honestly",
    "Your questions for them: team size, tech stack, onboarding, how success is measured",
]


def interview_prep(profile, job, matched: list[str], missing: list[str]) -> dict:
    my_skills = with_implied({s["name"] for s in profile.skills})
    job_skills = [s["skill"] for s in job.parsed.get("skills", [])]
    required = [s["skill"] for s in job.parsed.get("skills", []) if s["required"]]

    # 1. technical topics: skills the job asks for, the ones you have first
    technical = []
    for skill in sorted(set(job_skills), key=lambda s: (s not in my_skills, s not in required, s)):
        if skill in TOPICS:
            technical.append({"skill": skill, "you_have_it": skill in my_skills, "topics": TOPICS[skill]})

    # 2. your stories: for each matched skill, the CV project/bullet that proves it
    stories = []
    places = [(p["name"], b) for p in profile.projects for b in p.get("bullets", [])] + \
             [(f"{e['role']} at {e['company']}", b) for e in profile.experience for b in e.get("bullets", [])]
    used = set()
    for skill in matched:
        for where, bullet in places:
            if skill in find_skills(bullet) and bullet not in used:
                stories.append({"skill": skill, "where": where, "story": bullet})
                used.add(bullet)
                break

    # 3. gaps to study
    gaps = [{"skill": s, "required": s in required,
             "advice": ("Required: learn the basics and build a small example before the interview. "
                        "Say honestly that it is new to you and how you would learn it fast.")
             if s in required else "Nice to have: read an overview so you can talk about it."}
            for s in missing]

    tips = []
    if job.language_requirement == "german_plus":
        tips.append("German is a plus: learn a short self-introduction in German and mention if you are learning.")
    if job.visa_status == "confirmed":
        tips.append("The JD mentions visa/relocation support: you can ask about the process at the end.")
    elif job.visa_status == "unclear":
        tips.append("The JD does not mention visa support: ask politely about sponsorship early, e.g. in the first call.")
    if (job.experience_required or 0) > (profile.years_experience or 0):
        tips.append(f"They ask for {job.experience_required:g}+ years; you have ~{profile.years_experience:g}. "
                    "Focus on how much you own end to end (L2 LineSync, OPC Server, leading juniors).")

    return {"technical": technical, "stories": stories, "gaps": gaps, "general_questions": ALWAYS, "tips": tips}


# ------------------------------------------------------------------ questions built from YOUR CV

# (pattern in a bullet / tech line, question). {project} = the project or job from your CV.
PROJECT_RULES = [
    (r"pluggable|driver", "In {project}, explain the driver architecture: how does a new protocol plug in?"),
    (r"opc[\s-]?ua", "How did {project} talk to the OPC-UA server: browsing, subscriptions or polling? Why?"),
    (r"modbus|fins|plc", "How did PLC communication work in {project}, and what happened when a PLC connection dropped?"),
    (r"rbac|role", "How did RBAC work in {project}? Where were permissions checked on each request?"),
    (r"audit trail|audit", "How did you build the audit trail in {project} so records can't be changed afterwards?"),
    (r"digital signature|21 cfr", "How did electronic signatures meet 21 CFR Part 11 in {project}?"),
    (r"pyinstaller|nssm|windows service", "How did you deploy {project}, and how did you ship updates to a running site?"),
    (r"real-time|live machine|live values", "How did {project} get live values to the browser, and how often did it refresh?"),
    (r"backup|restore", "How did database backup and restore work in {project}?"),
    (r"jwt", "How did JWT authentication work in {project}? Where were tokens stored and how did they expire?"),
    (r"mysql|database|persist|schema", "How did you design the database in {project}, and how did you handle database failures?"),
    (r"lead|junior", "How do you lead the junior developer on {project}: reviews, planning, getting them unblocked?"),
    (r"recipe", "How did recipe management work in {project}, and how did a recipe reach a machine?"),
    (r"config\.ini|configuration", "How did you validate the generated configuration in {project} before it reached a machine?"),
    (r"node\.js|express", "How did you structure the Node.js/Express backend in {project}: middleware, errors, auth?"),
    (r"aws|ec2", "How did you deploy to AWS EC2 in {project}: security groups, environment config, restarts?"),
    (r"angular", "How did you structure the Angular frontend in {project}: services, state, live updates?"),
]


def project_questions(profile, focus: set[str] | None = None) -> list[dict]:
    """Deep-dive questions about YOUR projects (and jobs), most relevant projects first, rotating across projects."""
    focus = focus or set()
    per_project = []
    for p in profile.projects:
        text = " ".join([*p.get("bullets", []), p.get("tech", "")]).lower()
        name = p["name"]
        qs = [f"Walk me through the architecture of {name}: what were the main parts and why?"]
        qs += [template.format(project=name) for pattern, template in PROJECT_RULES if re.search(pattern, text)]
        qs.append(f"If {name} had to handle 10× more machines or users, what would you change first?")
        per_project.append((len(set(p.get("skills", [])) & focus), name, qs))
    for e in profile.experience or []:
        name = f"your role at {e['company']}"
        overlap = len(set(find_skills(" ".join(e.get("bullets", [])))) & focus)
        per_project.append((overlap - 2, name, [f"Walk me through what you build and own in {name}."]))
    per_project.sort(key=lambda x: -x[0])
    # Round robin in pairs: opener + one specific question per project, then the next pair, …
    found, seen, depth = [], set(), 0
    while any(depth < len(qs) for _, _, qs in per_project):
        for relevance, name, qs in per_project:
            for q in qs[depth:depth + 2]:
                if q not in seen:
                    seen.add(q)
                    found.append({"question": q, "where": name, "relevance": relevance})
        depth += 2
    return found


# Ideal answer structures, used by the mock interview (and as the fallback when AI is not configured).
ANSWER_STRUCTURES = {
    "HR": ["Short answer first (1 sentence)", "One concrete reason tied to this company/role", "Link to your experience", "End positively / with a question"],
    "Project deep dive": ["Context: what the system does and for whom", "Architecture: main parts and data flow", "Your role and decisions (why this, not that)",
                          "Hardest problem and how you solved it", "Result / what you'd improve"],
    "Technical": ["Define the concept in one sentence", "How it works (key mechanism)", "When to use it / trade-offs", "Example from your own work"],
    "DSA": ["Clarify input/output and edge cases", "Brute force first, state its complexity", "Better approach (data structure + why)",
            "Code it cleanly, talk while coding", "Test with an example, state final complexity"],
    "System design": ["Requirements and scale (ask questions)", "API and data model", "High-level components and data flow",
                      "Bottlenecks, scaling, failure handling", "Trade-offs and what you'd do next"],
    "Behavioral": ["Situation (short)", "Task: your responsibility", "Action: what YOU did, step by step", "Result: outcome, ideally a number", "What you learned"],
    "Germany / relocation": ["Clear motivation for Germany (career, industry, the role)", "Concrete plan and timeline (notice period, relocation)",
                             "Show commitment (e.g. learning German)"],
    "Visa": ["Answer directly: yes, EU Blue Card", "Show you know the process (degree recognition, salary threshold, ~1–3 months)",
             "Reassure: you handle paperwork quickly"],
    "Salary": ["Researched range for this role and city (yearly gross)", "Say it is flexible for the right role", "Ask about the total package"],
}


# ------------------------------------------------------------------ detailed answer guide per question

def _bullets(profile):
    return [(p["name"], b) for p in profile.projects for b in p.get("bullets", [])] + \
           [(f"{e['role']} at {e['company']}", b) for e in profile.experience or [] for b in e.get("bullets", [])]


def _cv_facts(question: str, category: str, profile, where: str | None, skill: str | None) -> list[str]:
    """Real CV facts worth mentioning in this answer (never invented)."""
    bullets = _bullets(profile)
    if category == "Project deep dive" and where:
        own = [b for w, b in bullets if w == where or where.endswith(w.split(" at ")[-1])]
        return own[:4]
    if skill or category == "Technical":
        wanted = {skill} if skill else set(find_skills(question))
        hits = [f"{w}: {b}" for w, b in bullets if wanted & set(find_skills(b))]
        return hits[:3]
    if category == "Behavioral":
        pattern = r"lead|junior|from scratch|compliance|21 cfr|reduc|deploy|connection|backup"
        return [f"{w}: {b}" for w, b in bullets if re.search(pattern, b, re.I)][:3]
    if category == "System design":
        return [f"{w}: {b}" for w, b in bullets if re.search(r"driver|persist|real-time|architecture", b, re.I)][:3]
    if category == "HR" and "yourself" in question.lower():
        current = (profile.experience or [{}])[0]
        facts = [f"Now: {current.get('role')} at {current.get('company')} ({current.get('dates')})"] if current else []
        facts += [f"Before: {e['role']} at {e['company']}" for e in (profile.experience or [])[1:3]]
        facts += [f"Education: {degree_text(e)}" for e in (profile.education or [])[:1]]
        facts += [f"Key project: {p['name']}" for p in profile.projects[:2]]
        return facts
    return []


def answer_guide(q: dict, profile, job, matched: list[str]) -> dict:
    """How to answer ONE predicted question: what they check, length, step-by-step structure, CV facts, pitfalls, opening."""
    question, category = q["question"], q["category"]
    low = question.lower()
    skill = q.get("skill")
    name = profile.name.split()[0]
    current = (profile.experience or [{}])[0]
    strengths = ", ".join(matched[:3]) or "your main skills"
    years = f"{profile.years_experience:g}" if profile.years_experience else "a few"

    if "yourself" in low:
        g = {"checks": "Can you summarise your fit for THIS role in English, clearly and briefly?", "length": "60–90 seconds",
             "steps": [("Present", f"Your current role ({current.get('role')} at {current.get('company')}) and what you build there."),
                       ("Past", "1–2 sentences on earlier roles and your MSc in the UK: only what leads to this job."),
                       ("Why you fit", f"2 strengths this JD asks for, each with one concrete example: {strengths}."),
                       ("Future", f"Why this role at {job.company}, and why Germany now. End there, they will ask more.")],
             "avoid": ["Reading your CV line by line", "Personal life details", "Ending with 'that's it': end with what you want next"],
             "opening": f"I'm {name}, a software engineer with about {years} years of experience. Right now I work as "
                        f"{current.get('role', 'a developer')} at {current.get('company', 'my company')}, where I build …"}
    elif "why do you want to work" in low or category == "HR" and "why" in low and job.company.lower() in low:
        g = {"checks": "Real motivation and whether you researched the company.", "length": "45–60 seconds",
             "steps": [("The company", f"One specific thing about {job.company}: product, customers, tech or mission (from their website / the research tab)."),
                       ("The role", f"Map 2 JD requirements to your own work, e.g. {strengths} in your projects."),
                       ("What you bring and want", "What you'd contribute in the first months and what you want to learn there.")],
             "avoid": ["Generic praise ('great company')", "Visa, salary or 'Germany' as the main reason"],
             "opening": f"What attracts me to {job.company} is … and the role fits my experience with {strengths}."}
    elif "leaving" in low:
        g = {"checks": "That you leave FOR something, not away from something.", "length": "30 seconds",
             "steps": [("Positive about now", "What you learned and still like in your current job."),
                       ("The pull", "The concrete reason: an international career in Germany, a bigger product, a specific domain."),
                       ("Link to this role", "Why this job is the right next step.")],
             "avoid": ["Criticising your employer, manager or salary", "Hiding a short tenure: if asked, be honest and calm"],
             "opening": "I've learned a lot at my current company, and I'm now looking for …"}
    elif category == "Germany / relocation":
        g = {"checks": "That you will really come, stay, and can start on a realistic date.", "length": "45–60 seconds",
             "steps": [("Motivation", "Your real reasons for Germany: career, industry, the kind of companies (only what is true for you)."),
                       ("Plan", "Your notice period and a realistic start date including the visa process."),
                       ("Commitment", "Show you are serious: e.g. learning German (only if true), already researched cities/process.")],
             "avoid": ["Sounding unsure or 'just trying'", "Promising a start date you can't keep"],
             "opening": "I'm specifically looking for a long-term role in Germany because …"}
    elif category == "Visa":
        g = {"checks": "Whether hiring you is simple and predictable for them.", "length": "20–40 seconds",
             "steps": [("Direct answer", "Yes, you would need sponsorship, typically through the EU Blue Card."),
                       ("Show you know the process", "A recognised degree (you have an MSc from a UK university; recognition can be checked "
                        "in the anabin database) and a salary above the yearly Blue Card threshold."),
                       ("Reassure", "You handle the paperwork quickly; the company mainly signs the job offer and a form.")],
             "avoid": ["Apologising or sounding unsure", "Quoting exact thresholds or processing times you haven't checked this year"],
             "opening": "Yes. I'd apply for the EU Blue Card. My MSc is from a UK university, so the degree side is straightforward …"}
    elif category == "Salary":
        g = {"checks": "Whether your expectation fits their budget and you know the German market.", "length": "20–30 seconds",
             "steps": [("Research first", "Check this role and city on salary sites and the research tab (yearly gross, EUR)."),
                       ("Give a range", "A realistic yearly gross range in EUR, not a single number."),
                       ("Stay flexible", "Say the whole package and the role matter to you; ask what their range is.")],
             "avoid": ["Using your current Indian salary as the anchor", "Monthly or net numbers (Germany talks yearly gross)"],
             "opening": "Based on my research for this role in this city, I'm looking at a range of … gross per year, depending on the package."}
    elif category == "Project deep dive":
        g = {"checks": "Depth, ownership and decisions: do you understand what you built and why?", "length": "2–4 minutes (they will interrupt)",
             "steps": [("Context", "What the system does and for whom (one sentence)."),
                       ("Architecture", "Main parts and the data flow from start to end; draw it if you can."),
                       ("Your part", "What YOU designed, built or decided, and why this option over another."),
                       ("Hardest problem", "One real difficulty and how you solved it."),
                       ("Result and next step", "What it achieved, and what you would improve now.")],
             "avoid": ["Saying 'we' without making your own part clear", "Technologies you can't explain in depth", "Inventing numbers"],
             "opening": f"{q.get('where', 'The project')} is … I was responsible for …"}
    elif category == "DSA":
        g = {"checks": "How you think: clarifying, choosing a data structure, writing clean code, testing.", "length": "20–40 minutes",
             "steps": [("Clarify", "Restate the problem, ask about input size, edge cases (empty, duplicates)."),
                       ("Brute force", "Say the simple solution and its complexity first."),
                       ("Improve", "Pick the right structure (dict/set, two pointers, sorting…) and explain why."),
                       ("Code", "Write clean Python while talking; small helper functions, good names."),
                       ("Test", "Walk through an example and an edge case; state final time and space complexity.")],
             "avoid": ["Coding in silence", "Jumping to code before clarifying", "Ignoring complexity"],
             "opening": "Let me first make sure I understand: the input is … and the expected output is …"}
    elif category == "System design":
        g = {"checks": "Structured thinking about scale, data and failures, and honest trade-offs.", "length": "30–45 minutes",
             "steps": [("Requirements", "Ask: users/machines, data volume, latency, availability."),
                       ("API and data", "Main endpoints and the data model (tables, time-series data)."),
                       ("Components", "Ingestion, storage, API, frontend; draw the data flow."),
                       ("Scale and failures", "Bottlenecks, caching, queues, what happens when a machine/DB is down."),
                       ("Trade-offs", "What you'd do first vs later; use your OPC server / L2 LineSync experience as a real anchor.")],
             "avoid": ["Naming tools without reasons", "Skipping requirements", "Claiming scale you never ran"],
             "opening": "Before I design anything, I'd like to clarify a few requirements: …"}
    elif category == "Behavioral":
        g = {"checks": "How you act in real situations: ownership, collaboration, learning.", "length": "1–2 minutes",
             "steps": [("Situation", "Short context: project, team, what was at stake."), ("Task", "Your responsibility."),
                       ("Action", "What YOU did, step by step, the most detailed part."), ("Result", "Outcome, with a real number if you have one."),
                       ("Learning", "What you do differently since then.")],
             "avoid": ["Blaming others", "A story without a result", "Inventing a story: use a real one from the facts below"],
             "opening": "In my current role, we had a situation where …"}
    elif skill and "have you worked with" in low:
        g = {"checks": "Honesty and how fast you learn.", "length": "30–45 seconds",
             "steps": [("Honest answer", f"Say clearly that you haven't used {skill} in production."),
                       ("Closest experience", "Name the related skill you do have and how it transfers."),
                       ("Ramp-up plan", f"How you'd learn {skill} fast: what you've already started, a small project.")],
             "avoid": ["Pretending to have experience", "Just saying 'no'"],
             "opening": f"I haven't used {skill} in production yet. The closest experience I have is …"}
    else:  # Technical (and reported questions)
        g = {"checks": "Real understanding, not memorised definitions, and whether you've used it.", "length": "1–2 minutes",
             "steps": [("Define", "One clear sentence."), ("How it works", "The key mechanism, with a tiny example."),
                       ("When and trade-offs", "When to use it, when not, and the alternatives."),
                       ("Your experience", "Where you used it in your projects (facts below).")],
             "avoid": ["Guessing: say what you would check", "Long theory without an example"],
             "opening": f"In short, {skill or 'it'} is … In my work I used it for …"}
    return {"checks": g["checks"], "length": g["length"],
            "steps": [{"step": s, "detail": d} for s, d in g["steps"]],
            "cv_facts": _cv_facts(question, category, profile, q.get("where"), skill),
            "avoid": g["avoid"], "opening": g["opening"]}
