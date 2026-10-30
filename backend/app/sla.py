from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .events import add_event
from .models import Assignment, JobEvent, Notification, Ticket, User
from .notifications import notify, notify_role

SLA_HOURS = {"critical": 4, "high": 8, "medium": 24, "low": 72}
OPEN = ("new", "triaged", "assigned", "in_progress", "blocked")


def _naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def sla_info(t: Ticket, resolved_at=None) -> dict:
    hours = SLA_HOURS.get(t.priority, 24)
    created = _naive_utc(t.created_at)
    deadline = created + timedelta(hours=hours)
    if t.status in ("resolved", "closed"):
        done = _naive_utc(resolved_at) if resolved_at else None
        state = "met" if (done is None or done <= deadline) else "missed"
        return {"state": state, "hours": hours, "deadline": deadline.isoformat(), "minutes_left": None}
    now = _now()
    total = hours * 3600
    used = (now - created).total_seconds()
    if used >= total:
        state = "breached"
    elif used >= 0.7 * total:
        state = "at_risk"
    else:
        state = "on_track"
    return {"state": state, "hours": hours, "deadline": deadline.isoformat(),
            "minutes_left": int((deadline - now).total_seconds() // 60)}


def resolved_at_for(db: Session, t: Ticket):
    if t.status not in ("resolved", "closed"):
        return None
    e = db.scalar(select(JobEvent).where(JobEvent.ticket_id == t.id, JobEvent.event_type == "completed")
                  .order_by(JobEvent.id.desc()).limit(1))
    return e.created_at if e else None


def assignee_id(db: Session, ticket_id: int):
    a = db.scalar(select(Assignment).where(Assignment.ticket_id == ticket_id, Assignment.active.is_(True)))
    return a.technician_id if a else None


def run_sla_check(db: Session) -> int:
    """Warns at 70% of the time used, escalates at the deadline. Each warning is sent only once."""
    system = db.scalar(select(User).where(User.role == "system_admin"))
    changed = 0
    for t in db.scalars(select(Ticket).where(Ticket.status.in_(OPEN))).all():
        info = sla_info(t)
        if info["state"] not in ("at_risk", "breached"):
            continue
        kind = "sla_" + info["state"]
        already = db.scalar(select(Notification.id).where(Notification.ticket_id == t.id,
                                                          Notification.kind == kind).limit(1))
        if already:
            continue
        tech = assignee_id(db, t.id)
        if info["state"] == "at_risk":
            msg = f"Ticket #{t.id} is at risk of missing its deadline ({info['minutes_left']} min left)"
            if tech:
                notify(db, tech, msg, t.id, kind)
            notify_role(db, "facilities_admin", msg, t.id, kind)
        else:
            msg = f"Ticket #{t.id} passed its deadline and was escalated to managers"
            if tech:
                notify(db, tech, msg, t.id, kind)
            notify_role(db, "facilities_admin", msg, t.id, kind)
            notify_role(db, "department_manager", msg, t.id, kind)
            if system:
                add_event(db, t.id, "sla_breached", system, "Deadline passed. Escalated to managers automatically.")
        changed += 1
    db.commit()
    return changed