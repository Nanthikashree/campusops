import base64
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Attachment

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
KINDS = ("complaint", "before", "after")
MAX_PER_KIND = 3
MAX_BYTES = 2_500_000
SIGNATURES = {
    "image/jpeg": ("jpg", lambda b: b[:3] == b"\xff\xd8\xff"),
    "image/png": ("png", lambda b: b[:8] == b"\x89PNG\r\n\x1a\n"),
    "image/webp": ("webp", lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP"),
}


def count_kind(db: Session, ticket_id: int, kind: str) -> int:
    return len(db.scalars(select(Attachment.id).where(
        Attachment.ticket_id == ticket_id, Attachment.kind == kind)).all())


def decode_image(data_url: str):
    """Returns (bytes, content_type, extension), or raises ValueError."""
    if not data_url.startswith("data:") or ";base64," not in data_url:
        raise ValueError("The image must be sent as a base64 data URL")
    head, b64 = data_url.split(";base64,", 1)
    ctype = head[5:].lower()
    if ctype not in SIGNATURES:
        raise ValueError("Only JPEG, PNG or WebP images are allowed")
    try:
        raw = base64.b64decode(b64, validate=True)
    except Exception:
        raise ValueError("The image data is not valid")
    if len(raw) > MAX_BYTES:
        raise ValueError("The image is too large (maximum 2.5 MB)")
    ext, looks_right = SIGNATURES[ctype]
    if not looks_right(raw):
        raise ValueError("The file is not a real image")
    return raw, ctype, ext


def store(raw: bytes, ext: str) -> str:
    UPLOAD_DIR.mkdir(exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"
    (UPLOAD_DIR / name).write_bytes(raw)
    return name