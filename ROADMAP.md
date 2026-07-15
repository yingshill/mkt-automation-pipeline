# TechEquity Marketing Workflow — Roadmap

What's being built and when. Hub: [README](README.md) · why: [DECISIONS](DECISIONS.md) · test results: [test log](docs/testing/content-agent-tests.md).

---

## Done

- Repo scaffolded (2026-07-01).
- `WORKSPACES/techequity/` created in the shared ClawMax install and registered in the dashboard's workspace registry (2026-07-02) — empty skeleton, no agents/workflows authored yet. **Note:** this is a *local dev clone* of open-source ClawMax (`openclaw_GTM/clawmax/`, MIT), separate from TechEquity's own formal design-partner access — see Open questions, don't conflate the two.
- **✅ Merged to `master`, 2026-07-14 — the prototype no longer lives in a worktree.** It was originally built on branch `worktree-content-pipeline-prototype`; that work is now merged (fast-forward) into `master` and the worktree/branch were removed. All paths below are relative to this repo's root, not a worktree.
  - Task 1 — shared SQLite store (`prototype/skills/store.py`). Done.
  - Task 2 — YouTube + speaker-page fetch layer (`prototype/skills/fetch_sessions.py`). Done; real session-data sourcing deferred, see DECISIONS.md.
  - Task 3 — Content Agent persona + draft validator. Done — generates real draft output for LinkedIn, Instagram, Facebook, a YouTube-shorts script, and Sidekick, from one placeholder session (`prototype/output/drafts/local-placeholder-001-*.md`).
  - Task 4 — Lead Capture Agent persona + enrichment validator + sample leads. Done.
  - Task 5 — Outreach Agent persona (draft-only, no send capability). Done.
  - Task 6 — Nurture Agent persona (sequence templates, no live scheduler). Done.
  - Task 7 — Markdown dashboard renderer. Done.
  - Task 8 — Orchestration driver (wires all 5 together end-to-end). **Still in progress** — `prototype/tests/test_run_pipeline.py` is now committed (as WIP) but imports `prototype.run_pipeline`, which doesn't exist yet. Not part of the captions-integration work below.
- **✅ Captions-integration extension, 2026-07-13/14 — 4 tasks, all reviewed clean, merged.**
  - Task 1 — `validate_content_agent_input` added to `prototype/skills/validators.py`.
  - Task 2 — Content Agent persona (`prototype/agents/content-agent.md`) rewritten to accept template + Luma event details + optional past-reference post, alongside the original session input.
  - Task 3 — schema fix: `drafts.session_id` made nullable in `store.py` (found during Task 2's manual validation — the store couldn't persist a session-less draft, exactly the case this extension exists for).
  - Task 4 — dashboard fix: `render_dashboard.py` now surfaces session-less ("unattached") drafts, which it previously counted but never displayed (found during the final whole-branch review).
  - **Validated with 2 real test runs** — see [test log](docs/testing/content-agent-tests.md): an upcoming real event with no speakers announced yet (correctly avoided fabricating names), and an already-happened real event with a full real 6-speaker roster (100% accurate, no invented speaker; one reviewer false-positive caught and corrected).

## Active

- **Finish Task 8** — the orchestration driver — to get a working end-to-end run of the full 5-part prototype. Not blocking the captions-integration work, which is already merged and tested independently of it.
- **Keep testing and refining the Content Agent against the [test log](docs/testing/content-agent-tests.md)'s open candidates** — notably: adding per-speaker session-title and run-of-show fields to `luma_event_details` (a real posted-post comparison showed the real posts include both, untested so far), testing the post-event/recap path (needs a real session/transcript), and testing with a `past_reference_post` provided (untested so far).
- **Design spec — living document:** `docs/superpowers/specs/2026-07-13-mateja-captions-integration-design.md` (now in this repo's root `docs/`, not a worktree). Covers the Content Agent's extended input contract, LinkedIn-only output for now, and the Doc hand-off (local file + manual paste, pending a real Docs-write integration — investigated during Task 2; no available Google Drive integration can write into an existing Doc). Update this file in place as the design evolves.
- **Still pending, not yet acted on:**
  1. Trigger for weekly content planning (Slack + Monday board) — no automated trigger built yet, manual for now.
  2. Video-shorts workflow (Sidekick → Gemini/Claude → CapCut/Figma) has no written breakdown from Mateja yet — only covered verbally. [VERIFY] whether she'll send one.
  3. Whether Sheena has directly confirmed the ClawMax-as-runtime direction, or whether it's still the user's own directional call — see Open questions.

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
