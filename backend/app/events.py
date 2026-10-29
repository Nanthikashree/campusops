import hashlib
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import JobEvent


def _ts(dt: datetime) -> str:
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def _hash(prev_hash, ticket_id, event_type, actor_id, note, created_at) -> str:
    raw = "|".join([prev_hash, str(ticket_id), event_type, str(actor_id), note, _ts(created_at)])
    return hashlib.sha256(raw.encode()).hexdigest()


def add_event(db: Session, ticket_id: int, event_type: str, actor, note: str = "") -> JobEvent:
    """Adds one entry to the job card. Entries are only ever added, never edited."""
    last = db.scalar(
        select(JobEvent).where(JobEvent.ticket_id == ticket_id).order_by(JobEvent.id.desc()).limit(1)
    )
    prev = last.hash if last else ""
    created = datetime.now(timezone.utc)
    ev = JobEvent(
        ticket_id=ticket_id, event_type=event_type, actor_id=actor.id,
        actor_role=actor.role, note=note, created_at=created, prev_hash=prev,
    )
    ev.hash = _hash(prev, ticket_id, event_type, actor.id, note, created)
    db.add(ev)
    db.flush()  # so the next event in the same request can see this one
    return ev


def verify_chain(db: Session, ticket_id: int) -> bool:
    """True if no entry has been changed or removed since it was written."""
    events = db.scalars(
        select(JobEvent).where(JobEvent.ticket_id == ticket_id).order_by(JobEvent.id)
    ).all()
    prev = ""
    for ev in events:
        expected = _hash(prev, ev.ticket_id, ev.event_type, ev.actor_id, ev.note, ev.created_at)
        if ev.prev_hash != prev or ev.hash != expected:
            return False
        prev = ev.hash
    return True