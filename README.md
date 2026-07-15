# TechEquity Marketing Workflow

You're in the **build project** — the actual AI-agent marketing pipeline for TechEquity AI / ClawMax, built to run on ClawMax (which runs on OpenClaw). This repo owns the design source and build docs; it does not own the BD/pitch context or the runtime.

**The set:**
- [Roadmap](ROADMAP.md) — what's active/backlog for the build.
- [Decisions](DECISIONS.md) — why this project is structured the way it is.
- [Test log](docs/testing/content-agent-tests.md) — living collection of validation tests run against the Content Agent (real inputs, real outputs, independent-review findings). Grows with every new test; don't duplicate its content elsewhere.
- **BD / pitch / relationship context** → `claude/brand_os/brands/techequity/` (separate repo) — the strategy, research brief, run-sheet, and pilot proposals that led to this build. This repo does not duplicate that reasoning; read it there.
- **Runtime** → the shared local ClawMax install at `Projects & Learning/openclaw_GTM/clawmax/`. This project deploys into a dedicated workspace there: `WORKSPACES/techequity/` — created 2026-07-02, currently an empty skeleton (`AGENTS/`, `WORKFLOWS/`, `ORG/`, `TEMPLATES/`, `PARTNERS/`, `SKILLS/custom/`, `SYSTEM/`), registered in `~/.openclaw/dashboard-workspaces.json` so ClawMax's dashboard recognizes it. This repo holds the design source (agent personas, workflow definitions) before/as they're ported into that workspace.

---

## What this project is

The design-partner build confirmed in the 2026-07-01 call with Sheena Tu: a social-media content pipeline that runs on ClawMax itself (dogfooding), doubling as the proof TechEquity needs to present to become a ClawMax design partner. Full reasoning: `brand_os/brands/techequity/DECISIONS.md`.

## Status

- **Stage:** Prototype substantially built and **merged into `master`** as of 2026-07-14 (the worktree/branch it was built in is gone — don't look for it). Content Agent extended to draft from a template + real Luma event details (not just a session), validated in two real test runs — see [test log](docs/testing/content-agent-tests.md). Lead Capture, Outreach, Nurture agents + dashboard renderer are also built. Orchestration driver (wiring all 5 together end-to-end) is still in progress. **Not yet ported to ClawMax/OpenClaw** — still lives entirely in Claude Code / this repo, per the design spec's staged plan.
- **Created:** 2026-07-01. Last build activity: 2026-07-14 — see `ROADMAP.md` for exact task status.
