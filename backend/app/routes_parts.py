from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .deps import require_roles
from .models import Approval, Part, Ticket, User
from .parts import available, decide_approval, request_part
from .routes_assign import MANAGERS, check_is_my_job, get_ticket_or_404
from .routes_tickets import ticket_out

router = APIRouter(prefix="/api")
STAFF = ("technician", *MANAGERS, "procurement_approver")


class PartIn(BaseModel):
    part_id: int
    quantity: int = Field(default=1, ge=1, le=50)


class DecideIn(BaseModel):
    decision: str
    note: str = Field(default="", max_length=300)


def approval_dict(db: Session, a: Approval) -> dict:
    part = db.get(Part, a.part_id) if a.part_id else None
    ticket = db.get(Ticket, a.ticket_id) if a.ticket_id else None
    req = db.get(User, a.requested_by)
    dec = db.get(User, a.decided_by) if a.decided_by else None
    return {
        "id": a.id, "kind": a.kind, "status": a.status,
        "part": part.name if part else None, "quantity": a.quantity, "amount": a.amount,
        "ticket_id": a.ticket_id, "ticket": ticket.title if ticket else None,
        "requested_by": req.name if req else None, "decided_by": dec.name if dec else None,
        "note": a.note, "created_at": a.created_at.isoformat(),
    }


@router.get("/parts")
def list_parts(user: User = Depends(require_roles(*STAFF)), db: Session = Depends(get_db)):
    return [
        {"id": p.id, "name": p.name, "stock": p.stock, "reserved": p.reserved,
         "available": available(p), "min_stock": p.min_stock, "unit_cost": p.unit_cost,
         "low": available(p) < p.min_stock}
        for p in db.scalars(select(Part).order_by(Part.id)).all()
    ]


@router.post("/tickets/{ticket_id}/parts")
def add_part(ticket_id: int, body: PartIn, user: User = Depends(require_roles("technician", *MANAGERS)),
             db: Session = Depends(get_db)):
    t = get_ticket_or_404(db, ticket_id)
    if user.role == "technician":
        check_is_my_job(db, t.id, user)
    part = db.get(Part, body.part_id)
    if part is None:
        raise HTTPException(404, "Part not found")
    try:
        result = request_part(db, t, part, body.quantity, user)
    except ValueError as e:
        db.rollback()
        raise HTTPException(409, str(e))
    db.commit()
    return {**result, "ticket": ticket_out(db, t)}


@router.get("/approvals")
def list_approvals(status: str | None = None,
                   user: User = Depends(require_roles("procurement_approver", *MANAGERS)),
                   db: Session = Depends(get_db)):
    q = select(Approval).order_by(Approval.id.desc())
    if status:
        q = q.where(Approval.status == status)
    return [approval_dict(db, a) for a in db.scalars(q).all()]


@router.post("/approvals/{approval_id}/decide")
def decide(approval_id: int, body: DecideIn, user: User = Depends(require_roles("procurement_approver")),
           db: Session = Depends(get_db)):
    a = db.get(Approval, approval_id)
    if a is None:
        raise HTTPException(404, "Approval not found")
    try:
        result = decide_approval(db, a, user, body.decision, body.note)
    except PermissionError as e:
        db.rollback()
        raise HTTPException(403, str(e))
    except ValueError as e:
        db.rollback()
        raise HTTPException(409, str(e))
    db.commit()
    return {**result, "approval": approval_dict(db, a)}