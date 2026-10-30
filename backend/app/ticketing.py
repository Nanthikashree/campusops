from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .events import add_event
from .intake import analyze
from .models import EmailMessage, Ticket, User
from .notifications import notify, notify_role
from .related import find_similar


def create_ticket_core(db: Session, user: User, description: str, room_id, issue_type: str,
                       asset: str, urgency: str, channel: str):
    t = Ticket(title=description[:80], description=description, room_id=room_id, reporter_id=user.id,
               issue_type=issue_type, asset=(asset or "")[:100], channel=channel, status="new", priority=urgency)
    db.add(t)
    db.flush()
    add_event(db, t.id, "logged", user, f"Reported via {channel}: {description}")
    similar = find_similar(db, t)
    for s in similar:
        add_event(db, t.id, "linked", user, f"Looks related to #{s.id}: {s.title[:60]}")
        add_event(db, s.id, "linked", user, f"Another report (#{t.id}) looks related to this one")
    notify_role(db, "facilities_admin", f"New {t.priority} request #{t.id}: {t.title[:60]}", t.id, "new_ticket")
    return t, similar


def process_email(db: Session, message_id: str, sender: str, subject: str, body: str) -> dict:
    dup = {"status": "duplicate", "message": "This email was already handled. Nothing new was created."}
    existing = db.scalar(select(EmailMessage).where(EmailMessage.message_id == message_id))
    if existing is not None:
        return {**dup, "ticket_id": existing.ticket_id}
    sender = sender.strip().lower()
    try:
        msg = EmailMessage(message_id=message_id, sender=sender, subject=subject[:200], body=body)
        db.add(msg)
        user = db.scalar(select(User).where(User.email == sender))
        if user is None:
            msg.status = "invalid"
            db.commit()
            return {"status": "invalid", "message": "The sender is not a registered campus user"}
        text = f"{subject}. {body}".strip(". ")[:500]
        result = analyze(db, text)
        room = result["room"]
        t, similar = create_ticket_core(db, user, text, room["id"] if room else None,
                                        result["issue_type"], result["asset"], result["urgency"], "email")
        msg.status = "processed"
        msg.ticket_id = t.id
        if result["question"]:
            notify(db, user.id, f"About your email (ticket #{t.id}): {result['question']}", t.id, "clarification")
        db.commit()
        return {"status": "processed", "ticket_id": t.id, "issue_type": result["issue_type"],
                "room": room["name"] if room else None, "urgency": result["urgency"],
                "question": result["question"], "similar_ticket_ids": [s.id for s in similar]}
    except IntegrityError:
        db.rollback()
        again = db.scalar(select(EmailMessage).where(EmailMessage.message_id == message_id))
        return {**dup, "ticket_id": again.ticket_id if again else None}