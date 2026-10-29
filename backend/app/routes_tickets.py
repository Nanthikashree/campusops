from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .assignment import assignee_name
from .database import get_db
from .deps import get_current_user
from .events import add_event, verify_chain
from .intake import analyze
from .models import CHANNELS, ISSUE_TYPES, PRIORITIES, JobEvent, Room, Ticket, User

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
    return {
        "id": t.id, "title": t.title, "description": t.description, "status": t.status,
        "priority": t.priority, "issue_type": t.issue_type, "asset": t.asset, "channel": t.channel,
        "room": f"{room.building.name} - {room.name}" if room else None,
        "reporter": reporter.name if reporter else None,
        "assignee": assignee_name(db, t.id),
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

    t = Ticket(
        title=body.description[:80], description=body.description, room_id=body.room_id,
        reporter_id=user.id, issue_type=body.issue_type, asset=body.asset[:100],
        channel=body.channel, status="new", priority=body.urgency,
    )
    db.add(t)
    db.flush()  # gives the ticket an id
    add_event(db, t.id, "logged", user, f"Reported via {body.channel}: {body.description}")
    db.commit()
    return ticket_out(db, t)


@router.get("/tickets")
def list_tickets(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = select(Ticket).order_by(Ticket.id.desc())
    if user.role == "student_faculty":
        q = q.where(Ticket.reporter_id == user.id)  # users only see their own
    return [ticket_out(db, t) for t in db.scalars(q).all()]


@router.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = db.get(Ticket, ticket_id)
    if t is None or (user.role == "student_faculty" and t.reporter_id != user.id):
        raise HTTPException(404, "Ticket not found")
    names = {u.id: u.name for u in db.scalars(select(User)).all()}
    events = db.scalars(select(JobEvent).where(JobEvent.ticket_id == t.id).order_by(JobEvent.id)).all()
    return {
        **ticket_out(db, t),
        "job_card": [
            {"event": e.event_type, "by": names.get(e.actor_id), "role": e.actor_role,
             "note": e.note, "at": e.created_at.isoformat()}
            for e in events
        ],
        "log_intact": verify_chain(db, t.id),
    }