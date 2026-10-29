from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .bookings import (
    booking_dict, free_rooms, overlapping, room_problem, suggest_alternatives,
)
from .database import get_db
from .deps import get_current_user, require_roles
from .events import add_event
from .models import BOOKING_KINDS, Booking, Room, Ticket, User
from .routes_assign import MANAGERS

router = APIRouter(prefix="/api")
OPEN_TICKET = ("new", "triaged", "assigned", "in_progress", "blocked")


class BookingIn(BaseModel):
    room_id: int
    title: str = Field(min_length=3, max_length=200)
    kind: str = "class"
    start_time: datetime
    end_time: datetime
    attendees: int = Field(default=0, ge=0, le=500)


class MoveIn(BaseModel):
    room_id: int


class RoomStatusIn(BaseModel):
    status: str


def naive(dt: datetime) -> datetime:
    return dt.replace(tzinfo=None)


def room_impact(db: Session, room: Room) -> list:
    """Upcoming bookings in this room, exams first, each with replacement suggestions."""
    upcoming = db.scalars(
        select(Booking).where(
            Booking.room_id == room.id, Booking.status == "active", Booking.end_time > datetime.now()
        )
    ).all()
    upcoming.sort(key=lambda b: (b.kind != "exam", b.start_time))
    return [
        {
            "booking": booking_dict(db, b),
            "alternatives": suggest_alternatives(db, room, b.start_time, b.end_time, b.attendees),
        }
        for b in upcoming
    ]


@router.get("/rooms")
def list_rooms(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rooms = db.scalars(select(Room).order_by(Room.id)).all()
    return [
        {"id": r.id, "name": r.name, "building": r.building.name, "type": r.room_type,
         "capacity": r.capacity, "status": r.status}
        for r in rooms
    ]


@router.get("/rooms/availability")
def availability(start: datetime, end: datetime, attendees: int = 0,
                 user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    start, end = naive(start), naive(end)
    if end <= start:
        raise HTTPException(400, "The end time must be after the start time")
    rooms = free_rooms(db, start, end, attendees)
    return [
        {"id": r.id, "name": r.name, "building": r.building.name, "type": r.room_type, "capacity": r.capacity}
        for r in rooms
    ]


@router.post("/rooms/{room_id}/status")
def set_room_status(room_id: int, body: RoomStatusIn, user: User = Depends(require_roles(*MANAGERS)),
                    db: Session = Depends(get_db)):
    if body.status not in ("available", "unusable"):
        raise HTTPException(400, "status must be 'available' or 'unusable'")
    room = db.get(Room, room_id)
    if room is None:
        raise HTTPException(404, "Room not found")
    room.status = body.status
    affected = room_impact(db, room) if body.status == "unusable" else []
    if body.status == "unusable":
        open_tickets = db.scalars(
            select(Ticket).where(Ticket.room_id == room.id, Ticket.status.in_(OPEN_TICKET))
        ).all()
        for t in open_tickets:
            add_event(db, t.id, "room_marked_unusable", user,
                      f"{room.name} marked unusable. {len(affected)} booking(s) affected.")
    db.commit()
    exams = sum(1 for a in affected if a["booking"]["kind"] == "exam")
    return {
        "room": room.name, "status": room.status,
        "summary": f"{len(affected)} booking(s) affected, including {exams} exam(s)",
        "affected": affected,
    }


@router.get("/tickets/{ticket_id}/impact")
def ticket_impact(ticket_id: int, user: User = Depends(require_roles(*MANAGERS)), db: Session = Depends(get_db)):
    t = db.get(Ticket, ticket_id)
    if t is None:
        raise HTTPException(404, "Ticket not found")
    if t.room_id is None:
        return {"room": None, "affected": []}
    room = db.get(Room, t.room_id)
    affected = room_impact(db, room)
    return {"room": room.name, "room_status": room.status, "affected": affected}


@router.post("/bookings")
def create_booking(body: BookingIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    start, end = naive(body.start_time), naive(body.end_time)
    if end <= start:
        raise HTTPException(400, "The end time must be after the start time")
    if (end - start) > timedelta(hours=8):
        raise HTTPException(400, "A booking can be at most 8 hours")
    if body.kind not in BOOKING_KINDS:
        raise HTTPException(400, f"kind must be one of {BOOKING_KINDS}")
    if body.kind == "exam" and user.role not in MANAGERS:
        raise HTTPException(403, "Only managers and admins can schedule exams")
    room = db.get(Room, body.room_id)
    if room is None:
        raise HTTPException(404, "Room not found")

    problem = room_problem(room, body.attendees)
    if problem:
        raise HTTPException(409, {"message": problem,
                                  "alternatives": suggest_alternatives(db, room, start, end, body.attendees)})
    clashes = overlapping(db, room.id, start, end)
    if clashes:
        raise HTTPException(409, {
            "message": f"{room.name} is already booked at that time",
            "conflicts": [booking_dict(db, c) for c in clashes],
            "alternatives": suggest_alternatives(db, room, start, end, body.attendees),
        })

    b = Booking(room_id=room.id, title=body.title, kind=body.kind, start_time=start, end_time=end,
                attendees=body.attendees, booked_by=user.id)
    db.add(b)
    db.commit()
    return booking_dict(db, b)


@router.get("/bookings")
def list_bookings(date: str | None = None, room_id: int | None = None, mine: bool = False,
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = select(Booking).where(Booking.status == "active").order_by(Booking.start_time)
    if date:
        try:
            day = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(400, "date must look like 2026-10-30")
        q = q.where(Booking.start_time >= day, Booking.start_time < day + timedelta(days=1))
    if room_id:
        q = q.where(Booking.room_id == room_id)
    if mine:
        q = q.where(Booking.booked_by == user.id)
    return [booking_dict(db, b) for b in db.scalars(q).all()]


@router.post("/bookings/{booking_id}/cancel")
def cancel_booking(booking_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    b = db.get(Booking, booking_id)
    if b is None:
        raise HTTPException(404, "Booking not found")
    if b.booked_by != user.id and user.role not in MANAGERS:
        raise HTTPException(403, "You can only cancel your own bookings")
    if b.status != "active":
        raise HTTPException(409, "This booking is already cancelled")
    b.status = "cancelled"
    db.commit()
    return booking_dict(db, b)


@router.post("/bookings/{booking_id}/move")
def move_booking(booking_id: int, body: MoveIn, user: User = Depends(require_roles(*MANAGERS)),
                 db: Session = Depends(get_db)):
    b = db.get(Booking, booking_id)
    if b is None or b.status != "active":
        raise HTTPException(404, "Active booking not found")
    new_room = db.get(Room, body.room_id)
    if new_room is None:
        raise HTTPException(404, "Room not found")
    # Re-check everything at the moment of moving, not when the suggestion was made.
    problem = room_problem(new_room, b.attendees)
    if problem:
        raise HTTPException(409, problem)
    if overlapping(db, new_room.id, b.start_time, b.end_time, exclude_id=b.id):
        raise HTTPException(409, f"{new_room.name} was booked by someone else in the meantime")
    old = db.get(Room, b.room_id)
    b.room_id = new_room.id
    b.note = f"Moved from {old.name} to {new_room.name} by {user.name}"
    db.commit()
    return booking_dict(db, b)