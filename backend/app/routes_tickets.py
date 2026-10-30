from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .approvals import approval_dict
from .assignment import assignee_name
from .database import get_db
from .deps import get_current_user
from .events import verify_chain
from .intake import analyze
from .models import CHANNELS, ISSUE_TYPES, PRIORITIES, Approval, Assignment, JobEvent, Room, Ticket, User
from .sla import assignee_id, resolved_at_for, sla_info
from .ticketing import create_ticket_core
from .workflow import build_workflow, current_stage

router = APIRouter(prefix="/api")


class AnalyzeIn(BaseModel):
    text: str = Field(min_length=3, max_length=500)


class TicketIn(BaseModel):
    description: str = Field(min_length=3, max_length=500)
    room_id: int | None = None
    issue_type: str = "other"
    asset: str = ""
    urgency: str = "medium"
    channel: str = "form"


def ticket_out(db: Session, t: Ticket) -> dict:
    room = db.get(Room, t.room_id) if t.room_id else None
    reporter = db.get(User, t.reporter_id)
    stage = current_stage(db, t)
    return {
        "id": t.id, "title": t.title, "description": t.description, "status": t.status,
        "priority": t.priority, "issue_type": t.issue_type, "asset": t.asset, "channel": t.channel,
        "room": f"{room.building.name} - {room.name}" if room else None,
        "reporter": reporter.name if reporter else None,
        "assignee": assignee_name(db, t.id),
        "assignee_id": assignee_id(db, t.id),
        "sla": sla_info(t, resolved_at_for(db, t)),
        "stage": stage["stage"], "waiting_for": stage["waiting_for"],
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


@router.post("/intake/analyze")
def intake_analyze(body: AnalyzeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return analyze(db, body.text)


@router.post("/tickets")
def create_ticket(body: TicketIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.issue_type not in ISSUE_TYPES:
        raise HTTPException(400, f"issue_type must be one of {ISSUE_TYPES}")
    if body.urgency not in PRIORITIES:
        raise HTTPException(400, f"urgency must be one of {PRIORITIES}")
    if body.channel not in CHANNELS:
        raise HTTPException(400, f"channel must be one of {CHANNELS}")
    if body.room_id is not None and db.get(Room, body.room_id) is None:
        raise HTTPException(400, "That room does not exist")
    t, similar = create_ticket_core(db, user, body.description, body.room_id, body.issue_type,
                                    body.asset[:100], body.urgency, body.channel)
    db.commit()
    return {**ticket_out(db, t), "similar_ticket_ids": [s.id for s in similar]}


@router.get("/tickets")
def list_tickets(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = select(Ticket).order_by(Ticket.id.desc())
    if user.role == "student_faculty":
        q = q.where(Ticket.reporter_id == user.id)  # users only see their own requests
    elif user.role == "technician":
        q = q.join(Assignment, Assignment.ticket_id == Ticket.id).where(
            Assignment.technician_id == user.id, Assignment.active.is_(True))  # technicians see their own jobs
    return [ticket_out(db, t) for t in db.scalars(q).all()]


@router.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = db.get(Ticket, ticket_id)
    hidden = t is None
    if t is not None and user.role == "student_faculty" and t.reporter_id != user.id:
        hidden = True
    if t is not None and user.role == "technician" and assignee_id(db, t.id) != user.id:
        hidden = True
    if hidden:
        raise HTTPException(404, "Ticket not found")
    names = {u.id: u.name for u in db.scalars(select(User)).all()}
    events = db.scalars(select(JobEvent).where(JobEvent.ticket_id == t.id).order_by(JobEvent.id)).all()
    approvals = db.scalars(select(Approval).where(Approval.ticket_id == t.id).order_by(Approval.id)).all()
    return {
        **ticket_out(db, t),
        "workflow": build_workflow(db, t),
        "approvals": [approval_dict(db, a, user) for a in approvals],
        "job_card": [
            {"event": e.event_type, "by": names.get(e.actor_id), "role": e.actor_role,
             "note": e.note, "at": e.created_at.isoformat()}
            for e in events
        ],
        "log_intact": verify_chain(db, t.id),
    }