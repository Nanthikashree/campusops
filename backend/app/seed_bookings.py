from datetime import datetime, timedelta

from sqlalchemy import select

from . import models  # noqa: F401
from .database import Base, SessionLocal, engine
from .models import Booking, Room, User


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.scalar(select(Booking).limit(1)) is not None:
            print("Bookings already exist. Nothing to do.")
            return
        day = (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        rooms = {r.name: r.id for r in db.scalars(select(Room)).all()}
        faculty = db.scalar(select(User).where(User.email == "faculty@campus.edu"))
        manager = db.scalar(select(User).where(User.email == "priya@campus.edu"))

        plan = [
            # room, title, kind, start hour, end hour, attendees, booked by
            ("B203", "CSE Lecture - Algorithms", "class", 9, 10, 38, faculty),
            ("B203", "Mid-term Exam - Data Structures", "exam", 11, 13, 38, manager),
            ("B201", "Physics Class", "class", 11, 12, 55, faculty),
            ("A101", "Maths Tutorial", "class", 11, 13, 50, faculty),
            ("Lab 2", "Chemistry Practical", "class", 10, 12, 25, faculty),
            ("Seminar Hall", "Workshop", "event", 14, 16, 90, manager),
        ]
        for room, title, kind, h1, h2, people, who in plan:
            db.add(Booking(room_id=rooms[room], title=title, kind=kind,
                           start_time=day + timedelta(hours=h1), end_time=day + timedelta(hours=h2),
                           attendees=people, booked_by=who.id))
        db.commit()
        print(f"Demo bookings created for {day.date()} (tomorrow).")
    finally:
        db.close()


if __name__ == "__main__":
    run()