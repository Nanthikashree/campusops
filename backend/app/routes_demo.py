from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from . import seed_bookings, seed_parts, seed_slots
from .assignment import assign_ticket, change_status
from .database import get_db
from .deps import require_roles
from .events import add_event
from .models import (Approval, ApprovalStep, Assignment, Booking, EmailMessage, JobEvent, Notification,
                     Part, PartReservation, Room, Slot, SlotBooking, StaffProfile, Ticket, User)
from .parts import request_part
from .routes_assign import MANAGERS
from .routes_bookings import room_impact
from .sla import run_sla_check, sla_info
from .ticketing import create_ticket_core

router = APIRouter(prefix="/api")


def need_user(db: Session, email: str) -> User:
    u = db.scalar(select(User).where(User.email == email))
    if u is None:
        raise HTTPException(409, f"Demo user {email} is missing. Run the seed first.")
    return u


@router.post("/demo/scenario/exam-ac-failure")
def scenario_exam(user: User = Depends(require_roles(*MANAGERS)), db: Session = Depends(get_db)):
    student = need_user(db, "student@campus.edu")
    room = db.scalar(select(Room).where(Room.name == "B203"))
    part = db.scalar(select(Part).where(Part.name == "AC Capacitor"))
    if room is None or part is None:
        raise HTTPException(409, "Rooms or parts are missing. Run the seeds first.")
    t, _ = create_ticket_core(db, student, "AC not working in B203. The mid-term exam is scheduled there tomorrow at 11 AM",
                              room.id, "maintenance", "AC", "high", "chat")
    room.status = "unusable"
    add_event(db, t.id, "room_marked_unusable", user, f"{room.name} marked unusable until the AC is fixed")
    affected = room_impact(db, room)
    chosen, _ranking = assign_ticket(db, t, user)
    if chosen is None:
        db.rollback()
        raise HTTPException(409, "No technician is free. Reset the demo and try again.")
    tech = db.get(User, chosen["technician_id"])
    change_status(t, "in_progress")
    add_event(db, t.id, "started", tech, "Work started (demo)")
    part_result = request_part(db, t, part, 1, tech)
    db.commit()
    return {
        "ticket_id": t.id, "room": room.name, "technician": tech.name,
        "bookings_affected": [{"booking": a["booking"]["title"], "kind": a["booking"]["kind"],
                               "alternatives": [x["name"] for x in a["alternatives"]]} for a in affected],
        "parts": part_result["message"],
        "next_step": "Log in as manager, then procurement, and approve the purchase request.",
    }


@router.post("/demo/scenario/wifi-outage")
def scenario_wifi(user: User = Depends(require_roles(*MANAGERS)), db: Session = Depends(get_db)):
    student = need_user(db, "student@campus.edu")
    faculty = need_user(db, "faculty@campus.edu")
    reports = [
        (student, "Wi-Fi is down in the Science Block"),
        (faculty, "No internet in Lab 2, students cannot submit assignments"),
        (student, "Library Wi-Fi is not connecting"),
        (faculty, "Cannot log in to the campus network from Block A"),
    ]
    tickets = [create_ticket_core(db, u, text, None, "it_network", "Router", "high", "chat")[0] for u, text in reports]
    lead = tickets[0]
    chosen, _ = assign_ticket(db, lead, user)
    if chosen is None:
        db.rollback()
        raise HTTPException(409, "No network technician is free. Reset the demo and try again.")
    first = db.get(User, chosen["technician_id"])
    db.get(StaffProfile, first.id).status = "on_leave"
    db.flush()
    moved, _ = assign_ticket(db, lead, user, exclude_ids=(first.id,), kind="reassigned")
    lead.created_at = lead.created_at - timedelta(hours=9)  # push it past its 8 hour deadline
    db.flush()
    run_sla_check(db)
    return {
        "ticket_ids": [t.id for t in tickets], "first_technician": first.name,
        "reassigned_to": moved["name"] if moved else None,
        "sla": sla_info(lead)["state"],
        "next_step": "Open the incidents list: the 4 complaints appear as one incident, and the lead ticket was escalated.",
    }


@router.post("/demo/reset")
def reset(user: User = Depends(require_roles("system_admin", "facilities_admin")), db: Session = Depends(get_db)):
    for model in (Notification, EmailMessage, PartReservation, ApprovalStep, Approval, JobEvent,
                  Assignment, Ticket, SlotBooking, Slot, Booking):
        db.execute(delete(model))
    for r in db.scalars(select(Room)).all():
        r.status = "available"
    for s in db.scalars(select(StaffProfile)).all():
        s.status = "available"
    stock = {name: qty for name, qty, _m, _c in seed_parts.PARTS}
    for p in db.scalars(select(Part)).all():
        p.stock = stock.get(p.name, p.stock)
        p.reserved = 0
    db.commit()
    seed_bookings.run()
    seed_slots.run()
    return {"ok": True, "message": "Demo data reset. Users, rooms and staff stay as they were."}