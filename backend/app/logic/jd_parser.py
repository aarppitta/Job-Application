"""Read a job description and pull out the facts we need.

Every function here takes plain text and returns plain values, so each one can be
tested on its own. `parse_job()` at the bottom runs all of them.
"""
import hashlib
import html
import re
import unicodedata
from datetime import date
from html.parser import HTMLParser

from app.logic.skills import find_skills

# ------------------------------------------------------------------ text helpers


class _HTMLToText(HTMLParser):
    BLOCKS = {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "tr"}

    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_starttag(self, tag, attrs):
        self.parts.append("\n- " if tag == "li" else "\n" if tag in self.BLOCKS else "")

    def handle_endtag(self, tag):
        if tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)


def html_to_text(value: str) -> str:
    if not value:
        return ""
    if "&lt;" in value and "<" not in value:  # Greenhouse sends escaped HTML
        value = html.unescape(value)
    if "<" in value:
        parser = _HTMLToText()
        parser.feed(value)
        value = "".join(parser.parts)
    value = re.sub(r"[ \t\xa0]+", " ", value)
    value = re.sub(r" *\n *", "\n", value)
    return re.sub(r"\n{3,}", "\n\n", value).strip()


def simplify(text: str) -> str:
    """Lowercase and remove accents: 'München' -> 'munchen'."""
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower().replace("ß", "ss")


def jd_hash(text: str) -> str:
    """Fingerprint of a JD. Same text (ignoring spaces/punctuation) = same hash."""
    return hashlib.sha256(re.sub(r"[^a-z0-9]+", " ", simplify(text)).strip().encode()).hexdigest()


def first_match(patterns: list[str], text: str) -> str | None:
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(0)
    return None


# ------------------------------------------------------------------ location / work mode

GERMAN_CITIES = [
    "berlin", "munich", "munchen", "hamburg", "frankfurt", "stuttgart", "dusseldorf", "cologne", "koln", "leipzig",
    "dresden", "nuremberg", "nurnberg", "karlsruhe", "mannheim", "hannover", "hanover", "bremen", "aachen", "augsburg",
    "bonn", "darmstadt", "dortmund", "essen", "erlangen", "freiburg", "heidelberg", "ingolstadt", "kiel", "mainz",
    "munster", "potsdam", "regensburg", "ulm", "wiesbaden", "wolfsburg", "wurzburg", "jena", "chemnitz", "kassel",
    "bielefeld", "braunschweig", "paderborn", "heilbronn", "walldorf", "garching", "bochum", "duisburg", "magdeburg",
]
OTHER_COUNTRIES = {
    "austria": "Austria", "vienna": "Austria", "switzerland": "Switzerland", "zurich": "Switzerland",
    "netherlands": "Netherlands", "amsterdam": "Netherlands", "poland": "Poland", "united kingdom": "United Kingdom",
    "london": "United Kingdom", "usa": "United States", "united states": "United States", "india": "India",
    "france": "France", "paris": "France", "spain": "Spain",
    "belgium": "Belgium", "brussels": "Belgium", "luxembourg": "Luxembourg", "ireland": "Ireland", "dublin": "Ireland",
    "portugal": "Portugal", "lisbon": "Portugal", "italy": "Italy", "milan": "Italy", "denmark": "Denmark",
    "copenhagen": "Denmark", "sweden": "Sweden", "stockholm": "Sweden", "finland": "Finland", "helsinki": "Finland",
    "estonia": "Estonia", "tallinn": "Estonia", "latvia": "Latvia", "lithuania": "Lithuania", "czech": "Czechia",
    "czechia": "Czechia", "prague": "Czechia", "slovakia": "Slovakia", "hungary": "Hungary", "budapest": "Hungary",
    "romania": "Romania", "bulgaria": "Bulgaria", "greece": "Greece", "croatia": "Croatia", "slovenia": "Slovenia",
    "cyprus": "Cyprus", "malta": "Malta", "warsaw": "Poland", "barcelona": "Spain", "madrid": "Spain",
    "europe": "Europe", "european union": "Europe", "eu": "Europe", "emea": "Europe", "eea": "Europe",
}
# Tina applies to Germany on site, and to remote jobs anywhere in the EU (or "Remote, Europe").
EU_COUNTRIES = {
    "Germany", "Austria", "Netherlands", "Poland", "France", "Spain", "Belgium", "Luxembourg", "Ireland", "Portugal",
    "Italy", "Denmark", "Sweden", "Finland", "Estonia", "Latvia", "Lithuania", "Czechia", "Slovakia", "Hungary",
    "Romania", "Bulgaria", "Greece", "Croatia", "Slovenia", "Cyprus", "Malta", "Europe",
}
REMOTE_WORDS = r"\b(remote|anywhere|work from home|home ?office|distributed|fully remote)\b"


def is_eu_remote(location: str | None, remote: bool = False) -> bool:
    """'Remote - Europe', 'Amsterdam (remote)', 'EU Remote', or any EU place flagged remote by the job board."""
    text = simplify(location or "")
    is_remote = remote or bool(re.search(REMOTE_WORDS, text))
    return is_remote and (detect_country(location) in EU_COUNTRIES)


def detect_country(location: str | None) -> str | None:
    text = simplify(location or "")
    if not text:
        return None
    if re.search(r"\b(germany|deutschland)\b", text) or any(re.search(rf"\b{c}\b", text) for c in GERMAN_CITIES):
        return "Germany"
    for word, country in OTHER_COUNTRIES.items():
        if re.search(rf"\b{word}\b", text):
            return country
    return None


def detect_city(location: str | None) -> str | None:
    text = simplify(location or "")
    return next((c for c in GERMAN_CITIES if re.search(rf"\b{c}\b", text)), None)


def detect_remote_type(text: str) -> str:
    t = simplify(text)
    if re.search(r"\bhybrid\b|\d days? (?:in|at) (?:the )?office", t):
        return "hybrid"
    if re.search(r"fully remote|100 ?% remote|remote[- ]first|\bremote\b|home ?office", t):
        return "remote"
    if re.search(r"on[- ]?site|vor ort", t):
        return "onsite"
    return "unknown"


def detect_employment_type(text: str) -> str | None:
    t = simplify(text)
    rules = [
        (r"werkstudent|working student", "Working student"),
        (r"\bintern(ship)?\b|praktikum", "Internship"),
        (r"freelanc|freiberuf|\bcontractor\b", "Contract"),
        (r"part[- ]time|teilzeit", "Part-time"),
        (r"full[- ]time|vollzeit|permanent|unbefristet", "Full-time"),
    ]
    return next((label for pattern, label in rules if re.search(pattern, t)), None)


# ------------------------------------------------------------------ experience / seniority / salary

WORD_NUMBERS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "ten": 10}


def extract_experience_years(text: str) -> float | None:
    """'3+ years of experience' -> 3. Takes the biggest requirement, ignores >15 (company history)."""
    values = []
    for m in re.finditer(r"(\d{1,2}(?:[.,]5)?)\s*(?:-\s*\d{1,2}\s*)?\+?\s*(?:years?|yrs?|jahre?n?)\b[^.\n]{0,80}?(?:experience|erfahrung)", text, re.I):
        values.append(float(m.group(1).replace(",", ".")))
    for m in re.finditer(r"\b(one|two|three|four|five|six|seven|eight|ten)\+?\s+(?:or more\s+)?years?\b[^.\n]{0,80}?experience", text, re.I):
        values.append(float(WORD_NUMBERS[m.group(1).lower()]))
    values = [v for v in values if 0 < v <= 15]
    return max(values) if values else None


def detect_seniority(title: str, years: float | None) -> str:
    t = simplify(title)
    rules = [
        (r"\b(head of|director)\b", "head"),
        (r"\b(principal|staff)\b", "principal"),
        (r"\b(lead|team ?lead|teamleiter|architect)\b", "lead"),
        (r"\b(senior|sr\.?)\b", "senior"),
        (r"\b(werkstudent|working student)\b", "working_student"),
        (r"\b(intern|praktikum)\b", "intern"),
        (r"\b(junior|jr\.?|graduate|entry[- ]level)\b", "junior"),
    ]
    for pattern, level in rules:
        if re.search(pattern, t):
            return level
    if years is not None and years >= 5:
        return "senior"
    return "mid"


def extract_salary(text: str) -> dict:
    """'€60,000 - €75,000' -> {'min': 60000, 'max': 75000, 'currency': 'EUR'}"""
    number = r"(\d{2,3}(?:[.,]\d{3})+|\d{2,3}\s?k)"
    m = re.search(rf"(?:€|eur)\s*{number}(?:\s*(?:-|–|to|bis)\s*(?:€|eur)?\s*{number})?|{number}\s*(?:-|–|to|bis)\s*{number}\s*(?:€|eur)", text, re.I)
    if not m:
        return {}
    nums = [g for g in m.groups() if g]

    def to_int(v: str) -> int:
        v = v.lower().replace(" ", "")
        return int(float(v[:-1]) * 1000) if v.endswith("k") else int(re.sub(r"[.,]", "", v))

    values = [to_int(n) for n in nums]
    if max(values) < 10000:
        return {}
    return {"min": min(values), "max": max(values), "currency": "EUR"}


# ------------------------------------------------------------------ visa sponsorship

SPONSOR_YES = [
    r"visa sponsorship", r"sponsor(?:ing)? (?:your |a |the )?(?:work )?visa", r"visa (?:support|assistance)",
    r"relocation (?:assistance|support|package|budget)", r"work permit (?:support|assistance)",
    r"(?:eu )?blue card", r"blaue karte", r"international (?:candidates|applicants) (?:are )?(?:welcome|encouraged)",
    r"relocate to germany",
]
SPONSOR_NO = [
    r"(?:must|need to|required to) (?:already )?(?:have|hold|possess) (?:a |an )?(?:valid )?(?:eu |eea |german )?(?:work(?:ing)? )?(?:permit|authori[sz]ation|right to work)",
    r"(?:no|not|unable to|cannot|can't|do not) (?:offer |provide )?(?:visa )?sponsor",
    r"sponsorship (?:is )?not (?:available|possible|offered)",
    r"eu (?:citizens?|nationals?) only",
    r"right to work in (?:germany|the eu) (?:is )?(?:required|mandatory)",
    r"(?:gultige|bestehende) arbeitserlaubnis",
]


def detect_sponsorship(text: str) -> tuple[str, list[str]]:
    """Returns ('confirmed' | 'unclear' | 'unlikely', quoted evidence).
    'unlikely' wins, because 'must already have a work permit' is a hard rule."""
    t = simplify(text)
    no = [m.group(0) for p in SPONSOR_NO for m in re.finditer(p, t)]
    if no:
        return "unlikely", no[:3]
    yes = []
    for p in SPONSOR_YES:
        for m in re.finditer(p, t):
            before = t[max(0, m.start() - 25): m.start()]
            if not re.search(r"\b(no|not|without|keine?)\b[\w\s]{0,12}$", before):  # skip "no relocation support"
                yes.append(m.group(0))
    if yes:
        return "confirmed", yes[:3]
    return "unclear", []


# ------------------------------------------------------------------ language

GERMAN_REQUIRED = [
    r"(?:fluent|excellent|very good|business[- ]fluent|native|proficient|strong)\s+(?:\w+\s+){0,3}german",
    r"german\s*(?:\(|:|-)?\s*(?:level\s*)?(?:c1|c2|b2)",
    r"german (?:language )?(?:skills )?(?:is |are )?(?:required|mandatory|a must|essential)",
    r"(?:fliessend|verhandlungssicher|sehr gut)\w*\s+(?:\w+\s+){0,2}deutsch",
    r"(?:sehr gute|gute|fliessende) deutschkenntnisse",
    r"deutsch\w*\s*(?:\(|:|-)?\s*(?:mindestens\s+)?(?:c1|c2|b2)",
    r"(?:communicat\w*|fluent|speak\w*)[^.\n]{0,80}\b(?:english and german|german and english)\b",
]
GERMAN_PLUS = [
    r"german (?:language )?(?:skills )?(?:is |would be )?(?:a (?:big )?plus|nice[- ]to[- ]have|an advantage|preferred|beneficial)",
    r"basic german", r"german (?:is )?not required", r"deutschkenntnisse (?:sind )?von vorteil",
]
GERMAN_WORDS = set("und der die das mit fur wir sie ist von zu den ein eine auf im bei oder sowie sind ihre unsere kenntnisse erfahrung".split())


def detect_language(text: str) -> tuple[str, list[str]]:
    """'english' | 'german_plus' (German is a bonus) | 'german_required' | 'german_jd' (JD written in German)."""
    t = simplify(text)
    plus = [m.group(0) for p in GERMAN_PLUS for m in re.finditer(p, t)]
    required = [m.group(0) for p in GERMAN_REQUIRED for m in re.finditer(p, t)]
    required = [r for r in required if not any(r in p or p in r for p in plus)]
    if required:
        return "german_required", required[:3]
    if plus:
        return "german_plus", plus[:3]
    words = re.findall(r"[a-z]+", t)
    if words and sum(w in GERMAN_WORDS for w in words) / len(words) > 0.08 and "english" not in t:
        return "german_jd", ["job description is written in German"]
    return "english", []


# ------------------------------------------------------------------ requirements & skills

REQUIREMENT_HEADINGS = r"^(requirements?|qualifications?|your profile|what you (?:bring|have|need)|who you are|you have|must[- ]haves?|about you|ihr profil|dein profil|anforderungen)\b"
NICE_HEADINGS = r"^(nice[- ]to[- ]haves?|bonus|preferred|good to have|plus|wunschenswert|von vorteil)\b"
OTHER_HEADINGS = r"^(what we offer|we offer|benefits|about us|responsibilities|your tasks|your role|wir bieten|deine aufgaben|ihre aufgaben)\b"
NICE_WORDS = r"\b(nice to have|a plus|bonus|advantage|preferred|ideally|von vorteil)\b"


def split_requirements(text: str) -> tuple[list[str], list[str]]:
    """Returns (must-have lines, nice-to-have lines) found under the usual headings."""
    must, nice, mode = [], [], None
    for raw in text.split("\n"):
        line = raw.strip().lstrip("-•* ").strip()
        if not line:
            continue
        low = simplify(line)
        if len(line) < 60 and re.match(NICE_HEADINGS, low):
            mode = "nice"
        elif len(line) < 60 and re.match(REQUIREMENT_HEADINGS, low):
            mode = "must"
        elif len(line) < 60 and re.match(OTHER_HEADINGS, low):
            mode = None
        elif mode == "must":
            (nice if re.search(NICE_WORDS, low) else must).append(line)
        elif mode == "nice":
            nice.append(line)
    return must, nice


def extract_job_skills(text: str, must: list[str], nice: list[str]) -> list[dict]:
    """[{'skill': 'Python', 'required': True, 'importance': 1.0}, ...]

    importance: 1.0 = listed in requirements, 0.5 = only mentioned elsewhere or "nice to have".
    """
    everywhere = find_skills(text)
    in_must = find_skills("\n".join(must))
    in_nice = find_skills("\n".join(nice))
    nice_sentences = set()
    for sentence in re.split(r"[.\n]", text):
        if re.search(NICE_WORDS, sentence, re.I):
            nice_sentences.update(find_skills(sentence))
    result = []
    for skill, count in sorted(everywhere.items(), key=lambda kv: -kv[1]):
        optional = (skill in in_nice or skill in nice_sentences) and skill not in in_must
        if optional or (must and skill not in in_must):
            importance = 0.5
        else:
            importance = min(1.0, 0.6 + 0.2 * count)
        result.append({"skill": skill, "required": not optional, "importance": importance})
    return result


INDUSTRIAL_WORDS = [
    r"scada", r"\bplcs?\b", r"\bopc\b", r"opc[\s-]?ua", r"modbus", r"\bmes\b", r"iiot", r"industrial", r"manufactur\w*",
    r"factory", r"production (?:line|plant)", r"\bot\b", r"industry 4\.0", r"\bhmi\b", r"process control",
    r"automation (?:systems?|technology|engineering)", r"automotive", r"energy", r"automatisierung", r"pharma\w*", r"\bgmp\b", r"life sciences",
]


def industrial_signals(text: str) -> list[str]:
    t = simplify(text)
    return [m.group(0) for p in INDUSTRIAL_WORDS if (m := re.search(p, t))]


# ------------------------------------------------------------------ scam / fraud

RISK_RULES = [
    (r"(?:application|registration|training|processing) fee", "Asks you to pay a fee"),
    (r"pay (?:for )?(?:your )?(?:own )?(?:training|equipment|visa)", "Asks you to pay money"),
    (r"\b(?:refundable )?deposit\b", "Mentions a deposit payment"),
    (r"bitcoin|\busdt\b|crypto(?:currency)? (?:payment|wallet)", "Crypto payment"),
    (r"bank (?:account|login) (?:details|number)|\biban\b|credit card", "Asks for bank details"),
    (r"(?:copy|scan) of (?:your )?(?:passport|id card)|passport number", "Asks for passport/ID up front"),
    (r"(?:contact|apply|message) (?:us )?(?:only )?(?:via|on) (?:telegram|whatsapp)", "Apply only via messenger app"),
    (r"earn (?:up to )?[€$]\s?\d{3,}\s?(?:per|a|/) ?(?:day|week)", "Unrealistic earnings promise"),
    (r"bit\.ly/|tinyurl\.com/", "Uses a link shortener"),
]


def detect_risks(text: str, application_url: str | None = None) -> list[str]:
    blob = simplify(f"{text} {application_url or ''}")
    return [label for pattern, label in RISK_RULES if re.search(pattern, blob)]


# ------------------------------------------------------------------ everything together


MONTH_NAMES = {name: i % 12 + 1 for i, name in enumerate(
    "january february march april may june july august september october november december "
    "januar februar märz april mai juni juli august september oktober november dezember".split())}
DEADLINE = re.compile(r"(?:application deadline|closing date|apply (?:by|before|until)|deadline|bewerbungsfrist|bewerbungsschluss"
                      r"|bewerbung(?:en)? bis(?: zum)?|bewerben sie sich bis(?: zum)?)\s*(?:is|ist|:|-)?\s*"
                      r"(?:(\d{1,2})[./](\d{1,2})[./](\d{2,4})|(\d{1,2})\.?\s+([a-zä]+)\s+(\d{4})|([a-z]+)\s+(\d{1,2}),?\s+(\d{4}))", re.I)


def find_deadline(text: str) -> str | None:
    """'Application deadline: 15.11.2026' / 'Bewerbungsfrist 30. November 2026' / 'apply by November 30, 2026' → '2026-11-30'."""
    m = DEADLINE.search(text)
    if not m:
        return None
    g = m.groups()
    try:
        if g[0]:
            day, month, year = int(g[0]), int(g[1]), int(g[2])
        elif g[3]:
            day, month, year = int(g[3]), MONTH_NAMES[g[4].lower()], int(g[5])
        else:
            day, month, year = int(g[7]), MONTH_NAMES[g[6].lower()], int(g[8])
        return date(year + 2000 if year < 100 else year, month, day).isoformat()
    except (KeyError, ValueError):
        return None


def parse_job(title: str, description: str, location: str | None, application_url: str | None = None) -> dict:
    """Run every extractor. Returns a dict that is stored on the Job row."""
    text = html_to_text(description)
    must, nice = split_requirements(text)
    visa, visa_evidence = detect_sponsorship(text)
    language, language_evidence = detect_language(text)
    years = extract_experience_years("\n".join(must) or text)
    work_mode = detect_remote_type(f"{title} {location or ''}")
    if work_mode == "unknown":
        work_mode = detect_remote_type(text)
    return {
        "text": text,
        "jd_hash": jd_hash(text or title),
        "country": detect_country(location) or detect_country(title),
        "remote_type": work_mode,
        "employment_type": detect_employment_type(f"{title}\n{text}"),
        "experience_required": years,
        "seniority": detect_seniority(title, years),
        "visa_status": visa,
        "language_requirement": language,
        "risk_flags": detect_risks(text, application_url),
        "description_incomplete": len(text) < 200,
        "parsed": {
            "requirements": must,
            "nice_to_have": nice,
            "skills": extract_job_skills(text, must, nice),
            "salary": extract_salary(text),
            "visa_evidence": visa_evidence,
            "language_evidence": language_evidence,
            "industrial_signals": industrial_signals(f"{title}\n{text}"),
            "deadline": find_deadline(text),
        },
    }
