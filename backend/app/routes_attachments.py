from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .attachments import KINDS, MAX_PER_KIND, UPLOAD_DIR, count_kind, decode_image, store
from .database import get_db
from .deps import get_current_user
from .events import add_event
from .models import Attachment, Ticket, User
from .routes_assign import MANAGERS, get_ticket_or_404
from .sla import assignee_id

router = APIRouter(prefix="/api")

KIND_TEXT = {"complaint": "Complaint photo", "before": "Before-work photo", "after": "After-work photo"}


class UploadIn(BaseModel):
    kind: str
    data_url: str = Field(max_length=3_500_000)
    caption: str = Field(default="", max_length=200)


def can_view(db: Session, user: User, t: Ticket) -> bool:
    if user.role == "student_faculty":
        return t.reporter_id == user.id
    if user.role == "technician":
        return assignee_id(db, t.id) == user.id
    return True


@router.post("/tickets/{ticket_id}/attachments")
def upload(ticket_id: int, body: UploadIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = get_ticket_or_404(db, ticket_id)
    if body.kind not in KINDS:
        raise HTTPException(400, f"kind must be one of {list(KINDS)}")

    if body.kind == "complaint":
        if not (t.reporter_id == user.id or user.role in MANAGERS):
            raise HTTPException(403, "Only the person who reported it can add complaint photos")
        if t.status == "closed":
            raise HTTPException(409, "This request is closed")
    else:
        if user.role != "technician" or assignee_id(db, t.id) != user.id:
            raise HTTPException(403, "Only the assigned technician can add before and after photos")
        if body.kind == "before" and t.status not in ("assigned", "in_progress", "blocked"):
            raise HTTPException(409, "Before photos must be added before the work is finished")
        if body.kind == "after" and t.status != "in_progress":
            raise HTTPException(409, "After photos can be added while the job is in progress, before you mark it complete")

    if count_kind(db, t.id, body.kind) >= MAX_PER_KIND:
        raise HTTPException(409, f"You can add at most {MAX_PER_KIND} photos of this kind")
    try:
        raw, ctype, ext = decode_image(body.data_url)
    except ValueError as e:
        raise HTTPException(400, str(e))

    a = Attachment(ticket_id=t.id, kind=body.kind, filename=store(raw, ext), content_type=ctype,
                   size=len(raw), caption=body.caption, uploaded_by=user.id)
    db.add(a)
    db.flush()
    add_event(db, t.id, "photo_added", user, f"{KIND_TEXT[body.kind]} added")
    db.commit()
    return {"id": a.id, "kind": a.kind}


@router.get("/tickets/{ticket_id}/attachments")
def list_attachments(ticket_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = get_ticket_or_404(db, ticket_id)
    if not can_view(db, user, t):
        raise HTTPException(404, "Ticket not found")
    names = {u.id: u for u in db.scalars(select(User)).all()}
    rows = db.scalars(select(Attachment).where(Attachment.ticket_id == t.id).order_by(Attachment.id)).all()
    return [
        {"id": a.id, "kind": a.kind, "caption": a.caption,
         "by": names[a.uploaded_by].name if a.uploaded_by in names else "Unknown",
         "role": names[a.uploaded_by].role if a.uploaded_by in names else "",
         "at": a.created_at.isoformat()}
        for a in rows
    ]


@router.get("/attachments/{attachment_id}/file")
def get_file(attachment_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = db.get(Attachment, attachment_id)
    t = db.get(Ticket, a.ticket_id) if a else None
    if a is None or t is None or not can_view(db, user, t):
        raise HTTPException(404, "Photo not found")
    path = UPLOAD_DIR / a.filename
    if not path.exists():
        raise HTTPException(404, "Photo not found")
    return Response(content=path.read_bytes(), media_type=a.content_type,
                    headers={"Cache-Control": "private, max-age=3600"})