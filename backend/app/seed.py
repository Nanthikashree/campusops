from sqlalchemy import select

from . import models  # noqa: F401
from .database import Base, SessionLocal, engine
from .models import Building, Room, User
from .security import hash_password

DEMO_PASSWORD = "campus123"

USERS = [
    ("Aishu Student", "student@campus.edu", "student_faculty"),
    ("Dr. Kumar", "faculty@campus.edu", "student_faculty"),
    ("Ravi Electrician", "ravi@campus.edu", "technician"),
    ("Raghav Network", "raghav@campus.edu", "technician"),
    ("Karthik General", "karthik@campus.edu", "technician"),
    ("Priya Manager", "priya@campus.edu", "department_manager"),
    ("Meena Facilities", "meena@campus.edu", "facilities_admin"),
    ("Arun Procurement", "arun@campus.edu", "procurement_approver"),
    ("System Admin", "admin@campus.edu", "system_admin"),
]

BUILDINGS = [
    ("Block A", "academic"),
    ("Block B", "academic"),
    ("Block C", "academic"),
    ("Science Block", "lab"),
    ("Library", "admin"),
    ("Boys Hostel", "hostel"),
    ("Girls Hostel", "hostel"),
]


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.scalar(select(User).limit(1)) is not None:
            print("Already seeded. Nothing to do.")
            return

        for name, email, role in USERS:
            db.add(User(name=name, email=email, role=role, password_hash=hash_password(DEMO_PASSWORD)))

        buildings = {}
        for name, kind in BUILDINGS:
            b = Building(name=name, kind=kind)
            db.add(b)
            buildings[name] = b
        db.flush()  # gives every building an id

        for name in ("Block A", "Block B", "Block C"):
            for floor in (1, 2):
                for n in (1, 2, 3):
                    room = f"{floor}0{n}"
                    db.add(Room(building_id=buildings[name].id, name=f"{name[-1]}{room}",
                                room_type="classroom", capacity=60 if n == 1 else 40))
        db.add(Room(building_id=buildings["Block A"].id, name="Seminar Hall", room_type="hall", capacity=120))
        for n in (1, 2, 3):
            db.add(Room(building_id=buildings["Science Block"].id, name=f"Lab {n}", room_type="lab", capacity=30))
        for hostel in ("Boys Hostel", "Girls Hostel"):
            for n in range(101, 106):
                db.add(Room(building_id=buildings[hostel].id, name=f"H-{n}", room_type="hostel_room", capacity=3))

        db.commit()
        print("Seeded users, buildings and rooms.")
        print(f"Every demo user has the password: {DEMO_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    run()