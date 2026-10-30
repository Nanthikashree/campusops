from sqlalchemy import select
from sqlalchemy.orm import Session

from .events import add_event
from .intake import _has
from .models import Assignment, StaffProfile, Ticket, User

ACTIVE_STATUSES = ("assigned", "in_progress", "blocked")

# Which status can follow which. Anything else is refused.
TRANSITIONS = {
    "new": ["triaged", "assigned"],
    "triaged": ["assigned"],
    "assigned": ["in_progress","blocked"],
    "in_progress": ["blocked", "resolved"],
    "blocked": ["in_progress"],
    "resolved": ["closed", "in_progress"],
    "closed": [],
}


def change_status(ticket: Ticket, new_status: str):
    if new_status not in TRANSITIONS.get(ticket.status, []):
        raise ValueError(f"A ticket cannot go from '{ticket.status}' to '{new_status}'")
    ticket.status = new_status


def required_skill(ticket: Ticket) -> str:
    text = f"{ticket.asset} {ticket.description}".lower()
    if ticket.issue_type == "it_network":
        return "network"
    if ticket.issue_type == "equipment":
        return "equipment"
    if ticket.issue_type == "maintenance":
        if any(_has(text, w) for w in ("ac", "a/c", "air conditioner", "cooling", "hvac")):
            return "hvac"
        if any(_has(text, w) for w in ("tap", "leak", "leakage", "water", "pipe", "plumbing", "toilet")):
            return "plumbing"
        if any(_has(text, w) for w in ("light", "fan", "power", "switch", "electric", "electrical", "bulb", "socket")):
            return "electrical"
    return "general"


def active_load(db: Session, tech_id: int) -> int:
    q = (
        select(Assignment)
        .join(Ticket, Ticket.id == Assignment.ticket_id)
        .where(
            Assignment.technician_id == tech_id,
            Assignment.active.is_(True),
            Ticket.status.in_(ACTIVE_STATUSES),
        )
    )
    return len(db.scalars(q).all())


def assignee_name(db: Session, ticket_id: int):
    a = db.scalar(select(Assignment).where(Assignment.ticket_id == ticket_id, Assignment.active.is_(True)))
    if a is None:
        return None
    u = db.get(User, a.technician_id)
    return u.name if u else None


def rank_technicians(db: Session, ticket: Ticket, exclude_ids=()):
    skill = required_skill(ticket)
    rows = db.execute(
        select(User, StaffProfile)
        .join(StaffProfile, StaffProfile.user_id == User.id)
        .where(User.role == "technician")
    ).all()
    out = []
    for user, prof in rows:
        skills = [s.strip() for s in prof.skills.split(",") if s.strip()]
        load = active_load(db, user.id)
        item = {"technician_id": user.id, "name": user.name, "skills": skills,
                "active_jobs": load, "eligible": True, "score": 0, "why": []}
        if user.id in exclude_ids:
            item["eligible"] = False
            item["why"].append("is going on leave")
        elif prof.status != "available":
            item["eligible"] = False
            item["why"].append("is on leave")
        elif load >= prof.max_jobs:
            item["eligible"] = False
            item["why"].append(f"is at full capacity ({load}/{prof.max_jobs} jobs)")
        else:
            if skill in skills:
                points = 50
                item["why"].append(f"has the '{skill}' skill (+50)")
            elif "general" in skills:
                points = 15
                item["why"].append(f"has no '{skill}' skill but can do general work (+15)")
            else:
                points = None
                item["eligible"] = False
                item["why"].append(f"does not have the '{skill}' skill")
            if points is not None:
                item["score"] = points - 10 * load
                item["why"].append(f"has {load} active job(s) (-{10 * load})")
        out.append(item)
    # eligible first, then highest score, then lowest id (so ties are predictable)
    out.sort(key=lambda x: (not x["eligible"], -x["score"], x["technician_id"]))
    return skill, out


def assign_ticket(db: Session, ticket: Ticket, actor: User, technician_id=None, exclude_ids=(), kind=None):
    if ticket.status not in ("new", "triaged", "assigned"):
        raise ValueError("Work has already started on this ticket, so it cannot be reassigned")

    skill, ranking = rank_technicians(db, ticket, exclude_ids)

    if technician_id is not None:
        chosen = next((r for r in ranking if r["technician_id"] == technician_id), None)
        if chosen is None:
            raise ValueError("That user is not a technician")
        if not chosen["eligible"]:
            raise ValueError(f"{chosen['name']} cannot take this job: " + ", ".join(chosen["why"]))
        reason = f"Chosen by {actor.name}. {chosen['name']} " + ", ".join(chosen["why"])
    else:
        chosen = ranking[0] if ranking and ranking[0]["eligible"] else None
        if chosen is None:
            return None, ranking
        reason = f"Best match: {chosen['name']} " + ", ".join(chosen["why"])

    olds = db.scalars(
        select(Assignment).where(Assignment.ticket_id == ticket.id, Assignment.active.is_(True))
    ).all()
    for old in olds:
        old.active = False
    db.add(Assignment(ticket_id=ticket.id, technician_id=chosen["technician_id"],
                      assigned_by=actor.id, active=True, reason=reason))
    if ticket.status in ("new", "triaged"):
        change_status(ticket, "assigned")
    add_event(db, ticket.id, kind or ("reassigned" if olds else "assigned"), actor, reason)
    return chosen, ranking