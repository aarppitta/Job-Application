"""Starting profile (copied from Arpita's CV, kept in data/standard_cv.txt) and default settings.

Email, phone and visa need are not on the CV, so they are empty until you fill them in Settings.
"""
from app.config import settings

DEFAULT_PROFILE = {
    "name": "Arpita Chaudhari",
    "headline": "Industrial Software Engineer · IIoT & OT Systems",
    "location": "Ahmedabad, India",
    "github_url": "https://github.com/aarppitta",
    "linkedin_url": "https://linkedin.com/in/arpita-chaudhari",
    # From the project brief. The CV dates add up to ~2.4 years including an 18-month internship.
    "years_experience": 2.5,
    "target_country": "Germany",
    "summary": (
        "Industrial Software Engineer with hands-on expertise in IIoT systems, WebSCADA platforms and industrial "
        "protocol communication. Builds custom Python-based OPC servers, 21 CFR Part 11-compliant WebSCADA "
        "applications, OPC-UA tag management tools and Windows service-packaged deployments for pharmaceutical and "
        "manufacturing environments. Proficient in Angular and FastAPI; experienced in leading junior engineers."
    ),
    "education": ["MSc Computer Science, University of Greenwich, London"],
    "experience": [
        {"company": "Kevision Systems", "location": "Ahmedabad, India", "role": "System Software Engineer — Industrial Automation", "dates": "April 2026 – Present",
         "bullets": [
             "Design and develop industrial automation software — WebSCADA platforms, OPC servers, SCADA interfaces and pharma machine data-logging tools for manufacturing environments.",
             "Build Python-based backend services (FastAPI, Django) for industrial data acquisition and PLC communication via OPC-UA, Modbus TCP/RTU, FINS Serial and FINS Ethernet protocols.",
             "Develop Angular frontend applications for real-time process monitoring, operator controls, recipe management, machine configuration and production reporting.",
             "Implement 21 CFR Part 11 compliance features — electronic audit trails, digital signature workflows and data integrity controls for regulated pharma environments.",
             "Package production Python applications as standalone Windows executables (PyInstaller) and register them as persistent Windows services using NSSM for zero-dependency deployment on production-floor machines.",
             "Lead junior developers — code reviews, coding standards, task assignment and technical mentoring across concurrent projects.",
         ]},
        {"company": "Quarks Systems", "location": "Ahmedabad, India", "role": "Junior Full Stack Developer", "dates": "August 2025 – December 2025",
         "bullets": [
             "Built and maintained RESTful APIs in Node.js/Express.js; integrated backend services with camera and printing hardware modules.",
             "Maintained Postman API documentation, improving cross-team integration efficiency by ~30%.",
         ]},
        {"company": "Fortray Global Services Limited", "location": "London, United Kingdom", "role": "Full Stack Developer Intern — MEAN Stack", "dates": "July 2023 – December 2024",
         "bullets": [
             "Built backend services in Node.js/Express.js with MongoDB, deployed to AWS EC2, with JWT authentication and RBAC.",
             "Worked in Agile sprints delivering end-to-end frontend/backend integration across multiple release cycles.",
         ]},
    ],
    "languages": [{"language": "English", "level": "Professional"}],
    "target_roles": [
        "Industrial Software Engineer", "IIoT Engineer", "Industrial IoT Engineer", "Automation Software Engineer",
        "Python Backend Engineer", "SCADA Software Developer", "MES Integration Engineer", "OT Software Engineer",
        "OT Application Developer", "Backend Engineer", "Full Stack Engineer", "Software Engineer", "Python Developer",
        "Automation Software Developer", "Industrial Digitalization Engineer",
    ],
    "skills": [{"name": s, "years": None} for s in [
        # from the CV
        "Python", "FastAPI", "Django", "Angular", "TypeScript", "JavaScript", "Node.js", "Express.js", "MongoDB",
        "MySQL", "REST APIs", "JWT", "RBAC", "AWS", "Agile", "Postman",
        "SCADA", "WebSCADA", "OPC", "OPC UA", "Modbus", "FINS", "PLC", "IIoT", "21 CFR Part 11",
        "PyInstaller", "Windows Services", "LabVIEW", "Zenon",
        # from the project brief (not on the CV)
        "React", "Docker", "Git",
    ]],
    "domain_experience": [
        "WebSCADA platforms", "Industrial process monitoring", "OPC server development (OPC-UA, Modbus TCP/RTU, FINS)",
        "PLC communication", "Pharma manufacturing", "21 CFR Part 11 compliance (audit trails, digital signatures)",
        "Recipe management", "Machine registration and configuration", "Production reporting",
        "Windows service deployment (PyInstaller, NSSM)", "Leading junior developers",
    ],
    "projects": [
        {"name": "L2 LineSync — WebSCADA System", "tech": "Angular · FastAPI · Python · MySQL · PyInstaller · NSSM · 21 CFR Part 11",
         "description": "Process monitoring, recipes, RBAC, digital signatures, audit trail (21 CFR Part 11)",
         "skills": ["WebSCADA", "SCADA", "Angular", "FastAPI", "Python", "MySQL", "RBAC", "21 CFR Part 11", "PyInstaller", "Windows Services"],
         "bullets": [
             "L2 industrial process-monitoring platform — acquires real-time process data from the L1 server and displays live machine status, alarms and process values across production lines.",
             "Recipe management: full CRUD for recipes, per-machine recipe assignment, and per-machine / per-recipe production reports.",
             "User management: group-level and user-level CRUD, multi-tier RBAC (operator, supervisor, admin), configurable security policy and feature-level access-rights control.",
             "Machine registration and configuration, including database backup and restore for administrators.",
             "Digital signature functionality meeting 21 CFR Part 11 electronic signature requirements, plus a tamper-evident audit trail of all system and user actions.",
             "Packaged the FastAPI backend as a standalone Windows executable (PyInstaller) running as a persistent background service via NSSM.",
         ]},
        {"name": "OPC Server — Custom Industrial Data Gateway", "tech": "Python · Django · MySQL · OPC-UA · Modbus TCP/RTU · FINS Serial · FINS Ethernet",
         "description": "Open-source alternative to Kepware with pluggable protocol drivers",
         "skills": ["Python", "Django", "MySQL", "OPC", "OPC UA", "Modbus", "FINS", "PLC"],
         "bullets": [
             "Engineered a fully custom Python OPC server from scratch as an open-source alternative to commercial OPC servers such as Kepware.",
             "Pluggable, protocol-agnostic driver architecture with four production drivers: Modbus TCP/RTU, FINS Serial, FINS Ethernet and OPC-UA.",
             "Reads live process data from PLCs and persists it into MySQL with a normalised schema for historical analysis, trend reporting and alarm logging.",
         ]},
        {"name": "Pulse Connect — OPC-UA Tag Browser & Config Generator", "tech": "Python · OPC-UA (asyncua) · Angular · FastAPI · MySQL",
         "description": "Browse OPC-UA tags and generate data-logging config",
         "skills": ["Python", "OPC UA", "Angular", "FastAPI", "MySQL"],
         "bullets": [
             "Connects to an OPC-UA server, browses the tag namespace and lets engineers classify tags as Process Tags or Alarm Tags through a guided UI.",
             "Generates a structured config.ini consumed directly by machine data-logging services, reducing commissioning time for new machines.",
         ]},
        {"name": "Pharma Processing Machine — Configuration Tool", "tech": "Python · config.ini · Industrial Protocols · Pharma Manufacturing",
         "description": "Validated config.ini generator for pharma machines",
         "skills": ["Python"],
         "bullets": [
             "Python utility that generates validated config.ini files (IP addresses, database settings, trigger bits) for pharma processing machines in a regulated environment.",
         ]},
        {"name": "Compression Machine Interface — Angular SCADA", "tech": "Angular · TypeScript · LabVIEW · Zenon",
         "description": "Operator screens on top of LabVIEW / Zenon",
         "skills": ["Angular", "TypeScript", "SCADA", "LabVIEW", "Zenon"],
         "bullets": [
             "Angular-based SCADA application with real-time operator screens for compression machines.",
             "Defined the data interface contract between the Angular frontend and the LabVIEW / Zenon backend layer.",
             "Leading a junior developer on this project — component architecture, code review, integration testing and delivery planning.",
         ]},
    ],
}

DEFAULT_SETTINGS = {
    "min_score": 80,                  # ATS threshold for "qualified"
    "weights": {"skills": 30, "experience": 20, "role": 15, "industrial": 10,
                "location": 10, "language": 5, "sponsorship": 5, "seniority": 5},
    "max_runtime_hours": 6,
    "repeat_every_minutes": 30,       # the automation searches again after this pause
    "daily_auto_start": True,         # start the automation by itself every day...
    "daily_start_time": "08:00",      # ...at this time (computer's local time), as long as the backend is running
    "sources": ["greenhouse", "lever", "smartrecruiters", "personio", "ashby", "arbeitnow",
                "berlinstartupjobs", "munichstartup", "startupcityhamburg"],
    # Job roles to search for. JOB_KEYWORDS in .env replaces this list on another computer.
    "search_queries": [k.strip() for k in settings.job_keywords.split(",") if k.strip()] or [
        "Software Engineer", "Mid Software Engineer", "Software Developer", "Softwareentwickler",
        "Industrial Software Engineer", "IIoT Engineer", "IoT Software Engineer", "Automation Software Engineer",
        "SCADA Software Developer", "MES Integration Engineer", "OT Software Engineer",
        "Manufacturing Software Engineer", "Python Developer", "Python Software Engineer", "Python Backend Engineer",
        "Django Developer", "Backend Engineer", "Backend Developer", "Full Stack Engineer", "Full Stack Developer",
        "Python Full Stack Developer", "Angular Developer", "TypeScript Developer", "Node.js Developer", "Prompt Engineer",
    ],
    # Companies to follow = their own careers pages (the part of their job-board URL).
    # Checked 2026-10-07: each has software/engineering jobs in Germany. Banks/fintech, industrial/IoT, tech.
    "greenhouse_boards": ["celonis", "n26", "getyourguide", "contentful", "raisin", "commercetools", "helsing",
                          "isaraerospace", "sumup", "hellofresh", "flix", "staffbase", "parloa",
                          "traderepublicbank", "solarisbank", "adyen", "konux", "tulip", "trivago", "scout24",
                          "autoscout24", "doctolib", "wolt", "freenow"],  # boards.greenhouse.io/<board>
    "lever_companies": ["mobileye"],  # jobs.lever.co/<company>
    "smartrecruiters_companies": ["BoschGroup", "Continental", "DeliveryHero", "Sixt", "Brainlab"],  # jobs.smartrecruiters.com/<Company>
    "personio_companies": ["vivid", "ottonova", "ryd", "magazino", "wandelbots", "arculus", "envelio", "kiwigrid",
                           "node-energy", "stark", "1komma5grad", "tonies"],  # <company>.jobs.personio.de
    "goal_date": "2027-01-31",        # Germany job by January 2027 (Strategy page counts down to this)
    "study_hours_per_week": 15,       # time you can spend learning; the weekly plan splits it
    "ashby_boards": ["qonto", "moss", "upvest", "sereact", "enpal", "babbel", "n8n", "tacto", "langdock", "forto",
                     "deepl", "black-forest-labs"],  # jobs.ashbyhq.com/<board>
}

# CV versions: the same real CV, with a different headline and skill order. Nothing is added.
# A job gets the version whose role family fits it best (logic/analysis.py → recommend_cv_version).
CV_VERSIONS = {
    "CV-001": {"name": "General Germany Software Engineer", "family": "general",
               "headline": "Software Engineer · Python, Full Stack & Industrial Systems",
               "focus": ["Python", "TypeScript", "Angular", "React", "FastAPI", "Django", "REST APIs", "MySQL", "Docker"]},
    "CV-002": {"name": "Python Backend Germany", "family": "backend",
               "headline": "Python Backend Engineer · FastAPI, Django, REST APIs",
               "focus": ["Python", "FastAPI", "Django", "REST APIs", "MySQL", "SQL", "JWT", "RBAC", "Docker", "AWS"]},
    "CV-003": {"name": "Industrial Software Engineer", "family": "industrial",
               "headline": "Industrial Software Engineer · WebSCADA, OPC UA & PLC Integration",
               "focus": ["Python", "SCADA", "WebSCADA", "OPC UA", "OPC", "Modbus", "FINS", "PLC", "21 CFR Part 11", "FastAPI", "Angular"]},
    "CV-004": {"name": "IIoT Engineer", "family": "iiot",
               "headline": "IIoT Engineer · Machine Data, OPC UA, Modbus & Python",
               "focus": ["IIoT", "OPC UA", "Modbus", "FINS", "PLC", "Python", "MySQL", "Docker", "FastAPI"]},
    "CV-005": {"name": "Full Stack Developer", "family": "fullstack",
               "headline": "Full Stack Developer · Angular/React, Node.js, Python",
               "focus": ["Angular", "React", "TypeScript", "JavaScript", "Node.js", "Express.js", "Python", "FastAPI", "MongoDB", "MySQL"]},
}

# Role families for ranking which roles fit you (title words, case-insensitive). Primary = your main targets.
ROLE_FAMILIES = {
    "backend": {"label": "Python / Backend Engineer", "primary": True,
                "words": ["backend", "back-end", "python", "fastapi", "django", "api"]},
    "general": {"label": "Software Engineer / Developer", "primary": True,
                "words": ["software engineer", "software developer", "softwareentwickler", "developer", "engineer"]},
    "fullstack": {"label": "Full Stack Developer", "primary": True,
                  "words": ["full stack", "full-stack", "fullstack", "angular", "react", "node", "frontend", "front-end"]},
    "industrial": {"label": "Industrial / Automation / SCADA / MES / OT Software", "primary": False,
                   "words": ["industrial", "automation", "scada", "mes", "ot ", "plc", "manufacturing", "automatisierung"]},
    "iiot": {"label": "IIoT / IoT Engineer", "primary": False, "words": ["iiot", "iot", "edge", "connectivity", "device"]},
}


def starting_profile() -> dict:
    """The CV used when the profile is first created: PROFILE_JSON / PROFILE_FILE if set, else Arpita's CV above.
    Only keys of DEFAULT_PROFILE are used; anything missing falls back to the default."""
    import json

    raw = settings.profile_json
    if not raw and settings.profile_file:
        with open(settings.profile_file, encoding="utf-8") as f:
            raw = f.read()
    if not raw:
        return DEFAULT_PROFILE
    custom = json.loads(raw)
    unknown = set(custom) - set(DEFAULT_PROFILE)
    if unknown:
        raise ValueError(f"PROFILE_JSON has unknown keys: {', '.join(sorted(unknown))}")
    profile = {**DEFAULT_PROFILE, **custom}
    profile["skills"] = [s if isinstance(s, dict) else {"name": s, "years": None} for s in profile["skills"]]
    return profile


def user_settings(profile) -> dict:
    """Default settings overwritten by whatever the user saved."""
    merged = {**DEFAULT_SETTINGS, **(profile.settings or {})}
    merged["weights"] = {**DEFAULT_SETTINGS["weights"], **(profile.settings or {}).get("weights", {})}
    return merged
