# TechEquity Content Pipeline — Claude Code Prototype Design

**Status:** Approved, not yet implemented.
**Precedes:** `WORKSPACES/techequity/` (the ClawMax runtime) — this prototype is built and validated in Claude Code first, then ported to OpenClaw `AGENTS.md`/`SOUL.md` + a ClawMax `WORKFLOW.md`. See `../../../DECISIONS.md` for why.
**Context:** `../../../../claude/brand_os/brands/techequity/` holds the BD/pitch reasoning this build serves (design-partner pitch to ClawMax). This spec does not duplicate that reasoning.

---

## Goal

Prototype, in Claude Code, the full 5-part pipeline described in `clawmax-gtm-pilot.md` (content engine, lead capture, outreach agent, nurture sequence, dashboard) — adapted to use TechEquity's **session library** as the content source (Pillar 3 of `strategy.md`) rather than ClawMax product releases, and targeting TechEquity's actual active channels. Validate the pipeline's shape and each agent's persona/judgment before porting to OpenClaw + ClawMax.

## Scoping decisions (from brainstorming session, 2026-07-02)

- **Scope:** full pilot — all 5 parts, not a narrower slice. User chose this explicitly over a content-only MVP.
- **Content source:** TechEquity's recorded session library (YouTube `@TechEquityAi` playlists + the site's searchable speaker DB) — not ClawMax product content. Dogfooding is about the *infrastructure* (running on ClawMax), not the content topic.
- **Channels:** all active channels per `research-brief.md` §B — LinkedIn, Instagram, Facebook, YouTube (shorts script), Sidekick community.
- **Input data:** pull real public data (YouTube playlist metadata/transcripts, public speaker-DB entries) — no auth/API access needed since it's public. No mock data.
- **Lead capture:** no live inbound source is connected (Vigo API access not yet requested — see `brand_os/brands/techequity/ROADMAP.md`). The Lead Capture Agent's schema/enrichment logic is exercised against a handful of sample lead records. This is a known, explicit prototype limitation — not something to paper over.
- **Lead storage:** local SQLite (stdlib `sqlite3`, no extra dependency) — structured enough for lead/outreach/nurture relations, easy to inspect, swappable for Vigo later.
- **Outreach:** draft-only. No send capability exists in the code at all — this is a structural guarantee (no email/API send function implemented), not a disabled flag, so there's no way to accidentally message a real person during prototyping.
- **Nurture:** generates sequence *templates* (what touch 2, 3, 4 would say) rather than a real scheduler running against wall-clock time. Scheduling is a production concern.
- **Dashboard:** a generated markdown status report, not a web UI. The real dashboard is ClawMax's job once ported.
- **Voice source:** no `DNA.md` exists for TechEquity in brand_os, and this project doesn't route through brand_os's Notion pipeline — so a lightweight voice brief (derived from `research-brief.md` + `strategy.md`'s notes on Sheena's design-agency background) is written directly into the Content Agent's persona file, rather than authoring a formal brand_os DNA.md this repo won't consume.

## Architecture

**Approach:** true multi-agent simulation, not a single deterministic script chain. Each of the 5 pilot deliverables is a distinct Claude Code subagent with its own persona and judgment calls, each calling shared deterministic tool scripts for mechanical work. This directly prototypes OpenClaw's split (`SOUL.md` = persona, skills = tools) so the persona files and tool scripts port with minimal rework.

```
prototype/
├── agents/                      → ports to OpenClaw AGENTS.md/SOUL.md later
│   ├── content-agent.md         (persona + voice brief + channel-format rules)
│   ├── lead-capture-agent.md    (persona + enrichment logic)
│   ├── outreach-agent.md        (persona + draft-only constraint stated explicitly)
│   └── nurture-agent.md         (persona + sequence-template logic)
├── skills/                      → ports to OpenClaw skills later
│   ├── fetch_sessions.py        (YouTube playlist + speaker-DB pull, public data)
│   ├── store.py                 (SQLite schema + CRUD: sessions, drafts, leads, outreach, nurture_stage)
│   └── render_dashboard.py      (reads store → markdown report)
├── data/
│   └── pipeline.db              (SQLite; sample lead records seeded for Lead Capture Agent testing)
├── workflow.md                  → ports to ClawMax WORKFLOW.md later (declares the agent sequence/dependencies)
└── output/
    ├── drafts/                  (generated per-channel post drafts)
    ├── outreach-drafts/
    └── dashboard.md             (latest generated report)
```

## Components

1. **Content Agent** — input: one session (YouTube video + speaker-DB entry). Output: draft posts for LinkedIn, Instagram, Facebook, a YouTube-shorts script, and a Sidekick post — each following that channel's format conventions and the voice brief. Writes drafts to `store.py` and `output/drafts/`.
2. **Lead Capture Agent** — input: a sample or (eventually) real interest-signal record. Output: enriched lead record (company/context, suggested interest tier, contact) written to the store. Exercised against seeded sample records for now.
3. **Outreach Agent** — input: an enriched lead + the session/content that likely sparked interest. Output: a draft personalized follow-up message, written to `output/outreach-drafts/`. No send path exists in the code.
4. **Nurture Agent** — input: a lead's current stage. Output: the next 2-3 touch message templates for that stage, written to the store. No real scheduler.
5. **Dashboard (script, not an agent)** — reads the full store, renders `output/dashboard.md`: sessions processed, drafts generated per channel, leads captured, outreach drafted, nurture stage per lead.

## Data flow

```
YouTube playlist + speaker DB (public, no auth)
        │
        ▼
  Content Agent  ──► store.sessions, store.drafts ──► output/drafts/*.md
        │
        ▼ (sample lead records seeded directly into store.leads)
  Lead Capture Agent ──► store.leads (enriched)
        │
        ▼
  Outreach Agent ──► output/outreach-drafts/*.md, store.outreach
        │
        ▼
  Nurture Agent ──► store.nurture_stage
        │
        ▼
  render_dashboard.py ──► output/dashboard.md
```

## Error handling

- YouTube fetch: if no transcript is available for a video, fall back to title + description; log the fallback, never fail the run silently.
- Content generation: retry on failure rather than dropping a channel's draft; a failed channel is reported in the dashboard as "not generated," not silently omitted.
- Store writes: standard SQLite transaction semantics; no partial writes across a single agent's output.
- Outreach: structurally cannot fail into a real send, because no send capability exists in the code.

## Testing

- `store.py`: unit tests on CRUD operations (insert/update/query sessions, leads, drafts, nurture stage) — matches the pytest convention already used in `brand_os/tests/`.
- `fetch_sessions.py`: verified against at least one real YouTube playlist entry and one real speaker-DB entry, confirming the fallback path (no transcript) also works.
- Content quality: human-reviewed, same as brand_os's existing asset-review flow — not automated, since voice/quality judgment doesn't reduce to an assertion.
- `render_dashboard.py`: verified against the seeded sample store, confirming all five categories (sessions, drafts, leads, outreach, nurture) render correctly including the zero/empty case.

## Explicit non-goals for this prototype

- No live Vigo integration (access not yet requested).
- No real outreach sending.
- No real-time nurture scheduling.
- No web dashboard UI.
- No OpenClaw/ClawMax deployment yet — this lives entirely in Claude Code / this repo until validated.
