import json
from prototype.run_pipeline import fetch_and_seed, DB_PATH
from prototype.skills.store import list_sessions


def test_fetch_and_seed_persists_sessions_and_sample_leads(tmp_path):
    db_path = str(tmp_path / "pipeline.db")
    sessions_path = tmp_path / "sample_sessions.json"
    sessions_path.write_text(json.dumps([
        {
            "video_id": "local-placeholder-001",
            "title": "[PLACEHOLDER] TechEquity AI Summit — Sample Session",
            "url": "local://placeholder-001.mp4",
            "description": "PLACEHOLDER RECORD — not a real session.",
            "speaker_name": None,
            "speaker_bio": None,
            "transcript": None,
            "transcript_available": False,
        }
    ]))

    fetch_and_seed(db_path, sessions_path=str(sessions_path))

    sessions = list_sessions(db_path)
    assert len(sessions) == 1
    assert sessions[0]["video_id"] == "local-placeholder-001"
    assert sessions[0]["transcript_available"] == 0
