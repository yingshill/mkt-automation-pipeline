# Content Agent Input Extension — Mateja's Captions Workflow Integration

**Status:** Approved, not yet implemented.
**Extends:** `2026-07-02-content-pipeline-prototype-design.md`'s Content Agent — this is an addendum to that spec, not a replacement. Everything in the original spec not mentioned here still applies.
**Context:** `../../../../claude/brand_os/brands/techequity/` holds the BD/pitch reasoning; specifically see `engagement/meeting-notes/2026-07-13-mateja-workflow-outline.md` (Mateja Ueligitone's written captions workflow, delivered 2026-07-13) and `DECISIONS.md` (ClawMax confirmed as the runtime; captions project confirmed as the near-term partnership deliverable). This spec does not duplicate that reasoning.

**🔴 Living document, not append-only.** This file is the single design reference for the captions-integration work specifically (distinct from the original 2026-07-02 prototype spec, which stays as its own historical record). As the integration's design evolves — new inputs, a resolved Doc-write path, additional channels once specced — **update this file in place** rather than creating a new dated spec for each change. Only fork a new spec file if the work outgrows "extending the Content Agent" into a genuinely separate effort.

---

## Goal

Extend the existing Content Agent so it can draft LinkedIn captions the way Mateja's team actually works today, without disturbing its original session-in/5-channel-out design — which stays intact for the separate "harvest the archive" use case (Pillar 3 of `strategy.md`).

## Scoping decisions (from brainstorming session, 2026-07-13)

- **New inputs, all optional alongside the existing session input:** `template_text` (the post template from "the Doc"), `luma_event_details` (event title/speakers/date/blurb), `past_reference_post` (optional, for style matching). The agent uses whichever combination of session content + these three is provided.
- **Output scope stays 5 channels in principle; only LinkedIn is built now.** This is a sequencing gap (IG/FB/YouTube-shorts/Sidekick don't have a template/tone spec yet), not a permanent narrowing. The persona file states this explicitly so it reads as "pending," not "decided out of scope."
- **No live data-source integration this pass.** Luma event details and template text are **plain manual input** — no Luma API, no live Docs-read integration. Same reasoning as the dead YouTube RSS situation in the original spec: don't build against an integration that isn't confirmed to exist.
- **Doc hand-off: local file + manual paste, not a live write.** Investigated direct Google Docs API write during brainstorming — the available Google Drive tooling (`create_file`, `read_file_content`, `get_file_metadata`, `get_file_permissions`) has no capability to write into an _existing_ Doc; `create_file` only makes new files. Direct write is a real, documented follow-up once that access exists (see Explicit non-goals), not something this pass pretends to solve.

## Architecture

No new components. This modifies:

```
prototype/
├── agents/
│   └── content-agent.md          → persona gains an extended "Inputs" section
├── skills/
│   └── validators.py             → validate_draft unchanged; may add a light
│                                     input-shape check if a combined-input
│                                     helper function is introduced (see below)
└── output/drafts/                → unchanged pattern, one .md file per draft
```

No changes to `render_dashboard.py` or the other three agents (Lead Capture, Outreach, Nurture) — none of them are affected by this change.

**⚠️ Correction, 2026-07-13 (found during implementation, not anticipated at design time):** this spec originally said "no changes to `store.py`" — that was wrong. `store.py`'s `drafts` table declares `session_id INTEGER NOT NULL REFERENCES sessions(id)`, which makes it impossible to persist exactly the case this extension exists for — a template+Luma draft with no session. Confirmed by actually attempting `store.insert_draft(db_path, None, "LinkedIn", content)` during Task 2's manual validation: raises `sqlite3.IntegrityError`. `store.py` needs a small, scoped fix: drop the `NOT NULL` constraint on `drafts.session_id` (a draft can legitimately exist without a session). See the implementation plan's Task 3.

## Input contract (extended)

The Content Agent's persona currently states: "You turn one recorded session ... into platform-specific draft posts." This becomes: "You turn a **combination of inputs** — a recorded session (if available), a post template, Luma event details, and optionally a past reference post — into platform-specific draft posts. Not all inputs are required for every draft; use whichever are provided."

Concretely, the dispatch input becomes a dict of optional fields rather than a single required session dict:

```
{
  "session": <existing session dict, or None>,
  "template_text": <str, the post template from "the Doc">,
  "luma_event_details": {
    "event_title": <str>, "date": <str>, "time": <str>,
    "location": <str>, "speakers": <list[str]>, "blurb": <str>
  } or None,
  "past_reference_post": <str, optional>
}
```

At least one of `session` or (`template_text` + `luma_event_details`) must be present — the persona should say so explicitly and decline to draft (rather than fabricate) if neither is given.

**When both a session and template/Luma details are provided** (the post-event recap case): the template supplies structure and the past-reference-post supplies tone; the session supplies the actual substance (what the talk covered) — the agent doesn't have to choose one input source over another, it blends them the way Mateja does manually today.

## Output contract

Unchanged shape: `{"channel": <str>, "content": <str>}`, still validated by the existing `validate_draft`. The persona explicitly lists which channels are buildable now (LinkedIn) versus pending a template/tone spec (Instagram, Facebook, YouTube-shorts, Sidekick), so a run that only produces a LinkedIn draft is expected behavior, not a silent gap.

## Data flow

```
[manual input: template_text + luma_event_details (+ optional past_reference_post) (+ optional session)]
        │
        ▼
  Content Agent (extended persona)
        │
        ▼
  validate_draft  →  store.insert_draft  →  output/drafts/{id}-LinkedIn.md
        │
        ▼
  (human) pastes into "the Doc" review tab
        │
        ▼
  existing review loop, unchanged: Sheena/Ave review+comment,
  Mateja/Satvika edit, format in TypeGrow, manual schedule/post
```

## Error handling

- If neither a session nor (template + Luma details) is provided, the agent must say so explicitly rather than drafting from nothing — same "don't fabricate" discipline as the original spec's transcript-unavailable case.
- If `template_text` is provided but doesn't look like a real template (e.g., empty or clearly not template-shaped), the agent flags this rather than silently drafting free-form and calling it "from the template."
- Everything from the original spec's error handling (content generation retry, no partial store writes) still applies unchanged.

## Testing

- No new test file. Extend `test_validators.py` if a combined-input helper function is introduced; `validate_draft` itself doesn't change shape, since the output contract is unchanged.
- Manual validation step (mirrors the original Task 3 pattern): dispatch the Content Agent with a real combined input (a real template + real Luma event details for an actual upcoming TechEquity event, no session needed to prove this path works), inspect the LinkedIn draft by eye against Mateja's actual voice/format expectations, run it through `validate_draft`.

## Explicit non-goals for this pass

- No live Luma API integration.
- No live Google Docs read or write integration — this is the biggest deferred piece; revisit once either (a) a Google Docs API surface capable of writing into an existing doc becomes available, or (b) TechEquity is comfortable granting broader Docs access for this to become fully automated.
- No Instagram/Facebook/YouTube-shorts/Sidekick draft generation yet — waiting on template/tone specs for each.
- No change to Lead Capture, Outreach, or Nurture components.

**⚠️ Correction, 2026-07-13 (found during the final whole-branch review):** this spec originally listed "Dashboard" among the untouched components — wrong. Once `drafts.session_id` became nullable (Task 3), `render_dashboard.py` silently dropped session-less drafts from its body while still counting them in the header total, since it only ever grouped drafts under a session. Fixed in Task 4 — an "Unattached Drafts" section now surfaces them.
