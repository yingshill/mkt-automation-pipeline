import pytest
from prototype.skills.content_router import classify_phase


def test_classify_phase_far_out_no_session_is_announcement_1():
    assert classify_phase(days_until_event=20, has_session=False) == "announcement_1"


def test_classify_phase_boundary_15_days_is_announcement_1():
    assert classify_phase(days_until_event=15, has_session=False) == "announcement_1"


def test_classify_phase_boundary_14_days_is_announcement_2():
    assert classify_phase(days_until_event=14, has_session=False) == "announcement_2"


def test_classify_phase_mid_range_is_announcement_2():
    assert classify_phase(days_until_event=7, has_session=False) == "announcement_2"


def test_classify_phase_boundary_3_days_is_announcement_2():
    assert classify_phase(days_until_event=3, has_session=False) == "announcement_2"


def test_classify_phase_boundary_2_days_is_announcement_3():
    assert classify_phase(days_until_event=2, has_session=False) == "announcement_3"


def test_classify_phase_1_day_is_announcement_3():
    assert classify_phase(days_until_event=1, has_session=False) == "announcement_3"


def test_classify_phase_zero_days_is_during_event():
    assert classify_phase(days_until_event=0, has_session=False) == "during_event"


def test_classify_phase_zero_days_with_session_is_still_during_event():
    assert classify_phase(days_until_event=0, has_session=True) == "during_event"


def test_classify_phase_past_with_session_is_post_event_recap():
    assert classify_phase(days_until_event=-1, has_session=True) == "post_event_recap"


def test_classify_phase_past_without_session_is_awaiting_recording():
    assert classify_phase(days_until_event=-1, has_session=False) == "awaiting_recording"


def test_classify_phase_far_future_with_session_is_still_announcement_1():
    # has_session is irrelevant pre-event (rules 1-4 don't check it)
    assert classify_phase(days_until_event=20, has_session=True) == "announcement_1"


def test_compute_days_until_event_future_date():
    from datetime import date
    from prototype.skills.content_router import compute_days_until_event
    assert compute_days_until_event("2026-07-20", today=date(2026, 7, 14)) == 6


def test_compute_days_until_event_past_date():
    from datetime import date
    from prototype.skills.content_router import compute_days_until_event
    assert compute_days_until_event("2026-07-10", today=date(2026, 7, 14)) == -4


def test_compute_days_until_event_same_day():
    from datetime import date
    from prototype.skills.content_router import compute_days_until_event
    assert compute_days_until_event("2026-07-14", today=date(2026, 7, 14)) == 0


def test_compute_days_until_event_missing_date_raises():
    from datetime import date
    from prototype.skills.content_router import compute_days_until_event
    with pytest.raises(ValueError, match="event_date"):
        compute_days_until_event("", today=date(2026, 7, 14))


def test_compute_days_until_event_malformed_date_raises():
    from datetime import date
    from prototype.skills.content_router import compute_days_until_event
    with pytest.raises(ValueError, match="event_date"):
        compute_days_until_event("not-a-date", today=date(2026, 7, 14))
