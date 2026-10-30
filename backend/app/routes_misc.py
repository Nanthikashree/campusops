from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .assignment import change_status
from .database import get_db
from .deps import get_current_user, require_roles
from .events import add_event
from .models import PRIORITIES, Approval, JobEvent, Notification, Part, Room, Ticket, User
from .notifications import notify
from .routes_assign import MANAGERS, get_ticket_or_404
from .routes_tickets import ticket_out
from .sla import OPEN, assignee_id, run_sla_check, sla_info

router = APIRouter(prefix="/api")
STAFF = ("technician", *MANAGERS, "procurement_approver")


@router.get("/notifications")
def my_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Notification).where(Notification.user_id == user.id)
                      .order_by(Notification.id.desc()).limit(50)).all()
    return {
        "unread": sum(1 for n in rows if not n.is_read),
        "items": [{"id": n.id, "ticket_id": n.ticket_id, "kind": n.kind, "message": n.message,
                   "read": n.is_read, "at": n.created_at.isoformat()} for n in rows],
    }


@router.post("/notifications/read-all")
def read_all(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for n in db.scalars(select(Notification).where(Notification.user_id == user.id,
                                                   Notification.is_read.is_(False))).all():
        n.is_read = True
    db.commit()
    return {"ok": True}


@router.get("/dashboard/summary")
def summary(user: User = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    run_sla_check(db)
    tickets = db.scalars(select(Ticket)).all()
    done = {}
    for e in db.scalars(select(JobEvent).where(JobEvent.event_type == "completed").order_by(JobEvent.id)).all():
        done[e.ticket_id] = e.created_at
    open_t = [t for t in tickets if t.status in OPEN]
    states = [sla_info(t)["state"] for t in open_t]
    finished = [t for t in tickets if t.status in ("resolved", "closed")]
    met = sum(1 for t in finished if sla_info(t, done.get(t.id))["state"] == "met")
    by_type = {}
    for t in tickets:
        by_type[t.issue_type] = by_type.get(t.issue_type, 0) + 1
    parts = db.scalars(select(Part)).all()
    return {
        "open_requests": len(open_t),
        "in_progress": sum(1 for t in open_t if t.status == "in_progress"),
        "blocked": sum(1 for t in open_t if t.status == "blocked"),
        "resolved": len(finished),
        "sla_at_risk": states.count("at_risk"),
        "sla_breached": states.count("breached"),
        "sla_compliance": round(100 * met / len(finished)) if finished else None,
        "pending_approvals": len(db.scalars(select(Approval).where(Approval.status == "pending")).all()),
        "low_stock_parts": sum(1 for p in parts if p.stock - p.reserved < p.min_stock),
        "unusable_rooms": len(db.scalars(select(Room).where(Room.status == "unusable")).all()),
        "by_type": by_type,
    }


@router.get("/incidents")
def incidents(user: User = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    rows = db.scalars(select(Ticket).where(Ticket.status.in_(OPEN), Ticket.created_at >= since)).all()
    groups = {}
    for t in rows:
        if t.issue_type == "it_network":
            key = ("it_network", None)
        elif t.room_id:
            key = (t.issue_type, t.room_id)
        else:
            continue
        groups.setdefault(key, []).append(t)
    out = []
    for (kind, room_id), ts in groups.items():
        if len(ts) < 2:
            continue
        where = "campus-wide" if room_id is None else db.get(Room, room_id).name
        top = max(ts, key=lambda x: PRIORITIES.index(x.priority)).priority
        label = kind.replace("_", " ")
        out.append({"title": f"{label} problem ({where})", "count": len(ts), "priority": top,
                    "ticket_ids": [t.id for t in ts],
                    "summary": f"{len(ts)} related complaints about {label} ({where}). Handle them together."})
    out.sort(key=lambda x: -x["count"])
    return out


class VerifyIn(BaseModel):
    fixed: bool
    comment: str = Field(default="", max_length=300)
    rating: int | None = Field(default=None, ge=1, le=5)


@router.post("/tickets/{ticket_id}/verify")
def verify(ticket_id: int, body: VerifyIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = get_ticket_or_404(db, ticket_id)
    if t.reporter_id != user.id:
        raise HTTPException(403, "Only the person who reported it can confirm the fix")
    if t.status != "resolved":
        raise HTTPException(409, "Only a resolved request can be confirmed")
    try:
        if body.fixed:
            change_status(t, "closed")
            note = "Reporter confirmed the fix"
            if body.rating:
                note += f" (rating {body.rating}/5)"
            if body.comment:
                note += f". {body.comment}"
            add_event(db, t.id, "verified", user, note)
        else:
            change_status(t, "in_progress")
            add_event(db, t.id, "reopened", user, ("Reporter says it is not fixed. " + body.comment).strip())
            tech = assignee_id(db, t.id)
            if tech:
                notify(db, tech, f"Ticket #{t.id} was reopened by the reporter", t.id, "reopened")
    except ValueError as e:
        raise HTTPException(409, str(e))
    db.commit()
    return ticket_out(db, t)


@router.post("/sla/age/{ticket_id}")
def age_ticket(ticket_id: int, hours: int = 5, user: User = Depends(require_roles(*MANAGERS)),
               db: Session = Depends(get_db)):
    """DEMO HELPER: makes a ticket look older, so you can show the SLA warning and escalation live."""
    if not 1 <= hours <= 200:
        raise HTTPException(400, "hours must be between 1 and 200")
    t = get_ticket_or_404(db, ticket_id)
    t.created_at = t.created_at - timedelta(hours=hours)
    db.commit()
    run_sla_check(db)
    return ticket_out(db, t)