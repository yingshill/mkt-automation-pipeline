import pytest
from prototype.skills.validators import validate_draft, validate_lead_enrichment

VALID_CHANNELS = {"LinkedIn", "Instagram", "Facebook", "YouTube", "Sidekick"}
VALID_TIERS = {"Bronze", "Silver", "Gold", "Platinum", "Design Partner"}


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
