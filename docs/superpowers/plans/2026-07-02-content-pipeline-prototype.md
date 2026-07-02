# TechEquity Content Pipeline Prototype — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude-Code-native prototype of the 5-part TechEquity content pipeline (content engine, lead capture, outreach, nurture, dashboard), sourcing from TechEquity's YouTube session library, validated end-to-end before porting to OpenClaw/ClawMax.

**Architecture:** A shared SQLite store (`prototype/skills/store.py`) is the single source of truth all components read/write. Deterministic work (fetching public YouTube/speaker data, persisting, rendering the dashboard) is plain tested Python. Judgment work (turning a session into on-voice posts, enriching a lead, drafting outreach, planning a nurture sequence) is done by Claude Code subagents, each defined by a persona file in `prototype/agents/` and validated by a Python schema-checker so its output has a testable contract even though its content is human-reviewed, not asserted.

**Tech Stack:** Python 3, stdlib `sqlite3`, `requests`, `beautifulsoup4`, `youtube-transcript-api`, `pytest`. Agent personas are markdown, invoked via Claude Code's Agent tool — no separate LLM API wiring, since this prototype runs inside Claude Code itself.

## Global Constraints

- Outreach must have **zero send capability implemented** — no email/API send function exists anywhere in the codebase, per `../specs/2026-07-02-content-pipeline-prototype-design.md`.
- All external data fetches are **public, unauthenticated** — no API keys, no Vigo integration (access not yet requested).
- Content-quality judgment is **human-reviewed, not automated** — validators check shape/schema only, never "goodness."
- Nurture sequences are **templates, not a live scheduler** — no wall-clock/cron logic.
- Every fetch with a plausible failure mode (missing transcript, missing speaker page) **falls back and logs**, never fails the run silently.
- File layout mirrors OpenClaw's own structure (`agents/`, `skills/`) on purpose, for a low-friction future port.
- Any XML parsing of network-fetched data uses `defusedxml`, never stdlib `xml.etree.ElementTree` directly — stdlib XML parsers are vulnerable to XXE/billion-laughs on untrusted input.

---

## Grounding notes (found during planning, not assumed)

- TechEquity's speaker directory index (`https://techequity-ai.org/speaker/`) is filter/sort-driven and did not expose speaker entries in a plain fetch — it's likely client-rendered. **Individual speaker pages** (e.g. `https://techequity-ai.org/speaker/george-ekas/`) *are* plain server-rendered HTML with name (`h1`), title/company (`h2` + logo image), bio paragraph, session block (time, title link, location, topic tags), and a LinkedIn link. So speaker enrichment works by **guessing a slug from the speaker's name** (`name.lower().replace(' ', '-')`) and fetching that page directly — with a graceful fallback (log + skip) if the slug 404s, since the index can't be reliably enumerated without a browser.
- The channel's actual `UC...` ID (needed for the RSS video feed) was not resolved during planning — a page fetch through the summarizing WebFetch tool doesn't expose raw HTML/meta tags. Task 2 includes a real resolution step (regex against the raw page HTML) rather than a hardcoded guessed ID.

---

### Task 1: Shared SQLite store

**Files:**
- Create: `prototype/skills/store.py`
- Create: `prototype/tests/test_store.py`
- Create: `prototype/requirements.txt`

**Interfaces:**
- Produces (used by every later task):
  - `init_db(db_path: str) -> None`
  - `insert_session(db_path: str, video_id: str, title: str, url: str, speaker_name: str | None = None, speaker_bio: str | None = None, description: str | None = None, transcript: str | None = None, transcript_available: bool = False) -> int`
  - `get_session_by_video_id(db_path: str, video_id: str) -> dict | None`
  - `list_sessions(db_path: str) -> list[dict]`
  - `insert_draft(db_path: str, session_id: int, channel: str, content: str) -> int`
  - `list_drafts(db_path: str, session_id: int | None = None) -> list[dict]`
  - `insert_lead(db_path: str, name: str, source: str, email: str | None = None, company: str | None = None, context: str | None = None) -> int`
  - `update_lead_enrichment(db_path: str, lead_id: int, company: str | None = None, suggested_tier: str | None = None, context: str | None = None) -> None`
  - `list_leads(db_path: str) -> list[dict]`
  - `insert_outreach(db_path: str, lead_id: int, message: str, session_id: int | None = None) -> int`
  - `list_outreach(db_path: str, lead_id: int | None = None) -> list[dict]`
  - `upsert_nurture_stage(db_path: str, lead_id: int, stage: str, next_touch_template: str) -> None`
  - `list_nurture_stages(db_path: str) -> list[dict]`

- [ ] **Step 1: Write the failing tests**

Create `prototype/tests/test_store.py`:

```python
import sqlite3
import pytest
from prototype.skills.store import (
    init_db, insert_session, get_session_by_video_id, list_sessions,
    insert_draft, list_drafts,
    insert_lead, update_lead_enrichment, list_leads,
    insert_outreach, list_outreach,
    upsert_nurture_stage, list_nurture_stages,
)


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "pipeline.db")
    init_db(path)
    return path


def test_init_db_creates_all_tables(db_path):
    conn = sqlite3.connect(db_path)
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    conn.close()
    assert {"sessions", "drafts", "leads", "outreach", "nurture_stage"} <= tables


def test_insert_and_get_session(db_path):
    session_id = insert_session(
        db_path, video_id="abc123", title="AI Agents 101",
        url="https://youtube.com/watch?v=abc123",
        speaker_name="Jane Doe", speaker_bio="Founder of X",
        description="A talk about agents", transcript="full transcript text",
        transcript_available=True,
    )
    assert session_id == 1
    session = get_session_by_video_id(db_path, "abc123")
    assert session["title"] == "AI Agents 101"
    assert session["transcript_available"] == 1


def test_insert_session_duplicate_video_id_raises(db_path):
    insert_session(db_path, video_id="dup1", title="First", url="u")
    with pytest.raises(sqlite3.IntegrityError):
        insert_session(db_path, video_id="dup1", title="Second", url="u2")


def test_list_sessions_returns_all(db_path):
    insert_session(db_path, video_id="v1", title="One", url="u1")
    insert_session(db_path, video_id="v2", title="Two", url="u2")
    sessions = list_sessions(db_path)
    assert len(sessions) == 2
    assert {s["video_id"] for s in sessions} == {"v1", "v2"}


def test_insert_and_list_drafts(db_path):
    session_id = insert_session(db_path, video_id="v1", title="One", url="u1")
    insert_draft(db_path, session_id, "LinkedIn", "A LinkedIn post draft")
    insert_draft(db_path, session_id, "Instagram", "An Instagram caption")
    drafts = list_drafts(db_path, session_id=session_id)
    assert len(drafts) == 2
    assert {d["channel"] for d in drafts} == {"LinkedIn", "Instagram"}


def test_list_drafts_without_session_filter_returns_all(db_path):
    s1 = insert_session(db_path, video_id="v1", title="One", url="u1")
    s2 = insert_session(db_path, video_id="v2", title="Two", url="u2")
    insert_draft(db_path, s1, "LinkedIn", "draft 1")
    insert_draft(db_path, s2, "LinkedIn", "draft 2")
    assert len(list_drafts(db_path)) == 2


def test_insert_lead_and_enrich(db_path):
    lead_id = insert_lead(db_path, name="Sam Prospect", source="sample-seed", email="sam@example.com")
    update_lead_enrichment(db_path, lead_id, company="Acme AI", suggested_tier="Gold", context="Interested in sponsorship")
    leads = list_leads(db_path)
    assert len(leads) == 1
    assert leads[0]["company"] == "Acme AI"
    assert leads[0]["suggested_tier"] == "Gold"
    assert leads[0]["enriched_at"] is not None


def test_insert_and_list_outreach(db_path):
    lead_id = insert_lead(db_path, name="Sam Prospect", source="sample-seed")
    session_id = insert_session(db_path, video_id="v1", title="One", url="u1")
    insert_outreach(db_path, lead_id, "Hi Sam, following up on...", session_id=session_id)
    outreach = list_outreach(db_path, lead_id=lead_id)
    assert len(outreach) == 1
    assert "Sam" in outreach[0]["message"]


def test_upsert_nurture_stage_updates_in_place(db_path):
    lead_id = insert_lead(db_path, name="Sam Prospect", source="sample-seed")
    upsert_nurture_stage(db_path, lead_id, stage="touch_1", next_touch_template="Following up...")
    upsert_nurture_stage(db_path, lead_id, stage="touch_2", next_touch_template="Checking in...")
    stages = list_nurture_stages(db_path)
    assert len(stages) == 1
    assert stages[0]["stage"] == "touch_2"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow" && python3 -m pytest prototype/tests/test_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'prototype.skills.store'`

- [ ] **Step 3: Write the implementation**

Create `prototype/requirements.txt`:

```
pytest>=8.0
requests>=2.31
beautifulsoup4>=4.12
youtube-transcript-api>=0.6
defusedxml>=0.7
```

Create `prototype/__init__.py` (empty), `prototype/skills/__init__.py` (empty), `prototype/tests/__init__.py` (empty) so the package imports in tests resolve.

Create `prototype/skills/store.py`:

```python
"""Shared SQLite store for the TechEquity content pipeline prototype.

Every pipeline component (fetch, content agent, lead capture agent,
outreach agent, nurture agent, dashboard) reads/writes through this
module. This is the layer that ports to a real datastore (or Vigo)
once the prototype graduates out of Claude Code.
"""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    speaker_name TEXT,
    speaker_bio TEXT,
    description TEXT,
    transcript TEXT,
    transcript_available INTEGER NOT NULL DEFAULT 0,
    fetched_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    channel TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT,
    company TEXT,
    context TEXT,
    suggested_tier TEXT,
    source TEXT NOT NULL,
    enriched_at TEXT
);

CREATE TABLE IF NOT EXISTS outreach (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL REFERENCES leads(id),
    session_id INTEGER REFERENCES sessions(id),
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS nurture_stage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL UNIQUE REFERENCES leads(id),
    stage TEXT NOT NULL,
    next_touch_template TEXT,
    updated_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = _connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def insert_session(db_path, video_id, title, url, speaker_name=None,
                    speaker_bio=None, description=None, transcript=None,
                    transcript_available=False) -> int:
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO sessions (video_id, title, url, speaker_name, "
            "speaker_bio, description, transcript, transcript_available, fetched_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (video_id, title, url, speaker_name, speaker_bio, description,
             transcript, int(transcript_available), _now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_session_by_video_id(db_path, video_id) -> dict | None:
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM sessions WHERE video_id = ?", (video_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_sessions(db_path) -> list[dict]:
    conn = _connect(db_path)
    try:
        rows = conn.execute("SELECT * FROM sessions ORDER BY id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def insert_draft(db_path, session_id, channel, content) -> int:
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO drafts (session_id, channel, content, created_at) "
            "VALUES (?, ?, ?, ?)",
            (session_id, channel, content, _now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_drafts(db_path, session_id=None) -> list[dict]:
    conn = _connect(db_path)
    try:
        if session_id is None:
            rows = conn.execute("SELECT * FROM drafts ORDER BY id").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM drafts WHERE session_id = ? ORDER BY id", (session_id,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def insert_lead(db_path, name, source, email=None, company=None, context=None) -> int:
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO leads (name, email, company, context, suggested_tier, source, enriched_at) "
            "VALUES (?, ?, ?, ?, NULL, ?, NULL)",
            (name, email, company, context, source),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_lead_enrichment(db_path, lead_id, company=None, suggested_tier=None, context=None) -> None:
    conn = _connect(db_path)
    try:
        conn.execute(
            "UPDATE leads SET company = COALESCE(?, company), "
            "suggested_tier = COALESCE(?, suggested_tier), "
            "context = COALESCE(?, context), enriched_at = ? WHERE id = ?",
            (company, suggested_tier, context, _now(), lead_id),
        )
        conn.commit()
    finally:
        conn.close()


def list_leads(db_path) -> list[dict]:
    conn = _connect(db_path)
    try:
        rows = conn.execute("SELECT * FROM leads ORDER BY id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def insert_outreach(db_path, lead_id, message, session_id=None) -> int:
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO outreach (lead_id, session_id, message, created_at) "
            "VALUES (?, ?, ?, ?)",
            (lead_id, session_id, message, _now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_outreach(db_path, lead_id=None) -> list[dict]:
    conn = _connect(db_path)
    try:
        if lead_id is None:
            rows = conn.execute("SELECT * FROM outreach ORDER BY id").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM outreach WHERE lead_id = ? ORDER BY id", (lead_id,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def upsert_nurture_stage(db_path, lead_id, stage, next_touch_template) -> None:
    conn = _connect(db_path)
    try:
        conn.execute(
            "INSERT INTO nurture_stage (lead_id, stage, next_touch_template, updated_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(lead_id) DO UPDATE SET "
            "stage = excluded.stage, next_touch_template = excluded.next_touch_template, "
            "updated_at = excluded.updated_at",
            (lead_id, stage, next_touch_template, _now()),
        )
        conn.commit()
    finally:
        conn.close()


def list_nurture_stages(db_path) -> list[dict]:
    conn = _connect(db_path)
    try:
        rows = conn.execute("SELECT * FROM nurture_stage ORDER BY id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow" && python3 -m venv .venv && .venv/bin/pip install -r prototype/requirements.txt && .venv/bin/python -m pytest prototype/tests/test_store.py -v`
Expected: `9 passed`

- [ ] **Step 5: Commit**

```bash
cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow"
git add prototype/skills/store.py prototype/tests/test_store.py prototype/requirements.txt \
        prototype/__init__.py prototype/skills/__init__.py prototype/tests/__init__.py .venv 2>/dev/null
git add prototype/skills/store.py prototype/tests/test_store.py prototype/requirements.txt \
        prototype/__init__.py prototype/skills/__init__.py prototype/tests/__init__.py
echo ".venv/" >> .gitignore
echo "prototype/data/pipeline.db" >> .gitignore
echo "__pycache__/" >> .gitignore
git add .gitignore
git commit -m "feat: add shared SQLite store for content pipeline prototype"
```

---

### Task 2: Session fetch layer (YouTube + speaker enrichment)

**Files:**
- Create: `prototype/skills/fetch_sessions.py`
- Create: `prototype/tests/test_fetch_sessions.py`

**Interfaces:**
- Consumes: nothing from Task 1 directly (this task only fetches and returns dicts; persistence is the caller's job in Task 8).
- Produces (used by Task 8's orchestrator):
  - `resolve_channel_id(handle: str) -> str` — raises `ValueError` if not found
  - `fetch_channel_videos(channel_id: str) -> list[dict]` — each dict has `video_id`, `title`, `url`, `description`, `published_at`
  - `fetch_transcript(video_id: str) -> str | None` — `None` if unavailable (fallback case)
  - `fetch_speaker_profile(speaker_name: str) -> dict | None` — `{"bio": str, "title_company": str}` or `None` if the guessed page 404s
  - `build_session_record(video: dict) -> dict` — combines the above into the exact kwargs shape `store.insert_session` expects

- [ ] **Step 1: Write the failing tests**

Create `prototype/tests/test_fetch_sessions.py`:

```python
import pytest
from prototype.skills.fetch_sessions import (
    resolve_channel_id, fetch_channel_videos, fetch_transcript,
    fetch_speaker_profile, build_session_record, slugify_name,
)


def test_slugify_name_matches_known_speaker_page():
    # Verified during planning: https://techequity-ai.org/speaker/george-ekas/ is real.
    assert slugify_name("George Ekas") == "george-ekas"


@pytest.mark.integration
def test_resolve_channel_id_returns_uc_prefixed_id():
    channel_id = resolve_channel_id("TechEquityAi")
    assert channel_id.startswith("UC")


@pytest.mark.integration
def test_fetch_channel_videos_returns_at_least_one_real_video():
    channel_id = resolve_channel_id("TechEquityAi")
    videos = fetch_channel_videos(channel_id)
    assert len(videos) > 0
    assert "video_id" in videos[0]
    assert "title" in videos[0]
    assert videos[0]["url"].startswith("https://www.youtube.com/watch?v=")


@pytest.mark.integration
def test_fetch_transcript_handles_missing_transcript_gracefully():
    # A deliberately invalid video_id must return None, not raise.
    result = fetch_transcript("this-video-id-does-not-exist")
    assert result is None


@pytest.mark.integration
def test_fetch_speaker_profile_known_speaker_returns_bio():
    profile = fetch_speaker_profile("George Ekas")
    assert profile is not None
    assert "bio" in profile
    assert len(profile["bio"]) > 0


@pytest.mark.integration
def test_fetch_speaker_profile_unknown_speaker_returns_none():
    profile = fetch_speaker_profile("Definitely Not A Real Speaker Zzz")
    assert profile is None


def test_build_session_record_shape():
    video = {
        "video_id": "abc123",
        "title": "AI Agents 101",
        "url": "https://www.youtube.com/watch?v=abc123",
        "description": "A talk about agents by Jane Doe",
        "published_at": "2026-05-01T00:00:00Z",
    }
    record = build_session_record(video)
    assert record["video_id"] == "abc123"
    assert record["title"] == "AI Agents 101"
    assert record["url"] == video["url"]
    assert "transcript_available" in record
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow" && .venv/bin/python -m pytest prototype/tests/test_fetch_sessions.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'prototype.skills.fetch_sessions'`

- [ ] **Step 3: Register the `integration` marker**

Create `prototype/pytest.ini`:

```ini
[pytest]
markers =
    integration: hits real external services (YouTube, techequity-ai.org); requires network
```

- [ ] **Step 4: Write the implementation**

Create `prototype/skills/fetch_sessions.py`:

```python
"""Fetch TechEquity session data from public sources — no API keys.

Video listing: YouTube's public RSS feed (works for channel_id or
playlist_id, no auth). Transcripts: youtube-transcript-api (public
scrape of YouTube's own transcript endpoint). Speaker enrichment:
individual TechEquity speaker pages, found by guessing a slug from
the speaker's name (the index page is client-rendered and can't be
listed reliably without a browser — see plan grounding notes).
"""
import re
import defusedxml.ElementTree as ET  # nosec — stdlib ElementTree is XXE/billion-laughs
                                       # vulnerable on untrusted XML; this feed is fetched
                                       # over the network, so treat it as untrusted input.

import requests
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

YOUTUBE_RSS_URL = "https://www.youtube.com/feeds/videos.xml"
SPEAKER_PAGE_URL = "https://techequity-ai.org/speaker/{slug}/"
_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}


def resolve_channel_id(handle: str) -> str:
    resp = requests.get(f"https://www.youtube.com/@{handle}", timeout=10)
    resp.raise_for_status()
    match = re.search(r'"channelId":"(UC[\w-]{22})"', resp.text)
    if not match:
        raise ValueError(f"Could not resolve channel ID for handle @{handle}")
    return match.group(1)


def fetch_channel_videos(channel_id: str) -> list[dict]:
    resp = requests.get(YOUTUBE_RSS_URL, params={"channel_id": channel_id}, timeout=10)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    videos = []
    for entry in root.findall("atom:entry", _ATOM_NS):
        video_id = entry.find("yt:videoId", _ATOM_NS).text
        title = entry.find("atom:title", _ATOM_NS).text
        published = entry.find("atom:published", _ATOM_NS).text
        media_group = entry.find("{http://search.yahoo.com/mrss/}group")
        description = ""
        if media_group is not None:
            desc_el = media_group.find("{http://search.yahoo.com/mrss/}description")
            if desc_el is not None and desc_el.text:
                description = desc_el.text
        videos.append({
            "video_id": video_id,
            "title": title,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "description": description,
            "published_at": published,
        })
    return videos


def fetch_transcript(video_id: str) -> str | None:
    try:
        segments = YouTubeTranscriptApi.get_transcript(video_id)
    except (TranscriptsDisabled, NoTranscriptFound, Exception):
        return None
    return " ".join(seg["text"] for seg in segments)


def slugify_name(name: str) -> str:
    return name.strip().lower().replace(" ", "-")


def fetch_speaker_profile(speaker_name: str) -> dict | None:
    slug = slugify_name(speaker_name)
    resp = requests.get(SPEAKER_PAGE_URL.format(slug=slug), timeout=10)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    title_el = soup.find("h2")
    bio_el = soup.find("p")
    return {
        "title_company": title_el.get_text(strip=True) if title_el else "",
        "bio": bio_el.get_text(strip=True) if bio_el else "",
    }


def build_session_record(video: dict) -> dict:
    transcript = fetch_transcript(video["video_id"])
    return {
        "video_id": video["video_id"],
        "title": video["title"],
        "url": video["url"],
        "description": video.get("description", ""),
        "transcript": transcript,
        "transcript_available": transcript is not None,
        "speaker_name": None,
        "speaker_bio": None,
    }
```

**Known limitation to carry forward (not a bug):** `build_session_record` doesn't populate `speaker_name` — video titles/descriptions don't reliably contain a parseable speaker name. Task 8's orchestrator step documents extracting the speaker name as a manual/agent-assisted step before calling `fetch_speaker_profile`, rather than this module guessing at name-extraction regexes with no ground truth to validate against.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow" && .venv/bin/pip install -r prototype/requirements.txt && .venv/bin/python -m pytest prototype/tests/test_fetch_sessions.py -v`
Expected: `8 passed`. If any `integration`-marked test fails due to a real site/markup change (e.g. `resolve_channel_id` regex no longer matches, or the speaker page's `h2`/`p` selectors have changed), that's real signal to fix the scraper against current markup — not a flaky test to retry blindly.

- [ ] **Step 6: Commit**

```bash
cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow"
git add prototype/skills/fetch_sessions.py prototype/tests/test_fetch_sessions.py prototype/pytest.ini prototype/requirements.txt
git commit -m "feat: add YouTube + speaker-page fetch layer"
```

---

### Task 3: Content Agent

**Files:**
- Create: `prototype/agents/content-agent.md`
- Create: `prototype/skills/validators.py` (starts here, other agents add to it in later tasks)
- Create: `prototype/tests/test_validators.py` (starts here)
- Create: `prototype/output/drafts/.gitkeep`

**Interfaces:**
- Consumes: a session dict shaped like `store.get_session_by_video_id()`'s return value.
- Produces: `validate_draft(draft: dict) -> None` (raises `ValueError` on malformed shape); later tasks add their own `validate_*` functions to the same file.

- [ ] **Step 1: Write the failing test**

Create `prototype/tests/test_validators.py`:

```python
import pytest
from prototype.skills.validators import validate_draft

VALID_CHANNELS = {"LinkedIn", "Instagram", "Facebook", "YouTube", "Sidekick"}


def test_validate_draft_accepts_well_formed_draft():
    validate_draft({"channel": "LinkedIn", "content": "A real post about the session."})


def test_validate_draft_rejects_unknown_channel():
    with pytest.raises(ValueError, match="channel"):
        validate_draft({"channel": "MySpace", "content": "..."})


def test_validate_draft_rejects_empty_content():
    with pytest.raises(ValueError, match="content"):
        validate_draft({"channel": "LinkedIn", "content": ""})


def test_validate_draft_rejects_missing_keys():
    with pytest.raises(ValueError):
        validate_draft({"channel": "LinkedIn"})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow" && .venv/bin/python -m pytest prototype/tests/test_validators.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'prototype.skills.validators'`

- [ ] **Step 3: Write the implementation**

Create `prototype/skills/validators.py`:

```python
"""Schema validators for agent-produced output.

These check *shape*, never *quality* — content quality is human-reviewed
per the design spec's global constraint. A validator passing means the
output is safe to persist, not that it's good copy.
"""

VALID_CHANNELS = {"LinkedIn", "Instagram", "Facebook", "YouTube", "Sidekick"}


def validate_draft(draft: dict) -> None:
    if "channel" not in draft or "content" not in draft:
        raise ValueError("draft missing required keys: channel, content")
    if draft["channel"] not in VALID_CHANNELS:
        raise ValueError(f"unknown channel: {draft['channel']!r} (expected one of {VALID_CHANNELS})")
    if not draft["content"] or not draft["content"].strip():
        raise ValueError("draft content must not be empty")
```

Create `prototype/agents/content-agent.md`:

```markdown
# Content Agent

## Persona

You are the Content Agent for TechEquity AI's content pipeline. You turn one
recorded session (a talk from the Silicon Valley AI Summit or a monthly
forum) into platform-specific draft posts.

## Voice brief (derived from research-brief.md + strategy.md — no formal
## brand_os DNA.md exists for TechEquity, so this is the source of truth
## for voice until one is written)

- TechEquity is run by design-agency-background founders (Sheena Tu: MFA
  Design, ex-Monigle brand agency). Favor clean, professional, brand-forward
  language over hype or clickbait — this is a design-literate audience.
- Audience: AI/tech professionals, sponsors, and the Silicon Valley AI
  community — not developers specifically (that's ClawMax's audience, a
  different pipeline).
- The org is volunteer-run and lean. Content should read as credible and
  well-produced, never as if a giant marketing team is behind it — authentic
  scale, not corporate gloss.
- Every post must be traceable to a real session — no fabricated quotes,
  no invented statistics. If the transcript is unavailable, work only from
  the title/description and say less rather than embellish.

## Channel format rules

- **LinkedIn:** 150-300 words, professional tone, one clear insight from
  the talk, ends with a question or a link to the recording.
- **Instagram:** 1-2 short sentences + 3-5 hashtags, caption-first (assume
  a still frame or slide as the image, not generated here).
- **Facebook:** similar to LinkedIn but shorter (80-150 words), more
  community-toned ("come learn with us" register, not corporate).
- **YouTube (shorts script):** a 30-45 second spoken script, 3-5 short
  lines, hook in the first line.
- **Sidekick:** plain-text community post, 2-4 sentences, casual register
  (Sidekick is TechEquity's internal community channel, not a public
  broadcast surface) — **[VERIFY]** exact format/length conventions once
  Sidekick's actual posting mechanics are confirmed; treat this as a
  reasonable default, not a confirmed spec.

## Output contract

Produce one draft per channel as a dict: `{"channel": <one of LinkedIn,
Instagram, Facebook, YouTube, Sidekick>, "content": <the draft text>}`.
Every draft must pass `prototype/skills/validators.py::validate_draft`
before being persisted via `store.insert_draft`.

## Constraints

- Do not invent session content that isn't in the transcript/description.
- If `transcript_available` is `False` for the input session, say so
  explicitly in your response before drafting, and draft only from the
  title/description — shorter, more conservative drafts are correct here.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow" && .venv/bin/python -m pytest prototype/tests/test_validators.py -v`
Expected: `4 passed`

- [ ] **Step 5: Manual validation — one real Content Agent invocation**

This step cannot be a pytest assertion (it's a judgment call, per the design spec's constraint that content quality is human-reviewed). Do this once Task 2's fetch layer has populated at least one real session into the store (Task 8 wires that up) — for now, validate the persona against one manually-fetched session:

1. Run `fetch_channel_videos` for the resolved TechEquity channel ID and take the first video.
2. Dispatch a subagent via the Agent tool with the content of `prototype/agents/content-agent.md` as its instructions, plus that video's title/description/transcript as input.
3. For each of the 5 channels in the response, run it through `validate_draft`.
4. Confirm by eye: no fabricated claims, correct register per channel per the format rules above.
5. If it passes, persist via `store.insert_draft` for each channel and note the result in `prototype/output/drafts/` as a `.md` file per channel (filename: `{video_id}-{channel}.md`).

- [ ] **Step 6: Commit**

```bash
cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow"
git add prototype/agents/content-agent.md prototype/skills/validators.py prototype/tests/test_validators.py prototype/output/drafts/.gitkeep
git commit -m "feat: add Content Agent persona + draft validator"
```

---

### Task 4: Lead Capture Agent

**Files:**
- Create: `prototype/agents/lead-capture-agent.md`
- Modify: `prototype/skills/validators.py` (add `validate_lead_enrichment`)
- Modify: `prototype/tests/test_validators.py` (add tests)
- Create: `prototype/data/sample_leads.json` (seed data, since no live inbound source exists)

**Interfaces:**
- Consumes: a raw lead record `{"name": str, "source": str, "email": str | None, "company": str | None}`.
- Produces: `validate_lead_enrichment(enrichment: dict) -> None`.

- [ ] **Step 1: Write the failing tests**

Add to `prototype/tests/test_validators.py`:

```python
from prototype.skills.validators import validate_lead_enrichment

VALID_TIERS = {"Bronze", "Silver", "Gold", "Platinum", "Design Partner"}


def test_validate_lead_enrichment_accepts_well_formed():
    validate_lead_enrichment({
        "suggested_tier": "Gold", "company": "Acme AI", "context": "Asked about sponsorship at the May forum",
    })


def test_validate_lead_enrichment_rejects_unknown_tier():
    with pytest.raises(ValueError, match="tier"):
        validate_lead_enrichment({"suggested_tier": "Diamond", "company": "Acme AI", "context": "..."})


def test_validate_lead_enrichment_rejects_empty_context():
    with pytest.raises(ValueError, match="context"):
        validate_lead_enrichment({"suggested_tier": "Gold", "company": "Acme AI", "context": ""})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow" && .venv/bin/python -m pytest prototype/tests/test_validators.py -v`
Expected: FAIL with `ImportError: cannot import name 'validate_lead_enrichment'`

- [ ] **Step 3: Write the implementation**

Add to `prototype/skills/validators.py`:

```python
VALID_TIERS = {"Bronze", "Silver", "Gold", "Platinum", "Design Partner"}


def validate_lead_enrichment(enrichment: dict) -> None:
    if "suggested_tier" not in enrichment or "context" not in enrichment:
        raise ValueError("enrichment missing required keys: suggested_tier, context")
    if enrichment["suggested_tier"] not in VALID_TIERS:
        raise ValueError(f"unknown tier: {enrichment['suggested_tier']!r} (expected one of {VALID_TIERS})")
    if not enrichment["context"] or not enrichment["context"].strip():
        raise ValueError("enrichment context must not be empty")
```

Create `prototype/data/sample_leads.json` (seed data — there is no live inbound source, per the design spec's explicit prototype limitation):

```json
[
  {
    "name": "Priya Anand",
    "source": "sample-seed",
    "email": "priya@example-startup.ai",
    "company": "Example Startup AI",
    "raw_note": "Filled out the exhibitor interest form after the March forum, asked about mid-tier sponsorship."
  },
  {
    "name": "Marcus Webb",
    "source": "sample-seed",
    "email": "marcus@bigcorp.example",
    "company": "BigCorp Example",
    "raw_note": "LinkedIn DM after seeing a recap post, asked whether BigCorp could get a keynote slot at the November summit."
  },
  {
    "name": "Dana Kim",
    "source": "sample-seed",
    "email": null,
    "company": null,
    "raw_note": "Attended two monthly forums as a guest, asked a volunteer about becoming a paid member/sponsor."
  }
]
```

Create `prototype/agents/lead-capture-agent.md`:

```markdown
# Lead Capture Agent

## Persona

You are the Lead Capture Agent for TechEquity AI. You take a raw interest
signal (currently: seeded sample records, since no live inbound source is
connected yet — see `prototype/data/sample_leads.json`) and enrich it into
a structured lead ready for outreach.

## What "enrichment" means here

- Infer a **suggested sponsorship/membership tier** from the raw note —
  one of: Bronze, Silver, Gold, Platinum, Design Partner. Base this on
  explicit signals in the note (company size hints, what they asked for),
  not guesswork dressed as confidence — if the note gives no real signal,
  default to the lowest tier (Bronze) rather than inventing justification
  for a higher one.
- Write a one-to-two sentence **context** summary: what prompted this lead,
  in plain language an outreach drafter can use directly.
- Do not fabricate a company or contact detail that isn't in the raw note.

## Output contract

For each raw lead, produce `{"suggested_tier": <one of the 5 tiers>,
"company": <from raw note, may be None>, "context": <your summary>}`.
This must pass `prototype/skills/validators.py::validate_lead_enrichment`
before being persisted via `store.update_lead_enrichment`.

## Constraints

- No live inbound source exists yet — this agent is validated against
  `prototype/data/sample_leads.json`, not real traffic. Don't treat sample
  data's outputs as production-ready; they're for pipeline validation.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow" && .venv/bin/python -m pytest prototype/tests/test_validators.py -v`
Expected: `7 passed`

- [ ] **Step 5: Manual validation — one real Lead Capture Agent invocation**

1. Load `prototype/data/sample_leads.json`, take the first record.
2. Insert it via `store.insert_lead` (name, source, email, company from the raw record).
3. Dispatch a subagent via the Agent tool with `prototype/agents/lead-capture-agent.md` as instructions, passing the `raw_note`.
4. Run the response through `validate_lead_enrichment`.
5. If it passes, persist via `store.update_lead_enrichment`.

- [ ] **Step 6: Commit**

```bash
cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow"
git add prototype/agents/lead-capture-agent.md prototype/skills/validators.py prototype/tests/test_validators.py prototype/data/sample_leads.json
git commit -m "feat: add Lead Capture Agent persona + enrichment validator + sample leads"
```

---

### Task 5: Outreach Agent

**Files:**
- Create: `prototype/agents/outreach-agent.md`
- Modify: `prototype/skills/validators.py` (add `validate_outreach_message`)
- Modify: `prototype/tests/test_validators.py` (add tests)
- Create: `prototype/output/outreach-drafts/.gitkeep`

**Interfaces:**
- Consumes: an enriched lead dict (from Task 4) + optionally a session dict (from Task 1's store) that likely sparked interest.
- Produces: `validate_outreach_message(message: dict) -> None`.

- [ ] **Step 1: Write the failing tests**

Add to `prototype/tests/test_validators.py`:

```python
from prototype.skills.validators import validate_outreach_message

FORBIDDEN_SEND_MARKERS = ("smtp", "sendgrid", "ses.send_email", "requests.post(", "mailto:")


def test_validate_outreach_message_accepts_well_formed():
    validate_outreach_message({"lead_id": 1, "message": "Hi Priya, following up on your interest..."})


def test_validate_outreach_message_rejects_empty_message():
    with pytest.raises(ValueError, match="message"):
        validate_outreach_message({"lead_id": 1, "message": ""})


def test_validate_outreach_message_rejects_missing_lead_id():
    with pytest.raises(ValueError, match="lead_id"):
        validate_outreach_message({"message": "..."})


def test_outreach_agent_file_contains_no_send_capability():
    # Structural guarantee from the design spec: no send path exists at all.
    with open("prototype/agents/outreach-agent.md") as f:
        content = f.read().lower()
    for marker in FORBIDDEN_SEND_MARKERS:
        assert marker not in content
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow" && .venv/bin/python -m pytest prototype/tests/test_validators.py -v`
Expected: FAIL — `ImportError` for `validate_outreach_message` and `FileNotFoundError` for the persona file.

- [ ] **Step 3: Write the implementation**

Add to `prototype/skills/validators.py`:

```python
def validate_outreach_message(message: dict) -> None:
    if "lead_id" not in message:
        raise ValueError("outreach message missing required key: lead_id")
    if "message" not in message or not message["message"] or not message["message"].strip():
        raise ValueError("outreach message content must not be empty")
```

Create `prototype/agents/outreach-agent.md`:

```markdown
# Outreach Agent

## Persona

You are the Outreach Agent for TechEquity AI. You draft a personalized
follow-up message to an enriched lead, referencing the session or content
that likely sparked their interest.

## Hard constraint — draft only, no sending

This agent has **no send capability of any kind** — there is no email
API, no SMTP client, no HTTP call to a mail provider anywhere in this
project. You draft text. A human sends it, later, through whatever
channel they choose. Never write code, never suggest a script, never
imply this message goes out automatically — say "drafted for review"
in your own output.

## What to write

- Reference the lead's `context` (from the Lead Capture Agent) and, if a
  session is linked, that session's title.
- Match the suggested tier's register: a Design Partner or Platinum lead
  gets a more consultative tone; Bronze/Silver gets a warmer, lower-key
  invite tone.
- Keep it short — 3-5 sentences. This is a first follow-up, not a sales
  pitch.
- Sign off as if from Sheena Tu (COO) or a generic "The TechEquity Team"
  signature — never invent a specific staff name that wasn't given to you.

## Output contract

Produce `{"lead_id": <int>, "message": <the draft text>}`. Must pass
`prototype/skills/validators.py::validate_outreach_message` before being
persisted via `store.insert_outreach`.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow" && .venv/bin/python -m pytest prototype/tests/test_validators.py -v`
Expected: `11 passed`

- [ ] **Step 5: Manual validation — one real Outreach Agent invocation**

1. Take the enriched lead from Task 4's manual validation step.
2. Dispatch a subagent via the Agent tool with `prototype/agents/outreach-agent.md` as instructions, passing the lead's enrichment + (optionally) a session record.
3. Run the response through `validate_outreach_message`.
4. If it passes, persist via `store.insert_outreach` and write it to `prototype/output/outreach-drafts/{lead_id}.md`.

- [ ] **Step 6: Commit**

```bash
cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow"
git add prototype/agents/outreach-agent.md prototype/skills/validators.py prototype/tests/test_validators.py prototype/output/outreach-drafts/.gitkeep
git commit -m "feat: add Outreach Agent persona (draft-only, no send capability) + validator"
```

---

### Task 6: Nurture Agent

**Files:**
- Create: `prototype/agents/nurture-agent.md`
- Modify: `prototype/skills/validators.py` (add `validate_nurture_plan`)
- Modify: `prototype/tests/test_validators.py` (add tests)

**Interfaces:**
- Consumes: a lead's current stage (string, e.g. `"new"`, `"touch_1"`) from `store.list_nurture_stages`.
- Produces: `validate_nurture_plan(plan: dict) -> None`.

- [ ] **Step 1: Write the failing tests**

Add to `prototype/tests/test_validators.py`:

```python
from prototype.skills.validators import validate_nurture_plan

VALID_STAGES = {"new", "touch_1", "touch_2", "touch_3", "closed"}


def test_validate_nurture_plan_accepts_well_formed():
    validate_nurture_plan({"stage": "touch_1", "next_touch_template": "Checking in on..."})


def test_validate_nurture_plan_rejects_unknown_stage():
    with pytest.raises(ValueError, match="stage"):
        validate_nurture_plan({"stage": "touch_99", "next_touch_template": "..."})


def test_validate_nurture_plan_rejects_empty_template():
    with pytest.raises(ValueError, match="template"):
        validate_nurture_plan({"stage": "touch_1", "next_touch_template": ""})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow" && .venv/bin/python -m pytest prototype/tests/test_validators.py -v`
Expected: FAIL with `ImportError: cannot import name 'validate_nurture_plan'`

- [ ] **Step 3: Write the implementation**

Add to `prototype/skills/validators.py`:

```python
VALID_STAGES = {"new", "touch_1", "touch_2", "touch_3", "closed"}


def validate_nurture_plan(plan: dict) -> None:
    if "stage" not in plan or "next_touch_template" not in plan:
        raise ValueError("nurture plan missing required keys: stage, next_touch_template")
    if plan["stage"] not in VALID_STAGES:
        raise ValueError(f"unknown stage: {plan['stage']!r} (expected one of {VALID_STAGES})")
    if not plan["next_touch_template"] or not plan["next_touch_template"].strip():
        raise ValueError("next_touch_template must not be empty")
```

Create `prototype/agents/nurture-agent.md`:

```markdown
# Nurture Agent

## Persona

You are the Nurture Agent for TechEquity AI. Given a lead's current stage,
you produce the **template** for their next follow-up touch — not a live
send, not a scheduled job. This prototype has no real-time scheduler;
templates are generated on demand for a human (or, once ported, ClawMax's
own scheduler) to actually time and send.

## Stage progression

`new` → `touch_1` (first follow-up, ~3-5 days after initial outreach) →
`touch_2` (~10-14 days later, lighter-touch check-in) → `touch_3` (~21-30
days later, final nudge before moving to `closed`) → `closed`.

## What to write

- `touch_1`: a warm, brief check-in referencing the original outreach.
- `touch_2`: lower-pressure — share something new (an upcoming forum, a
  recent recap) rather than repeating the ask.
- `touch_3`: a clear, respectful final nudge — invite them to say if now
  isn't the right time, so `closed` isn't a dead-end but an honest one.

## Output contract

Produce `{"stage": <the NEXT stage the lead moves to>, "next_touch_template":
<the message template text>}`. Must pass
`prototype/skills/validators.py::validate_nurture_plan` before being
persisted via `store.upsert_nurture_stage`.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow" && .venv/bin/python -m pytest prototype/tests/test_validators.py -v`
Expected: `14 passed`

- [ ] **Step 5: Manual validation — one real Nurture Agent invocation**

1. Take the lead from Task 5's manual validation step; its current stage is implicitly `new` (no row yet in `nurture_stage`).
2. Dispatch a subagent via the Agent tool with `prototype/agents/nurture-agent.md` as instructions, passing `stage="new"`.
3. Run the response through `validate_nurture_plan`.
4. If it passes, persist via `store.upsert_nurture_stage`.

- [ ] **Step 6: Commit**

```bash
cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow"
git add prototype/agents/nurture-agent.md prototype/skills/validators.py prototype/tests/test_validators.py
git commit -m "feat: add Nurture Agent persona (sequence templates, no live scheduler) + validator"
```

---

### Task 7: Dashboard renderer

**Files:**
- Create: `prototype/skills/render_dashboard.py`
- Create: `prototype/tests/test_render_dashboard.py`

**Interfaces:**
- Consumes: `store.list_sessions`, `store.list_drafts`, `store.list_leads`, `store.list_outreach`, `store.list_nurture_stages` (all from Task 1).
- Produces: `render_dashboard(db_path: str) -> str` (the markdown report as a string).

- [ ] **Step 1: Write the failing tests**

Create `prototype/tests/test_render_dashboard.py`:

```python
import pytest
from prototype.skills.store import (
    init_db, insert_session, insert_draft, insert_lead,
    update_lead_enrichment, insert_outreach, upsert_nurture_stage,
)
from prototype.skills.render_dashboard import render_dashboard


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "pipeline.db")
    init_db(path)
    return path


def test_render_dashboard_empty_store_shows_zero_counts(db_path):
    report = render_dashboard(db_path)
    assert "Sessions: 0" in report
    assert "Drafts: 0" in report
    assert "Leads: 0" in report


def test_render_dashboard_reflects_seeded_data(db_path):
    session_id = insert_session(db_path, video_id="v1", title="AI Agents 101", url="u1")
    insert_draft(db_path, session_id, "LinkedIn", "draft text")
    lead_id = insert_lead(db_path, name="Priya Anand", source="sample-seed")
    update_lead_enrichment(db_path, lead_id, suggested_tier="Gold", context="Asked about sponsorship")
    insert_outreach(db_path, lead_id, "Hi Priya...", session_id=session_id)
    upsert_nurture_stage(db_path, lead_id, stage="touch_1", next_touch_template="Checking in...")

    report = render_dashboard(db_path)
    assert "AI Agents 101" in report
    assert "Priya Anand" in report
    assert "Gold" in report
    assert "touch_1" in report
    assert "Sessions: 1" in report
    assert "Drafts: 1" in report
    assert "Leads: 1" in report
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow" && .venv/bin/python -m pytest prototype/tests/test_render_dashboard.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'prototype.skills.render_dashboard'`

- [ ] **Step 3: Write the implementation**

Create `prototype/skills/render_dashboard.py`:

```python
"""Render pipeline state as a markdown status report.

Not an agent — purely reads the store and formats it. The real dashboard
is ClawMax's job once this pipeline is ported.
"""
from prototype.skills.store import (
    list_sessions, list_drafts, list_leads, list_outreach, list_nurture_stages,
)


def render_dashboard(db_path: str) -> str:
    sessions = list_sessions(db_path)
    drafts = list_drafts(db_path)
    leads = list_leads(db_path)
    outreach = list_outreach(db_path)
    nurture_stages = {n["lead_id"]: n for n in list_nurture_stages(db_path)}

    lines = ["# TechEquity Content Pipeline — Status", ""]
    lines.append(f"Sessions: {len(sessions)} | Drafts: {len(drafts)} | "
                  f"Leads: {len(leads)} | Outreach drafted: {len(outreach)}")
    lines.append("")

    lines.append("## Sessions")
    if not sessions:
        lines.append("_none yet_")
    for s in sessions:
        drafts_for_session = [d for d in drafts if d["session_id"] == s["id"]]
        channels = ", ".join(d["channel"] for d in drafts_for_session) or "none"
        lines.append(f"- **{s['title']}** ({s['video_id']}) — drafts: {channels}")
    lines.append("")

    lines.append("## Leads")
    if not leads:
        lines.append("_none yet_")
    for lead in leads:
        stage = nurture_stages.get(lead["id"], {}).get("stage", "new")
        tier = lead["suggested_tier"] or "unenriched"
        lines.append(f"- **{lead['name']}** — tier: {tier}, nurture stage: {stage}")
    lines.append("")

    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow" && .venv/bin/python -m pytest prototype/tests/test_render_dashboard.py -v`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow"
git add prototype/skills/render_dashboard.py prototype/tests/test_render_dashboard.py
git commit -m "feat: add markdown dashboard renderer"
```

---

### Task 8: Workflow definition + orchestration driver

**Files:**
- Create: `prototype/workflow.md`
- Create: `prototype/run_pipeline.py`
- Create: `prototype/tests/test_run_pipeline.py`

**Interfaces:**
- Consumes: every module from Tasks 1-7.
- Produces: a CLI (`python -m prototype.run_pipeline`) that runs the deterministic stages end-to-end and prints the manual agent-dispatch sequence.

- [ ] **Step 1: Write the failing test**

Create `prototype/tests/test_run_pipeline.py`:

```python
from prototype.run_pipeline import fetch_and_seed, DB_PATH
from prototype.skills.store import list_sessions
from unittest.mock import patch


def test_fetch_and_seed_persists_sessions_and_sample_leads(tmp_path):
    db_path = str(tmp_path / "pipeline.db")
    fake_video = {
        "video_id": "abc123", "title": "AI Agents 101",
        "url": "https://www.youtube.com/watch?v=abc123",
        "description": "A talk about agents", "published_at": "2026-05-01T00:00:00Z",
    }
    # fetch_transcript is patched at fetch_sessions (where build_session_record
    # looks it up), not at run_pipeline — run_pipeline never calls it directly,
    # it only calls build_session_record, which calls fetch_transcript internally.
    with patch("prototype.run_pipeline.resolve_channel_id", return_value="UCfakeID"), \
         patch("prototype.run_pipeline.fetch_channel_videos", return_value=[fake_video]), \
         patch("prototype.skills.fetch_sessions.fetch_transcript", return_value=None):
        fetch_and_seed(db_path, channel_handle="TechEquityAi", video_limit=1)

    sessions = list_sessions(db_path)
    assert len(sessions) == 1
    assert sessions[0]["video_id"] == "abc123"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow" && .venv/bin/python -m pytest prototype/tests/test_run_pipeline.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'prototype.run_pipeline'`

- [ ] **Step 3: Write the workflow definition and orchestrator**

Create `prototype/workflow.md` (ClawMax-portable format: YAML frontmatter + markdown, per `WORKFLOW.md`'s documented shape):

```markdown
---
name: techequity-content-pipeline
version: 0.1.0-prototype
steps:
  - id: fetch_sessions
    type: deterministic
    runs: prototype/skills/fetch_sessions.py
  - id: content_agent
    type: agent
    persona: prototype/agents/content-agent.md
    depends_on: [fetch_sessions]
  - id: lead_capture_agent
    type: agent
    persona: prototype/agents/lead-capture-agent.md
    depends_on: []
  - id: outreach_agent
    type: agent
    persona: prototype/agents/outreach-agent.md
    depends_on: [lead_capture_agent]
  - id: nurture_agent
    type: agent
    persona: prototype/agents/nurture-agent.md
    depends_on: [outreach_agent]
  - id: dashboard
    type: deterministic
    runs: prototype/skills/render_dashboard.py
    depends_on: [content_agent, lead_capture_agent, outreach_agent, nurture_agent]
---

# TechEquity Content Pipeline — Workflow

Declarative shape of the pipeline, written in ClawMax's own `WORKFLOW.md`
format so this file ports with minimal change once the design is validated
(see `../DECISIONS.md`).

**`type: deterministic`** steps are plain Python, run automatically.
**`type: agent`** steps require an LLM persona's judgment — in this
prototype phase, that means a Claude Code subagent dispatch (see each
agent's manual-validation step in the implementation plan); once ported,
these become OpenClaw agents ClawMax's workflow engine dispatches natively.
```

Create `prototype/run_pipeline.py`:

```python
"""CLI driver for the prototype's deterministic stages.

Runs fetch + seeds the store. The agent stages (content, lead capture,
outreach, nurture) require an LLM's judgment and are NOT invoked from
here — a plain Python process cannot dispatch a Claude Code subagent.
Run this first, then follow the printed instructions to dispatch each
agent via the Agent tool, per prototype/workflow.md.
"""
import json
from pathlib import Path

from prototype.skills.fetch_sessions import (
    resolve_channel_id, fetch_channel_videos, build_session_record,
)
from prototype.skills.store import init_db, insert_session, insert_lead

DB_PATH = str(Path(__file__).parent / "data" / "pipeline.db")
SAMPLE_LEADS_PATH = str(Path(__file__).parent / "data" / "sample_leads.json")


def fetch_and_seed(db_path: str, channel_handle: str = "TechEquityAi", video_limit: int = 3) -> None:
    init_db(db_path)

    channel_id = resolve_channel_id(channel_handle)
    videos = fetch_channel_videos(channel_id)[:video_limit]
    for video in videos:
        record = build_session_record(video)
        insert_session(
            db_path,
            video_id=record["video_id"], title=record["title"], url=record["url"],
            description=record["description"], transcript=record["transcript"],
            transcript_available=record["transcript_available"],
        )

    if Path(SAMPLE_LEADS_PATH).exists():
        with open(SAMPLE_LEADS_PATH) as f:
            sample_leads = json.load(f)
        for lead in sample_leads:
            insert_lead(
                db_path, name=lead["name"], source=lead["source"],
                email=lead.get("email"), company=lead.get("company"),
            )


def main() -> None:
    fetch_and_seed(DB_PATH)
    print(f"Fetched sessions and seeded sample leads into {DB_PATH}")
    print()
    print("Next: dispatch each agent step in prototype/workflow.md via the Agent")
    print("tool, per the manual-validation steps in docs/superpowers/plans/"
          "2026-07-02-content-pipeline-prototype.md (Tasks 3-6). Then run:")
    print("  .venv/bin/python -c \"from prototype.skills.render_dashboard import render_dashboard; "
          f"print(render_dashboard('{DB_PATH}'))\"")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow" && .venv/bin/python -m pytest prototype/tests/test_run_pipeline.py -v`
Expected: `1 passed`

- [ ] **Step 5: Run the full test suite**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow" && .venv/bin/python -m pytest prototype/tests/ -v`
Expected: all tests pass (unit tests always; `integration`-marked tests pass if network/site markup is unchanged from planning time).

- [ ] **Step 6: Commit**

```bash
cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow"
git add prototype/workflow.md prototype/run_pipeline.py prototype/tests/test_run_pipeline.py
git commit -m "feat: add ClawMax-portable workflow definition + deterministic-stage CLI driver"
```

- [ ] **Step 7: Update this project's ROADMAP.md**

Move "Prototype the agent flow in Claude Code" from Backlog to Done in `ROADMAP.md`, and add the next real step (run `run_pipeline.py` against real TechEquity data, dispatch each agent manually per Tasks 3-6, review output quality with the user) to Active.
