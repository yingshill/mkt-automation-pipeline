# Content Router — Phase Classifier + Template Assembler

**Status:** Approved, not yet implemented.
**Extends:** `2026-07-13-mateja-captions-integration-design.md`'s Content Agent — this router sits *before* it, deciding which phase applies and assembling the exact input dict that agent already expects. Does not change the Content Agent's persona or contract.
**Context:** Identified as a known gap in `docs/testing/content-agent-tests.md` (2026-07-14) — both tests logged there required a human to already know the scenario and manually assemble the Content Agent's input. This spec closes that gap.

**🔴 Living document, not append-only.** As the router's design evolves — new phases, adjusted thresholds, a real events-linking mechanism once live data exists — update this file in place. Only fork a new spec if the work grows beyond "route + assemble for the Content Agent" into a separate effort.

---

## Goal

Given a rawer request (an event's title and date, optionally an existing session), automatically decide which point in the event lifecycle applies (first announcement, updated lineup, last call, live update, post-event recap) and assemble the exact input dict the Content Agent already consumes — without a human first deciding which template/data combination to use by hand.

## Scoping decisions (from brainstorming session, 2026-07-14)

- **Rule-based, not an LLM classification step.** Phase is determined by date math (days until/since the event) and one data-availability check (does a session/recording exist), not judgment. Reserve AI for genuinely ambiguous input (e.g., no event specified at all) — and even then, the response is "decline and say what's missing," not a guess.
- **Two units, not one function:** a **phase classifier** (pure — dates + a boolean in, a phase label out, no I/O) and a **template assembler** (phase + raw inputs in, the Content Agent's dict out). Different concerns, different reasons to change, independently testable.
- **The router owns a real template catalog.** The 5 real TechEquity post variants (Announcement 1/2/3, During, Post-recap), extracted from their archived social copy into local, reusable files — not just a phase label the human still has to go find a template for.
- **No live Luma/Docs integration.** Event title/date/details are still supplied as plain input by the caller, same as the Content Agent's existing `luma_event_details` — this router doesn't fetch anything live.
- **Day-thresholds are proposed defaults, not sourced from TechEquity's real cadence** — no evidence yet of their actual announcement timing pattern. Adjustable once real data exists.

## Architecture

```
prototype/
├── skills/
│   ├── store.py                  → gains one new table (events) + functions
│   ├── content_router.py         → NEW: classify_phase() + assemble_input()
│   └── (content-agent.md, validators.py, etc. — unchanged)
├── data/
│   └── templates/                → NEW: 5 template files, one per phase
│       ├── announcement_1.md
│       ├── announcement_2.md
│       ├── announcement_3.md
│       ├── during_event.md
│       └── post_event_recap.md
└── tests/
    └── test_content_router.py    → NEW
```

No changes to `content-agent.md`, `validators.py`, `render_dashboard.py`, or the other three agents.

## Data model — new `events` table

Added to `store.py`'s `SCHEMA`, alongside the existing tables:

```sql
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_title TEXT NOT NULL,
    event_date TEXT NOT NULL,
    session_id INTEGER REFERENCES sessions(id),
    created_at TEXT NOT NULL
);
```

- `event_date` is an ISO date string (`"2026-07-28"`), so it sorts and compares correctly as text.
- `session_id` starts `NULL` (no recording yet) and gets set once a session exists for that event — this is the signal the classifier checks. Setting it is a separate, later concern (not part of this router's job); this spec only reads it.
- New `store.py` functions, following the existing style exactly:
  - `insert_event(db_path, event_title, event_date) -> int`
  - `get_event(db_path, event_id) -> dict | None`
  - `link_session_to_event(db_path, event_id, session_id) -> None`

## Component 1 — Phase classifier

**Pure function, no I/O:**

```python
def classify_phase(days_until_event: int, has_session: bool) -> str:
    """Returns one of: announcement_1, announcement_2, announcement_3,
    during_event, awaiting_recording, post_event_recap."""
```

Rules — evaluated in this order (`days_until_event` decides first; `has_session` only breaks the tie once the event has passed):

1. `days_until_event > 14` → `announcement_1`
2. `3 <= days_until_event <= 14` → `announcement_2`
3. `1 <= days_until_event <= 2` → `announcement_3`
4. `days_until_event == 0` → `during_event`
5. `days_until_event < 0` and `has_session` is `True` → `post_event_recap`
6. `days_until_event < 0` and `has_session` is `False` → `awaiting_recording`

**`has_session` is irrelevant for rules 1-4** — a pre-event teaser clip existing early doesn't change which pre-event announcement stage applies; only once the event date has passed does whether a recording exists decide between `post_event_recap` and `awaiting_recording`. This is deliberately unambiguous: every `(days_until_event, has_session)` pair matches exactly one rule above, checked in order.

`days_until_event` is computed by the caller (or a thin wrapper) as `(event_date - today).days`, with `today` passed in as an explicit parameter — never computed internally via `datetime.now()` — so tests are deterministic and don't depend on wall-clock time.

## Component 2 — Template assembler

```python
def assemble_input(phase: str, event: dict, session: dict | None = None,
                    past_reference_post: str | None = None) -> dict:
    """Loads the matching template from prototype/data/templates/ and
    returns the exact dict shape content-agent.md expects:
    {session, template_text, luma_event_details, past_reference_post}."""
```

- `awaiting_recording` is not a template-loading case — `assemble_input` raises `ValueError` naming that no draft can be produced yet (nothing to post — the event passed and no recording exists), rather than returning a dict.
- For every other phase, loads `prototype/data/templates/{phase}.md`, builds `luma_event_details` from `event`, passes `session` through if given (only populated for `post_event_recap`), and returns the assembled dict — ready to hand directly to the Content Agent, unchanged.

## Template catalog

Same honest-construction process as the two existing test runs: each file is a real TechEquity example post, generalized by hand into a fill-in-the-blank shape, clearly documented (in a header comment in each file) as constructed for this system, not a literal export of "the Doc." `during_event.md` and `post_event_recap.md` are built the same way from TechEquity's real "During" and "Post" example copy (already read this session, not yet transcribed into files).

## Data flow

```
caller supplies: event_title, event_date, today (+ session if known)
        │
        ▼
  store.insert_event / get_event  →  has_session = event["session_id"] is not None
        │
        ▼
  classify_phase(days_until_event, has_session)  →  phase
        │
        ▼
  assemble_input(phase, event, session, past_reference_post)  →  Content Agent input dict
        │
        ▼
  (existing, unchanged) Content Agent
```

## Error handling

- Missing/unparseable `event_date`: raise `ValueError` naming the problem — same discipline as `validate_content_agent_input`.
- `awaiting_recording`: not silently skipped — `assemble_input` raises `ValueError` explaining the event has passed and no recording exists yet, so the caller (human or future orchestrator) knows to wait, not that something broke.
- Template file missing for a given phase (e.g., a new phase added without its template): raise `FileNotFoundError` with the expected path — fail loud, don't fall back to a different template silently.

## Testing

- `classify_phase`: pure unit tests, one per row of the phase table above, plus boundary cases (exactly 3 days, exactly 14 days, exactly 0).
- `assemble_input`: one test per phase confirming the right template file loads and the output dict passes `validate_content_agent_input`; one test confirming `awaiting_recording` raises instead of returning.
- `store.py` additions: `insert_event`/`get_event`/`link_session_to_event`, following the existing `test_store.py` pattern exactly (real inserts/queries, no mocks).
- Manual validation: run the assembled output from at least one phase through an actual Content Agent dispatch (mirroring the two tests already in `docs/testing/content-agent-tests.md`) — log it there as Test 3 once implemented.

## Explicit non-goals for this pass

- No live Luma API integration — event details are still manual input.
- No automatic session-to-event linking — `link_session_to_event` exists but nothing calls it yet; that's a separate, later concern (likely tied to Task 8's orchestration driver).
- No change to the Content Agent's persona, `validators.py`, or the other three agents.
- Day-thresholds are defaults, not validated against TechEquity's real posting cadence.
