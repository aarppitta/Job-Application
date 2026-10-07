"""Runs when the backend starts: makes sure the master user and the profile (from your CV) exist."""
from app.auth import check_password, hash_password
from app.config import settings
from app.database import SessionLocal
from app.defaults import starting_profile
from app.models import Profile, User


def ensure_master_user() -> None:
    username = settings.master_username.strip().lower()
    with SessionLocal() as db:
        user = db.query(User).filter_by(username=username).first()
        if user is None:
            user = User(username=username, password_hash=hash_password(settings.master_password))
            db.add(user)
            db.flush()
        elif not check_password(settings.master_password, user.password_hash):
            user.password_hash = hash_password(settings.master_password)  # password changed in .env

        profile = db.query(Profile).filter_by(user_id=user.id).first()
        if profile is None:
            db.add(Profile(user_id=user.id, settings={}, **starting_profile()))
        else:
            # Older profiles had no CV bullet points: fill them in from the standard CV.
            if any("bullets" not in e for e in profile.experience or []):
                profile.experience = starting_profile()["experience"]
            if any("bullets" not in p for p in profile.projects or []):
                profile.projects = starting_profile()["projects"]

        db.commit()
