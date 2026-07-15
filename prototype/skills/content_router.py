"""Routes a raw event request to a lifecycle phase and assembles the
Content Agent's input dict for it.

Units, deliberately separate: compute_days_until_event() parses a date
string with explicit error handling; classify_phase() is pure (an int
+ a bool in, a phase label out, no I/O); assemble_input() (added in
Task 4) loads the matching template and does the I/O. Each is testable
in isolation.
"""
from datetime import date, datetime
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent.parent / "data" / "templates"


def compute_days_until_event(event_date: str, today: date) -> int:
    if not event_date:
        raise ValueError("event_date is missing")
    try:
        parsed = datetime.strptime(event_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"event_date {event_date!r} is not a valid ISO date (YYYY-MM-DD)")
    return (parsed - today).days


def classify_phase(days_until_event: int, has_session: bool) -> str:
    if days_until_event > 14:
        return "announcement_1"
    if 3 <= days_until_event <= 14:
        return "announcement_2"
    if 1 <= days_until_event <= 2:
        return "announcement_3"
    if days_until_event == 0:
        return "during_event"
    if has_session:
        return "post_event_recap"
    return "awaiting_recording"
