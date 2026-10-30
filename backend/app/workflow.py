from sqlalchemy import select
from sqlalchemy.orm import Session

from .approvals import current_step, ensure_steps
from .labels import role_label
from .models import Approval, Assignment, JobEvent, Ticket, User

RANK = {"new": 0, "triaged": 0, "assigned": 1, "in_progress": 2, "blocked": 2, "resolved": 3, "closed": 4}


def build_workflow(db: Session, t: Ticket) -> list:
    events = db.scalars(select(JobEvent).where(JobEvent.ticket_id == t.id).order_by(JobEvent.id)).all()
    names = {u.id: (u.name, u.role) for u in db.scalars(select(User)).all()}

    def last(*types):
        for e in reversed(events):
            if e.event_type in types:
                return e
        return None

    def who(e):
        if e is None:
            return None
        name, role = names.get(e.actor_id, ("Unknown", e.actor_role))
        return f"{name} ({role_label(role)})"

    rank = RANK.get(t.status, 0)
    reporter = names.get(t.reporter_id, ("Unknown", ""))[0]
    asg = db.scalar(select(Assignment).where(Assignment.ticket_id == t.id, Assignment.active.is_(True)))
    tech = names.get(asg.technician_id, ("Unknown", ""))[0] if asg else None
    tech_wait = f"{tech} (Technician)" if tech else "Technician"
    steps = []

    def add(key, title, desc, state, e=None, waiting=None, by=None, note=""):
        steps.append({
            "key": key, "title": title, "description": desc, "state": state,
            "at": e.created_at.isoformat() if e else None,
            "by": by if by else (who(e) if state == "done" else None),
            "waiting_for": waiting, "note": note,
        })

    logged = last("logged")
    add("submitted", "Request submitted", "The reporter describes the issue", "done", logged)
    add("categorised", "Categorised and prioritised", "AI and rules identify the type, location and priority",
        "done", logged, by="System (AI and rules)",
        note=f"{t.issue_type.replace('_', ' ')}, {t.priority} priority")

    e = last("assigned", "reassigned")
    if rank >= 1:
        add("assigned", "Technician assigned", "The Facilities Administrator assigns the best-matched technician",
            "done", e, note=f"Assigned to {tech}" if tech else "")
    else:
        add("assigned", "Technician assigned", "The Facilities Administrator assigns the best-matched technician",
            "current", waiting="Facilities Administrator or Department Manager")

    e = last("started")
    if rank >= 2:
        add("started", "Work started", "The technician begins the work", "done", e)
    elif rank == 1:
        add("started", "Work started", "The technician begins the work", "current", waiting=tech_wait)
    else:
        add("started", "Work started", "The technician begins the work", "pending")

    blocked_event = last("blocked")
    desc = "Parts are reserved, or a purchase is approved if stock is short"
    if blocked_event is None:
        add("parts", "Parts and purchase approval", desc, "skipped", note="No parts were needed")
    elif t.status == "blocked":
        ap = db.scalar(select(Approval).where(Approval.ticket_id == t.id, Approval.status == "pending")
                       .order_by(Approval.id.desc()).limit(1))
        cur = current_step(ensure_steps(db, ap)) if ap else None
        wait = f"{role_label(cur.role)} (level {cur.level})" if cur else "Approval decision"
        add("parts", "Parts and purchase approval", desc, "blocked", blocked_event,
            waiting=wait, note=blocked_event.note)
    else:
        add("parts", "Parts and purchase approval", desc, "done", last("purchase_approved", "parts_reserved"))

    e = last("completed")
    if rank >= 3:
        add("completed", "Work completed", "The technician signs off with what was done", "done", e,
            note=e.note if e else "")
    elif t.status == "in_progress":
        add("completed", "Work completed", "The technician signs off with what was done", "current", waiting=tech_wait)
    else:
        add("completed", "Work completed", "The technician signs off with what was done", "pending")

    e = last("verified")
    if t.status == "closed":
        add("verified", "Reporter confirmation", "The reporter confirms the fix", "done", e, note=e.note if e else "")
    elif t.status == "resolved":
        add("verified", "Reporter confirmation", "The reporter confirms the fix", "current", waiting=f"{reporter} (Reporter)")
    else:
        add("verified", "Reporter confirmation", "The reporter confirms the fix", "pending")

    add("closed", "Request closed", "The request is closed and the record is kept",
        "done" if t.status == "closed" else "pending", e if t.status == "closed" else None, by="System")
    return steps


def current_stage(db: Session, t: Ticket) -> dict:
    if t.status == "closed":
        return {"stage": "Closed", "waiting_for": None}
    for s in build_workflow(db, t):
        if s["state"] in ("current", "blocked"):
            return {"stage": s["title"], "waiting_for": s["waiting_for"]}
    return {"stage": "Completed", "waiting_for": None}