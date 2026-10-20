"""Is this the same vacancy we already saved (maybe from another website)?

Checks, strongest first:
1. same URL (tracking parameters removed) or same application URL
2. identical job description text (same hash)
3. same company + same city + similar title/description
"""
import math
import re
from collections import Counter
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.logic.jd_parser import detect_city, simplify

STOP_WORDS = set("a an and are as at be by for from has have in is it of on or our that the this to we with you your will und der die das mit fur wir sie ist von zu".split())


def clean_url(url: str | None) -> str | None:
    """Remove tracking parameters (utm_source, gh_src...) so the same link compares equal."""
    if not url:
        return None
    p = urlparse(url.strip())
    if not p.netloc:
        return url.strip()
    query = [(k, v) for k, v in parse_qsl(p.query) if not re.match(r"utm_|gh_src|ref$|source$|lever-source|trk|gclid", k, re.I)]
    return urlunparse(("https", p.netloc.lower().removeprefix("www."), p.path.rstrip("/") or "/", "", urlencode(sorted(query)), ""))


def company_key(name: str) -> str:
    """'ABC Deutschland GmbH & Co. KG' -> 'abc'"""
    s = simplify(name)
    s = re.sub(r"\b(gmbh|& co\.? kg|ag|se|kg|ug|inc\.?|ltd\.?|llc|group|deutschland|germany)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def title_words(title: str) -> set[str]:
    t = simplify(title)
    t = re.sub(r"\(.*?\)|\b(m|w|d|f)\s*/\s*(m|w|d|f)(\s*/\s*(m|w|d|f))?\b|\bsenior\b|\bjunior\b", " ", t)
    t = t.replace("full stack", "fullstack").replace("back-end", "backend").replace("front-end", "frontend")
    words = set(re.findall(r"[a-z0-9+#]+", t)) - STOP_WORDS
    return {"engineer" if w in ("developer", "entwickler", "programmer") else w for w in words}


def title_similarity(a: str, b: str) -> float:
    wa, wb = title_words(a), title_words(b)
    return len(wa & wb) / len(wa | wb) if wa and wb else 0.0


def text_similarity(a: str, b: str) -> float:
    """Cosine similarity of word counts (0 = different, 1 = identical)."""
    ca = Counter(w for w in re.findall(r"[a-z0-9+#]+", simplify(a)) if w not in STOP_WORDS)
    cb = Counter(w for w in re.findall(r"[a-z0-9+#]+", simplify(b)) if w not in STOP_WORDS)
    if not ca or not cb:
        return 0.0
    dot = sum(ca[w] * cb[w] for w in ca.keys() & cb.keys())
    return dot / (math.sqrt(sum(v * v for v in ca.values())) * math.sqrt(sum(v * v for v in cb.values())))


SPECIALISATIONS = {"frontend", "backend", "fullstack", "data", "devops", "qa", "embedded", "mobile"}


def is_same_job(new: dict, old: dict) -> tuple[bool, str]:
    """new/old: dicts with title, company, text, jd_hash, url, application_url, location (old text may be a function)."""
    if new.get("url") and clean_url(new["url"]) == clean_url(old.get("url")):
        return True, "same URL"
    if new.get("application_url") and clean_url(new["application_url"]) == clean_url(old.get("application_url")):
        return True, "same application URL"
    same_company = company_key(new["company"]) == company_key(old["company"])
    if new["jd_hash"] == old["jd_hash"] and (same_company or len(new["text"]) > 600):
        return True, "identical job description"
    if not same_company:
        return False, ""
    # "Frontend Engineer" and "Backend Engineer" at the same company are different jobs.
    sa, sb = title_words(new["title"]) & SPECIALISATIONS, title_words(old["title"]) & SPECIALISATIONS
    if sa and sb and not sa & sb:
        return False, ""
    # Same role in two different cities = two vacancies.
    ca, cb = detect_city(new.get("location")), detect_city(old.get("location"))
    if ca and cb and ca != cb:
        return False, ""
    titles = title_similarity(new["title"], old["title"])
    if titles < 0.25:
        return False, ""  # clearly different roles: don't even load the old description
    old_text = old["text"]() if callable(old["text"]) else old["text"]  # loaded lazily (database transfer)
    texts = text_similarity(new["text"], old_text)
    if titles >= 0.99 and texts >= 0.6:
        return True, "same company and title"
    if titles >= 0.5 and texts >= 0.8:
        return True, f"same company, similar title and description ({texts:.2f})"
    if texts >= 0.92:
        return True, f"same company, near-identical description ({texts:.2f})"
    return False, ""
