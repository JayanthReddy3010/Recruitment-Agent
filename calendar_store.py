"""
Mock calendar for interview scheduling. No real calendar integration --
a JSON file on disk is enough to prove double-booking prevention actually
works, which is the part that matters for the demo.
"""
import json
import os
from config import CALENDAR_FILE
from models import InterviewSlot


def _load() -> list[dict]:
    if not os.path.exists(CALENDAR_FILE):
        return []
    with open(CALENDAR_FILE, "r") as f:
        return json.load(f)


def _save(slots: list[dict]) -> None:
    os.makedirs(os.path.dirname(CALENDAR_FILE), exist_ok=True)
    with open(CALENDAR_FILE, "w") as f:
        json.dump(slots, f, indent=2)


def is_slot_taken(date_str: str, time_str: str) -> bool:
    return any(s["date"] == date_str and s["time"] == time_str for s in _load())


def book_slot(candidate_name: str, date_str: str, time_str: str, note: str = "") -> InterviewSlot:
    slots = _load()
    if is_slot_taken(date_str, time_str):
        raise ValueError(f"{date_str} {time_str} is already booked")
    entry = {"candidate_name": candidate_name, "date": date_str, "time": time_str, "note": note}
    slots.append(entry)
    _save(slots)
    return InterviewSlot(**entry)


def list_slots() -> list[InterviewSlot]:
    return [InterviewSlot(**s) for s in _load()]


def cancel_slot(candidate_name: str, date_str: str, time_str: str) -> bool:
    slots = _load()
    remaining = [
        s for s in slots
        if not (s["candidate_name"] == candidate_name and s["date"] == date_str and s["time"] == time_str)
    ]
    changed = len(remaining) != len(slots)
    if changed:
        _save(remaining)
    return changed
