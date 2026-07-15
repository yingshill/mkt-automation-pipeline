import pytest

PHASES = ["announcement_1", "announcement_2", "announcement_3", "during_event", "post_event_recap"]


@pytest.mark.parametrize("phase", PHASES)
def test_template_file_exists_and_is_non_empty(phase):
    with open(f"prototype/data/templates/{phase}.md") as f:
        content = f.read()
    assert len(content.strip()) > 0


@pytest.mark.parametrize("phase", PHASES)
def test_template_file_discloses_construction(phase):
    with open(f"prototype/data/templates/{phase}.md") as f:
        content = f.read()
    assert "constructed" in content.lower() or "generalized" in content.lower()
