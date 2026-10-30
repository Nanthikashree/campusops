from sqlalchemy import select
from sqlalchemy.orm import Session

from .assignment import change_status
from .events import add_event
from .models import Approval, Part, PartReservation, Ticket, User


def available(part: Part) -> int:
    return part.stock - part.reserved


def request_part(db: Session, ticket: Ticket, part: Part, qty: int, actor: User) -> dict:
    if ticket.status not in ("assigned", "in_progress", "blocked"):
        raise ValueError("Parts can only be requested while the job is assigned, in progress or blocked")
    pending = db.scalar(select(Approval).where(
        Approval.ticket_id == ticket.id, Approval.part_id == part.id, Approval.status == "pending"))
    if pending is not None:
        raise ValueError(f"A purchase request for {part.name} is already waiting for approval")

    avail = max(available(part), 0)
    if avail >= qty:
        part.reserved += qty
        db.add(PartReservation(ticket_id=ticket.id, part_id=part.id, quantity=qty, status="reserved"))
        add_event(db, ticket.id, "parts_reserved", actor, f"Reserved {qty} x {part.name}")
        return {"result": "reserved", "message": f"Reserved {qty} x {part.name}"}

    shortfall = qty - avail
    db.add(PartReservation(ticket_id=ticket.id, part_id=part.id, quantity=qty, status="waiting"))
    approval = Approval(kind="purchase", ticket_id=ticket.id, part_id=part.id, quantity=shortfall,
                        amount=shortfall * part.unit_cost, requested_by=actor.id)
    db.add(approval)
    if ticket.status != "blocked":
        change_status(ticket, "blocked")
    db.flush()
    msg = (f"Blocked: {part.name} is short by {shortfall}. "
           f"Purchase request #{approval.id} (Rs {approval.amount}) sent for approval.")
    add_event(db, ticket.id, "blocked", actor, msg)
    return {"result": "blocked", "approval_id": approval.id, "message": msg}


def decide_approval(db: Session, approval: Approval, actor: User, decision: str, note: str = "") -> dict:
    if approval.status != "pending":
        raise ValueError(f"This request was already {approval.status}")
    if approval.requested_by == actor.id:
        raise PermissionError("You cannot decide your own request")
    if decision not in ("approve", "reject"):
        raise ValueError("decision must be 'approve' or 'reject'")

    ticket = db.get(Ticket, approval.ticket_id) if approval.ticket_id else None
    part = db.get(Part, approval.part_id)
    waiting = db.scalar(select(PartReservation).where(
        PartReservation.ticket_id == approval.ticket_id,
        PartReservation.part_id == approval.part_id,
        PartReservation.status == "waiting"))
    approval.decided_by = actor.id
    approval.note = note

    if decision == "reject":
        approval.status = "rejected"
        if waiting:
            waiting.status = "cancelled"
        if ticket:
            add_event(db, ticket.id, "purchase_rejected", actor,
                      f"Purchase of {part.name} rejected. {note}".strip())
        return {"outcome": "rejected", "message": "Request rejected. The job stays blocked until a manager decides what to do."}

    # Approving: re-check the situation right now, not as it was when the request was made.
    if ticket is None or ticket.status != "blocked" or waiting is None:
        approval.status = "cancelled"
        approval.note = (note + " " if note else "") + "Cancelled: the job is no longer waiting for this part."
        if waiting:
            waiting.status = "cancelled"
        return {"outcome": "cancelled", "message": "The job is no longer waiting for this part, so nothing was bought."}

    part.stock += approval.quantity  # simulated purchase: the parts "arrive"
    approval.status = "approved"
    add_event(db, ticket.id, "purchase_approved", actor,
              f"Approved purchase of {approval.quantity} x {part.name} (Rs {approval.amount})")
    if available(part) >= waiting.quantity:
        part.reserved += waiting.quantity
        waiting.status = "reserved"
        change_status(ticket, "in_progress")
        add_event(db, ticket.id, "parts_reserved", actor,
                  f"Reserved {waiting.quantity} x {part.name}. Work can continue.")
        return {"outcome": "approved", "ticket_status": "in_progress",
                "message": "Approved. The part is reserved and the job is unblocked."}
    return {"outcome": "approved", "ticket_status": ticket.status,
            "message": "Approved, but there is still not enough stock. The job stays blocked."}


def consume_reservations(db: Session, ticket: Ticket, actor: User) -> list:
    used = []
    rows = db.scalars(select(PartReservation).where(
        PartReservation.ticket_id == ticket.id, PartReservation.status == "reserved")).all()
    for r in rows:
        part = db.get(Part, r.part_id)
        part.reserved -= r.quantity
        part.stock -= r.quantity
        r.status = "consumed"
        used.append(f"{r.quantity} x {part.name}")
    if used:
        add_event(db, ticket.id, "parts_used", actor, "Parts used: " + ", ".join(used))
    return used