"""The 50 recruitment companies (user's list, 2026-10-19): the starting data of the Recruitment companies directory.

These are recruiters WORTH INVESTIGATING, not a verified list of agencies that hire from India or sponsor visas.
Nothing here is "verified": the app checks websites itself (services/agencies.py) and you confirm the rest.
Links checked 2026-10-19: Robert Half, Huxley, Morgan Philips and Korn Ferry pages from the original list returned 404 and were
replaced by working pages on the SAME official domain. Actief Personalmanagement and Unique Personalservice did not answer
(unique.de is an unrelated advertising agency, so it was NOT used).
`feed` = an official job API the app reads automatically (checked 2026-10-19); everything else is "manual".
"""

CATEGORIES = {
    "india": "India–Germany & international placement",
    "staffing": "International recruitment & staffing",
    "engineering": "Automotive, engineering & technology",
    "specialist": "Digital, consulting & specialist",
}

# (id, name, website, category, focus, industries, job families, aliases for matching job postings, feed)
_ROWS = [
    (1, "IndiaWorks", "https://india-works.de/en/kandidaten/", "india", "India–Germany recruitment",
     ["International placement"], ["Software engineering", "Engineering"], [], None),
    (2, "IndoFachkraft", "https://www.indofachkraft.de/en", "india", "International skilled professionals, IT and other sectors",
     ["International placement", "IT & software"], ["Software engineering", "IT support"], [], None),
    (3, "Velai", "https://velai.eu/", "india", "IT and software professionals",
     ["IT & software", "International placement"], ["Software engineering"], [], None),
    (4, "Mitraworks", "https://www.mitraworks.de/en/", "india", "IT careers and India–Germany recruitment",
     ["IT & software", "International placement"], ["Software engineering", "IT support"], [], None),
    (5, "Helm & Company", "https://helmco.de/recruiting-services", "india", "Engineering, science and IT",
     ["Engineering & industrial", "IT & software", "Life sciences & healthcare"], ["Engineering", "Software engineering"], ["helm & co", "helmco"], None),
    (6, "ExpertDash", "https://www.expertdash.de/en", "india", "IT recruitment for German businesses",
     ["IT & software"], ["Software engineering", "IT support"], [], None),
    (7, "i2GO Europe", "https://i2go-europe.de/", "india", "International skilled-worker recruitment",
     ["International placement"], ["Engineering", "Industrial & technical"], ["i2go"], None),
    (8, "Federal Employment Agency — ZAV", "https://www.arbeitsagentur.de/vor-ort/zav", "india", "Official international placement services",
     ["International placement", "Public sector"], ["Software engineering", "Engineering", "Healthcare"], ["zav", "zentrale auslands- und fachvermittlung"], None),
    (9, "Triple Win", "https://triple-win-programm.de/en/", "india", "International nursing recruitment",
     ["Life sciences & healthcare", "International placement"], ["Healthcare"], [], None),
    (10, "NORKA Roots", "https://norkaroots.org/", "india", "Overseas recruitment and international employment support",
     ["International placement"], ["Healthcare", "Engineering"], ["norka"], None),
    (11, "Hays", "https://www.hays.de/en/", "staffing", "IT, engineering, automotive, data and SAP",
     ["IT & software", "Engineering & industrial", "Automotive & mobility"], ["Software engineering", "Data & analytics", "SAP & ERP", "Engineering"], ["hays ag", "hays"], None),
    (12, "Michael Page", "https://www.michaelpage.de/", "staffing", "Finance, technology, marketing and engineering",
     ["Finance & banking", "IT & software", "Digital & marketing", "Engineering & industrial"], ["Finance & accounting", "Software engineering", "Marketing & e-commerce"], ["page personnel", "pagegroup"], None),
    (13, "Robert Walters", "https://www.robertwalters.de/en/home.html", "staffing", "Technology, banking, fintech and finance",
     ["IT & software", "Finance & banking"], ["Software engineering", "Finance & accounting"], [], None),
    (14, "Robert Half", "https://www.roberthalf.com/de/de", "staffing", "Finance, accounting, technology and business support",
     ["Finance & banking", "IT & software", "Office & commercial"], ["Finance & accounting", "Software engineering", "Office & admin"], [], None),
    (15, "Randstad Germany", "https://www.randstad.de/", "staffing", "IT, manufacturing, logistics and professional services",
     ["IT & software", "Engineering & industrial", "Logistics & retail"], ["Software engineering", "Industrial & technical", "Office & admin"], ["randstad deutschland", "randstad professional", "randstad"], None),
    (16, "Adecco Germany", "https://www.adecco.de/", "staffing", "Engineering, industrial and commercial recruitment",
     ["Engineering & industrial", "Office & commercial"], ["Engineering", "Industrial & technical", "Office & admin"], ["adecco"], None),
    (17, "Manpower Germany", "https://www.manpower.de/", "staffing", "Finance, engineering, office and professional roles",
     ["Finance & banking", "Engineering & industrial", "Office & commercial"], ["Finance & accounting", "Engineering", "Office & admin"], ["manpower", "manpowergroup"], None),
    (18, "Amadeus Fire", "https://www.amadeus-fire.de/", "staffing", "IT, finance, accounting and commercial roles",
     ["IT & software", "Finance & banking", "Office & commercial"], ["Software engineering", "Finance & accounting", "Office & admin"], [], None),
    (19, "DIS AG", "https://www.dis-ag.com/", "staffing", "IT, engineering and commercial recruitment",
     ["IT & software", "Engineering & industrial", "Office & commercial"], ["Software engineering", "Engineering", "Office & admin"], ["dis ag"], None),
    (20, "SThree", "https://www.sthree.com/", "staffing", "STEM, technology, engineering and life sciences",
     ["IT & software", "Engineering & industrial", "Life sciences & healthcare"], ["Software engineering", "Engineering"], [], None),
    (21, "Computer Futures", "https://www.computerfutures.com/de-de/", "staffing", "Software, cloud, cybersecurity and data",
     ["IT & software"], ["Software engineering", "Cloud & cybersecurity", "Data & analytics"], [], None),
    (22, "Huxley", "https://www.huxley.com/de-de/", "staffing", "Technology and financial services",
     ["IT & software", "Finance & banking"], ["Software engineering", "Finance & accounting"], [], None),
    (23, "Real Staffing", "https://www.realstaffing.com/", "staffing", "Life sciences, healthcare and specialist technical recruitment",
     ["Life sciences & healthcare"], ["Healthcare", "Engineering"], [], None),
    (24, "GULP", "https://www.gulp.de/", "staffing", "IT, engineering, projects and specialist contracting",
     ["IT & software", "Engineering & industrial"], ["Software engineering", "Project management", "Engineering"], ["gulp information services"], None),
    (25, "FERCHAU", "https://www.ferchau.com/de/en/applicants/career", "engineering", "Automotive, IT, software and engineering",
     ["Automotive & mobility", "IT & software", "Engineering & industrial"], ["Software engineering", "Embedded", "Engineering"], ["ferchau"], None),
    (26, "Brunel", "https://www.brunel.net/de-de/karriere", "engineering", "IT, engineering, energy and industrial projects",
     ["IT & software", "Engineering & industrial"], ["Software engineering", "Engineering", "Project management"], ["brunel gmbh"], None),
    (27, "Akkodis", "https://www.akkodis.com/de/karriere", "engineering", "Digital engineering, software, cloud and data",
     ["IT & software", "Engineering & industrial", "Automotive & mobility"], ["Software engineering", "Cloud & cybersecurity", "Data & analytics", "Embedded"], ["akkodis germany"], None),
    (28, "ALTEN Germany", "https://www.alten-germany.de/", "engineering", "Automotive, embedded software and electronics",
     ["Automotive & mobility", "Engineering & industrial", "IT & software"], ["Embedded", "Software engineering", "Engineering"], ["alten"], ("smartrecruiters", "alten")),
    (29, "Bertrandt", "https://www.bertrandt.com/karriere", "engineering", "Vehicle development, software and mobility engineering",
     ["Automotive & mobility", "Engineering & industrial"], ["Embedded", "Software engineering", "Engineering"], ["bertrandt ag"], None),
    (30, "Da Vinci Engineering", "https://www.davinci.de/en/find-a-job/", "engineering", "Automotive, software and technical project management",
     ["Automotive & mobility", "Engineering & industrial"], ["Software engineering", "Project management", "Engineering"], ["da vinci"], None),
    (31, "Vesterling", "https://www.vesterling.com/", "engineering", "IT, software and technical specialists",
     ["IT & software", "Engineering & industrial"], ["Software engineering", "Engineering"], ["vesterling ag"], None),
    (32, "Ratbacher", "https://www.ratbacher.de/", "engineering", "IT, software, SAP and data",
     ["IT & software"], ["Software engineering", "SAP & ERP", "Data & analytics"], [], None),
    (33, "duerenhoff", "https://www.duerenhoff.de/", "engineering", "SAP consulting and enterprise systems",
     ["IT & software", "Consulting & executive"], ["SAP & ERP"], ["dürenhoff"], None),
    (34, "YER Germany", "https://www.yer.de/", "engineering", "Engineering, technology and specialist recruitment",
     ["Engineering & industrial", "IT & software"], ["Engineering", "Software engineering"], ["yer deutschland"], None),
    (35, "PRIMEPEOPLE", "https://www.primepeople.de/", "engineering", "IT leadership, digital transformation and technology",
     ["IT & software", "Consulting & executive"], ["Executive & leadership", "Project management"], ["prime people"], None),
    (36, "CareerTeam", "https://careerteam.de/", "specialist", "Digital business, e-commerce, marketing and product",
     ["Digital & marketing", "Logistics & retail", "IT & software"], ["Marketing & e-commerce", "Product & digital"], ["careerteam"], ("smartrecruiters", "careerteam")),
    (37, "Avomind", "https://www.avomind.com/", "specialist", "Consulting, strategy and commercial recruitment",
     ["Consulting & executive"], ["Product & digital", "Executive & leadership"], [], None),
    (38, "JAC Recruitment Germany", "https://www.jac-recruitment.de/", "specialist", "International business, engineering and technology",
     ["Engineering & industrial", "IT & software", "International placement"], ["Engineering", "Software engineering"], ["jac recruitment"], None),
    (39, "Academic Work", "https://www.academicwork.com/", "specialist", "Graduates, early-career, IT and engineering roles; verify German coverage",
     ["IT & software", "Engineering & industrial"], ["Graduates & early career", "Software engineering", "Engineering"], [], None),
    (40, "DEKRA Arbeit", "https://www.dekra-arbeit.de/", "specialist", "Industrial, technical, administrative and commercial roles",
     ["Engineering & industrial", "Office & commercial"], ["Industrial & technical", "Office & admin"], ["dekra arbeit"], None),
    (41, "I.K. Hofmann", "https://www.hofmann.info/", "specialist", "Engineering, industrial, technical and office roles",
     ["Engineering & industrial", "Office & commercial"], ["Engineering", "Industrial & technical", "Office & admin"], ["i.k. hofmann", "hofmann personal"], None),
    (42, "persona service", "https://www.persona.de/", "specialist", "Commercial, industrial, technical and administrative jobs",
     ["Engineering & industrial", "Office & commercial"], ["Industrial & technical", "Office & admin"], [], None),
    (43, "TEMPTON", "https://www.tempton.de/", "specialist", "Industrial, technical and commercial staffing",
     ["Engineering & industrial", "Office & commercial"], ["Industrial & technical", "Office & admin"], [], None),
    (44, "Orizon", "https://www.orizon.de/", "specialist", "Engineering, technical, industrial and office recruitment",
     ["Engineering & industrial", "Office & commercial"], ["Engineering", "Industrial & technical", "Office & admin"], ["orizon gmbh"], None),
    (45, "Actief Personalmanagement", "https://www.actief-personalmanagement.de/", "specialist", "Engineering, production, technical and administrative roles",
     ["Engineering & industrial", "Office & commercial"], ["Engineering", "Industrial & technical", "Office & admin"], ["actief"], None),
    (46, "Unique Personalservice", "https://www.unique-personalservice.de/", "specialist", "Commercial, industrial and technical staffing",
     ["Engineering & industrial", "Office & commercial"], ["Industrial & technical", "Office & admin"], [], None),
    (47, "pluss Personalmanagement", "https://www.pluss.de/", "specialist", "Healthcare and specialist staffing",
     ["Life sciences & healthcare"], ["Healthcare"], [], None),
    (48, "Morgan Philips", "https://www.morganphilips.com/", "specialist", "Specialist and executive recruitment, finance and business",
     ["Consulting & executive", "Finance & banking"], ["Executive & leadership", "Finance & accounting"], ["morgan philips group"], None),
    (49, "Korn Ferry", "https://www.kornferry.com/de", "specialist", "Executive search and professional recruitment",
     ["Consulting & executive"], ["Executive & leadership"], [], None),
    (50, "Kienbaum", "https://www.kienbaum.com/", "specialist", "Executive search, management and HR consulting",
     ["Consulting & executive"], ["Executive & leadership"], ["kienbaum consultants"], None),
]

COUNTRY = {10: "India"}  # NORKA Roots is a Kerala (India) government agency; the rest are listed for Germany


def _registration_url(url: str) -> str | None:
    """The given link is the candidate page when it points below the home page (…/kandidaten/, …/career…)."""
    path = url.split("://", 1)[1].split("/", 1)[1] if url.count("/") > 3 else ""
    return url if any(w in path for w in ("kandidat", "career", "karriere", "job", "applicant", "recruiting", "zav")) else None


RECRUITMENT_COMPANIES = [
    {"seed_id": i, "name": name, "website_url": url, "candidate_registration_url": _registration_url(url),
     "country": COUNTRY.get(i, "Germany"), "recruitment_category": cat, "focus": focus,
     "industry_specializations": industries, "job_family_specializations": families, "aliases": aliases,
     "job_feed": f"{feed[0]}:{feed[1]}" if feed else None}
    for i, name, url, cat, focus, industries, families, aliases, feed in _ROWS
]
