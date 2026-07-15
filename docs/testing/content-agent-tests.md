# Content Agent — Test Log

**Living document — log every validation test here, in place, as we keep testing and refining the workflow. Don't fork a new file per test; append a new numbered entry below instead.**

This is distinct from `docs/superpowers/specs/` (design decisions) and `docs/superpowers/plans/` (implementation tasks) — this file's one job is: what was tested, with what real inputs, what came out, and what it does/doesn't prove. Findings that suggest a design change belong in the living design spec (`docs/superpowers/specs/2026-07-13-mateja-captions-integration-design.md`), referenced from here, not duplicated.

**Method, reused every test:** (1) validate the input against `validate_content_agent_input`, (2) dispatch a fresh subagent with the exact current `prototype/agents/content-agent.md` as its instructions, (3) validate the output against `validate_draft`, (4) judge it by hand against the test's specific criteria, (5) dispatch a **second, independent** reviewer subagent — with no knowledge of how the draft was produced — to re-check accuracy against the real inputs. Per the "don't trust the report" discipline used throughout this project: the independent reviewer's claims get verified too, not accepted at face value (see Test 2 — its first verdict was wrong on its two headline points).

---

## Summary

| # | Date | Scenario | Real speakers given? | Verdict |
|---|---|---|---|---|
| 1 | 2026-07-13 | Pre-event announcement, upcoming real event, no speakers announced yet | No (empty list) | Passed for its scope — correctly declined to invent speakers. Template used was hand-built, not real. Didn't test filling in real speaker data. |
| 2 | 2026-07-14 | Pre-event announcement, real **already-happened** event, full real speaker roster | Yes (6 real speakers) | Speakers 100% accurate, no invented 7th. Independent reviewer's first-pass "fabrication" finding was itself wrong on its two headline points (verified against the template) — real findings are two minor ones, not fabrication. |

---

## Test 1 — 2026-07-13: Upcoming event, no speakers yet

**Purpose:** Can the Content Agent draft a LinkedIn post from a template + real event details, and correctly avoid inventing information it wasn't given?

**Inputs:**
- Template: hand-built by generalizing one real finished example post from TechEquity's archived `2026 Social Media Template.docx` into a fill-in-the-blank shape. **Not a literal template from their files** — no blank template exists in what's been shared; this was constructed for testing. "The Doc" (Mateja's actual live template) has never been available to test against.
- Event: real, genuinely upcoming — [Enterprise AI at Scale: Talks + AI Agent Workshops](https://luma.com/jul-ai-forum?utm_source=SVAI), Tuesday, July 28, 2026, Snowflake SVAI Hub. Speakers: `[]` (none announced yet at time of test, which is real/accurate for that event).
- `session`: None. `past_reference_post`: None.

**Process:** input validated → dispatched to a subagent running the exact `content-agent.md` persona → output validated → judged by hand → independently re-reviewed (task-review process, not a dedicated second-reviewer dispatch like Test 2).

**Output (LinkedIn draft):**
> Join us for Enterprise AI at Scale: Talks + AI Agent Workshops. [...] 🗓️ Featured speakers will be announced soon — check back as the lineup is confirmed. [...]
(Full text: `prototype/output/drafts/mateja-workflow-enterprise-ai-at-scale-talks-ai-agent-workshops-LinkedIn.md`)

**What it proved:** given an empty speaker list, the agent said "will be announced soon" instead of inventing names — the core "don't fabricate" behavior works in this case.

**What it didn't prove:** the far more common real case — a template's speaker slot with real names that need to be filled in *correctly*. That's exactly what Test 2 was designed to check.

---

## Test 2 — 2026-07-14: Already-happened event, full real speaker roster

**Purpose:** Test the case Test 1 couldn't — real speaker names, titles, and companies actually available, correctly used. Deliberately ignores the post-event/recap path (no session/transcript) — this is still testing the pre-event announcement path, just with better input data.

**Inputs:**
- Template: same hand-built stand-in as Test 1 (same disclosed limitation — not literally TechEquity's).
- Event: real, already happened — "Product & Business Strategy in AI: Talks + AI Agent Workshops, Ft Google and Snowflake," Thursday, February 19, 2026, Snowflake Silicon Valley AI Hub.
- Speakers (real, 6): Gopi Kallayil (Chief Business Strategist, AI, Google) · Ivan Lee (Founder & CEO, Datasaur) · Fahad Khan (Director of Programs, AI Foundations, Northrop Grumman) · Dave Nielsen (Head of Community, AI Alliance, IBM) · Mike Prince (CEO, Matchwise) · Anupam Datta (AI Research Lead, Snowflake).
- `session`: None (deliberately — not testing the recap/transcript path). `past_reference_post`: None.

**Output (LinkedIn draft, 201 words):**
> Join us for Product & Business Strategy in AI: Talks + AI Agent Workshops, featuring Google and Snowflake [...] Featured speakers include: Gopi Kallayil, Chief Business Strategist, AI at Google / Ivan Lee, Founder & CEO of Datasaur / Fahad Khan, Director of Programs, AI Foundations at Northrop Grumman / Dave Nielsen, Head of Community, AI Alliance (IBM) / Mike Prince, CEO of Matchwise / Anupam Datta, AI Research Lead at Snowflake [...]

**Independent reviewer's first verdict:** "Faithful to source? No" — flagged two "fabrications": the "TechEquity Ai Monthly Forum Series" framing, and an "AI leaders, developers, founders, and early-career talent" audience description.

**Controller correction (verified against the actual input given to the drafting agent):** both flagged phrases are **verbatim from the template's own fixed boilerplate text**, which the reviewer never checked against — it only checked the draft against `event_title`/`blurb`/`date`/`time`/`location`/`speakers`, not against the template. Not fabrication; the agent correctly reused the template's standing copy, which is exactly what a template is for. **This is a real gap in the reviewer's method, logged here so it isn't repeated in future tests: always check drafts against the full template text, not just the event-specific fields.**

**Real findings, after correction:**
- All 6 speakers: accurate name/title/company, correct order, no invented 7th. Confirmed independently.
- Minor: dropped "and strategic advantage" from the given blurb's closing clause (omission, not invention).
- Minor: closing question added "in production" — a reasonable interpretive gloss on "deploy," not a hard invented claim, but not verbatim either.

**Bonus check — real posted comparison:** this event already happened, so the actual real post TechEquity published for it exists in the same archive. Compared side by side:
- Real post includes a **per-speaker talk title** for each speaker (e.g., "Keynote: How AI is Transforming Consumers and Marketing • Gopi Kallayil") and a **detailed run-of-show** (5:00 PM Registration → 6:00 PM Welcome → 6:15 PM Keynotes → ...). Neither was in this test's input — the agent correctly didn't invent them, but this means **the input structure needs two more fields to match real quality**: a per-speaker session title, and an agenda/run-of-show array. Not yet a schema change — logged here as a candidate for the next input-contract iteration once we're ready to test that.
- Real post uses `@Speaker` LinkedIn-native mention tags; the draft used plain text names — expected, this is a pre-TypeGrow/pre-native-formatting stage.

**What this proves:** real speaker data gets used accurately; the template's fixed boilerplate gets reused correctly (not fabricated); the "no invented facts" discipline held even under a follow-up reviewer's incorrect first read.

**What this doesn't prove:** per-speaker talk titles and detailed agendas aren't yet part of the input contract, so a draft with that level of real-post detail hasn't been tested. Not reviewed by Mateja/Sheena/Ave. Not run through TypeGrow. Not scheduled or posted.

---

## Open candidates for future tests

- Add per-speaker session-title and run-of-show fields to `luma_event_details`, then re-test against a real event that has both, to see if the agent matches the real post's structure more closely.
- Test the post-event/recap path — requires a real session recording + transcript, deliberately out of scope for both tests above.
- Test with a `past_reference_post` provided, to check tone-matching behavior (untested so far — both tests left this `None`).

## Known gap — no routing/gate before the Content Agent (identified 2026-07-14, moving to design now)

Both tests above required a human (the controller, standing in for whoever eventually operates this) to already know which scenario applies and manually assemble the right input — which template variant, whether to fetch a session or Luma details. There's no component that takes a rawer request ("we need a post for the June forum") and decides that on its own.

TechEquity's real archive shows this isn't hypothetical — they already run distinct template variants per lifecycle phase: "Event Announcement 1" (first tease) → "Announcement 2" (updated lineup) → "Announcement 3" ("Last Call" urgency) → a live "During" update → "Post" recap + per-session recording posts. Nothing today decides which phase a given request falls into, or what data to fetch for it.

**Design direction (agreed 2026-07-14):** a rule-based router, not an LLM classification step — phase (pre-event #1/#2/#3 vs. during vs. post-recap) is mostly determinable by date math (days until/since the event) and data availability (does a recording exist yet), not judgment calls. See the design spec for the actual router design once written.
