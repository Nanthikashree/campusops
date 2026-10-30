from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .deps import get_current_user
from .models import User
from .security import create_token, verify_password

router = APIRouter(prefix="/api")

LOGIN_IDS = {
    "student": "student@campus.edu", "faculty": "faculty@campus.edu",
    "electrician": "ravi@campus.edu", "network": "raghav@campus.edu",
    "general": "karthik@campus.edu", "electrician2": "divya@campus.edu",
    "plumber": "suresh@campus.edu", "manager": "priya@campus.edu",
    "facilities": "meena@campus.edu", "procurement": "arun@campus.edu",
    "admin": "admin@campus.edu",
}


class LoginIn(BaseModel):
    email: str
    password: str


def user_info(u: User) -> dict:
    return {
        "id": u.id, "name": u.name, "email": u.email, "role": u.role,
        "user_type": getattr(u, "user_type", None) or "student",
        "portal": "user" if u.role == "student_faculty" else "admin",
    }


@router.post("/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    ident = body.email.strip().lower()
    if "@" not in ident:
        ident = LOGIN_IDS.get(ident, ident + "@campus.edu")
    u = db.scalar(select(User).where(User.email == ident))
    if u is None or not verify_password(body.password, u.password_hash):
        raise HTTPException(401, "Wrong ID or password")
    return {"token": create_token(u.id, u.role), "user": user_info(u)}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return user_info(user)