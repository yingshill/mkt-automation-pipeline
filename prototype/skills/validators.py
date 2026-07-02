"""Schema validators for agent-produced output.

These check *shape*, never *quality* — content quality is human-reviewed
per the design spec's global constraint. A validator passing means the
output is safe to persist, not that it's good copy.
"""

VALID_CHANNELS = {"LinkedIn", "Instagram", "Facebook", "YouTube", "Sidekick"}


def validate_draft(draft: dict) -> None:
    if "channel" not in draft or "content" not in draft:
        raise ValueError("draft missing required keys: channel, content")
    if draft["channel"] not in VALID_CHANNELS:
        raise ValueError(f"unknown channel: {draft['channel']!r} (expected one of {VALID_CHANNELS})")
    if not draft["content"] or not draft["content"].strip():
        raise ValueError("draft content must not be empty")
