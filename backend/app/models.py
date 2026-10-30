from datetime import datetime, timezone
from sqlalchemy import String, Integer, ForeignKey, Text, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


def now():
    return datetime.now(timezone.utc)


# The six roles from the problem statement
ROLES = [
    "student_faculty",
    "technician",
    "department_manager",
    "facilities_admin",
    "procurement_approver",
    "system_admin",
]

TICKET_STATUSES = ["new", "triaged", "assigned", "in_progress", "blocked", "resolved", "closed"]
ISSUE_TYPES = ["maintenance", "it_network", "room_booking", "equipment", "inventory", "other"]
PRIORITIES = ["low", "medium", "high", "critical"]
CHANNELS = ["form", "chat", "email"]
BOOKING_KINDS = ["class", "exam", "event", "meeting"]


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(150), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), default="")
    role: Mapped[str] = mapped_column(String(30))
    user_type: Mapped[str] = mapped_column(String(20), default="student")  # student, faculty, staff
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Building(Base):
    __tablename__ = "buildings"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    kind: Mapped[str] = mapped_column(String(30), default="academic")  # academic, hostel, lab, admin
    rooms: Mapped[list["Room"]] = relationship(back_populates="building")


class Room(Base):
    __tablename__ = "rooms"
    id: Mapped[int] = mapped_column(primary_key=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"))
    name: Mapped[str] = mapped_column(String(50))
    room_type: Mapped[str] = mapped_column(String(30), default="classroom")  # classroom, lab, hostel_room, hall
    capacity: Mapped[int] = mapped_column(Integer, default=40)
    status: Mapped[str] = mapped_column(String(20), default="available")  # available, unusable
    building: Mapped["Building"] = relationship(back_populates="rooms")


class Ticket(Base):
    __tablename__ = "tickets"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"), nullable=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    issue_type: Mapped[str] = mapped_column(String(30), default="other")
    asset: Mapped[str] = mapped_column(String(100), default="")
    channel: Mapped[str] = mapped_column(String(20), default="form")
    status: Mapped[str] = mapped_column(String(20), default="new")
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class JobEvent(Base):
    """The digital job card: an append-only log. Rows are added, never edited."""
    __tablename__ = "job_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"))
    event_type: Mapped[str] = mapped_column(String(40))
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    actor_role: Mapped[str] = mapped_column(String(30))
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    prev_hash: Mapped[str] = mapped_column(String(64), default="")
    hash: Mapped[str] = mapped_column(String(64), default="")


class StaffProfile(Base):
    __tablename__ = "staff_profiles"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    skills: Mapped[str] = mapped_column(String(200), default="")  # e.g. "electrical,hvac"
    status: Mapped[str] = mapped_column(String(20), default="available")  # available, on_leave
    max_jobs: Mapped[int] = mapped_column(Integer, default=4)


class Assignment(Base):
    __tablename__ = "assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"))
    technician_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assigned_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Booking(Base):
    __tablename__ = "bookings"
    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))
    title: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20), default="class")  # class, exam, event, meeting
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime] = mapped_column(DateTime)
    attendees: Mapped[int] = mapped_column(Integer, default=0)
    booked_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, cancelled
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Part(Base):
    __tablename__ = "parts"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    reserved: Mapped[int] = mapped_column(Integer, default=0)
    min_stock: Mapped[int] = mapped_column(Integer, default=2)
    unit_cost: Mapped[int] = mapped_column(Integer, default=0)


class PartReservation(Base):
    __tablename__ = "part_reservations"
    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"))
    part_id: Mapped[int] = mapped_column(ForeignKey("parts.id"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="reserved")  # reserved, waiting, consumed, cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), default="purchase")
    ticket_id: Mapped[int | None] = mapped_column(ForeignKey("tickets.id"), nullable=True)
    part_id: Mapped[int | None] = mapped_column(ForeignKey("parts.id"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    amount: Mapped[int] = mapped_column(Integer, default=0)
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, approved, rejected, cancelled
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ApprovalStep(Base):
    __tablename__ = "approval_steps"
    id: Mapped[int] = mapped_column(primary_key=True)
    approval_id: Mapped[int] = mapped_column(ForeignKey("approvals.id"))
    level: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, approved, rejected, skipped, cancelled
    approver_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    remarks: Mapped[str] = mapped_column(Text, default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    ticket_id: Mapped[int | None] = mapped_column(ForeignKey("tickets.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(30), default="info")
    message: Mapped[str] = mapped_column(Text, default="")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EmailMessage(Base):
    __tablename__ = "email_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[str] = mapped_column(String(200), unique=True)
    sender: Mapped[str] = mapped_column(String(150))
    subject: Mapped[str] = mapped_column(String(200), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="received")  # processed, invalid
    ticket_id: Mapped[int | None] = mapped_column(ForeignKey("tickets.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Slot(Base):
    __tablename__ = "slots"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20), default="exam")  # exam, lab, workshop, event
    description: Mapped[str] = mapped_column(Text, default="")
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime] = mapped_column(DateTime)
    capacity: Mapped[int] = mapped_column(Integer, default=30)
    opens_at: Mapped[datetime] = mapped_column(DateTime)
    closes_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="scheduled")  # scheduled, cancelled
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SlotBooking(Base):
    __tablename__ = "slot_bookings"
    id: Mapped[int] = mapped_column(primary_key=True)
    slot_id: Mapped[int] = mapped_column(ForeignKey("slots.id"))
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="booked")  # booked, cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)