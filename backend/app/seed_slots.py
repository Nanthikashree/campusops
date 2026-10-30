from datetime import datetime, timedelta

from sqlalchemy import select

from . import models  # noqa: F401
from .database import Base, SessionLocal, engine
from .models import Room, Slot, User
from .slots import create_slot


def at(days, hour, minute=0):
    return (datetime.now() + timedelta(days=days)).replace(hour=hour, minute=minute, second=0, microsecond=0)


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.scalar(select(Slot).limit(1)) is not None:
            print("Slots already exist. Nothing to do.")
            return
        actor = db.scalar(select(User).where(User.email == "meena@campus.edu"))
        if actor is None:
            print("Run the main seed first.")
            return
        rooms = {r.name: r.id for r in db.scalars(select(Room)).all()}
        long_ago = datetime.now() - timedelta(days=1)
        soon = datetime.now() + timedelta(minutes=30)
        plan = [
            ("CIA-I EXAM", "exam", "Internal assessment. Carry your ID card.", "B101", at(1, 15), at(1, 16, 30), 40, long_ago),
            ("Chemistry Lab Practical", "lab", "Bring your lab coat.", "Lab 3", at(1, 10), at(1, 12), 25, long_ago),
            ("AI Workshop", "workshop", "Hands-on session on AI tools.", "Seminar Hall", at(2, 10), at(2, 12), 100, at(1, 9)),
            ("Quick Quiz", "event", "Booking is already closed for this one.", "Lab 1", soon, soon + timedelta(hours=1), 20, long_ago),
        ]
        for title, kind, desc, room, start, end, cap, opens in plan:
            try:
                create_slot(db, actor, title, kind, desc, rooms[room], start, end, cap, opens)
            except (ValueError, KeyError) as e:
                print(f"Skipped {title}: {e}")
        db.commit()
        print("Demo slots created.")
    finally:
        db.close()


if __name__ == "__main__":
    run()