from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .approvals import current_step, ensure_steps
from .database import get_db
from .deps import get_current_user
from .models import Approval, Assignment, Part, Room, Ticket, User
from .sla import OPEN, sla_info

router = APIRouter(prefix="/api")


def item(db: Session, t: Ticket, action: str, tone: str = "blue") -> dict:
    room = db.get(Room, t.room_id) if t.room_id else None
    where = f"{room.building.name} - {room.name}" if room else "No location"
    return {"title": f"#{t.id} {t.title[:70]}", "detail": f"{where} · {t.priority} priority",
            "link": f"/tickets/{t.id}", "tag": t.status.replace("_", " "), "tone": tone, "action": action}


@router.get("/my-tasks")
def my_tasks(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tickets = db.scalars(select(Ticket).order_by(Ticket.id.desc())).all()
    active = {a.ticket_id: a.technician_id
              for a in db.scalars(select(Assignment).where(Assignment.active.is_(True))).all()}
    groups = []

    def group(title, items, empty):
        groups.append({"title": title, "items": items, "empty": empty})

    role = user.role
    headline = "Everything that needs your attention"
    if role == "technician":
        headline = "Jobs assigned to you"
        mine = [t for t in tickets if active.get(t.id) == user.id]
        group("To start", [item(db, t, "Start work") for t in mine if t.status == "assigned"],
              "Nothing is waiting to be started.")
        group("In progress", [item(db, t, "Finish the job", "amber") for t in mine if t.status == "in_progress"],
              "No job in progress.")
        group("Blocked: waiting for parts approval", [item(db, t, "Check the approval", "red") for t in mine if t.status == "blocked"],
              "Nothing is blocked.")
        group("Waiting for the reporter to confirm", [item(db, t, "Waiting", "gray") for t in mine if t.status == "resolved"],
              "Nothing is waiting for confirmation.")
        group("Recently closed", [item(db, t, "Done", "green") for t in mine if t.status == "closed"][:5],
              "No closed jobs yet.")
    elif role in ("facilities_admin", "department_manager", "system_admin"):
        headline = "Requests that need your action"
        group("Needs a technician", [item(db, t, "Assign a technician") for t in tickets if t.status in ("new", "triaged")],
              "Every request has a technician.")
        group("Blocked jobs", [item(db, t, "Follow the approval", "red") for t in tickets if t.status == "blocked"],
              "Nothing is blocked.")
        late = []
        for t in tickets:
            if t.status in OPEN:
                state = sla_info(t)["state"]
                if state in ("at_risk", "breached"):
                    late.append(item(db, t, "Follow up", "red" if state == "breached" else "amber"))
        group("Deadline at risk or breached", late, "No request is close to its deadline.")
    elif role == "student_faculty":
        headline = "Your requests"
        mine = [t for t in tickets if t.reporter_id == user.id]
        group("Waiting for your confirmation", [item(db, t, "Confirm the fix", "amber") for t in mine if t.status == "resolved"],
              "Nothing to confirm.")
        group("Open requests", [item(db, t, "Track") for t in mine if t.status in OPEN], "No open requests.")

    if role in ("department_manager", "procurement_approver", "system_admin"):
        if role == "procurement_approver":
            headline = "Approvals waiting for you"
        mine_ap = []
        for a in db.scalars(select(Approval).where(Approval.status == "pending").order_by(Approval.id)).all():
            cur = current_step(ensure_steps(db, a))
            if cur and cur.role == role and a.requested_by != user.id:
                part = db.get(Part, a.part_id)
                mine_ap.append({"title": f"Purchase request #{a.id}: {a.quantity} x {part.name}",
                                "detail": f"Rs {a.amount} · level {cur.level}", "link": "/approvals",
                                "tag": "waiting for you", "tone": "amber", "action": "Decide"})
        group("Approvals waiting for you", mine_ap, "No approvals are waiting.")
    return {"headline": headline, "groups": groups}