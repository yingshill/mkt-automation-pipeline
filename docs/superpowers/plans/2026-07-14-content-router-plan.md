# Content Router Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a rule-based router that decides which lifecycle phase an event post falls into (first announcement, updated lineup, last call, live update, post-event recap) and assembles the exact input dict the existing Content Agent already expects — closing the gap where a human had to manually decide and assemble this every time.

**Architecture:** Two small, independently-testable units in a new `prototype/skills/content_router.py`: a pure `classify_phase()` function (dates + a boolean in, a phase label out, no I/O) and an `assemble_input()` function (phase + raw event/session data in, the Content Agent's dict out, loads a template file). A new `events` table in `prototype/skills/store.py` tracks which events exist and whether a recording is linked yet. Five new template files in `prototype/data/templates/` give the assembler real content to load.

**Tech Stack:** Python 3, `sqlite3` (stdlib, matches `store.py`), `pytest` — same as the rest of the prototype. No new dependencies.

## Global Constraints

- `classify_phase` is rule-based and deterministic — no LLM call, no judgment. It takes `days_until_event: int` and `has_session: bool` and returns one of exactly 6 phase strings.
- `days_until_event` is always passed in by the caller (or a thin date-math wrapper) — never computed via `datetime.now()` inside `classify_phase` itself, so tests are deterministic.
- The 6 phases, in the order they're checked (first match wins): `days_until_event > 14` → `announcement_1`; `3 <= days_until_event <= 14` → `announcement_2`; `1 <= days_until_event <= 2` → `announcement_3`; `days_until_event == 0` → `during_event`; `days_until_event < 0` and `has_session` is `True` → `post_event_recap`; `days_until_event < 0` and `has_session` is `False` → `awaiting_recording`.
- `awaiting_recording` never produces a draft — `assemble_input` raises `ValueError` naming that the event has passed and no recording exists yet.
- Every template file is a hand-generalized version of a real TechEquity example post (from `2026 Social Media Template.docx`), disclosed as constructed — not a literal export of "the Doc." This must be stated in a header comment in every template file.
- No live Luma API, no live Docs integration — event details are still plain input, matching the existing `luma_event_details` shape in `content-agent.md`.
- No changes to `content-agent.md`, `validators.py`, `render_dashboard.py`, or the Lead Capture/Outreach/Nurture agents.

---

### Task 1: `events` table + store functions

**Files:**
- Modify: `prototype/skills/store.py:59` (insert the new table into the `SCHEMA` string, immediately before the closing `"""`)
- Modify: `prototype/skills/store.py` (append 3 new functions at the end of the file, after `list_nurture_stages`, currently ending at line 237)
- Modify: `prototype/tests/test_store.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces (used by Task 4): `insert_event(db_path: str, event_title: str, event_date: str) -> int`, `get_event(db_path: str, event_id: int) -> dict | None`, `link_session_to_event(db_path: str, event_id: int, session_id: int) -> None`.

- [ ] **Step 1: Write the failing tests**

Add to `prototype/tests/test_store.py` (add to the existing import line, and append these tests at the end of the file):

Change the top import line from:
```python
from prototype.skills.store import (
    init_db, insert_session, get_session_by_video_id, list_sessions,
    insert_draft, list_drafts,
    insert_lead, update_lead_enrichment, list_leads,
    insert_outreach, list_outreach,
    upsert_nurture_stage, list_nurture_stages,
)
```
to:
```python
from prototype.skills.store import (
    init_db, insert_session, get_session_by_video_id, list_sessions,
    insert_draft, list_drafts,
    insert_lead, update_lead_enrichment, list_leads,
    insert_outreach, list_outreach,
    upsert_nurture_stage, list_nurture_stages,
    insert_event, get_event, link_session_to_event,
)
```

Append to the end of `prototype/tests/test_store.py`:
```python
def test_insert_and_get_event(db_path):
    event_id = insert_event(db_path, event_title="June Forum", event_date="2026-06-30")
    event = get_event(db_path, event_id)
    assert event["event_title"] == "June Forum"
    assert event["event_date"] == "2026-06-30"
    assert event["session_id"] is None


def test_link_session_to_event(db_path):
    event_id = insert_event(db_path, event_title="June Forum", event_date="2026-06-30")
    session_id = insert_session(db_path, video_id="v1", title="June Forum Recording", url="u1")
    link_session_to_event(db_path, event_id, session_id)
    event = get_event(db_path, event_id)
    assert event["session_id"] == session_id


def test_get_event_returns_none_for_unknown_id(db_path):
    assert get_event(db_path, 9999) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow" && .venv/bin/python -m pytest prototype/tests/test_store.py -v`
Expected: FAIL with `ImportError: cannot import name 'insert_event'`

- [ ] **Step 3: Add the schema and functions**

In `prototype/skills/store.py`, change (around line 53-59, the end of the `SCHEMA` string):
```python
CREATE TABLE IF NOT EXISTS nurture_stage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL UNIQUE REFERENCES leads(id),
    stage TEXT NOT NULL,
    next_touch_template TEXT,
    updated_at TEXT NOT NULL
);
"""
```
to:
```python
CREATE TABLE IF NOT EXISTS nurture_stage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL UNIQUE REFERENCES leads(id),
    stage TEXT NOT NULL,
    next_touch_template TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_title TEXT NOT NULL,
    event_date TEXT NOT NULL,
    session_id INTEGER REFERENCES sessions(id),
    created_at TEXT NOT NULL
);
"""
```

Append to the end of `prototype/skills/store.py`:
```python
def insert_event(db_path, event_title, event_date) -> int:
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO events (event_title, event_date, session_id, created_at) "
            "VALUES (?, ?, NULL, ?)",
            (event_title, event_date, _now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_event(db_path, event_id) -> dict | None:
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM events WHERE id = ?", (event_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def link_session_to_event(db_path, event_id, session_id) -> None:
    conn = _connect(db_path)
    try:
        conn.execute(
            "UPDATE events SET session_id = ? WHERE id = ?",
            (session_id, event_id),
        )
        conn.commit()
    finally:
        conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow" && .venv/bin/python -m pytest prototype/tests/test_store.py -v`
Expected: `13 passed` (10 existing + 3 new)

- [ ] **Step 5: Commit**

```bash
cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow"
git add prototype/skills/store.py prototype/tests/test_store.py
git commit -m "feat: add events table for the content router's phase classifier"
```

---

### Task 2: Template catalog (5 files)

**Files:**
- Create: `prototype/data/templates/announcement_1.md`
- Create: `prototype/data/templates/announcement_2.md`
- Create: `prototype/data/templates/announcement_3.md`
- Create: `prototype/data/templates/during_event.md`
- Create: `prototype/data/templates/post_event_recap.md`
- Create: `prototype/tests/test_templates.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: 5 files on disk, one per phase name, that Task 4's `assemble_input` loads by path `prototype/data/templates/{phase}.md`.

- [ ] **Step 1: Write the failing test**

Create `prototype/tests/test_templates.py`:
```python
import pytest

PHASES = ["announcement_1", "announcement_2", "announcement_3", "during_event", "post_event_recap"]


@pytest.mark.parametrize("phase", PHASES)
def test_template_file_exists_and_is_non_empty(phase):
    with open(f"prototype/data/templates/{phase}.md") as f:
        content = f.read()
    assert len(content.strip()) > 0


@pytest.mark.parametrize("phase", PHASES)
def test_template_file_discloses_construction(phase):
    with open(f"prototype/data/templates/{phase}.md") as f:
        content = f.read()
    assert "constructed" in content.lower() or "generalized" in content.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow" && .venv/bin/python -m pytest prototype/tests/test_templates.py -v`
Expected: FAIL — `FileNotFoundError` for each phase (none of the files exist yet)

- [ ] **Step 3: Create the template files**

Create `prototype/data/templates/announcement_1.md` (generalized from the real "Event Announcement 1" post):
```markdown
<!-- Constructed by generalizing a real TechEquity "Event Announcement 1" post
     (2026 Social Media Template.docx) into a fill-in-the-blank shape.
     Not a literal export of "the Doc" -- see docs/testing/content-agent-tests.md
     for the disclosure this pattern follows. -->

Join us at [Event Title]

This session brings together perspectives from industry leaders—including [Speaker 1 Name] ([Speaker 1 Title/Company]), [Speaker 2 Name] ([Speaker 2 Title/Company]), and more—to explore [1-sentence theme summary].

TechEquity Ai invites you to an evening of applied AI learning and hands-on building at [Location]. We bring together AI leaders, developers, founders, early-career talent, and professionals exploring AI. This session pairs strategic insights and real-world use cases with technical workshops and live demos as part of our TechEquity Ai Monthly Forum Series.

🎙️ Featured Sessions
[Keynote/Workshop list — session title • speaker name, title, company]

🗓️ Agenda Highlights
[Times and segment names]

📅 [Date] ⏰ [Time] 📍 [Location]

🎟️ Register (RSVP required): [Luma link]

Seats are limited—join the builders shaping what comes next, together.

#TechEquityAi #AIBuilders #AIInnovation #FutureOfAI
```

Create `prototype/data/templates/announcement_2.md` (generalized from the real "Event Announcement 2" post — same shape as Announcement 1, but the title gains a partner call-out and the speaker list has grown):
```markdown
<!-- Constructed by generalizing a real TechEquity "Event Announcement 2" post
     (2026 Social Media Template.docx) into a fill-in-the-blank shape.
     Not a literal export of "the Doc" -- see docs/testing/content-agent-tests.md
     for the disclosure this pattern follows. -->

Join us at [Event Title], Ft [Partner Org(s)]

This session brings together perspectives from industry leaders—including [Speaker 1 Name] ([Speaker 1 Title/Company]), [Speaker 2 Name] ([Speaker 2 Title/Company]), [Speaker 3 Name] ([Speaker 3 Title/Company]), and more—to explore [1-sentence theme summary].

TechEquity Ai invites you to an evening of applied AI learning and hands-on building at [Location]. We bring together AI leaders, developers, founders, early-career talent, and professionals exploring AI. This session pairs strategic insights and real-world use cases with technical workshops and live demos as part of our TechEquity Ai Monthly Forum Series.

🎙️ Featured Sessions
[Keynote/Workshop list — session title • speaker name, title, company]

🗓️ Agenda Highlights
[Times and segment names]

📅 [Date] ⏰ [Time] 📍 [Location]

🎟️ Register (RSVP required): [Luma link]

Seats are limited—join the builders shaping what comes next, together.

#TechEquityAi #AIBuilders #AIInnovation #FutureOfAI
```

Create `prototype/data/templates/announcement_3.md` (generalized from the real "Last Call" post):
```markdown
<!-- Constructed by generalizing a real TechEquity "Event Announcement 3"
     ("Last Call") post (2026 Social Media Template.docx) into a
     fill-in-the-blank shape. Not a literal export of "the Doc" -- see
     docs/testing/content-agent-tests.md for the disclosure this pattern follows. -->

‼️Last Call: [Event Title]

We're closing in on an incredible evening of insight and hands-on building. Join industry leaders—including [Speaker 1 Name] ([Speaker 1 Title/Company]), [Speaker 2 Name] ([Speaker 2 Title/Company]), and more—as we explore [1-sentence theme summary].

TechEquity Ai invites you to [Location] for an evening that blends executive-level strategy with practical, builder-focused workshops. Expect real-world use cases, technical depth, and meaningful connections as part of our TechEquity Ai Monthly Forum Series.

🎙️ Featured Sessions
[Keynote/Workshop list — session title • speaker name, title, company]

📅 [Date] ⏰ [Time] 📍 [Location]

🎟️ Register (RSVP required): [Luma link]

Seats are limited—this is your final opportunity to join the builders shaping what comes next.

#TechEquityAi #AIBuilders #AIInnovation #FutureOfAI
```

Create `prototype/data/templates/during_event.md` (generalized from the real live-update post):
```markdown
<!-- Constructed by generalizing a real TechEquity "During-event" update post
     (2026 Social Media Template.docx) into a fill-in-the-blank shape. Not a
     literal export of "the Doc" -- see docs/testing/content-agent-tests.md
     for the disclosure this pattern follows. -->

Update: A full room and a lot of momentum already.⚡

We're live at [Location] as [Event Title] gets underway, bringing together product leaders, developers, founders, and AI practitioners for an evening of applied learning and hands-on building.

[1-2 sentence theme summary]. Expect a mix of strategic insight, technical depth, and real-world use cases across industries.

👩‍💻 What's happening tonight:
[Session list — keynote/workshop title — speaker name, title, company]

📍 In person: keynotes, technical workshops (laptop recommended), and networking
💻 Online: livestream access available for registered attendees, with recordings shared afterward

If you're here, connect between sessions and meet fellow builders. If you're joining online, tune in and be part of the conversation in real time.

#TechEquityAi #AIBuilders #AIInnovation #FutureOfAI
```

Create `prototype/data/templates/post_event_recap.md` (generalized from the real recap post):
```markdown
<!-- Constructed by generalizing a real TechEquity "Post-event recap" post
     (2026 Social Media Template.docx) into a fill-in-the-blank shape. Not a
     literal export of "the Doc" -- see docs/testing/content-agent-tests.md
     for the disclosure this pattern follows. Unlike the other 4 templates,
     this one is meant to be paired with a real session/transcript input,
     not template+Luma-details alone -- see the design spec's "post-event
     recap case" note on blending session content with this structure. -->

Event Recap

⚡ [1-sentence "from X to Y" summary of the evening]

We brought together [attendee count]+ product leaders, builders, founders, and AI practitioners for an evening of deep technical discussions, practical use cases, meaningful networking, and a growing Bay Area AI community last [day of week] at [Location].

🔎 [Section per keynote — speaker name, title/company, one-sentence takeaway from their talk]

💻 [Section on hands-on workshops — speaker names, what they covered]

Thank you to everyone who joined us as part of the TechEquity Ai Monthly Forum Series. See you next month for more AI discussions and workshops.

#TechEquityAi #AIBuilders #AIInnovation #FutureOfAI
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow" && .venv/bin/python -m pytest prototype/tests/test_templates.py -v`
Expected: `10 passed` (5 phases × 2 tests)

- [ ] **Step 5: Commit**

```bash
cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow"
git add prototype/data/templates/ prototype/tests/test_templates.py
git commit -m "feat: add content-router template catalog (5 phase templates)"
```

---

### Task 3: `classify_phase` — the phase classifier

**Files:**
- Create: `prototype/skills/content_router.py`
- Create: `prototype/tests/test_content_router.py`

**Interfaces:**
- Consumes: nothing from other tasks (pure functions).
- Produces (used by Task 4 and Task 5): `classify_phase(days_until_event: int, has_session: bool) -> str`, returning one of `"announcement_1"`, `"announcement_2"`, `"announcement_3"`, `"during_event"`, `"post_event_recap"`, `"awaiting_recording"`. Also `compute_days_until_event(event_date: str, today: date) -> int` — parses an ISO date string (`"2026-06-30"`) and returns `(event_date - today).days`, raising `ValueError` naming the problem if `event_date` is missing, empty, or not a valid ISO date. `today` is always passed in explicitly, never computed via `date.today()` internally, so tests are deterministic.

- [ ] **Step 1: Write the failing tests**

Create `prototype/tests/test_content_router.py`:
```python
import pytest
from prototype.skills.content_router import classify_phase


def test_classify_phase_far_out_no_session_is_announcement_1():
    assert classify_phase(days_until_event=20, has_session=False) == "announcement_1"


def test_classify_phase_boundary_15_days_is_announcement_1():
    assert classify_phase(days_until_event=15, has_session=False) == "announcement_1"


def test_classify_phase_boundary_14_days_is_announcement_2():
    assert classify_phase(days_until_event=14, has_session=False) == "announcement_2"


def test_classify_phase_mid_range_is_announcement_2():
    assert classify_phase(days_until_event=7, has_session=False) == "announcement_2"


def test_classify_phase_boundary_3_days_is_announcement_2():
    assert classify_phase(days_until_event=3, has_session=False) == "announcement_2"


def test_classify_phase_boundary_2_days_is_announcement_3():
    assert classify_phase(days_until_event=2, has_session=False) == "announcement_3"


def test_classify_phase_1_day_is_announcement_3():
    assert classify_phase(days_until_event=1, has_session=False) == "announcement_3"


def test_classify_phase_zero_days_is_during_event():
    assert classify_phase(days_until_event=0, has_session=False) == "during_event"


def test_classify_phase_zero_days_with_session_is_still_during_event():
    assert classify_phase(days_until_event=0, has_session=True) == "during_event"


def test_classify_phase_past_with_session_is_post_event_recap():
    assert classify_phase(days_until_event=-1, has_session=True) == "post_event_recap"


def test_classify_phase_past_without_session_is_awaiting_recording():
    assert classify_phase(days_until_event=-1, has_session=False) == "awaiting_recording"


def test_classify_phase_far_future_with_session_is_still_announcement_1():
    # has_session is irrelevant pre-event (rules 1-4 don't check it)
    assert classify_phase(days_until_event=20, has_session=True) == "announcement_1"


def test_compute_days_until_event_future_date():
    from datetime import date
    from prototype.skills.content_router import compute_days_until_event
    assert compute_days_until_event("2026-07-20", today=date(2026, 7, 14)) == 6


def test_compute_days_until_event_past_date():
    from datetime import date
    from prototype.skills.content_router import compute_days_until_event
    assert compute_days_until_event("2026-07-10", today=date(2026, 7, 14)) == -4


def test_compute_days_until_event_same_day():
    from datetime import date
    from prototype.skills.content_router import compute_days_until_event
    assert compute_days_until_event("2026-07-14", today=date(2026, 7, 14)) == 0


def test_compute_days_until_event_missing_date_raises():
    from datetime import date
    from prototype.skills.content_router import compute_days_until_event
    with pytest.raises(ValueError, match="event_date"):
        compute_days_until_event("", today=date(2026, 7, 14))


def test_compute_days_until_event_malformed_date_raises():
    from datetime import date
    from prototype.skills.content_router import compute_days_until_event
    with pytest.raises(ValueError, match="event_date"):
        compute_days_until_event("not-a-date", today=date(2026, 7, 14))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow" && .venv/bin/python -m pytest prototype/tests/test_content_router.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'prototype.skills.content_router'`

- [ ] **Step 3: Write the implementation**

Create `prototype/skills/content_router.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow" && .venv/bin/python -m pytest prototype/tests/test_content_router.py -v`
Expected: `17 passed` (12 phase-classifier tests + 5 date-parsing tests)

- [ ] **Step 5: Commit**

```bash
cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow"
git add prototype/skills/content_router.py prototype/tests/test_content_router.py
git commit -m "feat: add classify_phase, the content router's phase classifier"
```

---

### Task 4: `assemble_input` — the template assembler

**Files:**
- Modify: `prototype/skills/content_router.py`
- Modify: `prototype/tests/test_content_router.py`

**Interfaces:**
- Consumes: `classify_phase` (Task 3, same file), the 5 template files (Task 2), `validate_content_agent_input` from `prototype/skills/validators.py` (used only in tests, to confirm the assembled output is valid).
- Produces: `assemble_input(phase: str, event: dict, session: dict | None = None, past_reference_post: str | None = None) -> dict`, returning `{"session": ..., "template_text": ..., "luma_event_details": ..., "past_reference_post": ...}` — the exact shape `content-agent.md` expects. `event` is a dict shaped like `store.get_event`'s return value, with additional caller-supplied fields for `time`, `location`, `speakers`, and `blurb` (not stored in the `events` table, since those aren't needed for phase classification — only `event_title`/`event_date`/`session_id` are).

- [ ] **Step 1: Write the failing tests**

Add to `prototype/tests/test_content_router.py`:
```python
from prototype.skills.content_router import assemble_input
from prototype.skills.validators import validate_content_agent_input

SAMPLE_EVENT = {
    "event_title": "June Forum",
    "event_date": "2026-06-30",
    "time": "5:00 PM to 9:00 PM",
    "location": "Snowflake SVAI Hub, Menlo Park, CA",
    "speakers": ["Jane Doe — Founder, Example Inc"],
    "blurb": "A forum about example things.",
}


@pytest.mark.parametrize("phase", ["announcement_1", "announcement_2", "announcement_3", "during_event"])
def test_assemble_input_loads_correct_template_and_passes_validation(phase):
    result = assemble_input(phase, SAMPLE_EVENT)
    validate_content_agent_input(result)
    assert result["luma_event_details"]["event_title"] == "June Forum"
    assert result["template_text"] is not None
    assert len(result["template_text"].strip()) > 0
    assert result["session"] is None


def test_assemble_input_post_event_recap_includes_session():
    session = {"video_id": "v1", "title": "June Forum Recording", "transcript": "full transcript text", "transcript_available": True}
    result = assemble_input("post_event_recap", SAMPLE_EVENT, session=session)
    validate_content_agent_input(result)
    assert result["session"] == session


def test_assemble_input_awaiting_recording_raises():
    with pytest.raises(ValueError, match="recording"):
        assemble_input("awaiting_recording", SAMPLE_EVENT)


def test_assemble_input_passes_through_past_reference_post():
    result = assemble_input("announcement_1", SAMPLE_EVENT, past_reference_post="Last month's post text")
    assert result["past_reference_post"] == "Last month's post text"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow" && .venv/bin/python -m pytest prototype/tests/test_content_router.py -v`
Expected: FAIL with `ImportError: cannot import name 'assemble_input'`

- [ ] **Step 3: Write the implementation**

Append to `prototype/skills/content_router.py`:
```python
def assemble_input(phase: str, event: dict, session: dict | None = None,
                    past_reference_post: str | None = None) -> dict:
    if phase == "awaiting_recording":
        raise ValueError(
            f"'{event['event_title']}' has passed and no recording exists yet — "
            "nothing to draft. Wait for a recording before calling assemble_input again."
        )

    template_path = TEMPLATES_DIR / f"{phase}.md"
    with open(template_path) as f:
        template_text = f.read()

    luma_event_details = {
        "event_title": event["event_title"],
        "date": event["event_date"],
        "time": event.get("time", ""),
        "location": event.get("location", ""),
        "speakers": event.get("speakers", []),
        "blurb": event.get("blurb", ""),
    }

    return {
        "session": session,
        "template_text": template_text,
        "luma_event_details": luma_event_details,
        "past_reference_post": past_reference_post,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow" && .venv/bin/python -m pytest prototype/tests/test_content_router.py -v`
Expected: `24 passed` (17 from Task 3 + 7 new)

- [ ] **Step 5: Run the full test suite**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow" && .venv/bin/python -m pytest prototype/tests --ignore=prototype/tests/test_run_pipeline.py -v`
Expected: all pass, except possibly the pre-existing `@pytest.mark.integration` YouTube test (network-dependent, documented, unrelated to this work).

- [ ] **Step 6: Commit**

```bash
cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow"
git add prototype/skills/content_router.py prototype/tests/test_content_router.py
git commit -m "feat: add assemble_input, the content router's template assembler"
```

---

### Task 5: Manual validation — real Content Agent run through the router

**Files:**
- Modify: `docs/testing/content-agent-tests.md` (append as "Test 3" — read the file first to match its established format exactly)

**Interfaces:**
- Consumes: `classify_phase` + `assemble_input` (Task 3/4), `validate_draft` (existing), the actual `prototype/agents/content-agent.md` persona (existing, unchanged).
- Produces: nothing further tasks depend on — this is the last task in this plan.

This is a real judgment task, not a pytest assertion — content quality is human-reviewed, per this project's established convention (see `docs/testing/content-agent-tests.md`'s own stated method).

- [ ] **Step 1: Pick a real, already-happened event with a real speaker roster**

Use the same February 19, 2026 "Product & Business Strategy in AI: Talks + AI Agent Workshops, Ft Google and Snowflake" event already used in Test 2 (`docs/testing/content-agent-tests.md`) — real data, no need to source anything new.

- [ ] **Step 2: Run the router end-to-end for the `announcement_2` phase**

```bash
cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow" && .venv/bin/python -c "
from prototype.skills.content_router import classify_phase, assemble_input

event = {
    'event_title': 'Product & Business Strategy in AI: Talks + AI Agent Workshops, Ft Google and Snowflake',
    'event_date': '2026-02-19',
    'time': '5:00 PM to 9:00 PM',
    'location': 'Snowflake Silicon Valley AI Hub, Menlo Park, CA',
    'speakers': [
        'Gopi Kallayil — Chief Business Strategist, AI, Google',
        'Ivan Lee — Founder & CEO, Datasaur',
        'Fahad Khan — Director of Programs, AI Foundations, Northrop Grumman',
        'Dave Nielsen — Head of Community, AI Alliance (IBM)',
        'Mike Prince — CEO, Matchwise',
        'Anupam Datta — AI Research Lead, Snowflake',
    ],
    'blurb': 'Interdisciplinary sessions connecting physics AI, large language models, and open-source innovation with hands-on AI agent workshops, exploring how organizations design, deploy, and govern intelligent systems to drive real-world impact and strategic advantage.',
}

# days_until_event is negative (event already passed relative to today,
# 2026-07-14) with no session -- pick a days_until_event value that
# lands on announcement_2 instead, to test the router picking a
# pre-event phase and its matching template (the post-event path was
# already exercised structurally in Task 4's tests).
phase = classify_phase(days_until_event=7, has_session=False)
print('phase:', phase)
result = assemble_input(phase, event)
import json
print(json.dumps(result, indent=2))
"
```

Confirm the printed `phase` is `announcement_2` and `template_text` contains the `announcement_2.md` content (the "Ft [Partner Org(s)]" title pattern).

- [ ] **Step 3: Dispatch the actual Content Agent with the router's assembled output**

Dispatch a subagent via the Agent tool with the full content of `prototype/agents/content-agent.md` as its instructions, plus the `result` dict printed in Step 2 as its input. Ask it to produce the LinkedIn draft only.

- [ ] **Step 4: Validate and judge**

Run the response through `validate_draft`. Judge by eye: does it reflect the `announcement_2` template's structure (title with "Ft" partner call-out) and the real speaker roster accurately, per the same criteria used in Test 2.

- [ ] **Step 5: Log it as Test 3 in the test log**

Read `docs/testing/content-agent-tests.md` first to match its established format exactly (the Summary table + numbered `## Test N` sections with Purpose/Inputs/Output/Findings/What it proves/What it doesn't prove). Append a new `## Test 3` entry documenting: that this test used the router (not manual assembly) for the first time, which phase it picked and why (`days_until_event=7` → `announcement_2`), the draft produced, and the judgment against the criteria. Update the Summary table at the top with a new row. Note explicitly in "what this doesn't prove": the `days_until_event=7` value was chosen manually to exercise `announcement_2`, not derived from today's real date relative to this (already-passed) event — a live run would compute it from `event_date - today`.

- [ ] **Step 6: Commit**

```bash
cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow"
git add docs/testing/content-agent-tests.md
git commit -m "docs: log Test 3 -- first real Content Agent run through the content router"
```
