import pytest
from prototype.skills.store import (
    init_db, insert_session, insert_draft, insert_lead,
    update_lead_enrichment, insert_outreach, upsert_nurture_stage,
)
from prototype.skills.render_dashboard import render_dashboard


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "pipeline.db")
    init_db(path)
    return path


def test_render_dashboard_empty_store_shows_zero_counts(db_path):
    report = render_dashboard(db_path)
    assert "Sessions: 0" in report
    assert "Drafts: 0" in report
    assert "Leads: 0" in report


def test_render_dashboard_reflects_seeded_data(db_path):
    session_id = insert_session(db_path, video_id="v1", title="AI Agents 101", url="u1")
    insert_draft(db_path, session_id, "LinkedIn", "draft text")
    lead_id = insert_lead(db_path, name="Priya Anand", source="sample-seed")
    update_lead_enrichment(db_path, lead_id, suggested_tier="Gold", context="Asked about sponsorship")
    insert_outreach(db_path, lead_id, "Hi Priya...", session_id=session_id)
    upsert_nurture_stage(db_path, lead_id, stage="touch_1", next_touch_template="Checking in...")

    report = render_dashboard(db_path)
    assert "AI Agents 101" in report
    assert "Priya Anand" in report
    assert "Gold" in report
    assert "touch_1" in report
    assert "Sessions: 1" in report
    assert "Drafts: 1" in report
    assert "Leads: 1" in report
