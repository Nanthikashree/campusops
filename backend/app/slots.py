from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .bookings import overlapping, room_problem
from .models import Booking, Room, Slot, SlotBooking, User
from .notifications import notify

SLOT_KINDS = ["exam", "lab", "workshop", "event"]
BOOKING_KIND = {"exam": "exam", "lab": "class", "workshop": "event", "event": "event"}
CLOSE_BEFORE_MIN = 60     # booking closes this long before the start
CANCEL_BEFORE_MIN = 120   # a student can cancel a seat until this long before the start


def now_local() -> datetime:
    return datetime.now()


def is_student(user: User) -> bool:
    return user.role == "student_faculty" and getattr(user, "user_type", "student") == "student"


def booked_count(db: Session, slot_id: int) -> int:
    return len(db.scalars(select(SlotBooking.id).where(
        SlotBooking.slot_id == slot_id, SlotBooking.status == "booked")).all())


def my_seat(db: Session, slot_id: int, user_id: int):
    return db.scalar(select(SlotBooking).where(
        SlotBooking.slot_id == slot_id, SlotBooking.student_id == user_id, SlotBooking.status == "booked"))


def state_of(slot: Slot, booked: int) -> str:
    n = now_local()
    if slot.status == "cancelled":
        return "cancelled"
    if n >= slot.closes_at:
        return "closed"
    if n < slot.opens_at:
        return "opening_soon"
    if booked >= slot.capacity:
        return "full"
    return "open"


def slot_dict(db: Session, s: Slot, user=None) -> dict:
    booking = db.get(Booking, s.booking_id) if s.booking_id else None
    room = db.get(Room, booking.room_id) if booking else None
    booked = booked_count(db, s.id)
    state = state_of(s, booked)
    mine = my_seat(db, s.id, user.id) if user is not None else None
    cancel_until = s.start_time - timedelta(minutes=CANCEL_BEFORE_MIN)
    return {
        "id": s.id, "title": s.title, "kind": s.kind, "description": s.description,
        "room_id": room.id if room else None,
        "venue": f"{room.building.name} - {room.name}" if room else "Not set",
        "start": s.start_time.isoformat(), "end": s.end_time.isoformat(),
        "capacity": s.capacity, "booked": booked, "seats_left": max(s.capacity - booked, 0),
        "opens_at": s.opens_at.isoformat(), "closes_at": s.closes_at.isoformat(),
        "cancel_until": cancel_until.isoformat(), "state": state,
        "my_seat": mine is not None,
        "can_book": bool(user is not None and is_student(user) and state == "open" and mine is None),
        "can_cancel_seat": bool(mine is not None and state != "cancelled" and now_local() < cancel_until),
    }


def create_slot(db: Session, actor: User, title, kind, description, room_id, start, end, capacity, opens_at=None) -> Slot:
    if kind not in SLOT_KINDS:
        raise ValueError(f"kind must be one of {SLOT_KINDS}")
    if end <= start:
        raise ValueError("The end time must be after the start time")
    if start <= now_local():
        raise ValueError("The slot must start in the future")
    if (end - start) > timedelta(hours=8):
        raise ValueError("A slot can be at most 8 hours long")
    room = db.get(Room, room_id)
    if room is None:
        raise ValueError("Room not found")
    problem = room_problem(room, capacity)
    if problem:
        raise ValueError(problem)
    clashes = overlapping(db, room.id, start, end)
    if clashes:
        raise ValueError(f"{room.name} is already booked at that time ({clashes[0].title})")
    closes_at = start - timedelta(minutes=CLOSE_BEFORE_MIN)
    opens_at = opens_at or now_local()
    if opens_at > closes_at:
        raise ValueError(
            f"Booking closes {CLOSE_BEFORE_MIN} minutes before the start, so this slot would never be open. "
            "Start it later or choose an earlier opening time.")
    booking = Booking(room_id=room.id, title=title, kind=BOOKING_KIND[kind], start_time=start, end_time=end,
                      attendees=capacity, booked_by=actor.id, note="Created as a bookable slot")
    db.add(booking)
    db.flush()
    slot = Slot(title=title, kind=kind, description=description, booking_id=booking.id, start_time=start,
                end_time=end, capacity=capacity, opens_at=opens_at, closes_at=closes_at, created_by=actor.id)
    db.add(slot)
    db.flush()
    return slot


def student_clash(db: Session, student_id: int, slot: Slot):
    rows = db.scalars(select(Slot).join(SlotBooking, SlotBooking.slot_id == Slot.id).where(
        SlotBooking.student_id == student_id, SlotBooking.status == "booked", Slot.status == "scheduled",
        Slot.id != slot.id, Slot.start_time < slot.end_time, Slot.end_time > slot.start_time)).all()
    return rows[0] if rows else None


def book_seat(db: Session, user: User, slot: Slot):
    if not is_student(user):
        raise PermissionError("Only students can book these slots")
    if my_seat(db, slot.id, user.id) is not None:
        raise ValueError("You already have a seat in this slot")
    state = state_of(slot, booked_count(db, slot.id))
    if state == "cancelled":
        raise ValueError("This slot was cancelled")
    if state == "opening_soon":
        raise ValueError(f"Booking opens on {slot.opens_at:%d %b at %I:%M %p}")
    if state == "closed":
        raise ValueError(f"Booking is closed. It closes {CLOSE_BEFORE_MIN} minutes before the start")
    if state == "full":
        raise ValueError("This slot is full")
    clash = student_clash(db, user.id, slot)
    if clash is not None:
        raise ValueError(f"This overlaps with your other booking: {clash.title}")
    db.add(SlotBooking(slot_id=slot.id, student_id=user.id))
    notify(db, user.id, f"Seat booked: {slot.title} on {slot.start_time:%d %b, %I:%M %p}", None, "slot")


def cancel_seat(db: Session, user: User, slot: Slot):
    seat = my_seat(db, slot.id, user.id)
    if seat is None:
        raise ValueError("You have no seat in this slot")
    if now_local() >= slot.start_time - timedelta(minutes=CANCEL_BEFORE_MIN):
        raise ValueError(f"Cancellation ended {CANCEL_BEFORE_MIN} minutes before the start")
    seat.status = "cancelled"
    seat.cancelled_at = datetime.now(timezone.utc)
    notify(db, user.id, f"Your seat for {slot.title} was cancelled", None, "slot")


def cancel_slot(db: Session, slot: Slot, actor: User) -> int:
    if slot.status == "cancelled":
        raise ValueError("This slot is already cancelled")
    slot.status = "cancelled"
    booking = db.get(Booking, slot.booking_id) if slot.booking_id else None
    if booking is not None and booking.status == "active":
        booking.status = "cancelled"
        booking.note = f"Slot cancelled by {actor.name}"
    rows = db.scalars(select(SlotBooking).where(
        SlotBooking.slot_id == slot.id, SlotBooking.status == "booked")).all()
    for r in rows:
        r.status = "cancelled"
        r.cancelled_at = datetime.now(timezone.utc)
        notify(db, r.student_id, f"{slot.title} on {slot.start_time:%d %b, %I:%M %p} was cancelled", None, "slot")
    return len(rows)


def notify_slot_students(db: Session, booking_id: int, message: str):
    slot = db.scalar(select(Slot).where(Slot.booking_id == booking_id, Slot.status == "scheduled"))
    if slot is None:
        return
    for r in db.scalars(select(SlotBooking).where(
            SlotBooking.slot_id == slot.id, SlotBooking.status == "booked")).all():
        notify(db, r.student_id, message, None, "slot")