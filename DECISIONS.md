# TechEquity Marketing Workflow — Decisions

Why this project is structured the way it is. Append-only. Hub: [README](README.md) · what/when: [ROADMAP](ROADMAP.md).

---

## Separate build repo, shared ClawMax runtime, BD layer stays in brand_os

**Date:** 2026-07-01
**Context:** The user decided to build the TechEquity social-media content pipeline as its own project rather than inside `brand_os` (which owns Yingshi's own multi-brand content system, not client software builds) or inside the existing `openclaw_GTM/` exploration folder (which already holds a different, unrelated research thread on ClawMax's architecture for Claude Code's own benefit). Investigation found a pre-existing local clone of the real ClawMax product at `openclaw_GTM/clawmax/` (git remote: `github.com/Maximilien-ai/clawmax`, MIT), already partially configured with one workspace (`WORKSPACES/default`), and confirmed via ClawMax's own `WORKSPACES/README.md` that one ClawMax install supports multiple independent workspaces (agents/workflows/config per workspace), normally created via the dashboard's workspace switcher.
**Options considered:**
1. Build inside `brand_os/brands/techequity/` alongside the BD docs.
2. Clone a fresh, dedicated ClawMax instance just for this project.
3. New standalone repo for the build's design source + docs, deploying into a new workspace (`WORKSPACES/techequity/`) inside the existing shared `openclaw_GTM/clawmax/` install; BD/pitch context stays in `brand_os/brands/techequity/` and is linked, not duplicated.
**Decision:** Option 3. This repo (`techequity-marketing-workflow`) is the canonical home for the build's design source, `ROADMAP.md`, and `DECISIONS.md`. Runtime execution lives in a new ClawMax workspace inside the already-existing shared install.
**Tradeoffs:** Slightly more indirection (three locations to know about: BD context in brand_os, build docs here, runtime in openclaw_GTM) versus one big folder. In exchange: no duplicated ClawMax install, no duplicated reasoning about the relationship/pitch, and each place stays true to the existing single-source-of-truth contract already in place across this user's projects.

---

## Create the `techequity` ClawMax workspace now, not deferred

**Date:** 2026-07-02
**Context:** Initial plan deferred creating the ClawMax workspace until the build was scoped. The user corrected this — confirmed wanting the workspace created inside `openclaw_GTM/clawmax/` alongside the new project repo, not deferred.
**Decision:** Created `openclaw_GTM/clawmax/WORKSPACES/techequity/` as an empty skeleton, mirroring exactly the directory structure `setup.sh` creates for a fresh workspace (`AGENTS/`, `WORKFLOWS/`, `ORG/`, `TEMPLATES/`, `PARTNERS/`, `SKILLS/custom/`, `SYSTEM/` — verified by reading `setup.sh`'s own workspace-setup step, not guessed). Registered it in `~/.openclaw/dashboard-workspaces.json` (the same file ClawMax's dashboard reads to list workspaces) with `id: "techequity"`, so the ClawMax dashboard will show it as a selectable workspace. Left `activeWorkspaceId` as `"default"` — switching the active workspace is a runtime action for the user to make deliberately, not something to change silently.
**Tradeoffs:** None significant — this is additive (new folder, new array entry) and matches the installer's own pattern, so it carries the same risk profile as running ClawMax's normal workspace-creation flow.
