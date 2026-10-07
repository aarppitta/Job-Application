"""Login: bcrypt passwords + a JWT token sent as 'Authorization: Bearer <token>'."""
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Profile, User

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def make_token(user_id: int) -> str:
    expires = datetime.now(UTC) + timedelta(days=settings.token_days)
    return jwt.encode({"sub": str(user_id), "exp": expires}, settings.secret_key, algorithm="HS256")


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if creds is None:
        raise HTTPException(401, "Please log in.")
    try:
        user_id = int(jwt.decode(creds.credentials, settings.secret_key, algorithms=["HS256"])["sub"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Session expired. Please log in again.")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(401, "User not found.")
    return user


def current_profile(user: User = Depends(current_user), db: Session = Depends(get_db)) -> Profile:
    return db.query(Profile).filter_by(user_id=user.id).one()
