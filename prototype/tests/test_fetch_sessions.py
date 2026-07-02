import re

import pytest
from prototype.skills.fetch_sessions import (
    resolve_channel_id, fetch_channel_videos, fetch_transcript,
    fetch_speaker_profile, build_session_record, slugify_name,
)


def test_slugify_name_matches_known_speaker_page():
    # Verified during planning: https://techequity-ai.org/speaker/george-ekas/ is real.
    assert slugify_name("George Ekas") == "george-ekas"


@pytest.mark.integration
def test_resolve_channel_id_returns_uc_prefixed_id():
    channel_id = resolve_channel_id("TechEquityAi")
    assert channel_id.startswith("UC")


@pytest.mark.integration
def test_fetch_channel_videos_returns_at_least_one_real_video():
    channel_id = resolve_channel_id("TechEquityAi")
    videos = fetch_channel_videos(channel_id)
    assert len(videos) > 0
    assert "video_id" in videos[0]
    assert "title" in videos[0]
    assert videos[0]["url"].startswith("https://www.youtube.com/watch?v=")


@pytest.mark.integration
def test_fetch_transcript_handles_missing_transcript_gracefully():
    # A deliberately invalid video_id must return None, not raise.
    result = fetch_transcript("this-video-id-does-not-exist")
    assert result is None


@pytest.mark.integration
def test_fetch_speaker_profile_known_speaker_returns_bio():
    profile = fetch_speaker_profile("George Ekas")
    assert profile is not None
    assert "bio" in profile
    assert len(profile["bio"]) > 0


@pytest.mark.integration
def test_fetch_speaker_profile_known_speaker_returns_real_title_not_decorative_heading():
    # Regression test for the bug this task fixed: the live page (Elementor
    # page builder) emits a decorative `<h2> &gt; </h2>` breadcrumb heading
    # before the real title/company h2, both sharing the same CSS class. A
    # naive `soup.find("h2")` silently grabs the decorative ">" instead of
    # the title. Verified live during this task:
    # https://techequity-ai.org/speaker/george-ekas/ -> title_company ==
    # "Director of Engineering" (exact match, checked 2026-07-01).
    profile = fetch_speaker_profile("George Ekas")
    assert profile is not None
    title_company = profile["title_company"]
    assert title_company
    # Must contain actual words, not just punctuation/symbols (the decorative
    # heading's text content, if this regressed, would be a bare ">").
    assert re.search(r"\w", title_company)
    assert title_company == "Director of Engineering"


@pytest.mark.integration
def test_fetch_speaker_profile_unknown_speaker_returns_none():
    profile = fetch_speaker_profile("Definitely Not A Real Speaker Zzz")
    assert profile is None


def test_build_session_record_shape():
    video = {
        "video_id": "abc123",
        "title": "AI Agents 101",
        "url": "https://www.youtube.com/watch?v=abc123",
        "description": "A talk about agents by Jane Doe",
        "published_at": "2026-05-01T00:00:00Z",
    }
    record = build_session_record(video)
    assert record["video_id"] == "abc123"
    assert record["title"] == "AI Agents 101"
    assert record["url"] == video["url"]
    assert "transcript_available" in record
