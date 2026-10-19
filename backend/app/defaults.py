"""Starting profile (copied from Arpita's CV, kept in data/standard_cv.txt) and default settings.

Email, phone and visa need are not on the CV, so they are empty until you fill them in Settings.
Every application uses this one standard CV (logic/cv.py); there are no per-job CV versions.
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
        "Industrial Software Engineer with hands-on expertise in IIoT systems, WebSCADA platforms, and industrial "
        "protocol communication. Builds custom Python-based OPC servers, 21 CFR Part 11-compliant WebSCADA "
        "applications, OPC-UA tag management tools, and Windows service-packaged deployments for pharmaceutical and "
        "manufacturing environments. Proficient in Angular and FastAPI for full-stack industrial applications; "
        "experienced in leading junior engineers and delivering production-grade systems end-to-end. "
        "MSc Computer Science, University of Greenwich, London."
    ),
    "education": [  # degree | school | dates (newest first; see logic/cv.education_parts)
        "MSc Computer Science | Greenwich University, London, United Kingdom | January 2022 – January 2023",
        "Masters in Computer Applications | Gujarat Technological University, Ahmedabad, India | December 2015 – January 2018",
        "Bachelor of Computer Applications | Gujarat University, Ahmedabad, India | December 2012 – April 2015",
    ],
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
        "MySQL", "PostgreSQL", "REST APIs", "JWT", "RBAC", "AWS", "Agile", "Postman",
        "SCADA", "WebSCADA", "OPC", "OPC UA", "Modbus", "FINS", "PLC", "IIoT", "21 CFR Part 11",
        "PyInstaller", "Windows Services", "LabVIEW",
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
             "User management: group-level and user-level CRUD, multi-tier RBAC (operator, supervisor, admin), configurable security policy, change-password functionality and feature-level access-rights control.",
             "Machine registration and configuration: register machines, configure parameters, manage machine-level settings; settings module includes database backup and restore for administrators.",
             "Digital signature functionality — users digitally sign off critical actions (recipe approvals, batch releases) with credentials that are cryptographically recorded, fully meeting 21 CFR Part 11 electronic signature requirements.",
             "L2 LineSync audit module: tamper-evident log of all system and user actions, with electronic audit trails and data integrity controls for pharma and regulated manufacturing compliance.",
             "Packaged the FastAPI backend as a standalone Windows executable using PyInstaller and registered it as a persistent background service via NSSM — enabling single-click deployment on production-floor machines with no Python environment dependency.",
         ]},
        {"name": "OPC Server — Custom Industrial Data Gateway", "tech": "Python · Django · MySQL · OPC-UA · Modbus TCP/RTU · FINS Serial · FINS Ethernet",
         "description": "Open-source alternative to Kepware with pluggable protocol drivers",
         "skills": ["Python", "Django", "MySQL", "OPC", "OPC UA", "Modbus", "FINS", "PLC"],
         "bullets": [
             "Engineered a fully custom Python OPC server from scratch as a direct, open-source alternative to commercial OPC servers such as Kepware — delivering equivalent PLC connectivity and data acquisition capabilities at zero licensing cost.",
             "Implemented a pluggable, protocol-agnostic driver architecture with four production drivers: Modbus TCP/RTU, FINS Serial, FINS Ethernet and OPC-UA — allowing new device types to be onboarded by adding a driver module without touching core server logic.",
             "Reads live process data from PLCs through the driver layer and persists it into MySQL with a normalised schema supporting historical analysis, trend reporting and alarm logging.",
         ]},
        {"name": "Pulse Connect — OPC-UA Tag Browser & Config Generator", "tech": "Python · OPC-UA (asyncua) · Angular · FastAPI · MySQL",
         "description": "Browse OPC-UA tags and generate data-logging config",
         "skills": ["Python", "OPC UA", "Angular", "FastAPI", "MySQL"],
         "bullets": [
             "Full-stack industrial tool: connects to an OPC-UA server, browses the tag namespace, and lets engineers classify discovered tags as Process Tags or Alarm Tags through a guided UI — replacing a previously manual, error-prone process.",
             "Generates a structured config.ini file from the selected tag configuration, consumed directly by machine data-logging services with no further manual editing.",
             "Reduced commissioning time for new machines by enabling non-specialist engineers to configure data-logging end-to-end without editing raw configuration files.",
         ]},
        {"name": "Pharma Processing Machine — Configuration Tool", "tech": "Python · config.ini · Industrial Protocols · Pharma Manufacturing",
         "description": "Validated config.ini generator for pharma machines",
         "skills": ["Python"],
         "bullets": [
             "Python utility that generates config.ini files for pharma processing machines — specifying IP addresses, database connection settings and trigger bits required for machine data-logging services to initialise correctly.",
             "Eliminates manual INI file editing errors through a structured, validated configuration workflow; deployed in a regulated pharma manufacturing environment ahead of production runs.",
         ]},
        {"name": "Compression Machine Interface — Angular SCADA", "tech": "Angular · TypeScript · LabVIEW · Industrial SCADA Software",
         "description": "Operator screens on top of LabVIEW",
         "skills": ["Angular", "TypeScript", "SCADA", "LabVIEW"],
         "bullets": [
             "Angular-based SCADA application providing real-time operator screens for compression machines — machine status, process values, operator controls and parameter configuration.",
             "Defined the data interface contract between the Angular frontend and the LabVIEW backend layer, ensuring reliable state synchronisation and clean separation of concerns.",
             "Leading a junior developer on this project — component architecture, code review, integration testing approach and delivery planning.",
         ]},
        {"name": "Job Application — Job Discovery & Application Tracking Platform", "tech": "Python · FastAPI · SQLAlchemy · PostgreSQL · React · TypeScript · Tailwind CSS · Playwright · Vercel · Neon",
         "description": "Personal project: job discovery, CV matching and application tracking",
         "skills": ["Python", "FastAPI", "PostgreSQL", "React", "TypeScript", "REST APIs"],
         "bullets": [
             "Built a full-stack platform that collects jobs in Germany from the official job APIs of 75+ company career sites (Greenhouse, Lever, SmartRecruiters, Personio, Ashby, Workday) and public job feeds, with rate limiting and source-health monitoring.",
             "Implemented job normalisation, duplicate detection, version history for every job description, and freshness checks that hide closed postings.",
             "Developed rule-based CV-to-job matching (0–100 score from 8 weighted criteria) with requirement-level skill-gap analysis and language / visa checks.",
             "Built an application tracker (table, Kanban board, calendar) and a Word/PDF CV generator in German/EU format.",
             "Automated form filling on company application pages with Playwright, using only verified profile facts and stopping at CAPTCHAs or unknown questions; deployed on Vercel with Neon PostgreSQL; 48 automated tests.",
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
    "sources": ["greenhouse", "lever", "smartrecruiters", "personio", "ashby", "workday", "amazon", "recruiters", "arbeitnow",
                "berlinstartupjobs", "munichstartup", "startupcityhamburg"],
    # Job roles to search for. JOB_KEYWORDS in .env replaces this list on another computer.
    "search_queries": [k.strip() for k in settings.job_keywords.split(",") if k.strip()] or [
        # industrial / OT first (the CV's focus), then Python backend, full stack and general software roles
        "Industrial Software Engineer", "Automation Software Engineer",
        "Softwareentwickler Automatisierung", "SCADA Engineer", "SCADA Software Developer",
        "MES Developer", "MES Integration Engineer", "IIoT Engineer", "Industrial IoT Engineer", "IoT Software Engineer",
        "OT Software Engineer", "Manufacturing Software Engineer", "Python Developer", "Python Software Engineer",
        "Python Backend Engineer", "FastAPI Developer", "Django Developer", "Backend Engineer", "Backend Developer",
        "Full Stack Engineer", "Full Stack Developer", "Python Full Stack Developer", "Angular Developer",
        "TypeScript Developer", "Node.js Developer", "Software Engineer", "Mid Software Engineer", "Software Developer",
        "Softwareentwickler",
        # close IT roles that use the same skills (user, 2026-10-19)
        "Test Automation Engineer", "Application Support Engineer", "Business Systems Analyst",
    ],
    # Companies to follow = their own careers pages (the part of their job-board URL).
    # Checked 2026-10-07: each has software/engineering jobs in Germany. Banks/fintech, industrial/IoT, tech.
    "greenhouse_boards": ["celonis", "n26", "getyourguide", "contentful", "raisin", "commercetools", "helsing",
                          "isaraerospace", "sumup", "hellofresh", "flix", "staffbase", "parloa",
                          "traderepublicbank", "solarisbank", "adyen", "konux", "tulip", "trivago", "scout24",
                          "autoscout24", "doctolib", "wolt", "freenow", "kinexon"],  # boards.greenhouse.io/<board>
    "lever_companies": ["mobileye"],  # jobs.lever.co/<company>
    "smartrecruiters_companies": ["BoschGroup", "Continental", "DeliveryHero", "Sixt", "Brainlab", "enlyze",
                                  "alten", "careerteam"],  # last two: recruitment companies (ALTEN Germany, CareerTeam)  # jobs.smartrecruiters.com/<Company>
    "personio_companies": ["vivid", "ottonova", "ryd", "magazino", "wandelbots", "arculus", "envelio", "kiwigrid",
                           "node-energy", "stark", "1komma5grad", "tonies",
                           # industrial automation / energy software (checked 2026-10-19)
                           "softing", "meteocontrol", "wattfox", "twaice", "gridx", "entrix", "lumenaza"],  # <company>.jobs.personio.de
    # Recruitment agencies whose own job pages are read (sources.RECRUITER_SITES); found jobs show on "Recruiter jobs"
    "recruiter_sites": ["randstad", "brunel", "vesterling", "jac", "dekra", "persona", "tempton", "orizon", "hofmann"],
    "saved_searches": [],             # Jobs page: [{"name": "Munich industrial", "filters": {...}}]
    "goal_date": "2027-01-31",        # Germany job by January 2027 (Strategy page counts down to this)
    "study_hours_per_week": 15,       # time you can spend learning; the weekly plan splits it
    "ashby_boards": ["qonto", "moss", "upvest", "sereact", "enpal", "babbel", "n8n", "tacto", "langdock", "forto",
                     "deepl", "black-forest-labs", "robco", "workerbase"],
    # Big companies' own Workday career sites: host/tenant/site (checked 2026-10-19: each has jobs in Germany).
    # Not usable: Siemens (401), SAP (Cloudflare challenge), BMW/VW/Mercedes/Porsche/Allianz (own portals, no API).
    "workday_sites": ["db.wd3.myworkdayjobs.com/db/DBWebSite", "nvidia.wd5.myworkdayjobs.com/nvidia/NVIDIAExternalCareerSite",
                      "ag.wd3.myworkdayjobs.com/ag/Airbus", "accenture.wd103.myworkdayjobs.com/accenture/AccentureCareers",
                      "ms.wd5.myworkdayjobs.com/ms/External", "citi.wd5.myworkdayjobs.com/citi/2",
                      "autodesk.wd1.myworkdayjobs.com/autodesk/Ext", "hp.wd5.myworkdayjobs.com/hp/ExternalCareerSite",
                      "redhat.wd5.myworkdayjobs.com/redhat/jobs", "workday.wd5.myworkdayjobs.com/workday/Workday",
                      "statestreet.wd1.myworkdayjobs.com/statestreet/Global"],  # jobs.ashbyhq.com/<board>
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
