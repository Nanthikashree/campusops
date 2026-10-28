from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .deps import get_current_user, require_roles
from .models import User
from .security import create_token, verify_password

router = APIRouter(prefix="/api")

STAFF_ROLES = [
    "technician",
    "department_manager",
    "facilities_admin",
    "procurement_approver",
    "system_admin",
]


class LoginIn(BaseModel):
    email: str
    password: str


def user_info(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "portal": "user" if user.role == "student_faculty" else "admin",
    }


@router.post("/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Wrong email or password")
    return {"token": create_token(user.id, user.role), "user": user_info(user)}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return user_info(user)


# Test endpoints, to prove the role checks work. We'll remove them later.
@router.get("/admin/ping")
def admin_ping(user: User = Depends(require_roles(*STAFF_ROLES))):
    return {"message": f"Hello {user.name}, you are in the admin portal"}


@router.get("/approvals/ping")
def approvals_ping(user: User = Depends(require_roles("procurement_approver"))):
    return {"message": f"Hello {user.name}, you can approve purchases"}