import sqlite3
import pytest
from prototype.skills.store import (
    init_db, insert_session, get_session_by_video_id, list_sessions,
    insert_draft, list_drafts,
    insert_lead, update_lead_enrichment, list_leads,
    insert_outreach, list_outreach,
    upsert_nurture_stage, list_nurture_stages,
    insert_event, get_event, link_session_to_event,
)


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "pipeline.db")
    init_db(path)
    return path


def test_init_db_creates_all_tables(db_path):
    conn = sqlite3.connect(db_path)
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    conn.close()
    assert {"sessions", "drafts", "leads", "outreach", "nurture_stage"} <= tables


def test_insert_and_get_session(db_path):
    session_id = insert_session(
        db_path, video_id="abc123", title="AI Agents 101",
        url="https://youtube.com/watch?v=abc123",
        speaker_name="Jane Doe", speaker_bio="Founder of X",
        description="A talk about agents", transcript="full transcript text",
        transcript_available=True,
    )
    assert session_id == 1
    session = get_session_by_video_id(db_path, "abc123")
    assert session["title"] == "AI Agents 101"
    assert session["transcript_available"] == 1


def test_insert_session_duplicate_video_id_raises(db_path):
    insert_session(db_path, video_id="dup1", title="First", url="u")
    with pytest.raises(sqlite3.IntegrityError):
        insert_session(db_path, video_id="dup1", title="Second", url="u2")


def test_list_sessions_returns_all(db_path):
    insert_session(db_path, video_id="v1", title="One", url="u1")
    insert_session(db_path, video_id="v2", title="Two", url="u2")
    sessions = list_sessions(db_path)
    assert len(sessions) == 2
    assert {s["video_id"] for s in sessions} == {"v1", "v2"}


def test_insert_and_list_drafts(db_path):
    session_id = insert_session(db_path, video_id="v1", title="One", url="u1")
    insert_draft(db_path, session_id, "LinkedIn", "A LinkedIn post draft")
    insert_draft(db_path, session_id, "Instagram", "An Instagram caption")
    drafts = list_drafts(db_path, session_id=session_id)
    assert len(drafts) == 2
    assert {d["channel"] for d in drafts} == {"LinkedIn", "Instagram"}


def test_list_drafts_without_session_filter_returns_all(db_path):
    s1 = insert_session(db_path, video_id="v1", title="One", url="u1")
    s2 = insert_session(db_path, video_id="v2", title="Two", url="u2")
    insert_draft(db_path, s1, "LinkedIn", "draft 1")
    insert_draft(db_path, s2, "LinkedIn", "draft 2")
    assert len(list_drafts(db_path)) == 2


def test_insert_draft_without_session_id(db_path):
    draft_id = insert_draft(db_path, None, "LinkedIn", "A template+Luma draft with no session")
    drafts = list_drafts(db_path)
    assert len(drafts) == 1
    assert drafts[0]["id"] == draft_id
    assert drafts[0]["session_id"] is None


def test_insert_lead_and_enrich(db_path):
    lead_id = insert_lead(db_path, name="Sam Prospect", source="sample-seed", email="sam@example.com")
    update_lead_enrichment(db_path, lead_id, company="Acme AI", suggested_tier="Gold", context="Interested in sponsorship")
    leads = list_leads(db_path)
    assert len(leads) == 1
    assert leads[0]["company"] == "Acme AI"
    assert leads[0]["suggested_tier"] == "Gold"
    assert leads[0]["enriched_at"] is not None


def test_insert_and_list_outreach(db_path):
    lead_id = insert_lead(db_path, name="Sam Prospect", source="sample-seed")
    session_id = insert_session(db_path, video_id="v1", title="One", url="u1")
    insert_outreach(db_path, lead_id, "Hi Sam, following up on...", session_id=session_id)
    outreach = list_outreach(db_path, lead_id=lead_id)
    assert len(outreach) == 1
    assert "Sam" in outreach[0]["message"]


def test_upsert_nurture_stage_updates_in_place(db_path):
    lead_id = insert_lead(db_path, name="Sam Prospect", source="sample-seed")
    upsert_nurture_stage(db_path, lead_id, stage="touch_1", next_touch_template="Following up...")
    upsert_nurture_stage(db_path, lead_id, stage="touch_2", next_touch_template="Checking in...")
    stages = list_nurture_stages(db_path)
    assert len(stages) == 1
    assert stages[0]["stage"] == "touch_2"


def test_insert_and_get_event(db_path):
    event_id = insert_event(db_path, event_title="June Forum", event_date="2026-06-30")
    event = get_event(db_path, event_id)
    assert event["event_title"] == "June Forum"
    assert event["event_date"] == "2026-06-30"
    assert event["session_id"] is None


def test_link_session_to_event(db_path):
    event_id = insert_event(db_path, event_title="June Forum", event_date="2026-06-30")
    session_id = insert_session(db_path, video_id="v1", title="June Forum Recording", url="u1")
    link_session_to_event(db_path, event_id, session_id)
    event = get_event(db_path, event_id)
    assert event["session_id"] == session_id


def test_get_event_returns_none_for_unknown_id(db_path):
    assert get_event(db_path, 9999) is None
