"""Shared SQLite store for the TechEquity content pipeline prototype.

Every pipeline component (fetch, content agent, lead capture agent,
outreach agent, nurture agent, dashboard) reads/writes through this
module. This is the layer that ports to a real datastore (or Vigo)
once the prototype graduates out of Claude Code.
"""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    speaker_name TEXT,
    speaker_bio TEXT,
    description TEXT,
    transcript TEXT,
    transcript_available INTEGER NOT NULL DEFAULT 0,
    fetched_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES sessions(id),
    channel TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT,
    company TEXT,
    context TEXT,
    suggested_tier TEXT,
    source TEXT NOT NULL,
    enriched_at TEXT
);

CREATE TABLE IF NOT EXISTS outreach (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL REFERENCES leads(id),
    session_id INTEGER REFERENCES sessions(id),
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS nurture_stage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL UNIQUE REFERENCES leads(id),
    stage TEXT NOT NULL,
    next_touch_template TEXT,
    updated_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = _connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def insert_session(db_path, video_id, title, url, speaker_name=None,
                    speaker_bio=None, description=None, transcript=None,
                    transcript_available=False) -> int:
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO sessions (video_id, title, url, speaker_name, "
            "speaker_bio, description, transcript, transcript_available, fetched_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (video_id, title, url, speaker_name, speaker_bio, description,
             transcript, int(transcript_available), _now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_session_by_video_id(db_path, video_id) -> dict | None:
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM sessions WHERE video_id = ?", (video_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_sessions(db_path) -> list[dict]:
    conn = _connect(db_path)
    try:
        rows = conn.execute("SELECT * FROM sessions ORDER BY id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def insert_draft(db_path, session_id, channel, content) -> int:
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO drafts (session_id, channel, content, created_at) "
            "VALUES (?, ?, ?, ?)",
            (session_id, channel, content, _now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_drafts(db_path, session_id=None) -> list[dict]:
    conn = _connect(db_path)
    try:
        if session_id is None:
            rows = conn.execute("SELECT * FROM drafts ORDER BY id").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM drafts WHERE session_id = ? ORDER BY id", (session_id,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def insert_lead(db_path, name, source, email=None, company=None, context=None) -> int:
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO leads (name, email, company, context, suggested_tier, source, enriched_at) "
            "VALUES (?, ?, ?, ?, NULL, ?, NULL)",
            (name, email, company, context, source),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_lead_enrichment(db_path, lead_id, company=None, suggested_tier=None, context=None) -> None:
    conn = _connect(db_path)
    try:
        conn.execute(
            "UPDATE leads SET company = COALESCE(?, company), "
            "suggested_tier = COALESCE(?, suggested_tier), "
            "context = COALESCE(?, context), enriched_at = ? WHERE id = ?",
            (company, suggested_tier, context, _now(), lead_id),
        )
        conn.commit()
    finally:
        conn.close()


def list_leads(db_path) -> list[dict]:
    conn = _connect(db_path)
    try:
        rows = conn.execute("SELECT * FROM leads ORDER BY id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def insert_outreach(db_path, lead_id, message, session_id=None) -> int:
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO outreach (lead_id, session_id, message, created_at) "
            "VALUES (?, ?, ?, ?)",
            (lead_id, session_id, message, _now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_outreach(db_path, lead_id=None) -> list[dict]:
    conn = _connect(db_path)
    try:
        if lead_id is None:
            rows = conn.execute("SELECT * FROM outreach ORDER BY id").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM outreach WHERE lead_id = ? ORDER BY id", (lead_id,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def upsert_nurture_stage(db_path, lead_id, stage, next_touch_template) -> None:
    conn = _connect(db_path)
    try:
        conn.execute(
            "INSERT INTO nurture_stage (lead_id, stage, next_touch_template, updated_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(lead_id) DO UPDATE SET "
            "stage = excluded.stage, next_touch_template = excluded.next_touch_template, "
            "updated_at = excluded.updated_at",
            (lead_id, stage, next_touch_template, _now()),
        )
        conn.commit()
    finally:
        conn.close()


def list_nurture_stages(db_path) -> list[dict]:
    conn = _connect(db_path)
    try:
        rows = conn.execute("SELECT * FROM nurture_stage ORDER BY id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
