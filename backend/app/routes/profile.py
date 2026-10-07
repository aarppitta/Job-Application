"""Your profile (from your CV) and settings."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import current_profile
from app.database import get_db
from app.defaults import DEFAULT_SETTINGS, user_settings
from app.logic.skills import canonical_skill
from app.models import Profile
from app.serialize import to_dict

router = APIRouter(prefix="/api", tags=["profile"])

# Facts not on the CV: email + phone go on the tailored CV, visa need is used by the score.
NEEDED_FACTS = {"email": "Email", "phone": "Phone", "visa_required": "Visa sponsorship needed?"}


def profile_dict(p: Profile) -> dict:
    data = to_dict(p)
    data.pop("settings")
    data["missing_facts"] = [label for field, label in NEEDED_FACTS.items() if getattr(p, field) in (None, "")]
    return data


class ProfileUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    headline: str | None = None
    summary: str | None = None
    education: list[str] | None = None
    years_experience: float | None = None
    target_roles: list[str] | None = None
    skills: list[dict] | None = None        # [{"name": "Python", "years": 2.5}]
    languages: list[dict] | None = None
    visa_required: bool | None = None


@router.get("/profile")
def get_profile(profile: Profile = Depends(current_profile)):
    return profile_dict(profile)


@router.patch("/profile")
def update_profile(body: ProfileUpdate, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    changes = body.model_dump(exclude_unset=True)
    if "skills" in changes:
        seen, clean = set(), []
        for s in changes["skills"]:
            name = canonical_skill(str(s.get("name", "")))
            if name and name not in seen:
                seen.add(name)
                clean.append({"name": name, "years": s.get("years")})
        changes["skills"] = clean
    for field, value in changes.items():
        setattr(profile, field, value)
    db.commit()
    return profile_dict(profile)


@router.get("/settings")
def get_settings(profile: Profile = Depends(current_profile)):
    return user_settings(profile)


@router.patch("/settings")
def update_settings(body: dict, profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    unknown = set(body) - set(DEFAULT_SETTINGS)
    if unknown:
        raise HTTPException(422, f"Unknown settings: {', '.join(sorted(unknown))}")
    if "min_score" in body and not 0 <= float(body["min_score"]) <= 100:
        raise HTTPException(422, "min_score must be between 0 and 100.")
    if "daily_start_time" in body:
        import re

        if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", str(body["daily_start_time"])):
            raise HTTPException(422, "daily_start_time must look like 08:00.")
    if "search_queries" in body:
        keywords = list(dict.fromkeys(" ".join(str(k).split()) for k in body["search_queries"]))  # tidy + no repeats
        body["search_queries"] = [k for k in keywords if k]
        if not body["search_queries"]:
            raise HTTPException(422, "Add at least one job role to search for.")
    if "max_runtime_hours" in body and not 0 < float(body["max_runtime_hours"]) <= 6:
        raise HTTPException(422, "max_runtime_hours must be between 0 and 6.")
    profile.settings = {**(profile.settings or {}), **body}
    db.commit()
    return user_settings(profile)
