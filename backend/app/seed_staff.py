from sqlalchemy import select

from . import models  # noqa: F401
from .database import Base, SessionLocal, engine
from .models import StaffProfile, User
from .security import hash_password

SKILLS = {
    "ravi@campus.edu": "electrical,hvac",
    "raghav@campus.edu": "network,equipment",
    "karthik@campus.edu": "general,plumbing",
    "divya@campus.edu": "electrical,general",
    "suresh@campus.edu": "plumbing",
}
EXTRA_USERS = [
    ("Divya Electrician", "divya@campus.edu"),
    ("Suresh Plumber", "suresh@campus.edu"),
]


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for name, email in EXTRA_USERS:
            if db.scalar(select(User).where(User.email == email)) is None:
                db.add(User(name=name, email=email, role="technician", password_hash=hash_password("campus123")))
        db.flush()
        for email, skills in SKILLS.items():
            u = db.scalar(select(User).where(User.email == email))
            if u is not None and db.get(StaffProfile, u.id) is None:
                db.add(StaffProfile(user_id=u.id, skills=skills))
        db.commit()
        print("Technician profiles ready.")
    finally:
        db.close()


if __name__ == "__main__":
    run()