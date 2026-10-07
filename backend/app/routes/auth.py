"""Login. There is only one user (the master user from .env); nobody can register."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import check_password, current_user, make_token
from app.database import get_db
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class Credentials(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: Credentials, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=body.username.strip().lower()).first()
    if not user or not check_password(body.password, user.password_hash):
        raise HTTPException(401, "Wrong username or password.")
    return {"token": make_token(user.id), "username": user.username}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "username": user.username}
