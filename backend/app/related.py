from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Ticket

OPEN = ("new", "triaged", "assigned", "in_progress", "blocked")


def find_similar(db: Session, t: Ticket):
    """Open tickets from the last hour about the same thing: same room and type,
    or any network complaint (a Wi-Fi outage is campus-wide)."""
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    rows = db.scalars(select(Ticket).where(
        Ticket.id != t.id, Ticket.status.in_(OPEN), Ticket.created_at >= since,
        Ticket.issue_type == t.issue_type)).all()
    return [s for s in rows if t.issue_type == "it_network" or (t.room_id is not None and s.room_id == t.room_id)]