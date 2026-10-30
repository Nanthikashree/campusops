from sqlalchemy import select

from .database import SessionLocal
from .models import User

NAMES = {
    "student@campus.edu": "Student", "faculty@campus.edu": "Faculty",
    "ravi@campus.edu": "Electrician", "raghav@campus.edu": "Network Technician",
    "karthik@campus.edu": "General Technician", "divya@campus.edu": "Electrician 2",
    "suresh@campus.edu": "Plumber", "priya@campus.edu": "Department Manager",
    "meena@campus.edu": "Facilities Admin", "arun@campus.edu": "Procurement Approver",
    "admin@campus.edu": "System Admin",
}


def run():
    db = SessionLocal()
    try:
        for email, name in NAMES.items():
            u = db.scalar(select(User).where(User.email == email))
            if u is not None:
                u.name = name
        db.commit()
        print("Names updated.")
    finally:
        db.close()


if __name__ == "__main__":
    run()