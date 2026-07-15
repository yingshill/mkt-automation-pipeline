# TechEquity Marketing Workflow — Project Instructions

**Read this first, every session — this is the build project for the TechEquity AI / ClawMax social-media content pipeline.**

## Where the actual code lives

**⚠️ Corrected 2026-07-14 — this used to describe a git worktree; that's gone now, don't go looking for it.** The prototype was originally built in a separate worktree (`worktree-content-pipeline-prototype`) so it could iterate independently of the design docs on `master`. As of 2026-07-14, all of that work (the original 5-part prototype + the captions-integration extension, 11 tasks total) was merged into `master` via fast-forward, and the worktree + branch were removed. **The code lives directly in this repo root now** — `prototype/`, `docs/`, `README.md`, `ROADMAP.md`, `DECISIONS.md` are all on `master`, no `cd` into a subdirectory required. Run `git worktree list` if you ever need to confirm there's no worktree currently active before assuming this.

## Remote

`origin` → `https://github.com/yingshill/mkt-automation-pipeline.git` (added + first pushed 2026-07-14). Push to this remote for this repo — don't ask which repo, this is it.

## Orientation — what to read, and where

- [README.md](README.md) — what this project is, current build stage.
- [ROADMAP.md](ROADMAP.md) — what's active/backlog, open questions. Kept in sync with `git log` — if it looks stale, verify against `git log` in this repo root before trusting it (no worktree to check anymore).
- [DECISIONS.md](DECISIONS.md) — why things are structured this way (append-only).
- [docs/testing/content-agent-tests.md](docs/testing/content-agent-tests.md) — living log of every validation test run against the Content Agent (real inputs, real outputs, independent-review findings). Append new tests here; don't scatter test results elsewhere.
- **BD/pitch/relationship context** (not build) → `../claude/brand_os/brands/techequity/` — separate repo, owns the strategy/research/relationship reasoning. Has its own `CLAUDE.md` with its own orientation. Don't duplicate that reasoning here.
- **ClawMax runtime** (not yet deployed to — the prototype is still Claude-Code-only) → `../openclaw_GTM/clawmax/WORKSPACES/techequity/`

## Living design specs — update in place, don't fork new files

The captions-integration design spec (`docs/superpowers/specs/2026-07-13-mateja-captions-integration-design.md`, now directly in this repo's `docs/` — see the worktree correction above) is a **living document** for that specific effort — as the design evolves, edit it in place rather than creating a new dated spec each time. The original `2026-07-02-content-pipeline-prototype-design.md` stays as historical record for the initial 5-part prototype design; the two are not the same file and shouldn't be merged. Only fork a genuinely new spec if work grows beyond "extending the Content Agent" into a separate effort.

## Standing facts worth not re-deriving

- Confirmed direction (2026-07-13): **ClawMax is the runtime for the whole marketing workflow** — not a standalone chatbot. The **captions AI project specifically** (not the full 5-part pipeline) is the near-term partnership deliverable. See `DECISIONS.md` in the brand_os BD repo for the full reasoning.
- The prototype's approval loop must stay **human-in-the-loop by design** — TechEquity's real workflow has Sheena/Ave reviewing drafts and Mateja/Satvika editing them before anything posts. The agent's job is to produce a draft into their existing review surface, not to auto-publish.
