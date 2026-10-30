from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Notification, User


def notify(db: Session, user_id: int, message: str, ticket_id=None, kind: str = "info"):
    db.add(Notification(user_id=user_id, ticket_id=ticket_id, kind=kind, message=message))


def notify_role(db: Session, role: str, message: str, ticket_id=None, kind: str = "info"):
    for u in db.scalars(select(User).where(User.role == role)).all():
        notify(db, u.id, message, ticket_id, kind)