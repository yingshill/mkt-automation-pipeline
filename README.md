# TechEquity Marketing Workflow

You're in the **build project** — the actual AI-agent marketing pipeline for TechEquity AI / ClawMax, built to run on ClawMax (which runs on OpenClaw). This repo owns the design source and build docs; it does not own the BD/pitch context or the runtime.

**The set:**
- [Roadmap](ROADMAP.md) — what's active/backlog for the build.
- [Decisions](DECISIONS.md) — why this project is structured the way it is.
- **BD / pitch / relationship context** → `claude/brand_os/brands/techequity/` (separate repo) — the strategy, research brief, run-sheet, and pilot proposals that led to this build. This repo does not duplicate that reasoning; read it there.
- **Runtime** → the shared local ClawMax install at `Projects & Learning/openclaw_GTM/clawmax/`. This project deploys into a dedicated workspace there: `WORKSPACES/techequity/` — created 2026-07-02, currently an empty skeleton (`AGENTS/`, `WORKFLOWS/`, `ORG/`, `TEMPLATES/`, `PARTNERS/`, `SKILLS/custom/`, `SYSTEM/`), registered in `~/.openclaw/dashboard-workspaces.json` so ClawMax's dashboard recognizes it. This repo holds the design source (agent personas, workflow definitions) before/as they're ported into that workspace.

---

## What this project is

The design-partner build confirmed in the 2026-07-01 call with Sheena Tu: a social-media content pipeline that runs on ClawMax itself (dogfooding), doubling as the proof TechEquity needs to present to become a ClawMax design partner. Full reasoning: `brand_os/brands/techequity/DECISIONS.md`.

## Status

- **Stage:** Prototype substantially built, in Claude Code, on branch `worktree-content-pipeline-prototype`. Content, Lead Capture, Outreach, and Nurture agents + the dashboard renderer are committed. Orchestration driver (wiring all 5 together end-to-end) is in progress. **Not yet ported to ClawMax/OpenClaw** — still lives entirely in this repo's Claude Code worktree, per the design spec's staged plan.
- **Created:** 2026-07-01. Last build activity: 2026-07-02 (per worktree commits) — see `ROADMAP.md` for exact task status and the 2026-07-13 decision point on next direction.
