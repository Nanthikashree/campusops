from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Booking, Room, User

BOOKABLE_TYPES = ("classroom", "lab", "hall")


def room_problem(room: Room, attendees: int):
    """Returns a sentence explaining why the room can't be used, or None if it's fine."""
    if room.room_type not in BOOKABLE_TYPES:
        return f"{room.name} is not a bookable room"
    if room.status != "available":
        return f"{room.name} is out of service right now"
    if attendees > room.capacity:
        return f"{room.name} seats only {room.capacity}, but {attendees} people are coming"
    return None


def overlapping(db: Session, room_id: int, start, end, exclude_id=None):
    q = select(Booking).where(
        Booking.room_id == room_id,
        Booking.status == "active",
        Booking.start_time < end,
        Booking.end_time > start,
    )
    if exclude_id is not None:
        q = q.where(Booking.id != exclude_id)
    return db.scalars(q).all()


def free_rooms(db: Session, start, end, attendees: int = 0, exclude_room_ids=()):
    rooms = db.scalars(select(Room).where(Room.status == "available")).all()
    busy = set(
        db.scalars(
            select(Booking.room_id).where(
                Booking.status == "active", Booking.start_time < end, Booking.end_time > start
            )
        ).all()
    )
    return [
        r for r in rooms
        if r.room_type in BOOKABLE_TYPES
        and r.id not in busy
        and r.id not in exclude_room_ids
        and r.capacity >= attendees
    ]


def suggest_alternatives(db: Session, original: Room, start, end, attendees: int, limit: int = 3):
    out = []
    for r in free_rooms(db, start, end, attendees, exclude_room_ids=(original.id,)):
        score, why = 0, []
        if r.room_type == original.room_type:
            score += 30
            why.append(f"same type: {r.room_type} (+30)")
        if r.building_id == original.building_id:
            score += 20
            why.append("same building (+20)")
        penalty = min((r.capacity - attendees) // 5, 20)
        score -= penalty
        why.append(f"seats {r.capacity} for {attendees} people (-{penalty} for unused seats)")
        out.append({
            "room_id": r.id, "name": r.name, "building": r.building.name,
            "capacity": r.capacity, "score": score, "why": why,
        })
    out.sort(key=lambda x: (-x["score"], x["room_id"]))
    return out[:limit]


def booking_dict(db: Session, b: Booking) -> dict:
    room = db.get(Room, b.room_id)
    who = db.get(User, b.booked_by)
    return {
        "id": b.id, "room_id": b.room_id, "room": room.name, "building": room.building.name,
        "title": b.title, "kind": b.kind, "start": b.start_time.isoformat(),
        "end": b.end_time.isoformat(), "attendees": b.attendees,
        "booked_by": who.name if who else None, "status": b.status, "note": b.note,
    }