from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .deps import require_roles
from .models import Approval, Booking, JobEvent, Part, Room, Ticket, User
from .routes_assign import MANAGERS
from .sla import OPEN, _naive_utc, resolved_at_for, sla_info

router = APIRouter(prefix="/api")
DAY_START, DAY_END = 8, 18  # bookable hours of a room each day


def _local_date(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone().date()


@router.get("/analytics/overview")
def overview(date: str | None = None, user: User = Depends(require_roles(*MANAGERS)),
             db: Session = Depends(get_db)):
    tickets = db.scalars(select(Ticket)).all()
    rooms = {r.id: r for r in db.scalars(select(Room)).all()}
    today = datetime.now().date()

    # SLA compliance and average time to resolve
    finished = [t for t in tickets if t.status in ("resolved", "closed")]
    met, hours = 0, []
    for t in finished:
        done = resolved_at_for(db, t)
        if sla_info(t, done)["state"] == "met":
            met += 1
        if done:
            hours.append((_naive_utc(done) - _naive_utc(t.created_at)).total_seconds() / 3600)

    # Requests opened and resolved per day (last 7 days)
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    opened = Counter(_local_date(t.created_at) for t in tickets)
    done_events = db.scalars(select(JobEvent).where(JobEvent.event_type == "completed")).all()
    resolved_per_day = Counter(_local_date(e.created_at) for e in done_events)
    trend = [{"day": d.strftime("%a %d"), "opened": opened.get(d, 0), "resolved": resolved_per_day.get(d, 0)}
             for d in days]

    # Room utilisation on one day (default: the next day that has bookings)
    day = today
    if date:
        try:
            day = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            day = today
    else:
        nxt = db.scalars(select(Booking).where(
            Booking.status == "active", Booking.start_time >= datetime.combine(today, datetime.min.time())
        ).order_by(Booking.start_time).limit(1)).first()
        if nxt is not None:
            day = nxt.start_time.date()
    win_start = datetime.combine(day, datetime.min.time()).replace(hour=DAY_START)
    win_end = win_start.replace(hour=DAY_END)
    bookable = [r for r in rooms.values() if r.room_type in ("classroom", "lab", "hall")]
    per_room = {}
    for b in db.scalars(select(Booking).where(
            Booking.status == "active", Booking.start_time < win_end, Booking.end_time > win_start)).all():
        s, e = max(b.start_time, win_start), min(b.end_time, win_end)
        per_room[b.room_id] = per_room.get(b.room_id, 0) + max(0, (e - s).total_seconds() / 3600)
    total_hours = len(bookable) * (DAY_END - DAY_START)
    booked_hours = sum(per_room.values())
    util_rooms = sorted(
        ({"name": rooms[rid].name, "building": rooms[rid].building.name, "hours": round(h, 1),
          "percent": round(100 * h / (DAY_END - DAY_START))} for rid, h in per_room.items() if rid in rooms),
        key=lambda x: -x["hours"])[:8]

    # Shortages
    parts = db.scalars(select(Part).order_by(Part.id)).all()
    short = [{"name": p.name, "available": p.stock - p.reserved, "min_stock": p.min_stock}
             for p in parts if p.stock - p.reserved < p.min_stock]
    pending = db.scalars(select(Approval).where(Approval.status == "pending")).all()

    # Recurring problems in the last 30 days (same item in the same place)
    since = datetime.now(timezone.utc) - timedelta(days=30)
    groups = {}
    for t in tickets:
        created = t.created_at if t.created_at.tzinfo else t.created_at.replace(tzinfo=timezone.utc)
        if created < since:
            continue
        where = rooms[t.room_id].name if t.room_id in rooms else "Campus-wide"
        what = t.asset or t.issue_type.replace("_", " ")
        groups.setdefault((what, where), []).append(t.id)
    recurring = sorted(
        ({"what": k[0], "where": k[1], "count": len(v), "ticket_ids": v[-5:]}
         for k, v in groups.items() if len(v) >= 2),
        key=lambda x: -x["count"])[:6]

    open_tickets = [t for t in tickets if t.status in OPEN]
    return {
        "open_requests": len(open_tickets),
        "total_requests": len(tickets),
        "sla_compliance": round(100 * met / len(finished)) if finished else None,
        "avg_resolution_hours": round(sum(hours) / len(hours), 1) if hours else None,
        "by_priority": dict(Counter(t.priority for t in tickets)),
        "by_status": dict(Counter(t.status for t in tickets)),
        "trend": trend,
        "utilisation": {
            "date": day.isoformat(),
            "percent": round(100 * booked_hours / total_hours) if total_hours else 0,
            "booked_hours": round(booked_hours, 1),
            "rooms": util_rooms,
        },
        "shortages": short,
        "pending_purchases": {"count": len(pending), "amount": sum(a.amount for a in pending)},
        "recurring": recurring,
    }