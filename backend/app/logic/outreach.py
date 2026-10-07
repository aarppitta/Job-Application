"""Getting your CV in front of a real person, without spamming.

You find the people (search links); the app ranks them, writes a personal message for each, and tracks
contacted / replied / follow-up. Quality over quantity: 1 recruiter + 1 hiring manager + 1 follow-up per job.
Nothing is ever sent by the app.
"""
from datetime import datetime, timedelta

from app.logic.writer import INDUSTRIAL

KINDS = {  # kind -> (tier, label)
    "recruiter": (1, "Recruiter for this team/job"),
    "talent_acquisition": (2, "Talent Acquisition at the company"),
    "hiring_manager": (3, "Hiring / Engineering Manager"),
    "department_head": (4, "Department head"),
    "referral": (2, "Employee who could refer you"),
}
MAX_CONTACTS_PER_JOB = 3
FOLLOW_UP_DAYS = 7


def tier(kind: str) -> int:
    return KINDS.get(kind, (4, ""))[0]


def _best_project(profile, matched: list[str]) -> dict | None:
    ranked = sorted(profile.projects, key=lambda p: -len(set(p.get("skills", [])) & set(matched)))
    return ranked[0] if ranked and set(ranked[0].get("skills", [])) & set(matched) else None


def contact_message(profile, job, matched: list[str], contact, applied: bool) -> dict:
    """A short, personal message for ONE person. Different wording for recruiters and engineering managers."""
    first = contact.name.split()[0] if contact.name else ""
    hi = f"Hi {first}," if first else "Hi,"
    me = profile.name.split()[0]
    skills = ", ".join(([s for s in matched if s in INDUSTRIAL] + [s for s in matched if s not in INDUSTRIAL])[:3]) or "Python"
    project = _best_project(profile, matched)
    proj = f" (e.g. {project['name'].split('—')[0].strip()})" if project else ""
    abroad = "germany" not in (profile.location or "").lower()
    where = (f"I'm based in {profile.location.split(',')[0]} and looking specifically for roles in Germany"
             + (" with visa/relocation support." if profile.visa_required is not False else ".")) if abroad and profile.location else ""
    did = f"I {'recently applied' if applied else 'am applying'} for the {job.title} role at {job.company}."
    if tier(contact.kind) >= 3:  # engineering side: talk about the work, not the process
        body = (f"{did} My background is {skills}{proj}, which looks close to what your team builds. {where} "
                f"Would you be open to a short chat, or could you point me to the right person?")
    else:
        body = (f"{did} My background is {skills}{proj}, which seemed particularly relevant to the role. {where} "
                f"I'd be glad to connect and discuss whether my background could be a fit.")
    body = " ".join(body.split())
    note = f"{hi} {body} Best, {me}"
    if len(note) > 300:  # LinkedIn connection note limit
        note = f"{hi} {did} My background: {skills}{proj}. {'Looking for Germany roles with relocation. ' if abroad else ''}Glad to connect! {me}"
    note = note[:300]
    message = f"{hi}\n\n{body}\n\nBest,\n{profile.name}"
    subject = f"Application – {job.title} – {profile.name}"
    signature = "\n".join(x for x in (profile.email, profile.phone, profile.linkedin_url) if x)
    email = f"{hi}\n\n{body}\n\nMy CV is attached.\n\nBest regards,\n{profile.name}" + (f"\n{signature}" if signature else "")
    follow_up = (f"{hi} just following up on my message about the {job.title} role. I'm still very interested and happy to share "
                 f"more about my {skills.split(',')[0]} work. Thanks, {me}")
    return {"note": note, "note_length": len(note), "message": message, "email_subject": subject, "email_body": email,
            "follow_up": follow_up, "email_allowed": bool(contact.email)}


def outreach_plan(applied: bool, contacts: list) -> list[dict]:
    recruiter = [c for c in contacts if tier(c.kind) <= 2 and c.kind != "referral"]
    manager = [c for c in contacts if tier(c.kind) >= 3]
    contacted = lambda cs: any(c.contacted_at for c in cs)
    replied = any(c.replied_at for c in contacts)
    followed = any(c.followed_up_at for c in contacts)
    return [
        {"step": 1, "text": "Apply through the official careers page", "done": applied},
        {"step": 2, "text": "Identify the relevant recruiter (search links)", "done": bool(recruiter)},
        {"step": 3, "text": "Send a personalized LinkedIn connection request", "done": contacted(recruiter)},
        {"step": 4, "text": "Send the short message after they connect", "done": replied or contacted(recruiter)},
        {"step": 5, "text": "No recruiter / no answer after 5 days? Identify the hiring manager", "done": bool(manager), "optional": replied},
        {"step": 6, "text": "Send the hiring manager a concise message", "done": contacted(manager), "optional": replied},
        {"step": 7, "text": f"Follow up once after ~{FOLLOW_UP_DAYS} days (only once)", "done": followed or replied},
    ]


def health(app, job, contacts: list, threshold: float) -> dict:
    """Application health: which human-visibility actions are done, and what's missing."""
    recruiter = [c for c in contacts if tier(c.kind) <= 2 and c.kind != "referral"]
    manager = [c for c in contacts if tier(c.kind) >= 3]
    items = [
        ("Official application", app is not None, 20, "Apply on the careers page and click Mark as applied"),
        ("JD match", (job.ats_score or 0) >= threshold - 10, 10, "Low match: consider skipping"),
        ("Tailored CV", bool(app and app.tailored_cv) or bool(job.cv_prepared_at), 15, "Download the tailored CV"),
        ("Recruiter identified", bool(recruiter), 10, "Find the recruiter with the search links"),
        ("Recruiter contacted", any(c.contacted_at for c in recruiter), 15, "Send the recruiter the personal note"),
        ("Hiring manager identified", bool(manager), 5, "Find the engineering manager"),
        ("Hiring manager contacted", any(c.contacted_at for c in manager), 10, "Send the hiring manager a short message"),
        ("Referral", bool(app and app.referral) or any(c.kind == "referral" for c in contacts), 5, "Ask a contact at the company for a referral"),
        ("Follow-up scheduled", bool(app and app.next_follow_up) or any(c.followed_up_at or c.replied_at for c in contacts), 10, "Set a follow-up date"),
    ]
    score = sum(w for _, done, w, _ in items if done)
    return {"score": score, "items": [{"label": l, "done": d, "action": a} for l, d, _, a in items],
            "missing": [a for _, d, _, a in items if not d][:3]}


def follow_ups(app, contacts: list, now: datetime) -> list[dict]:
    """When to follow up. One follow-up per person, never more."""
    out = []
    for c in contacts:
        if c.contacted_at and not c.replied_at:
            due = c.contacted_at + timedelta(days=FOLLOW_UP_DAYS)
            if c.followed_up_at:
                out.append({"who": c.name, "due": None, "text": f"Already followed up with {c.name}: don't message again. Wait, or try the hiring manager."})
            else:
                out.append({"who": c.name, "due": due.isoformat(), "overdue": due <= now,
                            "text": f"Follow up with {c.name} on {due:%b %d}" + (" (due now)" if due <= now else "")})
    if app and app.status == "APPLIED" and not any(c.contacted_at for c in contacts):
        due = app.submitted_at + timedelta(days=2)
        out.append({"who": None, "due": due.isoformat(), "overdue": due <= now,
                    "text": "Contact a recruiter for this application" + (" (due now)" if due <= now else "")})
    return out
