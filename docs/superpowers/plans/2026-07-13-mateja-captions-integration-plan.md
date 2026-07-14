# Content Agent Input Extension Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing Content Agent's input contract to accept a post template, Luma event details, and an optional past-reference post alongside its existing session input, so it can draft LinkedIn captions the way Mateja Ueligitone's team actually works — without disturbing its original session-in/5-channel-out design.

**Architecture:** No new components. A schema validator (`validate_content_agent_input`) is added to the existing `prototype/skills/validators.py`, following the same pattern as the file's other four validators. The Content Agent's persona file (`prototype/agents/content-agent.md`) is rewritten to document the extended input shape, mark which channels are buildable now versus pending a template/tone spec, and state the new error-handling rules. A structural test (mirroring the existing outreach-agent content check) guards that the persona file actually documents the new input fields.

**Tech Stack:** Python 3, `pytest` — same as the rest of the prototype. No new dependencies.

## Global Constraints

- Validators check *shape*, never *quality* — content quality is human-reviewed, per the original design spec's global constraint. This applies to `validate_content_agent_input` exactly as it does to the existing four validators.
- No live Luma API integration, no live Google Docs read/write integration this pass — `template_text` and `luma_event_details` are plain manual input, per the design spec's explicit non-goals.
- No change to `render_dashboard.py` or the Lead Capture / Outreach / Nurture agents. `store.py` gets one scoped fix (Task 3 — `drafts.session_id` made nullable), found necessary during Task 2's implementation; not the broader rewrite this constraint originally ruled out.
- Output scope is LinkedIn only for now — Instagram/Facebook/YouTube-shorts/Sidekick are marked "pending template/tone spec" in the persona, not silently dropped.
- Design spec for this work: `docs/superpowers/specs/2026-07-13-mateja-captions-integration-design.md` — a living document; if this plan's implementation surfaces a design change, update that spec file in place rather than letting the plan and spec drift apart.

---

### Task 1: Add `validate_content_agent_input`

**Files:**
- Modify: `prototype/skills/validators.py`
- Modify: `prototype/tests/test_validators.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `validate_content_agent_input(input_dict: dict) -> None` (raises `ValueError` if neither `session` nor both `template_text` and `luma_event_details` are present). Task 2's manual validation step uses this function.

- [ ] **Step 1: Write the failing tests**

Add to `prototype/tests/test_validators.py` (after the existing imports on line 2, add the new import; the four new test functions can go at the end of the file):

Change line 2 from:
```python
from prototype.skills.validators import validate_draft, validate_lead_enrichment, validate_outreach_message, validate_nurture_plan
```
to:
```python
from prototype.skills.validators import validate_draft, validate_lead_enrichment, validate_outreach_message, validate_nurture_plan, validate_content_agent_input
```

Append to the end of the file:
```python
def test_validate_content_agent_input_accepts_session_only():
    validate_content_agent_input({
        "session": {"video_id": "abc123", "title": "AI Agents 101"},
        "template_text": None,
        "luma_event_details": None,
        "past_reference_post": None,
    })


def test_validate_content_agent_input_accepts_template_and_luma_only():
    validate_content_agent_input({
        "session": None,
        "template_text": "Join us at [Event Name] on [Date]...",
        "luma_event_details": {"event_title": "June Forum", "date": "2026-06-30"},
        "past_reference_post": None,
    })


def test_validate_content_agent_input_accepts_all_four_fields():
    validate_content_agent_input({
        "session": {"video_id": "abc123", "title": "AI Agents 101"},
        "template_text": "Join us at [Event Name] on [Date]...",
        "luma_event_details": {"event_title": "June Forum", "date": "2026-06-30"},
        "past_reference_post": "Last month's recap post text...",
    })


def test_validate_content_agent_input_rejects_template_without_luma():
    with pytest.raises(ValueError, match="session"):
        validate_content_agent_input({
            "session": None,
            "template_text": "Join us at [Event Name] on [Date]...",
            "luma_event_details": None,
            "past_reference_post": None,
        })


def test_validate_content_agent_input_rejects_luma_without_template():
    with pytest.raises(ValueError, match="session"):
        validate_content_agent_input({
            "session": None,
            "template_text": None,
            "luma_event_details": {"event_title": "June Forum", "date": "2026-06-30"},
            "past_reference_post": None,
        })


def test_validate_content_agent_input_rejects_all_none():
    with pytest.raises(ValueError, match="session"):
        validate_content_agent_input({
            "session": None,
            "template_text": None,
            "luma_event_details": None,
            "past_reference_post": None,
        })
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow/.claude/worktrees/content-pipeline-prototype" && .venv/bin/python -m pytest prototype/tests/test_validators.py -v`
Expected: FAIL with `ImportError: cannot import name 'validate_content_agent_input'`

- [ ] **Step 3: Write the implementation**

Append to `prototype/skills/validators.py`:
```python
def validate_content_agent_input(input_dict: dict) -> None:
    session = input_dict.get("session")
    template_text = input_dict.get("template_text")
    luma_event_details = input_dict.get("luma_event_details")
    if session is None and not (template_text and luma_event_details):
        raise ValueError(
            "content agent input must include either a session, or both "
            "template_text and luma_event_details"
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow/.claude/worktrees/content-pipeline-prototype" && .venv/bin/python -m pytest prototype/tests/test_validators.py -v`
Expected: `20 passed` (14 existing + 6 new)

- [ ] **Step 5: Commit**

```bash
cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow/.claude/worktrees/content-pipeline-prototype"
git add prototype/skills/validators.py prototype/tests/test_validators.py
git commit -m "feat: add validate_content_agent_input for extended Content Agent inputs"
```

---

### Task 2: Update the Content Agent persona for the extended input contract

**Files:**
- Modify: `prototype/agents/content-agent.md` (full rewrite — the persona changes throughout, not just one section)
- Modify: `prototype/tests/test_validators.py`

**Interfaces:**
- Consumes: `validate_content_agent_input` from Task 1 (used in this task's manual validation step, not by any automated test — the persona file itself isn't executable code).
- Produces: nothing other tasks depend on — this is the last task in this plan.

- [ ] **Step 1: Write the failing structural test**

Append to `prototype/tests/test_validators.py`:
```python
def test_content_agent_file_documents_extended_inputs():
    with open("prototype/agents/content-agent.md") as f:
        content = f.read()
    for marker in ("template_text", "luma_event_details", "past_reference_post"):
        assert marker in content
    assert "buildable now" in content
    assert "pending template/tone spec" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow/.claude/worktrees/content-pipeline-prototype" && .venv/bin/python -m pytest prototype/tests/test_validators.py::test_content_agent_file_documents_extended_inputs -v`
Expected: FAIL — `assert 'template_text' in content` fails (the current persona file has none of these markers)

- [ ] **Step 3: Rewrite the persona file**

Replace the entire contents of `prototype/agents/content-agent.md` with:

```markdown
# Content Agent

## Persona

You are the Content Agent for TechEquity AI's content pipeline. You turn a
combination of inputs — a recorded session (if available), a post template,
Luma event details, and optionally a past reference post — into
platform-specific draft posts. Not all inputs are required for every draft;
use whichever combination is provided.

## Inputs

You receive a dict shaped like:

```
{
  "session": <session dict from store.get_session_by_video_id, or None>,
  "template_text": <str, the post template pulled from "the Doc", or None>,
  "luma_event_details": {
    "event_title": <str>, "date": <str>, "time": <str>,
    "location": <str>, "speakers": <list[str]>, "blurb": <str>
  } or None,
  "past_reference_post": <str, optional, or None>
}
```

This must pass `prototype/skills/validators.py::validate_content_agent_input`
before you draft anything.

**At least one of `session` or (`template_text` AND `luma_event_details`)
must be present.** If neither condition is met, do not draft anything —
say explicitly that you don't have enough input to draft from, and name
which piece is missing.

**When both a session and template/Luma details are provided** (the
post-event recap case): the template supplies structure, the past
reference post (if given) supplies tone, and the session supplies the
actual substance — what the talk covered. Blend all three the way Mateja
does manually today; don't pick one source and ignore the others.

**If `template_text` is provided but doesn't look like a real template**
(empty, or clearly not template-shaped — e.g. a single word or an
unrelated sentence), say so explicitly rather than silently drafting
free-form content and calling it "from the template."

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
- Every post must be traceable to a real session or the given event
  details — no fabricated quotes, no invented statistics. If the
  transcript is unavailable, work only from the title/description and
  say less rather than embellish.

## Channel format rules

- **LinkedIn — buildable now:** 150-300 words, professional tone, one clear
  insight from the talk or event, ends with a question or a link to the
  recording/registration. This is the only channel currently in scope.
- **Instagram — pending template/tone spec, do not draft yet.** 1-2 short
  sentences + 3-5 hashtags, caption-first (assume a still frame or slide as
  the image, not generated here) — placeholder format, not yet confirmed
  against a real template.
- **Facebook — pending template/tone spec, do not draft yet.** Similar to
  LinkedIn but shorter (80-150 words), more community-toned ("come learn
  with us" register, not corporate) — placeholder format, not yet confirmed.
- **YouTube (shorts script) — pending template/tone spec, do not draft
  yet.** A 30-45 second spoken script, 3-5 short lines, hook in the first
  line — placeholder format, not yet confirmed.
- **Sidekick — pending template/tone spec, do not draft yet.** Plain-text
  community post, 2-4 sentences, casual register — **[VERIFY]** exact
  format/length conventions once Sidekick's actual posting mechanics are
  confirmed; treat this as a reasonable default, not a confirmed spec.

**Only draft the channels marked "buildable now."** If asked to draft a
"pending" channel, say explicitly that its template/tone spec isn't ready
yet rather than guessing at a format.

## Output contract

Produce one draft per channel as a dict: `{"channel": <one of LinkedIn,
Instagram, Facebook, YouTube, Sidekick>, "content": <the draft text>}`.
Every draft must pass `prototype/skills/validators.py::validate_draft`
before being persisted via `store.insert_draft`. For this pass, that means
one dict with `"channel": "LinkedIn"`.

## Constraints

- Do not invent session content, event details, or template content that
  wasn't given to you.
- If `transcript_available` is `False` for a given session, say so
  explicitly in your response before drafting, and draft only from the
  title/description — shorter, more conservative drafts are correct here.
- If neither `session` nor (`template_text` + `luma_event_details`) is
  present, do not draft — say explicitly what's missing.
- If `template_text` doesn't look like a real template, flag it rather
  than drafting free-form and calling it template-based.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow/.claude/worktrees/content-pipeline-prototype" && .venv/bin/python -m pytest prototype/tests/test_validators.py -v`
Expected: `21 passed`

- [ ] **Step 5: Run the full test suite**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow/.claude/worktrees/content-pipeline-prototype" && .venv/bin/python -m pytest prototype/tests/ -v`
Expected: all non-`integration`-marked tests pass; `integration`-marked tests pass if network/site markup is unchanged from when they were last run.

- [ ] **Step 6: Commit**

```bash
cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow/.claude/worktrees/content-pipeline-prototype"
git add prototype/agents/content-agent.md prototype/tests/test_validators.py
git commit -m "feat: extend Content Agent persona for template+Luma+past-post inputs"
```

- [ ] **Step 7: Manual validation — one real Content Agent invocation with the extended input**

This cannot be a pytest assertion — content quality is human-reviewed, per the project's global constraint. This validates the persona against a real template+Luma-details input (the path Mateja actually needs), with no session required:

1. Get a real, current post template from TechEquity's "the Doc" (ask the user for one, or use a real example from `brand_os/brands/techequity/inbox/processed/2026 Social Media Template.docx`'s event-announcement copy as a stand-in if a live template isn't on hand yet).
2. Get real Luma event details for an actual upcoming TechEquity forum (from `brand_os/brands/techequity/engagement/research-brief.md` §K's event calendar, or ask the user).
3. Build the input dict: `{"session": None, "template_text": <the template>, "luma_event_details": <the event details>, "past_reference_post": None}`.
4. Run it through `validate_content_agent_input` — confirm it passes.
5. Dispatch a subagent via the Agent tool with the content of `prototype/agents/content-agent.md` as its instructions, plus that input dict.
6. Run the response through `validate_draft`.
7. Confirm by eye: the draft actually reflects the template's structure and the real event details, correct LinkedIn register per the format rules, no fabricated claims.
8. If it passes, persist via `store.insert_draft` and write it to `prototype/output/drafts/` as a `.md` file (filename: `mateja-workflow-{event_title_slug}-LinkedIn.md`).

- [ ] **Step 8: Update this project's ROADMAP.md**

Move the "Design spec — living document" bullet in `ROADMAP.md`'s Active section from "Implementation plan not yet written" to noting the plan is implemented, and move this item to Done once Step 7's manual validation passes.

---

### Task 3: Make `drafts.session_id` nullable

**Found during Task 2's manual validation, not anticipated at design time:** `store.py`'s `drafts` table declares `session_id INTEGER NOT NULL REFERENCES sessions(id)` (line 28), which makes it impossible to persist a template+Luma draft with no session — exactly the case this whole extension exists for. Confirmed by actually running `store.insert_draft(db_path, None, "LinkedIn", content)`: raises `sqlite3.IntegrityError: NOT NULL constraint failed: drafts.session_id`. The `outreach` table already allows an optional `session_id` (line 48: `session_id INTEGER REFERENCES sessions(id)`, no `NOT NULL`) — `drafts` should follow the same pattern.

**Files:**
- Modify: `prototype/skills/store.py`
- Modify: `prototype/tests/test_store.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: no new function — `insert_draft`'s existing signature (`insert_draft(db_path, session_id, channel, content) -> int`) is unchanged; only the schema constraint changes, so callers can now legitimately pass `session_id=None`.

- [ ] **Step 1: Write the failing test**

Add to `prototype/tests/test_store.py` (after the existing `test_insert_and_list_drafts` test):
```python
def test_insert_draft_without_session_id(db_path):
    draft_id = insert_draft(db_path, None, "LinkedIn", "A template+Luma draft with no session")
    drafts = list_drafts(db_path)
    assert len(drafts) == 1
    assert drafts[0]["id"] == draft_id
    assert drafts[0]["session_id"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow/.claude/worktrees/content-pipeline-prototype" && .venv/bin/python -m pytest prototype/tests/test_store.py::test_insert_draft_without_session_id -v`
Expected: FAIL with `sqlite3.IntegrityError: NOT NULL constraint failed: drafts.session_id`

- [ ] **Step 3: Fix the schema**

In `prototype/skills/store.py`, change (line 28):
```python
    session_id INTEGER NOT NULL REFERENCES sessions(id),
```
to:
```python
    session_id INTEGER REFERENCES sessions(id),
```
(this is inside the `drafts` table definition in the `SCHEMA` string — the `sessions`, `leads`, `outreach`, and `nurture_stage` table definitions are untouched).

**This test fixture uses a fresh `tmp_path` database per the existing `db_path` fixture in `test_store.py`, so no migration of `prototype/data/pipeline.db` is needed for the test itself.** But the real local dev database at `prototype/data/pipeline.db` was created under the old schema (by earlier tasks' manual-validation runs) and `CREATE TABLE IF NOT EXISTS` will NOT retroactively drop a constraint on an already-existing table. Since this file is git-ignored, disposable prototype data (see `.gitignore`, added in Task 1 of the original plan), delete and let it regenerate:
```bash
cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow/.claude/worktrees/content-pipeline-prototype"
rm -f prototype/data/pipeline.db
```
State clearly in your report that you did this and why — it's a deliberate, documented action on disposable local data, not something to do silently.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow/.claude/worktrees/content-pipeline-prototype" && .venv/bin/python -m pytest prototype/tests/test_store.py -v`
Expected: `10 passed` (9 existing + 1 new)

- [ ] **Step 5: Verify the existing session-linked path still works (regression check)**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow/.claude/worktrees/content-pipeline-prototype" && .venv/bin/python -m pytest prototype/tests/test_store.py::test_insert_and_list_drafts -v`
Expected: `1 passed` — confirms the schema change didn't break the pre-existing session-linked draft case (that test creates a real session and inserts drafts against it).

- [ ] **Step 6: Confirm the originally-blocked manual-validation draft can now actually persist to the store**

This isn't a new pytest assertion — it's closing the loop on the exact gap Task 2 found. Run:
```bash
cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow/.claude/worktrees/content-pipeline-prototype" && .venv/bin/python -c "
from prototype.skills.store import init_db, insert_draft, list_drafts
init_db('prototype/data/pipeline.db')
draft_id = insert_draft('prototype/data/pipeline.db', None, 'LinkedIn', open('prototype/output/drafts/mateja-workflow-enterprise-ai-at-scale-talks-ai-agent-workshops-LinkedIn.md').read())
print('inserted draft', draft_id, '- session_id:', list_drafts('prototype/data/pipeline.db')[-1]['session_id'])
"
```
Expected output: `inserted draft <N> - session_id: None` — confirms Task 2's manual-validation draft (already on disk as a file) can now also be persisted to the database, closing the gap flagged in Task 2's report.

- [ ] **Step 7: Run the full test suite**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow/.claude/worktrees/content-pipeline-prototype" && .venv/bin/python -m pytest prototype/tests --ignore=prototype/tests/test_run_pipeline.py -v`
Expected: all pass except possibly the pre-existing, unrelated `@pytest.mark.integration` YouTube test (network-dependent, documented in Task 2's report and DECISIONS.md — not something this task touches or is responsible for).

- [ ] **Step 8: Commit**

```bash
cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow/.claude/worktrees/content-pipeline-prototype"
git add prototype/skills/store.py prototype/tests/test_store.py
git commit -m "fix: allow drafts.session_id to be nullable for session-less content"
```

---

### Task 4: Surface session-less drafts in the dashboard

**Found during the final whole-branch review, not anticipated at design time:** `render_dashboard.py` counts every draft in its header total (`Drafts: {len(drafts)}`), but the body only ever displays drafts grouped under a session (`[d for d in drafts if d["session_id"] == s["id"]]`). A draft with `session_id = None` — the exact new case Task 3 enables — matches no session, so it's counted but never shown. The design spec listed "no change to Dashboard" as a non-goal; that assumption predates Task 3's nullable-session_id change and is now stale.

**Files:**
- Modify: `prototype/skills/render_dashboard.py`
- Modify: `prototype/tests/test_render_dashboard.py`

**Interfaces:**
- Consumes: `store.list_drafts` (unchanged, already returns `session_id: None` rows since Task 3).
- Produces: no new function — `render_dashboard`'s existing signature is unchanged; only its output (an added section) changes.

- [ ] **Step 1: Write the failing test**

Add to `prototype/tests/test_render_dashboard.py`:
```python
def test_render_dashboard_shows_unattached_drafts(db_path):
    insert_draft(db_path, None, "LinkedIn", "A template+Luma draft with no session")

    report = render_dashboard(db_path)
    assert "Drafts: 1" in report
    assert "## Unattached Drafts" in report
    assert "LinkedIn" in report.split("## Unattached Drafts")[1]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow/.claude/worktrees/content-pipeline-prototype" && .venv/bin/python -m pytest prototype/tests/test_render_dashboard.py::test_render_dashboard_shows_unattached_drafts -v`
Expected: FAIL — `assert "## Unattached Drafts" in report` fails (the section doesn't exist yet)

- [ ] **Step 3: Add the section**

In `prototype/skills/render_dashboard.py`, after the `## Sessions` loop (after the line `lines.append("")` that follows it, i.e. after what is currently line 30) and before `lines.append("## Leads")`, insert:
```python
    unattached_drafts = [d for d in drafts if d["session_id"] is None]
    if unattached_drafts:
        lines.append("## Unattached Drafts")
        lines.append("_Drafts with no linked session — e.g. template+Luma-only captions._")
        for d in unattached_drafts:
            lines.append(f"- **{d['channel']}** (draft #{d['id']}) — {d['content'][:80]}{'...' if len(d['content']) > 80 else ''}")
        lines.append("")
```
This only renders the section when at least one unattached draft exists, so the empty-store test (`test_render_dashboard_empty_store_shows_zero_counts`) and the existing seeded-data test (`test_render_dashboard_reflects_seeded_data`, which has zero unattached drafts) are unaffected.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow/.claude/worktrees/content-pipeline-prototype" && .venv/bin/python -m pytest prototype/tests/test_render_dashboard.py -v`
Expected: `3 passed` (2 existing + 1 new)

- [ ] **Step 5: Run the full test suite**

Run: `cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow/.claude/worktrees/content-pipeline-prototype" && .venv/bin/python -m pytest prototype/tests --ignore=prototype/tests/test_run_pipeline.py -v`
Expected: all pass except the pre-existing, unrelated `@pytest.mark.integration` YouTube test (network-dependent, already documented).

- [ ] **Step 6: Commit**

```bash
cd "/Users/mac/Desktop/Projects & Learning/techequity-marketing-workflow/.claude/worktrees/content-pipeline-prototype"
git add prototype/skills/render_dashboard.py prototype/tests/test_render_dashboard.py
git commit -m "fix: surface unattached (session-less) drafts in the dashboard"
```
