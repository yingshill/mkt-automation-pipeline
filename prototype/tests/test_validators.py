import pytest
from prototype.skills.validators import validate_draft, validate_lead_enrichment, validate_outreach_message, validate_nurture_plan, validate_content_agent_input

VALID_CHANNELS = {"LinkedIn", "Instagram", "Facebook", "YouTube", "Sidekick"}
VALID_TIERS = {"Bronze", "Silver", "Gold", "Platinum", "Design Partner"}
FORBIDDEN_SEND_MARKERS = ("smtp", "sendgrid", "ses.send_email", "requests.post(", "mailto:")


def test_validate_draft_accepts_well_formed_draft():
    validate_draft({"channel": "LinkedIn", "content": "A real post about the session."})


def test_validate_draft_rejects_unknown_channel():
    with pytest.raises(ValueError, match="channel"):
        validate_draft({"channel": "MySpace", "content": "..."})


def test_validate_draft_rejects_empty_content():
    with pytest.raises(ValueError, match="content"):
        validate_draft({"channel": "LinkedIn", "content": ""})


def test_validate_draft_rejects_missing_keys():
    with pytest.raises(ValueError):
        validate_draft({"channel": "LinkedIn"})


def test_validate_lead_enrichment_accepts_well_formed():
    validate_lead_enrichment({
        "suggested_tier": "Gold", "company": "Acme AI", "context": "Asked about sponsorship at the May forum",
    })


def test_validate_lead_enrichment_rejects_unknown_tier():
    with pytest.raises(ValueError, match="tier"):
        validate_lead_enrichment({"suggested_tier": "Diamond", "company": "Acme AI", "context": "..."})


def test_validate_lead_enrichment_rejects_empty_context():
    with pytest.raises(ValueError, match="context"):
        validate_lead_enrichment({"suggested_tier": "Gold", "company": "Acme AI", "context": ""})


def test_validate_outreach_message_accepts_well_formed():
    validate_outreach_message({"lead_id": 1, "message": "Hi Priya, following up on your interest..."})


def test_validate_outreach_message_rejects_empty_message():
    with pytest.raises(ValueError, match="message"):
        validate_outreach_message({"lead_id": 1, "message": ""})


def test_validate_outreach_message_rejects_missing_lead_id():
    with pytest.raises(ValueError, match="lead_id"):
        validate_outreach_message({"message": "..."})


def test_outreach_agent_file_contains_no_send_capability():
    # Structural guarantee from the design spec: no send path exists at all.
    with open("prototype/agents/outreach-agent.md") as f:
        content = f.read().lower()
    for marker in FORBIDDEN_SEND_MARKERS:
        assert marker not in content


VALID_STAGES = {"new", "touch_1", "touch_2", "touch_3", "closed"}


def test_validate_nurture_plan_accepts_well_formed():
    validate_nurture_plan({"stage": "touch_1", "next_touch_template": "Checking in on..."})


def test_validate_nurture_plan_rejects_unknown_stage():
    with pytest.raises(ValueError, match="stage"):
        validate_nurture_plan({"stage": "touch_99", "next_touch_template": "..."})


def test_validate_nurture_plan_rejects_empty_template():
    with pytest.raises(ValueError, match="template"):
        validate_nurture_plan({"stage": "touch_1", "next_touch_template": ""})


def test_validate_content_agent_input_accepts_session_only():
    validate_content_agent_input({
        "session": {"video_id": "abc123", "title": "AI Agents 101"},
        "template_text": None,
        "luma_event_details": None,
        "past_reference_post": None,
    })


def test_validate_content_agent_input_accepts_template_and_luma_only():
    validate_content_agent_input({
        "session": None,
        "template_text": "Join us at [Event Name] on [Date]...",
        "luma_event_details": {"event_title": "June Forum", "date": "2026-06-30"},
        "past_reference_post": None,
    })


def test_validate_content_agent_input_accepts_all_four_fields():
    validate_content_agent_input({
        "session": {"video_id": "abc123", "title": "AI Agents 101"},
        "template_text": "Join us at [Event Name] on [Date]...",
        "luma_event_details": {"event_title": "June Forum", "date": "2026-06-30"},
        "past_reference_post": "Last month's recap post text...",
    })


def test_validate_content_agent_input_rejects_template_without_luma():
    with pytest.raises(ValueError, match="session"):
        validate_content_agent_input({
            "session": None,
            "template_text": "Join us at [Event Name] on [Date]...",
            "luma_event_details": None,
            "past_reference_post": None,
        })


def test_validate_content_agent_input_rejects_luma_without_template():
    with pytest.raises(ValueError, match="session"):
        validate_content_agent_input({
            "session": None,
            "template_text": None,
            "luma_event_details": {"event_title": "June Forum", "date": "2026-06-30"},
            "past_reference_post": None,
        })


def test_validate_content_agent_input_rejects_all_none():
    with pytest.raises(ValueError, match="session"):
        validate_content_agent_input({
            "session": None,
            "template_text": None,
            "luma_event_details": None,
            "past_reference_post": None,
        })
