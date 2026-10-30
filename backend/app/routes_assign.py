from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .assignment import active_load, assign_ticket, change_status, rank_technicians
from .database import get_db
from .deps import require_roles
from .events import add_event
from .models import Assignment, StaffProfile, Ticket, User
from .routes_tickets import ticket_out
from .parts import consume_reservations
router = APIRouter(prefix="/api")
MANAGERS = ("facilities_admin", "department_manager", "system_admin")


class AssignIn(BaseModel):
    technician_id: int | None = None


class StatusIn(BaseModel):
    status: str


class DoneIn(BaseModel):
    note: str = Field(min_length=3, max_length=500)


def get_ticket_or_404(db: Session, ticket_id: int) -> Ticket:
    t = db.get(Ticket, ticket_id)
    if t is None:
        raise HTTPException(404, "Ticket not found")
    return t


def check_is_my_job(db: Session, ticket_id: int, user: User):
    a = db.scalar(select(Assignment).where(Assignment.ticket_id == ticket_id, Assignment.active.is_(True)))
    if a is None or a.technician_id != user.id:
        raise HTTPException(403, "This job is not assigned to you")


@router.get("/tickets/{ticket_id}/assignment-preview")
def assignment_preview(ticket_id: int, user: User = Depends(require_roles(*MANAGERS)), db: Session = Depends(get_db)):
    t = get_ticket_or_404(db, ticket_id)
    skill, ranking = rank_technicians(db, t)
    best = ranking[0]["name"] if ranking and ranking[0]["eligible"] else None
    return {"needed_skill": skill, "recommended": best, "ranking": ranking}


@router.post("/tickets/{ticket_id}/assign")
def assign(ticket_id: int, body: AssignIn, user: User = Depends(require_roles(*MANAGERS)), db: Session = Depends(get_db)):
    t = get_ticket_or_404(db, ticket_id)
    try:
        chosen, ranking = assign_ticket(db, t, user, technician_id=body.technician_id)
    except ValueError as e:
        db.rollback()
        raise HTTPException(409, str(e))
    if chosen is None:
        db.rollback()
        raise HTTPException(409, "No technician is available for this job right now")
    db.commit()
    return {"ticket": ticket_out(db, t), "chosen": chosen, "ranking": ranking}


@router.post("/tickets/{ticket_id}/start")
def start_work(ticket_id: int, user: User = Depends(require_roles("technician")), db: Session = Depends(get_db)):
    t = get_ticket_or_404(db, ticket_id)
    check_is_my_job(db, t.id, user)
    try:
        change_status(t, "in_progress")
    except ValueError as e:
        raise HTTPException(409, str(e))
    add_event(db, t.id, "started", user, "Work started")
    db.commit()
    return ticket_out(db, t)


@router.post("/tickets/{ticket_id}/complete")
def complete_work(ticket_id: int, body: DoneIn, user: User = Depends(require_roles("technician")), db: Session = Depends(get_db)):
    t = get_ticket_or_404(db, ticket_id)
    check_is_my_job(db, t.id, user)
    try:
        change_status(t, "resolved")
    except ValueError as e:
        raise HTTPException(409, str(e))
    add_event(db, t.id, "completed", user, body.note)
    consume_reservations(db, t, user)
    db.commit()
    return ticket_out(db, t)


@router.get("/staff")
def list_staff(user: User = Depends(require_roles(*MANAGERS)), db: Session = Depends(get_db)):
    rows = db.execute(
        select(User, StaffProfile).join(StaffProfile, StaffProfile.user_id == User.id).order_by(User.id)
    ).all()
    return [
        {"id": u.id, "name": u.name, "skills": p.skills.split(","), "status": p.status,
         "active_jobs": active_load(db, u.id), "max_jobs": p.max_jobs}
        for u, p in rows
    ]


@router.post("/staff/{user_id}/status")
def set_staff_status(user_id: int, body: StatusIn, user: User = Depends(require_roles(*MANAGERS)), db: Session = Depends(get_db)):
    if body.status not in ("available", "on_leave"):
        raise HTTPException(400, "status must be 'available' or 'on_leave'")
    prof = db.get(StaffProfile, user_id)
    if prof is None:
        raise HTTPException(404, "Technician not found")
    prof.status = body.status
    db.flush()

    moved = []
    if body.status == "on_leave":
        tickets = db.scalars(
            select(Ticket)
            .join(Assignment, Assignment.ticket_id == Ticket.id)
            .where(Assignment.technician_id == user_id, Assignment.active.is_(True), Ticket.status == "assigned")
        ).all()
        for t in tickets:
            try:
                chosen, _ = assign_ticket(db, t, user, exclude_ids=(user_id,), kind="reassigned")
            except ValueError:
                chosen = None
            moved.append({
                "ticket_id": t.id,
                "new_technician": chosen["name"] if chosen else None,
                "note": "" if chosen else "No one is free. A manager must assign this by hand.",
            })
    db.commit()
    return {"status": body.status, "reassigned": moved}