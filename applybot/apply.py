"""Auto-apply bot: applies to your "Good match" jobs on the company's own application form.

Runs on your Mac (not on Vercel). It uses the app's API for the jobs, cover letter and "Mark as applied", uploads the ONE standard CV
(STANDARD_CV, made by standard_cv.py) to every application, and fills forms in Chrome with facts from your
profile + ~/.job-automation/answers.json only.

A job is marked as applied ONLY after the company's site confirms the submission.
Never: guesses an answer to a required question (the job goes to "needs you" instead), solves or bypasses a
CAPTCHA, ticks marketing / talent-pool boxes, applies twice, applies where the app says LEARN or SKIP.

  backend/venv/bin/python applybot/apply.py               # dry run: fills forms + screenshots, submits nothing
  backend/venv/bin/python applybot/apply.py --submit      # really apply (max --limit per run, default 10)
  backend/venv/bin/python applybot/apply.py --job 722     # only this job
"""
import argparse
import json
import re
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import certifi
import httpx
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

HOME = Path.home() / ".job-automation"
CONFIG, ANSWERS, LEDGER = HOME / "config.json", HOME / "answers.json", HOME / "applybot_log.json"
# The one CV sent with every application (answers.json "standard_cv" can point somewhere else).
STANDARD_CV = Path.home() / "Desktop/Resume/Standard CV/Arpita_Chaudhari_CV.pdf"

# ------------------------------------------------------------------ app API


class Api:
    def __init__(self, cfg: dict):
        self.http = httpx.Client(base_url=cfg["url"].rstrip("/"), timeout=120, verify=certifi.where())
        r = self.http.post("/api/auth/login", json={"username": cfg["username"], "password": cfg["password"]})
        if r.status_code != 200:
            sys.exit(f"Login to {cfg['url']} failed ({r.status_code}). Check {CONFIG}.")
        self.http.headers["Authorization"] = f"Bearer {r.json()['token']}"

    def call(self, method: str, path: str, **kw) -> httpx.Response:
        r = self.http.request(method, path, **kw)
        r.raise_for_status()
        return r

    def get(self, path: str, **params):
        return self.call("GET", path, params=params).json()

    def post(self, path: str, body: dict | None = None):
        return self.call("POST", path, json=body or {}).json()

    def patch(self, path: str, body: dict | None = None):
        return self.call("PATCH", path, json=body or {}).json()


# Tina's targeting (from the job title): junior/mid software roles only. These are hidden, never applied to.
OFF_PROFILE = [
    ("senior/lead", r"\b(senior|sr\.?|staff|lead|principal|head of|architect|director|manager)\b"),
    ("embedded/low-level", r"\b(embedded|firmware|low[- ]level|fpga|kernel|real[- ]time)\b|\bc\+\+|\brust\b"),
    ("Java/.NET/Go/iOS", r"\bjava\b(?!script)|\bkotlin\b|\.net\b|\bc#|\bgolang\b|\bgo\)|\bios\b|\bswift\b"),
    ("AI/ML-heavy", r"\b(ai|ml|machine learning|genai|llm)\b"),
    ("not development", r"\b(analyst|consultant|sales|support engineer|field application|technician|mechanic|hardware|recruiter)\b"),
]


def off_profile(title: str) -> str | None:
    for why, rx in OFF_PROFILE:
        if re.search(rx, title or "", re.I):
            return why
    return None


def candidates(api: Api, threshold: float) -> list[dict]:
    """Good matches (score ≥ threshold, not held back) you have not applied to, best first."""
    jobs, page = [], 1
    while True:
        data = api.get("/api/jobs", view="all", min_score=threshold, page=page)
        jobs += [j for j in data["items"] if not j["application_status"] and j["status"] == "QUALIFIED"]
        if page * 50 >= data["total"]:
            return jobs
        page += 1


# ------------------------------------------------------------------ your answers (facts only)


def load_answers(profile: dict) -> dict:
    """answers.json = facts that are not on the CV (salary, start date…). Created once from your profile."""
    if not ANSWERS.exists():
        ANSWERS.write_text(json.dumps({
            "_note": "Facts the bot may give on application forms. Edit freely. Empty = never answered. "
                     "custom: extra questions, e.g. {\"match\": \"notice period\", \"answer\": \"3 months\"} (match = regex).",
            "salary_eur_per_year": 70000, "salary_text": "EUR 70,000-72,000 per year",
            "earliest_start": "1 January 2027", "earliest_start_iso": "2027-01-01",
            "needs_visa_sponsorship": "Yes" if profile.get("visa_required") else "No",
            "authorized_to_work_in_germany": "No" if profile.get("visa_required") else "Yes",
            "living_in_germany": "No", "willing_to_relocate": "Yes",
            "german_level": "None", "english_level": "C1",
            "gender": "", "public_official": "No", "how_did_you_hear": "Job board",
            "birthday": "", "birthday_iso": "",
            "custom": [],
        }, indent=2))
    return json.loads(ANSWERS.read_text())


def posted_salary(job: dict) -> dict:
    """The salary range the job ad itself states (parsed by the app), as form answers; {} when none is given.
    Tina's rule: when the JD names a budget, answer within that budget instead of her default expectation."""
    s = (job.get("parsed") or {}).get("salary") or {}
    lo, hi = s.get("min"), s.get("max")
    if (s.get("currency") or "EUR").upper() != "EUR" or not lo or lo < 20000:  # monthly/hourly or non-EUR: don't guess
        return {}
    hi = hi if hi and hi >= lo else None
    mid = round((lo + hi) / 2, -3) if hi else lo
    text = f"EUR {lo:,.0f}-{hi:,.0f} per year" if hi else f"EUR {lo:,.0f} per year"
    return {"salary_eur_per_year": int(mid), "salary_text": text}


def facts(profile: dict, answers: dict, job: dict, letter: str) -> dict:
    name = profile["name"].split()
    location = profile.get("location") or ""
    exp = (profile.get("experience") or [{}])[0]
    worked_here = any(job["company"].lower()[:6] in (e.get("company") or "").lower() for e in profile.get("experience") or [])
    return {
        **answers, **posted_salary(job), "first": name[0], "last": " ".join(name[1:]), "full_name": profile["name"],
        "email": profile.get("email") or "", "phone": profile.get("phone") or "",
        "linkedin": profile.get("linkedin_url") or "", "github": profile.get("github_url") or "",
        "location": location, "city": location.split(",")[0].strip(), "country": location.split(",")[-1].strip(),
        "current_company": exp.get("company", ""), "current_title": exp.get("role", ""),
        "years": str(profile.get("years_experience") or ""), "worked_here": "Yes" if worked_here else "No",
        "letter": letter, "decline": "Prefer not to say", "consent_yes": "Yes",
    }


MARKETING = r"newsletter|marketing|career related information|future (opportunit|position|vacanc|role)|talent (pool|community)|job alert|retain my data|keep me|updates|zukünftig|talentpool|demographic|diversity|survey"
CONSENT = r"privacy|datenschutz|terms|agree|consent|einverstanden|zustimm|einwillig|acknowledge|confirm that|i have read|gelesen|declare|true,? correct|true and correct|wahr und richtig"
DEMOGRAPHIC = r"ethnic|race|disabil|veteran|sexual orientation|demographic|diversity|gender identity|hispanic|behinderung"
# "I consent to the use of AI for evaluating my candidacy": Tina answers No (checkboxes stay unticked)
AI_EVALUATION = (r"\b(ai|artificial intelligence|automated (decision|processing|systems?))\b.{0,80}"
                 r"(evaluat|assess|screen|review|candidacy|matching|bewert)|"
                 r"(evaluat|assess|screen|bewert).{0,60}\b(ai|artificial intelligence|künstliche intelligenz|ki)\b")
# "Which office are you applying to?": Tina wants the German offices (all of them when several can be picked)
OFFICE_Q = r"\boffice|standort|arbeitsort|which (city|location|site|hub)|preferred (location|city|site|office)|work location|location.{0,30}(apply|prefer|work from)"
GERMAN_PLACES = (r"germany|deutschland|berlin|munich|münchen|muenchen|hamburg|frankfurt|cologne|köln|koeln|düsseldorf|"
                 r"duesseldorf|stuttgart|chemnitz|leipzig|dresden|hannover|hanover|nuremberg|nürnberg|bremen|essen|dortmund|"
                 r"karlsruhe|mannheim|bonn|augsburg|freiburg|heidelberg|potsdam|regensburg|ulm|aachen|münster|wiesbaden|mainz|"
                 r"kiel|jena|garching|ottobrunn|ingolstadt|darmstadt|braunschweig|wolfsburg|erlangen|bielefeld|walldorf")
GERMAN_CITIES = ["Berlin", "Munich", "München", "Hamburg", "Frankfurt", "Cologne", "Köln", "Düsseldorf", "Stuttgart", "Chemnitz",
                 "Leipzig", "Dresden", "Hannover", "Nuremberg", "Karlsruhe", "Germany", "Deutschland"]
# (pattern on the question text, fact key); first match wins. The order matters ("first name" before "name").
RULES = [
    (MARKETING, "decline"),
    (CONSENT, "consent_yes"),
    (r"phone country|country code|vorwahl", "country"),
    (r"first name|given name|vorname|^first\b", "first"),
    (r"last name|family name|surname|nachname|^last\b", "last"),
    (r"e-?mail", "email"),
    (r"phone|telefon|mobile|handy|^number$", "phone"),
    (r"linkedin", "linkedin"),
    (r"github|portfolio|website|personal (site|page)", "github"),
    (r"salary|gehalt|compensation|vergütung|gehaltsvorstellung", "salary"),
    (r"birthday|date of birth|birth ?date|geburtsdatum|geburtstag|\bdob\b", "birthday"),
    (r"available|availability|start date|earliest|notice period|kündigungsfrist|eintritt|verfügbar|when can you start", "start"),
    (r"sponsor|visa", "needs_visa_sponsorship"),
    (r"authori[sz]ed to work|work permit|right to work|permission to work|arbeitserlaubnis|eligible to work|work authori[sz]ation", "authorized_to_work_in_germany"),
    (r"relocat|umzug|umziehen", "willing_to_relocate"),
    (r"(living|based|reside|wohn|leben|moving).*(germany|deutschland)", "living_in_germany"),
    (r"(worked|employed).*(before|previously)|previously (worked|employed)|ehemalige", "worked_here"),
    (r"public official|politically exposed|\bpep\b", "public_official"),
    (DEMOGRAPHIC, "decline"),
    (r"gender|geschlecht|pronoun|anrede|salutation", "gender"),
    (r"german|deutsch", "german_level"),
    (r"english|englisch", "english_level"),
    (r"hear about|how did you (find|learn)|where did you (find|see|hear)|aufmerksam|^source\b", "how_did_you_hear"),
    (r"current (company|employer)|arbeitgeber|\borg\b", "current_company"),
    (r"current (title|role|position)", "current_title"),
    (r"years of (professional )?(working )?experience|berufserfahrung", "years"),
    (r"(current )?(place of )?residence|wohnsitz", "location"),
    (r"cover letter|motivation|why (do|are|would) you|anschreiben|additional information|zusatzinformation|anything else|message|tell us about yourself|nachricht", "letter"),
    (r"\bfull name\b|^name\b|your name|vollständiger name", "full_name"),
    (r"country|land\b", "country"),
    (r"location|city|where are you (based|located)|wohnort|\bort\b|address|stadt", "location"),
]


def answer_for(q: str, kind: str, f: dict) -> str | None:
    text = q.lower()
    for c in f.get("custom") or []:
        if re.search(c["match"], q, re.I):
            return c["answer"]
    for pattern, key in RULES:
        if re.search(pattern, text):
            if key == "salary":
                return str(f["salary_eur_per_year"]) if kind == "number" else f["salary_text"]
            if key == "start":
                return f["earliest_start_iso"] if kind == "date" else f["earliest_start"]
            if key == "birthday":  # birthday_iso for date fields, birthday (as you wrote it) for text fields
                return (f.get("birthday_iso") if kind == "date" else f.get("birthday")) or None
            if key == "location" and kind == "combobox":
                return f["city"]
            if key == "location" and kind in ("select", "radio"):
                return f["country"]
            if key == "letter" and kind not in ("text", "textarea"):
                return None
            return f.get(key) or None
    return None


SYNONYMS = {"yes": ["yes", "ja", "true"], "no": ["no", "nein", "false"],
            "prefer not to say": ["prefer not", "rather not", "not to say", "keine angabe", "not specified", "decline", "do not wish", "don't wish", "möchte ich nicht"],
            "none": ["none", "no knowledge", "keine", "not at all", "no german", "a1", "a", "basic", "beginner", "grundkenntnisse"],
            "c1": ["c1", "fluent", "fließend", "professional", "verhandlungssicher", "advanced"],
            "job board": ["job board", "jobbörse", "arbeitnow", "online", "website", "internet", "other", "sonstige"],
            "female": ["female", "weiblich", "woman", "frau", "ms", "ms.", "mrs", "mrs."],
            "google": ["google", "google search", "search engine", "suchmaschine", "internet search", "internet", "online",
                       "website", "other", "sonstige"],
            "need sponsorship": ["need sponsorship", "require sponsorship", "requires sponsorship", "visa sponsorship", "sponsor",
                                 "need a visa", "require a visa", "visa required", "no work permit", "do not have", "don't have",
                                 "not authori", "non-eu", "outside the eu", "other"]}


def pick(options: list[str], answer: str) -> int | None:
    """Index of the option that means `answer` (exact first, then starts-with, then contains), else None.
    Catch-all words ("other", "sonstige") are only used when nothing more specific matches."""
    opts = [re.sub(r"\s+", " ", o).strip().lower() for o in options]
    wanted = SYNONYMS.get(answer.lower(), [answer.lower()])
    for words in ([w for w in wanted if w not in FALLBACK], [w for w in wanted if w in FALLBACK]):
        for test in (lambda o, w: o == w, lambda o, w: o.startswith(w + " ") or o.startswith(w + ",") or o.startswith(w + "/"),
                     lambda o, w: len(w) > 2 and w in o):
            for w in words:
                for i, o in enumerate(opts):
                    if o and test(o, w):
                        return i
    return None


FALLBACK = {"other", "sonstige", "sonstiges", "andere"}


# ------------------------------------------------------------------ the browser part

COLLECT = r"""(rootSel) => {
  const root = document.querySelector(rootSel) || document.body;
  const txt = e => ((e && (e.innerText || e.textContent)) || '').replace(/\s+/g, ' ').trim();
  const visible = e => { const r = e.getBoundingClientRect(), s = getComputedStyle(e); return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
  const isOptionLabel = x => x.querySelector('input') || (x.htmlFor && /radio|checkbox/.test((document.getElementById(x.htmlFor) || {}).type));
  const labelOf = el => {
    let t = '';
    if (el.id) { const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`); if (l) t = txt(l); }
    if (!t && el.closest('label')) t = txt(el.closest('label'));
    if (!t && el.getAttribute('aria-labelledby')) t = el.getAttribute('aria-labelledby').split(/\s+/).map(i => txt(document.getElementById(i))).join(' ');
    return t || el.getAttribute('aria-label') || '';
  };
  const questionOf = el => {
    const fs = el.closest('fieldset'); if (fs) { const lg = fs.querySelector('legend'); if (lg && txt(lg)) return txt(lg); }
    let n = el.parentElement;
    for (let i = 0; i < 7 && n && n !== document.body; i++, n = n.parentElement) {
      const lab = [...n.querySelectorAll('label,legend,[class*=label],[class*=Label],[class*=question],[class*=title],h3,h4')]
        .find(x => !x.contains(el) && txt(x) && !isOptionLabel(x) && !/^(yes|no|ja|nein)$/i.test(txt(x)));
      if (lab) return txt(lab);
    }
    return '';
  };
  const out = [];
  root.querySelectorAll('input,textarea,select').forEach((el, i) => {
    const type = (el.type || '').toLowerCase();
    if (['hidden', 'submit', 'button', 'search', 'image', 'reset'].includes(type) || el.disabled || el.name === 'g-recaptcha-response') return;
    let kind = el.tagName === 'SELECT' ? 'select' : el.tagName === 'TEXTAREA' ? 'textarea' : type === 'file' ? 'file' : type === 'radio' ? 'radio' : type === 'checkbox' ? 'checkbox' : type === 'number' ? 'number' : 'text';
    if (kind === 'text' && (el.getAttribute('role') === 'combobox' || el.getAttribute('aria-autocomplete') || /select__input/.test(el.className))) kind = 'combobox';
    if (kind === 'text' && (type === 'date' || /pick date|datum|dd\.mm|mm\/dd/i.test(el.placeholder || ''))) kind = 'date';
    if (kind === 'checkbox') {  // a checkbox shown as "Yes" / "No" buttons (Ashby)
      for (let n = 0, x = el.parentElement; n < 4 && x; n++, x = x.parentElement) {
        const b = [...x.querySelectorAll('button')].map(txt);
        if (b.some(t => /^(yes|ja)$/i.test(t)) && b.some(t => /^(no|nein)$/i.test(t))) { kind = 'yesno'; break; }
      }
    }
    const container = el.closest('label') || el.parentElement;
    if (!['file', 'yesno'].includes(kind) && !visible(el) && !(['radio', 'checkbox'].includes(kind) && container && visible(container))) return;  // invisible text field = honeypot: never fill
    if (!el.hasAttribute('data-ab')) el.setAttribute('data-ab', window.__ab = (window.__ab || 0) + 1);  // stable id, also after a re-collect
    i = el.getAttribute('data-ab');
    const label = labelOf(el), group = ['radio', 'checkbox', 'yesno'].includes(kind);
    let q = (group ? questionOf(el) : label || questionOf(el)) || el.placeholder || '';
    if (kind === 'checkbox' && !q) q = label;
    const req = el.required || el.getAttribute('aria-required') === 'true' || /\*|\(required\)|pflicht/i.test(kind === 'checkbox' ? label : q);
    out.push({idx: i, kind, type, name: el.name || el.id || '', q: q.replace(/\*|\(required\)|\(optional\)/gi, ' ').replace(/\s+/g, ' ').trim().slice(0, 300),
              label: label.slice(0, 200), required: !!req, value: kind === 'file' ? (el.files.length ? 'x' : '') : (group ? (el.checked ? 'x' : '') : (el.value || '')),
              options: kind === 'select' ? [...el.options].map(o => o.text) : []});
  });
  return out;
}"""

FIND_FORM = r"""() => {
  // only a form you can SEE counts (Recruitee & co. keep the form hidden behind an "Apply" tab until clicked)
  const shown = e => { const r = e.getBoundingClientRect(), s = getComputedStyle(e); return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
  const forms = [...document.querySelectorAll('form')].filter(f => shown(f) && f.querySelector('input[type=file], input[type=email], input[name*=email i]'));
  const score = f => f.querySelectorAll('input:not([type=hidden]),textarea,select').length + (f.querySelector('input[type=file]') ? 20 : 0);
  forms.sort((a, b) => score(b) - score(a));
  const best = forms.find(f => f.querySelector('input[type=file]')) || forms.find(f => score(f) >= 4);
  if (best) { best.setAttribute('data-ab-root', '1'); return true; }
  const email = document.querySelector('input[type=email], input[name*=email i]');
  return !!document.querySelector('input[type=file]') && !!email && shown(email);
}"""

CONFIRMED = re.compile(
    r"thank(s| you) for (your )?(appl|interest)|application (has been |was |is )?(received|submitted|sent|complete)|we('ve| have) received your application"
    r"|successfully (submitted|applied|sent)|vielen dank für (deine|ihre|dein|ihr) (bewerbung|interesse)|danke für (deine|ihre) bewerbung"
    r"|bewerbung (ist |wurde )?(erfolgreich|eingegangen|.{0,20}(gesendet|übermittelt))", re.I)
APPLY_LINK = re.compile(r"^(apply|apply now|apply for this (job|position)|jetzt bewerben|bewerben|zur bewerbung|apply on company (site|website)|company portal|i'?m interested)\b", re.I)
GREENHOUSE_JID = re.compile(r"gh_jid=(\d+)")


def greenhouse_form_url(job: dict, boards: list[str]) -> str | None:
    """Company careers page with ?gh_jid=… → the job's Greenhouse application page."""
    url = job.get("application_url") or ""
    if "greenhouse.io" in url:
        return url
    jid = (parse_qs(urlparse(url).query).get("gh_jid") or [None])[0]
    for board in boards if jid else []:
        if httpx.get(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{jid}", timeout=30, verify=certifi.where()).status_code == 200:
            return f"https://job-boards.greenhouse.io/{board}/jobs/{jid}"
    return None


def dismiss_cookies(page):
    for pattern in (r"^(reject all|decline( all)?|only (necessary|essential)|necessary only|nur (notwendige|erforderliche)|alle ablehnen|ablehnen)", r"^(accept( all)?|akzeptieren|alle akzeptieren|allow all|agree|zustimmen|ok)$"):
        btn = page.get_by_role("button", name=re.compile(pattern, re.I))
        if btn.count() and btn.first.is_visible():
            try:
                btn.first.click(timeout=3000)
                page.wait_for_timeout(800)
                return
            except PlaywrightError:
                pass


def open_form(page, url: str) -> bool:
    """Open the job and follow up to 2 "Apply" links until a page has an application form."""
    page.goto(url, timeout=60000, wait_until="domcontentloaded")
    for _ in range(3):
        page.wait_for_timeout(3500)
        dismiss_cookies(page)
        if page.evaluate(FIND_FORM):
            return True
        link = next((a for a in page.get_by_role("link").all() + page.get_by_role("button").all()
                     if a.is_visible() and APPLY_LINK.search((a.inner_text() or "").strip())), None)
        if link is None:
            return False
        href = link.get_attribute("href")
        if href and not href.startswith(("#", "javascript")):
            page.goto(link.evaluate("a => a.href"), timeout=60000, wait_until="domcontentloaded")
        else:
            tabs = len(page.context.pages)
            link.click()
            page.wait_for_timeout(2500)
            if len(page.context.pages) > tabs:  # "Apply" opened a new tab: continue there in this tab
                new = page.context.pages[-1]
                target = new.url
                new.close()
                page.goto(target, timeout=60000, wait_until="domcontentloaded")
    return False


def fill_form(page, f: dict, cv: Path, letter_file: Path) -> tuple[list, list]:
    """Fill every field we have a fact for. Returns (filled [(question, answer)], unanswered required questions)."""
    root = "[data-ab-root]"
    fields = page.evaluate(COLLECT, root)
    filled, missing, done_groups, cv_done = [], [], set(), False
    for fld in fields:
        loc = page.locator(f'[data-ab="{fld["idx"]}"]')
        if not loc.count():  # the site re-drew this field (e.g. after choosing a country): find it again
            again = next((x for x in page.evaluate(COLLECT, root) if (x["name"], x["kind"]) == (fld["name"], fld["kind"]) and fld["name"]), None)
            if again is None:
                if fld["required"]:
                    missing.append(f'{fld["q"]} (field disappeared)')
                continue
            loc = page.locator(f'[data-ab="{again["idx"]}"]')
        kind, q = fld["kind"], fld["q"]
        if kind != "file" and not (fld["required"] or kind in ("radio", "yesno", "checkbox")) and re.search(DEMOGRAPHIC + r"|gender|geschlecht|pronoun", q, re.I):
            continue  # optional diversity questions: leave empty
        key_text = f'{q} {fld["name"].replace("_", " ").replace("[", " ").replace("]", " ")}'
        if kind in ("select", "radio", "checkbox", "combobox") and re.search(OFFICE_Q, q or "", re.I):
            try:
                chosen = choose_german_offices(page, loc, fld, fields, done_groups)
            except PlaywrightError:
                chosen = None
            if chosen:
                filled.append((q, chosen))
                continue  # no German option: fall through to the normal answer (or "needs you")
        try:
            if kind == "file":
                if re.search(r"cover|anschreiben|motivation", key_text, re.I):
                    which = letter_file
                elif re.search(r"autofill|auto-fill|parse", key_text, re.I):
                    continue  # "autofill from resume" would overwrite our answers
                elif not cv_done and (re.search(r"resume|\bcv\b|lebenslauf|curriculum", key_text, re.I)
                                      or not re.search(r"reference|zeugnis|certificat|other|sonstig|transcript|photo|foto|portfolio|work sample", key_text, re.I)):
                    which, cv_done = cv, True
                else:
                    continue  # extra uploads (references, certificates…): leave empty
                loc.set_input_files(str(which))
                filled.append((q or "file", which.name))
                continue
            if kind in ("radio", "yesno") or (kind == "checkbox" and sum(1 for x in fields if x["name"] == fld["name"] and fld["name"]) > 1):
                group = fld["name"] or q
                if group in done_groups:
                    continue
                done_groups.add(group)
                members = [x for x in fields if (x["name"] or x["q"]) == group]
                answer = answer_for(q, kind, f)
                if kind == "yesno":
                    box = loc.locator("xpath=ancestor::*[.//button][1]")
                    i = pick(["Yes", "No"], answer) if answer else None
                    if i is not None:
                        box.get_by_role("button", name=re.compile(rf"^({'yes|ja' if i == 0 else 'no|nein'})$", re.I)).first.click()
                        filled.append((q, answer))
                    elif fld["required"]:
                        missing.append(q)
                    continue
                i = pick([m["label"] for m in members], answer) if answer else None
                if i is not None:
                    page.locator(f'[data-ab="{members[i]["idx"]}"]').check(force=True)
                    filled.append((q, members[i]["label"]))
                elif any(m["required"] for m in members) and not any(m["value"] for m in members):
                    missing.append(q or group)
                continue
            if kind == "checkbox":
                text = f'{fld["label"]} {q}'
                if re.search(MARKETING, fld["label"] or q, re.I):
                    if fld["required"]:
                        missing.append(f"{text[:120]} (marketing/data box: never ticked)")
                    continue
                if re.search(AI_EVALUATION, f'{fld["label"]} {q}', re.I):  # Tina says No to AI screening
                    if fld["required"]:
                        missing.append(f"{text[:120]} (AI-evaluation consent: you said No)")
                    continue
                if re.search(CONSENT, fld["label"] or q, re.I):
                    check_box(loc)
                    filled.append((fld["label"][:80] or q[:80], "checked"))
                    continue
                answer = answer_for(fld["label"] or q, kind, f)
                if answer and answer.lower() in ("yes", "ja"):
                    check_box(loc)
                    filled.append((text[:80], "Yes"))
                elif not answer and fld["required"]:
                    missing.append(text[:120])
                continue
            if fld["value"] and kind != "select":
                continue  # already filled by the site
            answer = answer_for(q or key_text, kind, f) or answer_for(key_text, kind, f)
            if kind == "select":
                i = pick(fld["options"], answer) if answer else None
                if i is None and fld["required"] and re.search(r"gender|geschlecht|anrede|" + DEMOGRAPHIC, q, re.I):
                    i = pick(fld["options"], "prefer not to say")
                if i is not None and i > 0 or (i == 0 and fld["options"][0].strip()):
                    loc.select_option(index=i)
                    filled.append((q, fld["options"][i]))
                elif fld["required"] and not (fld["value"] and loc.evaluate("e => e.selectedIndex > 0")):
                    missing.append(q)
                continue
            if answer is None:
                if fld["required"]:
                    missing.append(q or fld["name"])
                continue
            if kind == "combobox":
                if not choose_combobox(page, loc, answer):
                    if fld["required"]:
                        missing.append(q)
                    continue
            elif kind == "date":
                # native <input type=date> takes ISO; date-picker text boxes take MM/DD/YYYY (Greenhouse/Lever style)
                iso = re.fullmatch(r"\d{4}-\d{2}-\d{2}", answer)
                loc.fill(answer if fld["type"] == "date" or not iso else datetime.strptime(answer, "%Y-%m-%d").strftime("%m/%d/%Y"))
                loc.press("Enter")
            else:
                loc.fill(answer)
            filled.append((q, answer if len(answer) < 80 else answer[:77] + "…"))
        except PlaywrightError as e:
            if fld["required"]:
                missing.append(f"{q} (could not fill: {str(e).splitlines()[0][:80]})")
    answered = [fq for fq, _ in filled if fq]
    return filled, [m for m in missing if not any(m.startswith(fq) for fq in answered)]  # a field shown twice counts once


def check_box(loc) -> None:
    """Check a checkbox; falls back to a plain click for custom-styled (non-native) checkbox widgets."""
    try:
        loc.check(force=True, timeout=3000)
    except PlaywrightError:
        if not loc.is_checked():
            loc.click(force=True)


def choose_german_offices(page, loc, fld: dict, fields: list[dict], done_groups: set) -> str | None:
    """Office/location pickers: choose the German office(s); every German one when several may be selected.
    Returns what was chosen, or None when the field offers no German place."""
    kind = fld["kind"]
    if kind == "select":
        hits = [i for i, o in enumerate(fld["options"]) if (i > 0 or o.strip()) and re.search(GERMAN_PLACES, o, re.I)]
        if not hits:
            return None
        if loc.evaluate("e => e.multiple"):
            loc.select_option(index=hits)
            return ", ".join(fld["options"][i] for i in hits)
        loc.select_option(index=hits[0])
        return fld["options"][hits[0]]
    if kind in ("radio", "checkbox"):
        group = fld["name"] or fld["q"]
        members = [x for x in fields if (x["name"] or x["q"]) == group]
        hits = [m for m in members if re.search(GERMAN_PLACES, m["label"] or "", re.I)]
        if not hits:
            return None
        done_groups.add(group)
        if kind == "radio":
            hits = hits[:1]
        for m in hits:
            box = page.locator(f'[data-ab="{m["idx"]}"]')
            box.check(force=True) if kind == "radio" else check_box(box)
        return ", ".join(m["label"] for m in hits)
    if kind == "combobox":
        multi = loc.evaluate("e => e.getAttribute('aria-multiselectable') === 'true' || !!e.closest('[class*=\"multi\" i]')")
        picked = []
        for city in GERMAN_CITIES:
            if choose_combobox(page, loc, city):
                picked.append(city)
                if not multi:
                    break
        return ", ".join(picked) or None
    return None


def choose_combobox(page, loc, answer: str) -> bool:
    """Type into a search-select and click the option that matches `answer`."""
    loc.click()
    loc.fill(answer)
    page.wait_for_timeout(1500)
    options = page.locator("[role=option]:visible")
    texts = [t.strip() for t in options.all_inner_texts()]
    i = pick(texts, answer) if texts else None
    if i is None and texts and len(answer) > 3:
        i = next((n for n, t in enumerate(texts) if t.lower().startswith(answer.lower()[:4])), None)
    if i is None:  # the typed text filtered every option away: look at the full list and match by meaning (SYNONYMS)
        loc.fill("")
        page.wait_for_timeout(800)
        texts = [t.strip() for t in options.all_inner_texts()]
        i = pick(texts, answer) if texts else None
    if i is None:
        loc.fill("")
        page.keyboard.press("Escape")
        return False
    options.nth(i).click()
    return True


def captcha_shown(page) -> bool:
    for sel in ('iframe[src*="recaptcha"][src*="bframe"]', 'iframe[src*="hcaptcha"][title*="challenge" i]', 'iframe[title*="challenge" i]', "#cf-challenge-running"):
        loc = page.locator(sel)
        if any(loc.nth(i).is_visible() for i in range(loc.count())):
            box = loc.first.bounding_box()
            if box and box["height"] > 100:
                return True
    return False


def submit(page) -> tuple[str, str]:
    """Click submit and wait for the site's confirmation. → ("applied" | "captcha" | "failed", detail)"""
    before_url, before_ok = page.url, bool(CONFIRMED.search(page.inner_text("body")))
    root = page.locator("[data-ab-root]")
    scope = root if root.count() else page
    button = scope.locator("button[type=submit]:visible, input[type=submit]:visible")
    if not button.count():
        button = scope.get_by_role("button", name=re.compile(r"submit|send|apply|absenden|senden|bewerb", re.I))
    if not button.count():
        return "failed", "no submit button found"
    button.last.click()
    for _ in range(40):
        page.wait_for_timeout(1000)
        if captcha_shown(page):
            return "captcha", "the site showed a CAPTCHA (never bypassed)"
        body = page.inner_text("body") if page.locator("body").count() else ""
        if (CONFIRMED.search(body) and not before_ok) or (page.url != before_url and re.search(r"confirm|thank|success|danke|submitted", page.url, re.I)):
            return "applied", (CONFIRMED.search(body) or re.search(r".+", page.url)).group(0)[:120]
    errors = page.locator("[role=alert]:visible, [aria-invalid=true]:visible, .error:visible, [class*=error]:visible").all_inner_texts()
    return "failed", "no confirmation; " + ("; ".join(e.strip() for e in errors if e.strip())[:300] or "the form did not say why")


# ------------------------------------------------------------------ one job


def apply_one(api: Api, browser, job: dict, profile: dict, answers: dict, boards: list[str], really: bool, shots: Path, cv: Path) -> dict:
    result = {"job_id": job["id"], "title": job["title"], "company": job["company"], "score": job.get("ats_score"),
              "url": job.get("application_url") or job.get("source_url"), "at": datetime.now().isoformat(timespec="seconds")}
    decision = api.get(f"/api/jobs/{job['id']}/analysis")["recommendation"]
    if decision["decision"] != "APPLY":
        return {**result, "result": "skipped", "detail": f"app says {decision['label']}"}
    url = greenhouse_form_url(job, boards) if job["source"] == "greenhouse" else result["url"]
    if not url:
        return {**result, "result": "needs_you", "detail": "no application link"}
    letter = api.post(f"/api/jobs/{job['id']}/cover-letter")["text"]
    tmp = Path(tempfile.mkdtemp(prefix="applybot-"))
    from letter_pdf import write_letter_pdf  # cover letters go out as PDF (same layout everywhere), like the CV
    who = re.sub(r"[^A-Za-z0-9]+", "_", profile["name"]).strip("_")
    company = re.sub(r"[^A-Za-z0-9]+", "_", job["company"]).strip("_")[:40] or "Company"
    letter_file = write_letter_pdf(letter, tmp / f"{who}_Cover_Letter_{company}.pdf", browser.browser_type)

    context = browser.new_context(locale="en-US", viewport={"width": 1280, "height": 1000})
    page = context.new_page()
    page.set_default_timeout(10000)
    shot = shots / f"{datetime.now():%Y%m%d-%H%M}_{job['id']}.png"
    try:
        if not open_form(page, url):
            return {**result, "result": "needs_you", "detail": f"no application form found: the job may be closed, or the site needs you (apply here: {page.url})"}
        result["form_url"] = page.url
        if page.locator("input[type=password]:visible").count():
            return {**result, "result": "needs_you", "detail": "this site needs an account/login"}
        filled, missing = fill_form(page, facts(profile, answers, {**job, "parsed": api.get(f"/api/jobs/{job['id']}").get("parsed")},
                                                letter), cv, letter_file)
        result["answers"] = filled
        if not any(name == cv.name for _, name in filled):
            missing.append("CV upload field not found")
        if not any(answer == profile.get("email") for _, answer in filled):
            missing.append("email field not found or not visible (the form may be hidden behind a button)")
        page.screenshot(path=str(shot), full_page=True)
        result["screenshot"] = str(shot)
        if missing:
            return {**result, "result": "needs_you", "detail": "questions without a known answer: " + " | ".join(dict.fromkeys(missing)),
                    "missing": list(dict.fromkeys(missing))}
        if not really:
            return {**result, "result": "dry_run", "detail": "form filled, not submitted (run with --submit)"}
        outcome, detail = submit(page)
        page.screenshot(path=str(shot), full_page=True)
        if outcome == "applied":
            app = api.post(f"/api/jobs/{job['id']}/applied", {"cover_letter": letter})
            api.call("PATCH", f"/api/applications/{app['id']}",
                     json={"notes": f"Applied automatically by the apply bot on {datetime.now():%Y-%m-%d %H:%M} via {page.url} with the standard CV ({cv.name}). Site said: {detail}"})
        return {**result, "result": "applied" if outcome == "applied" else ("needs_you" if outcome == "captcha" else "failed"), "detail": detail}
    except PlaywrightError as e:
        return {**result, "result": "failed", "detail": str(e).splitlines()[0][:200]}
    finally:
        context.close()


# ------------------------------------------------------------------ main


def job_key(job: dict) -> str:
    """The job's link (same in the local and the live app, unlike the job id): the log key that prevents applying twice."""
    url = urlparse(job.get("application_url") or job.get("source_url") or f"job-{job['id']}")
    jid = parse_qs(url.query).get("gh_jid")
    return f"{url.netloc.lower().removeprefix('www.')}{url.path.rstrip('/')}" + (f"?gh_jid={jid[0]}" if jid else "")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--submit", action="store_true", help="really submit applications (default: dry run)")
    ap.add_argument("--limit", type=int, default=10, help="max jobs to try per run (default 10)")
    ap.add_argument("--job", type=int, action="append", help="only these job ids")
    ap.add_argument("--retry", action="store_true", help="also retry jobs that needed you / failed before")
    ap.add_argument("--headless", action="store_true", help="no browser window (sites trust it less)")
    ap.add_argument("--config", default=str(CONFIG), help=f"app login (default {CONFIG})")
    args = ap.parse_args()

    HOME.mkdir(exist_ok=True)
    api = Api(json.loads(Path(args.config).read_text()))
    profile, settings = api.get("/api/profile"), api.get("/api/settings")
    if not (profile.get("email") and profile.get("phone")):
        sys.exit("Set your email and phone in the app's Settings first.")
    answers = load_answers(profile)
    if not answers.get("standard_cv"):  # your CV changed in the app (My CV page)? rebuild the PDF first
        from standard_cv import build
        build(api, only_if_changed=True)
    cv = Path(answers.get("standard_cv") or STANDARD_CV).expanduser()
    if not cv.exists():
        sys.exit(f"Standard CV not found: {cv}. Run: backend/venv/bin/python applybot/standard_cv.py")
    ledger = json.loads(LEDGER.read_text()) if LEDGER.exists() else {}
    if args.job:
        jobs = [api.get(f"/api/jobs/{j}") for j in args.job]
        jobs = [j for j in jobs if not j["application_status"]]
    else:
        jobs = [j for j in candidates(api, settings["min_score"]) if args.retry or job_key(j) not in ledger]
        off = [(j, why) for j in jobs if (why := off_profile(j["title"]))]
        for j, why in off:   # Tina's targeting rules: hide instead of applying
            print(f"  skip (off-profile: {why}): {j['company']} · {j['title']}")
            try:
                api.patch(f"/api/jobs/{j['id']}", {"dismissed": True})
            except Exception:
                pass
        jobs = [j for j in jobs if not off_profile(j["title"])]
    jobs = [j for j in jobs if (ledger.get(job_key(j)) or {}).get("result") != "applied"]  # never twice, local or live app
    shots = HOME / "screenshots"
    shots.mkdir(exist_ok=True)

    results = []
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=args.headless)
        except PlaywrightError:
            browser = p.chromium.launch(headless=args.headless)
        for job in jobs:
            if len([r for r in results if r["result"] != "skipped"]) >= args.limit:
                break
            res = apply_one(api, browser, job, profile, answers, settings.get("greenhouse_boards", []), args.submit, shots, cv)
            results.append(res)
            print(f"[{res['result']:>9}] {job['company']} · {job['title']} (#{job['id']}): {res.get('detail', '')}", flush=True)
            if args.submit:  # a dry run never blocks a later real run
                # re-read before writing: entries added meanwhile (e.g. jobs you applied to by hand) must not be lost
                ledger = {**ledger, **(json.loads(LEDGER.read_text()) if LEDGER.exists() else {})}
                ledger[job_key(job)] = {k: res.get(k) for k in ("job_id", "company", "title", "result", "detail", "at", "form_url")}
                LEDGER.write_text(json.dumps(ledger, indent=1))
            time.sleep(3)
        browser.close()

    (HOME / "reports").mkdir(exist_ok=True)
    report = HOME / "reports" / f"{datetime.now():%Y-%m-%d_%H%M}.json"
    report.write_text(json.dumps(results, indent=1, ensure_ascii=False))
    counts = {k: sum(1 for r in results if r["result"] == k) for k in ("applied", "dry_run", "needs_you", "failed", "skipped")}
    print("\nSUMMARY " + " · ".join(f"{k}: {v}" for k, v in counts.items() if v) + f"  (report: {report})")
    for r in results:
        if r["result"] in ("needs_you", "failed"):
            print(f"  NEEDS YOU: {r['company']} · {r['title']}: {r['detail']}  {r.get('form_url') or r['url']}")


if __name__ == "__main__":
    main()
