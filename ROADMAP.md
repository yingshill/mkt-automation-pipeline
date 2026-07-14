# TechEquity Marketing Workflow — Roadmap

What's being built and when. Hub: [README](README.md) · why: [DECISIONS](DECISIONS.md).

---

## Done

- Repo scaffolded (2026-07-01).
- `WORKSPACES/techequity/` created in the shared ClawMax install and registered in the dashboard's workspace registry (2026-07-02) — empty skeleton, no agents/workflows authored yet. **Note:** this is a *local dev clone* of open-source ClawMax (`openclaw_GTM/clawmax/`, MIT), separate from TechEquity's own formal design-partner access — see Open questions, don't conflate the two.
- **⚠️ Corrected, 2026-07-13 — this section was stale relative to the actual worktree.** Content pipeline prototype (`.claude/worktrees/content-pipeline-prototype`, branch `worktree-content-pipeline-prototype`), per git log:
  - Task 1 — shared SQLite store (`skills/store.py`). Done.
  - Task 2 — YouTube + speaker-page fetch layer (`skills/fetch_sessions.py`). Done; real session-data sourcing deferred, see DECISIONS.md.
  - Task 3 — Content Agent persona + draft validator. **Done — generates real draft output** for LinkedIn, Instagram, Facebook, a YouTube-shorts script, and Sidekick, from one placeholder session (`prototype/output/drafts/local-placeholder-001-*.md`).
  - Task 4 — Lead Capture Agent persona + enrichment validator + sample leads. Done.
  - Task 5 — Outreach Agent persona (draft-only, no send capability). Done.
  - Task 6 — Nurture Agent persona (sequence templates, no live scheduler). Done.
  - Task 7 — Markdown dashboard renderer. Done.
  - Task 8 — Orchestration driver (wires all 5 together end-to-end). **In progress** — `prototype/tests/test_run_pipeline.py` exists but is uncommitted.

## Active

- **Finish Task 8** — the orchestration driver — to get a working end-to-end run of the prototype.
- **Confirmed direction, 2026-07-13** (from the "Social Media Intro" meeting with Mateja Ueligitone — see `../claude/brand_os/brands/techequity/engagement/meeting-notes/2026-07-13-social-media-intro.md`, and `../claude/brand_os/brands/techequity/DECISIONS.md`): Mateja's real captions/video-shorts workflow (Sidekick hooks/timestamps → manual Gemini/Claude scripting in fresh chats each time → CapCut/Figma editing) is almost exactly the gap the **Content Agent** already closes. Direction is now: **connect the existing Content Agent to her real workflow and port it to ClawMax** — not a standalone chatbot, not a from-scratch build. [VERIFY] with Sheena directly before treating this as fully locked (see Open questions).
- **✅ Unblocked, 2026-07-13 — Mateja delivered the captions workflow outline** (raw: `../claude/brand_os/brands/techequity/engagement/meeting-notes/2026-07-13-mateja-workflow-outline.md`; extracted: `research-brief.md` §B). Concrete integration requirements for porting the Content Agent, now known:
  1. Trigger: content is planned weekly in Slack + a Monday board — the agent needs a way to know what's due this week (Monday API, or a manual trigger for now).
  2. Draft input isn't just "a session" — it's a **post template** (from "the Doc") + Luma event details + optionally a past reference post for style. The existing Content Agent takes a session as input; needs adapting to also consume the template/Luma-details structure, not just replace the whole human process.
  3. **The approval loop is human-in-the-loop by design** — Sheena/Ave review, Mateja/Satvika edit — the agent should output a draft **into their existing review surface ("the Doc")**, not attempt to auto-publish. This actually matches the prototype's existing "draft-only" outreach-agent philosophy (see DECISIONS.md) — same caution applies here.
  4. TypeGrow formatting + final scheduling stay manual (Mateja's own bolding/spacing judgment, manual LinkedIn posting) — not in scope for the agent, at least initially.
  - Video-shorts side (Sidekick → Gemini/Claude → CapCut/Figma) has no written breakdown yet — only covered verbally in the meeting. [VERIFY] whether Mateja will send one.
- **🔴 Design spec — living document, 2026-07-13:** `.claude/worktrees/content-pipeline-prototype/docs/superpowers/specs/2026-07-13-mateja-captions-integration-design.md`. Covers the Content Agent's extended input contract (session + template + Luma details + optional past post), LinkedIn-only output for now, and the Doc hand-off (local file + manual paste, pending a real Docs-write integration). **Update this file in place** as the integration design evolves — don't create a new dated spec for incremental changes to this same effort. **Implementation plan now written and executed, 2026-07-13** (`.claude/worktrees/content-pipeline-prototype/.superpowers/sdd/task-2-brief.md` + its Task 1 predecessor): Task 1 (`validate_content_agent_input` in `skills/validators.py`) and Task 2 (Content Agent persona rewritten in `prototype/agents/content-agent.md` for the template+Luma+past-post input contract) are both complete. Step 7's manual validation — a real template+Luma-details LinkedIn draft for the upcoming "Enterprise AI at Scale" forum, run through a subagent invocation of the rewritten persona — **passed** (reflected the template structure and real event details, correct LinkedIn register, no fabricated speaker names despite the real event's empty speaker list; see `prototype/output/drafts/mateja-workflow-enterprise-ai-at-scale-talks-ai-agent-workshops-LinkedIn.md`). Not moved to Done — that call is left to the human.

## Backlog

### Features
- Prototype the agent flow in Claude Code first (source → plan → generate platform assets → publish tasks → analytics loop), then port validated design into OpenClaw `AGENTS.md`/`SOUL.md` + ClawMax `WORKFLOW.md`, deployed into `WORKSPACES/techequity/`.
- Evaluate reusing existing `brand_os` Python scripts (Notion integration) as OpenClaw skills via its local-directory/GitHub skill import, rather than rewriting.

### Portfolio artifacts
- (defer until the pilot ships)

## Artifacts tracker

| Name | Status | Themes | Placement |
|---|---|---|---|
| — | — | — | — |

## Open questions

- [VERIFY] What exactly "present to the partnership" requires as a deliverable — see `brand_os/brands/techequity/ROADMAP.md`, still unresolved there too.
- [VERIFY] Who funds the ongoing LLM API token cost once this runs for real — TechEquity has no marketing budget per `brand_os/brands/techequity/engagement/strategy.md`.
- **✅ Resolved, 2026-07-13, per the user** (see `../claude/brand_os/brands/techequity/DECISIONS.md`): **ClawMax is confirmed as the runtime for the whole marketing workflow** — not a standalone chatbot, not just for captions. The **captions AI project is the near-term partnership deliverable**, not the full 5-part pipeline. Practically, this means: finish Task 8 (orchestration driver), then prioritize porting the **Content Agent specifically** to ClawMax/OpenClaw first (captions/shorts drafting — the piece that satisfies the near-term deliverable), rather than porting all 5 agents at once. Lead Capture / Outreach / Nurture / Dashboard port later, once the captions piece is proven with Mateja and Sheena.
- [VERIFY] whether Sheena has confirmed this directly, or whether this is still the user's own directional call pending her sign-off — don't treat it as fully locked until confirmed live.
- Is the local ClawMax clone (`openclaw_GTM/clawmax/`) sufficient for the eventual port, or does TechEquity's formal design-partner status (still not requested — see `brand_os/brands/techequity/ROADMAP.md`) require a different/hosted instance? Don't assume the local dev clone is the same thing as production access.
