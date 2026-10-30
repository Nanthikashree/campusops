from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .deps import get_current_user, require_roles
from .models import Slot, SlotBooking, User
from .notifications import notify
from .routes_assign import MANAGERS
from .routes_bookings import naive
from .slots import book_seat, cancel_seat, cancel_slot, create_slot, now_local, slot_dict

router = APIRouter(prefix="/api")


class SlotIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    kind: str
    description: str = Field(default="", max_length=500)
    room_id: int
    start_time: datetime
    end_time: datetime
    capacity: int = Field(ge=1, le=500)
    opens_at: datetime | None = None


def get_slot_or_404(db: Session, slot_id: int) -> Slot:
    s = db.get(Slot, slot_id)
    if s is None:
        raise HTTPException(404, "Slot not found")
    return s


@router.get("/slots")
def list_slots(kind: str | None = None, mine: bool = False, include_past: bool = False,
               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = select(Slot).order_by(Slot.start_time)
    if kind:
        q = q.where(Slot.kind == kind)
    if not include_past:
        q = q.where(Slot.end_time >= now_local())
    out = [slot_dict(db, s, user) for s in db.scalars(q).all()]
    if mine:
        out = [s for s in out if s["my_seat"]]
    return out


@router.post("/slots")
def create(body: SlotIn, user: User = Depends(require_roles(*MANAGERS)), db: Session = Depends(get_db)):
    try:
        slot = create_slot(db, user, body.title.strip(), body.kind, body.description, body.room_id,
                           naive(body.start_time), naive(body.end_time), body.capacity,
                           naive(body.opens_at) if body.opens_at else None)
    except ValueError as e:
        db.rollback()
        raise HTTPException(409, str(e))
    if slot.opens_at <= now_local():
        for u in db.scalars(select(User).where(User.role == "student_faculty", User.user_type == "student")).all():
            notify(db, u.id, f"New {slot.kind} slot open for booking: {slot.title}", None, "slot")
    db.commit()
    return slot_dict(db, slot, user)


@router.post("/slots/{slot_id}/book")
def book(slot_id: int, user: User = Depends(require_roles("student_faculty")), db: Session = Depends(get_db)):
    slot = get_slot_or_404(db, slot_id)
    try:
        book_seat(db, user, slot)
    except PermissionError as e:
        db.rollback()
        raise HTTPException(403, str(e))
    except ValueError as e:
        db.rollback()
        raise HTTPException(409, str(e))
    db.commit()
    return slot_dict(db, slot, user)


@router.post("/slots/{slot_id}/cancel-seat")
def cancel_my_seat(slot_id: int, user: User = Depends(require_roles("student_faculty")), db: Session = Depends(get_db)):
    slot = get_slot_or_404(db, slot_id)
    try:
        cancel_seat(db, user, slot)
    except ValueError as e:
        db.rollback()
        raise HTTPException(409, str(e))
    db.commit()
    return slot_dict(db, slot, user)


@router.post("/slots/{slot_id}/cancel")
def cancel_whole_slot(slot_id: int, user: User = Depends(require_roles(*MANAGERS)), db: Session = Depends(get_db)):
    slot = get_slot_or_404(db, slot_id)
    try:
        told = cancel_slot(db, slot, user)
    except ValueError as e:
        db.rollback()
        raise HTTPException(409, str(e))
    db.commit()
    return {"message": f"Slot cancelled. {told} student(s) were notified.", "slot": slot_dict(db, slot, user)}


@router.get("/slots/{slot_id}/attendees")
def attendees(slot_id: int, user: User = Depends(require_roles(*MANAGERS)), db: Session = Depends(get_db)):
    get_slot_or_404(db, slot_id)
    rows = db.scalars(select(SlotBooking).where(
        SlotBooking.slot_id == slot_id, SlotBooking.status == "booked").order_by(SlotBooking.id)).all()
    names = {u.id: u for u in db.scalars(select(User)).all()}
    return [{"name": names[r.student_id].name, "email": names[r.student_id].email,
             "booked_at": r.created_at.isoformat()} for r in rows]