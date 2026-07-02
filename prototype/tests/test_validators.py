import pytest
from prototype.skills.validators import validate_draft

VALID_CHANNELS = {"LinkedIn", "Instagram", "Facebook", "YouTube", "Sidekick"}


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
