from sqlalchemy import select

from . import models  # noqa: F401
from .database import Base, SessionLocal, engine
from .models import Part

PARTS = [  # name, stock, min_stock, unit_cost
    ("Projector Lamp", 0, 2, 28000), ("AC Capacitor", 0, 3, 1500), ("AC Remote", 5, 2, 600),
    ("Network Router", 2, 1, 6500), ("HDMI Cable", 10, 3, 300), ("Ceiling Fan", 0, 2, 2200),
    ("Lab Reagent X", 4, 5, 900),
]


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.scalar(select(Part).limit(1)) is not None:
            print("Parts already exist. Nothing to do.")
            return
        for name, stock, min_stock, cost in PARTS:
            db.add(Part(name=name, stock=stock, min_stock=min_stock, unit_cost=cost))
        db.commit()
        print("Parts added.")
    finally:
        db.close()


if __name__ == "__main__":
    run()