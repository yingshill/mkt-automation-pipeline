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

---

## Defer real session-data sourcing; assume local video + placeholder stub for pipeline-shape validation

**Date:** 2026-07-01
**Context:** Implementing `docs/superpowers/plans/2026-07-02-content-pipeline-prototype.md`, Task 3's manual validation step required a real fetched session. Investigation found the plan's Task 2 grounding assumption no longer holds: YouTube's public RSS feed (`feeds/videos.xml?channel_id=...`), the mechanism `fetch_channel_videos` was built on, now 404s for every channel tested (confirmed via curl against both TechEquity's channel and a definitely-live reference channel, not a sandbox artifact). The user confirmed the team hasn't decided how this pipeline will actually source event recordings, and no real data (local or remote) is available right now — but the eventual input is expected to be a **local video file** rather than a YouTube-discovered one.
**Options considered:**
1. Fix video discovery now by scraping the channel's `/videos` page JSON, using `yt-dlp`, or switching to the paid/keyed YouTube Data API v3.
2. Pause all further pipeline work until the team decides on a data source.
3. Treat data-sourcing as explicitly out of scope for this prototype pass — build the rest of the pipeline (Lead Capture, Outreach, Nurture, Dashboard, orchestration) against a clearly-labeled placeholder session stub standing in for "a local video file, title/description provided manually, no transcript" — and revisit real sourcing once the team decides.
**Decision:** Option 3. This amends the original design spec's "no mock data" constraint (`docs/superpowers/specs/2026-07-02-content-pipeline-prototype-design.md`), narrowly: a single clearly-labeled placeholder session record (`prototype/data/sample_sessions.json`, mirroring the existing `sample_leads.json` seed pattern) may be used to validate pipeline mechanics, since no real data source exists yet to pull from. This is scoped to *mechanics validation only* — any content this stub produces is not to be treated as real, publishable material. `fetch_channel_videos`'s YouTube RSS dependency is left in the codebase but is not wired into the orchestrator (Task 8) for now; it's dead code pending a real team decision on sourcing, not deleted, since fixing it may still be the answer once that decision is made.
**Tradeoffs:** Unblocks Tasks 3-8 of the prototype without a real data source. In exchange: Content Agent's persona is validated against synthetic input, not a real session, so its output quality can't be judged as representative until real data exists. Revisits — narrowly — a decision (`no mock data`) recorded as a hard constraint in the design spec's Scoping decisions section; noted here rather than silently overridden, per this project's append-only decision log.
