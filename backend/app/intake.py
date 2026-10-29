import json
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from .ai import ask_ai
from .models import ISSUE_TYPES, PRIORITIES, Room

ISSUE_KEYWORDS = [
    ("it_network", ["wifi", "wi-fi", "internet", "network", "router", "lan", "server", "computer", "login", "email"]),
    ("equipment", ["projector", "microphone", "mic", "speaker", "smartboard", "smart board", "camera", "printer", "equipment"]),
    ("inventory", ["chemical", "chemicals", "reagent", "stock", "stationery", "shortage", "supplies"]),
    ("room_booking", ["book", "booking", "reserve", "reservation"]),
    ("maintenance", ["ac", "a/c", "air conditioner", "fan", "light", "bulb", "power", "electric", "electrical",
                     "switch", "plumbing", "leak", "leakage", "tap", "water", "door", "window", "paint",
                     "bench", "chair", "furniture", "broken"]),
]

ASSETS = {
    "projector": "Projector", "ac": "AC", "a/c": "AC", "air conditioner": "AC", "fan": "Fan",
    "light": "Light", "bulb": "Light", "router": "Router", "computer": "Computer", "printer": "Printer",
    "tap": "Tap", "door": "Door", "window": "Window", "chair": "Chair", "bench": "Bench",
    "microphone": "Microphone", "mic": "Microphone", "speaker": "Speaker",
    "chemical": "Chemicals", "chemicals": "Chemicals",
}

CRITICAL_WORDS = ["fire", "smoke", "spark", "sparks", "short circuit", "shock", "gas leak"]
HIGH_WORDS = ["exam", "urgent", "emergency", "no power", "power failure", "power cut", "flood",
              "flooding", "outage", "not working at all", "all students"]
LOW_WORDS = ["minor", "slight", "not urgent", "whenever", "no rush"]
ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def _has(text: str, word: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(word) + r"(?![a-z0-9])", text) is not None


def _squash(s: str) -> str:
    return re.sub(r"[\s\-_]", "", s.lower())


def rule_urgency(text: str) -> str:
    t = text.lower()
    if any(_has(t, w) for w in CRITICAL_WORDS):
        return "critical"
    if any(_has(t, w) for w in HIGH_WORDS):
        return "high"
    if any(_has(t, w) for w in LOW_WORDS):
        return "low"
    return "medium"


def find_room(text: str, rooms):
    squashed = _squash(text)
    best = None
    for r in rooms:
        key = _squash(r.name)
        if key in squashed and (best is None or len(key) > len(_squash(best.name))):
            best = r
    if best:
        return best
    m = re.search(r"block\s*([abc])\D{0,15}?(\d{3})", text.lower())
    if m:
        wanted = f"{m.group(1).upper()}{m.group(2)}"
        for r in rooms:
            if r.name == wanted:
                return r
    return None


def rule_extract(text: str, rooms) -> dict:
    t = text.lower()
    issue_type = "other"
    for kind, words in ISSUE_KEYWORDS:
        if any(_has(t, w) for w in words):
            issue_type = kind
            break
    asset = ""
    for word, label in ASSETS.items():
        if _has(t, word):
            asset = label
            break
    return {"issue_type": issue_type, "room": find_room(text, rooms), "asset": asset, "urgency": rule_urgency(text)}


def ai_extract(text: str, room_names: list[str]):
    prompt = (
        "You read campus maintenance complaints. Reply with ONLY a JSON object, no other text.\n"
        'Keys: "issue_type" (one of: maintenance, it_network, room_booking, equipment, inventory, other), '
        '"room" (one of the known rooms below, or null), "asset" (short name like AC or Projector, or null), '
        '"urgency" (one of: low, medium, high, critical).\n'
        f"Known rooms: {', '.join(room_names)}\n"
        f"Complaint: {text}"
    )
    out, provider = ask_ai(prompt)
    if not out:
        return None, None
    m = re.search(r"\{.*\}", out, re.S)
    if not m:
        return None, None
    try:
        return json.loads(m.group(0)), provider
    except json.JSONDecodeError:
        return None, None


def analyze(db: Session, text: str) -> dict:
    rooms = db.scalars(select(Room)).all()
    result = rule_extract(text, rooms)
    result["extracted_by"] = "rules"

    data, provider = ai_extract(text, [r.name for r in rooms])
    if isinstance(data, dict):
        if data.get("issue_type") in ISSUE_TYPES and data["issue_type"] != "other":
            result["issue_type"] = data["issue_type"]
        by_name = {r.name.lower(): r for r in rooms}
        if isinstance(data.get("room"), str) and data["room"].lower() in by_name:
            result["room"] = by_name[data["room"].lower()]
        if isinstance(data.get("asset"), str) and 0 < len(data["asset"]) <= 50:
            result["asset"] = data["asset"]
        # Safety rule: the AI can raise urgency but never lower what the keyword rules found.
        ai_u = data.get("urgency")
        if ai_u in PRIORITIES and ORDER[ai_u] > ORDER[result["urgency"]]:
            result["urgency"] = ai_u
        result["extracted_by"] = provider

    missing, question = [], ""
    if result["issue_type"] == "other":
        missing.append("issue_type")
        question = "What kind of problem is this (for example electrical, Wi-Fi, equipment or stock)?"
    elif result["issue_type"] in ("maintenance", "equipment") and result["room"] is None:
        missing.append("room")
        question = "Which room is this in? (for example B203 or Lab 2)"

    room = result["room"]
    return {
        "issue_type": result["issue_type"],
        "room": {"id": room.id, "name": room.name, "building": room.building.name} if room else None,
        "asset": result["asset"],
        "urgency": result["urgency"],
        "missing": missing,
        "question": question,
        "extracted_by": result["extracted_by"],
    }