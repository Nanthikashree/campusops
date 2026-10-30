from sqlalchemy import select
from sqlalchemy.orm import Session

from .labels import role_label
from .models import Approval, ApprovalStep, Part, Ticket, User

APPROVAL_CHAIN = [(1, "department_manager"), (2, "procurement_approver"), (3, "system_admin")]
LEVEL3_MIN_AMOUNT = 20000  # below this, the System Administrator level is skipped


def create_steps(db: Session, approval: Approval):
    for level, role in APPROVAL_CHAIN:
        skip = level == 3 and approval.amount < LEVEL3_MIN_AMOUNT
        db.add(ApprovalStep(approval_id=approval.id, level=level, role=role,
                            status="skipped" if skip else "pending"))
    db.flush()


def steps_of(db: Session, approval_id: int):
    return db.scalars(select(ApprovalStep).where(ApprovalStep.approval_id == approval_id)
                      .order_by(ApprovalStep.level)).all()


def ensure_steps(db: Session, approval: Approval):
    steps = steps_of(db, approval.id)
    if not steps and approval.status == "pending":  # requests made before levels existed
        create_steps(db, approval)
        steps = steps_of(db, approval.id)
    return steps


def current_step(steps):
    return next((s for s in steps if s.status == "pending"), None)


def approval_dict(db: Session, a: Approval, user=None) -> dict:
    part = db.get(Part, a.part_id) if a.part_id else None
    ticket = db.get(Ticket, a.ticket_id) if a.ticket_id else None
    req = db.get(User, a.requested_by)
    steps = ensure_steps(db, a)
    cur = current_step(steps) if a.status == "pending" else None
    names = {u.id: u.name for u in db.scalars(select(User)).all()}
    return {
        "id": a.id, "kind": a.kind, "status": a.status,
        "part": part.name if part else None, "quantity": a.quantity, "amount": a.amount,
        "ticket_id": a.ticket_id, "ticket": ticket.title if ticket else None,
        "requested_by": req.name if req else None, "note": a.note,
        "created_at": a.created_at.isoformat(),
        "waiting_for": role_label(cur.role) if cur else None,
        "can_decide": bool(user and cur and user.role == cur.role and a.requested_by != user.id),
        "steps": [
            {"level": s.level, "role": s.role, "role_label": role_label(s.role), "status": s.status,
             "approver": names.get(s.approver_id) if s.approver_id else None,
             "remarks": s.remarks, "at": s.decided_at.isoformat() if s.decided_at else None}
            for s in steps
        ],
    }