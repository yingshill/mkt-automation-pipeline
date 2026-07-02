"""Schema validators for agent-produced output.

These check *shape*, never *quality* — content quality is human-reviewed
per the design spec's global constraint. A validator passing means the
output is safe to persist, not that it's good copy.
"""

VALID_CHANNELS = {"LinkedIn", "Instagram", "Facebook", "YouTube", "Sidekick"}
VALID_TIERS = {"Bronze", "Silver", "Gold", "Platinum", "Design Partner"}


def validate_draft(draft: dict) -> None:
    if "channel" not in draft or "content" not in draft:
        raise ValueError("draft missing required keys: channel, content")
    if draft["channel"] not in VALID_CHANNELS:
        raise ValueError(f"unknown channel: {draft['channel']!r} (expected one of {VALID_CHANNELS})")
    if not draft["content"] or not draft["content"].strip():
        raise ValueError("draft content must not be empty")


def validate_lead_enrichment(enrichment: dict) -> None:
    if "suggested_tier" not in enrichment or "context" not in enrichment:
        raise ValueError("enrichment missing required keys: suggested_tier, context")
    if enrichment["suggested_tier"] not in VALID_TIERS:
        raise ValueError(f"unknown tier: {enrichment['suggested_tier']!r} (expected one of {VALID_TIERS})")
    if not enrichment["context"] or not enrichment["context"].strip():
        raise ValueError("enrichment context must not be empty")


def validate_outreach_message(message: dict) -> None:
    if "lead_id" not in message:
        raise ValueError("outreach message missing required key: lead_id")
    if "message" not in message or not message["message"] or not message["message"].strip():
        raise ValueError("outreach message content must not be empty")
