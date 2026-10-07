"""Short pitches to a recruiter about one job. YOU send them (copy/paste); the app never sends anything.

Three versions, all built only from your CV:
- note:    LinkedIn connection request, max 300 characters (LinkedIn's limit)
- message: longer LinkedIn message
- email:   subject + body
"""
from urllib.parse import quote

from app.logic.writer import INDUSTRIAL, _what_i_do

LINKEDIN_NOTE_LIMIT = 300


def _top_skills(profile, matched: list[str], n: int) -> list[str]:
    mine = [s["name"] for s in profile.skills]
    ordered = [s for s in matched if s in INDUSTRIAL] + [s for s in matched if s not in INDUSTRIAL]
    return (ordered or mine)[:n]


def write_pitch(profile, job, matched: list[str], contact_name: str | None, applied: bool) -> dict:
    hi = f"Hi {contact_name.split()[0]}," if contact_name and contact_name.strip() else "Hi,"
    title = " ".join(job.title.split())
    first = profile.name.split()[0]
    interest = f"I applied for the {title} role" if applied else f"I'm interested in the {title} role"
    relocating = "" if "germany" in (profile.location or "").lower() else " and relocating to Germany"

    # LinkedIn connection note: shorten until it fits 300 characters
    note = ""
    for n_skills in (4, 3, 2, 1):
        skills = ", ".join(_top_skills(profile, matched, n_skills))
        note = (f"{hi} I'm an {profile.headline.split('·')[0].strip() if profile.headline else 'software engineer'} "
                f"({skills}){relocating}. {interest} at {job.company} and would love to connect. Thanks, {first}")
        if len(note) <= LINKEDIN_NOTE_LIMIT:
            break
    note = note[:LINKEDIN_NOTE_LIMIT]

    current = (profile.experience or [None])[0]
    now = f"I currently work as {current['role']} at {current['company']}" if current else "I currently work"
    message = (f"{hi}\n\n{interest} at {job.company}. {now}, building {_what_i_do(profile, job, matched)}.\n\n"
               f"{'I am relocating to Germany and ' if relocating else ''}I would be glad to talk about whether my background fits the team. "
               f"My CV is attached / on my profile.\n\nBest regards,\n{profile.name}")
    subject = f"{title} – {profile.name}"
    signature = "\n".join(x for x in (profile.email, profile.phone, profile.linkedin_url) if x)
    email = message.replace(f"Best regards,\n{profile.name}", f"Best regards,\n{profile.name}\n{signature}".rstrip())
    return {"note": note, "note_length": len(note), "message": message, "email_subject": subject, "email_body": email}


def search_links(company: str, city: str | None) -> dict:
    """Search pages YOU open on LinkedIn / XING to find the company's recruiters (no scraping)."""
    where = f" {city}" if city else ""
    li = "https://www.linkedin.com/search/results/people/?keywords="
    return {
        "LinkedIn: recruiters": li + quote(f"recruiter {company}{where}"),
        "LinkedIn: talent acquisition": li + quote(f"talent acquisition {company}"),
        "LinkedIn: engineering manager": li + quote(f"engineering manager {company}{where}"),
        "XING: recruiters": "https://www.xing.com/search/members?keywords=" + quote(f"recruiter {company}"),
    }
