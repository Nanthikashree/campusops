import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config
from .database import get_db
from .deps import require_roles
from .models import EmailMessage, User
from .routes_assign import MANAGERS
from .ticketing import process_email

router = APIRouter(prefix="/api")


class EmailIn(BaseModel):
    message_id: str = Field(min_length=3, max_length=200)
    sender: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=150)
    subject: str = Field(default="", max_length=200)
    body: str = Field(min_length=3, max_length=1000)


class SimIn(BaseModel):
    sender: str = "student@campus.edu"
    subject: str = ""
    body: str = Field(min_length=3, max_length=1000)
    message_id: str | None = None  # reuse the same id to see duplicates being ignored


@router.post("/integrations/email")
def email_webhook(body: EmailIn, x_webhook_secret: str | None = Header(default=None),
                  db: Session = Depends(get_db)):
    """The simulated external email service calls this. It proves itself with a shared secret."""
    if x_webhook_secret != config.WEBHOOK_SECRET:
        raise HTTPException(401, "Bad webhook secret")
    result = process_email(db, body.message_id, body.sender, body.subject, body.body)
    if result["status"] == "invalid":
        raise HTTPException(422, result["message"])
    return result


@router.post("/integrations/email/simulate")
def email_simulate(body: SimIn, user: User = Depends(require_roles(*MANAGERS)), db: Session = Depends(get_db)):
    """Demo button: pretends an email just arrived."""
    mid = body.message_id or f"sim-{uuid.uuid4()}"
    result = process_email(db, mid, body.sender, body.subject, body.body)
    return {"message_id": mid, **result}


@router.get("/integrations/email/inbox")
def inbox(user: User = Depends(require_roles(*MANAGERS)), db: Session = Depends(get_db)):
    rows = db.scalars(select(EmailMessage).order_by(EmailMessage.id.desc()).limit(50)).all()
    return [{"id": m.id, "message_id": m.message_id, "from": m.sender, "subject": m.subject,
             "status": m.status, "ticket_id": m.ticket_id, "at": m.created_at.isoformat()} for m in rows]