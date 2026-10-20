"""SQLite storage. Plain functions, one short-lived connection per call.

Tables:
  sessions      - your notes. Only you write to this table; AI output never does.
  queue_items   - unresolved questions and next steps, each linked to a session.
  snapshots     - frozen copies of a session, taken right before an AI call.
  ai_calls      - every AI request/response (successful or not), for inspection.
  question_sets - a set of three understanding questions generated from a snapshot.
  questions     - each question, with your answer.
"""

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from . import config

SESSION_FIELDS = ["title", "topic", "goal", "explanation", "notes", "sources"]
QUEUE_KINDS = ["question", "task"]
PRIORITIES = ["high", "normal", "low"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id          INTEGER PRIMARY KEY,
    title       TEXT NOT NULL DEFAULT '',
    topic       TEXT NOT NULL DEFAULT '',
    goal        TEXT NOT NULL DEFAULT '',
    explanation TEXT NOT NULL DEFAULT '',
    notes       TEXT NOT NULL DEFAULT '',
    sources     TEXT NOT NULL DEFAULT '',
    is_example  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS queue_items (
    id             INTEGER PRIMARY KEY,
    session_id     INTEGER REFERENCES sessions(id),
    kind           TEXT NOT NULL CHECK (kind IN ('question', 'task')),
    text           TEXT NOT NULL,
    priority       TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN ('high', 'normal', 'low')),
    status         TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'done')),
    source         TEXT NOT NULL DEFAULT 'me',
    source_call_id INTEGER REFERENCES ai_calls(id),
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL,
    completed_at   TEXT
);
CREATE TABLE IF NOT EXISTS snapshots (
    id           INTEGER PRIMARY KEY,
    session_id   INTEGER NOT NULL REFERENCES sessions(id),
    content_hash TEXT NOT NULL,
    content_json TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    UNIQUE (session_id, content_hash)
);
CREATE TABLE IF NOT EXISTS ai_calls (
    id              INTEGER PRIMARY KEY,
    session_id      INTEGER NOT NULL REFERENCES sessions(id),
    snapshot_id     INTEGER REFERENCES snapshots(id),
    question_id     INTEGER REFERENCES questions(id),
    action          TEXT NOT NULL,
    prompt_version  TEXT NOT NULL,
    requested_model TEXT,
    returned_model  TEXT,
    request_json    TEXT,
    raw_response    TEXT,
    parsed_json     TEXT,
    stop_reason     TEXT,
    input_tokens    INTEGER,
    output_tokens   INTEGER,
    usage_json      TEXT,
    elapsed_ms      INTEGER,
    status          TEXT NOT NULL CHECK (status IN ('ok', 'error')),
    error           TEXT,
    warnings_json   TEXT,
    created_at      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS question_sets (
    id          INTEGER PRIMARY KEY,
    session_id  INTEGER NOT NULL REFERENCES sessions(id),
    snapshot_id INTEGER NOT NULL REFERENCES snapshots(id),
    ai_call_id  INTEGER NOT NULL REFERENCES ai_calls(id),
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS questions (
    id          INTEGER PRIMARY KEY,
    set_id      INTEGER NOT NULL REFERENCES question_sets(id),
    position    INTEGER NOT NULL,
    kind        TEXT NOT NULL,
    text        TEXT NOT NULL,
    answer      TEXT NOT NULL DEFAULT '',
    answered_at TEXT
);
"""


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@contextmanager
def connect():
    path = config.db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def _row(row):
    return dict(row) if row is not None else None


def _rows(rows):
    return [dict(r) for r in rows]


# ---------- sessions ----------

def create_session(is_example: bool = False, **fields) -> int:
    values = {f: fields.get(f, "") for f in SESSION_FIELDS}
    ts = now()
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO sessions (title, topic, goal, explanation, notes, sources, is_example,"
            " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (*[values[f] for f in SESSION_FIELDS], int(is_example), ts, ts),
        )
        return cur.lastrowid


def get_session(session_id: int) -> dict | None:
    with connect() as conn:
        return _row(conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone())


def update_session(session_id: int, fields: dict) -> str:
    """Save the editable fields. Returns the new updated_at timestamp."""
    unknown = set(fields) - set(SESSION_FIELDS)
    if unknown:
        raise ValueError(f"Not session fields: {unknown}")
    ts = now()
    assignments = ", ".join(f"{f} = ?" for f in fields)
    with connect() as conn:
        conn.execute(
            f"UPDATE sessions SET {assignments}, updated_at = ? WHERE id = ?",
            (*fields.values(), ts, session_id),
        )
    return ts


def list_sessions(limit: int | None = None) -> list[dict]:
    sql = "SELECT * FROM sessions ORDER BY updated_at DESC, id DESC"
    params = ()
    if limit:
        sql += " LIMIT ?"
        params = (limit,)
    with connect() as conn:
        return _rows(conn.execute(sql, params).fetchall())


def search_sessions(query: str) -> list[dict]:
    """Case-insensitive substring search over titles, topics and all note fields."""
    query = query.strip()
    if not query:
        return []
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    where = " OR ".join(f"{f} LIKE ? ESCAPE '\\'" for f in SESSION_FIELDS)
    with connect() as conn:
        return _rows(conn.execute(
            f"SELECT * FROM sessions WHERE {where} ORDER BY updated_at DESC",
            (pattern,) * len(SESSION_FIELDS),
        ).fetchall())


# ---------- queue ----------

def add_queue_item(session_id: int | None, kind: str, text: str, priority: str = "normal",
                   source: str = "me", source_call_id: int | None = None) -> int:
    ts = now()
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO queue_items (session_id, kind, text, priority, source, source_call_id,"
            " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (session_id, kind, text.strip(), priority, source, source_call_id, ts, ts),
        )
        return cur.lastrowid


def update_queue_item(item_id: int, **fields) -> None:
    allowed = {"kind", "text", "priority", "status"}
    if set(fields) - allowed:
        raise ValueError(f"Cannot update {set(fields) - allowed}")
    if "status" in fields:
        fields["completed_at"] = now() if fields["status"] == "done" else None
    fields["updated_at"] = now()
    assignments = ", ".join(f"{f} = ?" for f in fields)
    with connect() as conn:
        conn.execute(f"UPDATE queue_items SET {assignments} WHERE id = ?", (*fields.values(), item_id))


def list_queue(status: str | None = None, session_id: int | None = None) -> list[dict]:
    sql = ("SELECT q.*, s.title AS session_title FROM queue_items q"
           " LEFT JOIN sessions s ON s.id = q.session_id WHERE 1 = 1")
    params: list = []
    if status:
        sql += " AND q.status = ?"
        params.append(status)
    if session_id is not None:
        sql += " AND q.session_id = ?"
        params.append(session_id)
    sql += (" ORDER BY CASE q.priority WHEN 'high' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END,"
            " q.created_at DESC")
    with connect() as conn:
        return _rows(conn.execute(sql, params).fetchall())


# ---------- snapshots ----------

def get_or_create_snapshot(session_id: int, content: dict) -> int:
    """Store an exact copy of what is sent to the model. Identical content reuses one row."""
    content_json = json.dumps(content, sort_keys=True, ensure_ascii=False)
    content_hash = hashlib.sha256(content_json.encode("utf-8")).hexdigest()
    with connect() as conn:
        existing = conn.execute(
            "SELECT id FROM snapshots WHERE session_id = ? AND content_hash = ?",
            (session_id, content_hash),
        ).fetchone()
        if existing:
            return existing["id"]
        cur = conn.execute(
            "INSERT INTO snapshots (session_id, content_hash, content_json, created_at)"
            " VALUES (?, ?, ?, ?)",
            (session_id, content_hash, content_json, now()),
        )
        return cur.lastrowid


def get_snapshot(snapshot_id: int) -> dict | None:
    with connect() as conn:
        row = _row(conn.execute("SELECT * FROM snapshots WHERE id = ?", (snapshot_id,)).fetchone())
    if row:
        row["content"] = json.loads(row["content_json"])
    return row


# ---------- AI call records ----------

def insert_ai_call(record: dict) -> int:
    record = {**record, "created_at": now()}
    columns = ", ".join(record)
    placeholders = ", ".join("?" for _ in record)
    with connect() as conn:
        cur = conn.execute(f"INSERT INTO ai_calls ({columns}) VALUES ({placeholders})",
                           tuple(record.values()))
        return cur.lastrowid


def set_ai_call_warnings(call_id: int, warnings_json: str) -> None:
    with connect() as conn:
        conn.execute("UPDATE ai_calls SET warnings_json = ? WHERE id = ?", (warnings_json, call_id))


def get_ai_call(call_id: int) -> dict | None:
    with connect() as conn:
        return _row(conn.execute("SELECT * FROM ai_calls WHERE id = ?", (call_id,)).fetchone())


def list_ai_calls(session_id: int, action: str | None = None, status: str | None = None,
                  question_id: int | None = None) -> list[dict]:
    """Newest first."""
    sql = "SELECT * FROM ai_calls WHERE session_id = ?"
    params: list = [session_id]
    for column, value in (("action", action), ("status", status), ("question_id", question_id)):
        if value is not None:
            sql += f" AND {column} = ?"
            params.append(value)
    sql += " ORDER BY id DESC"
    with connect() as conn:
        return _rows(conn.execute(sql, params).fetchall())


# ---------- understanding questions ----------

def create_question_set(session_id: int, snapshot_id: int, ai_call_id: int,
                        questions: list[dict]) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO question_sets (session_id, snapshot_id, ai_call_id, created_at)"
            " VALUES (?, ?, ?, ?)",
            (session_id, snapshot_id, ai_call_id, now()),
        )
        set_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO questions (set_id, position, kind, text) VALUES (?, ?, ?, ?)",
            [(set_id, i, q["kind"], q["question"]) for i, q in enumerate(questions)],
        )
        return set_id


def list_question_sets(session_id: int) -> list[dict]:
    """Newest first, each with its questions in order."""
    with connect() as conn:
        sets = _rows(conn.execute(
            "SELECT * FROM question_sets WHERE session_id = ? ORDER BY id DESC", (session_id,)
        ).fetchall())
        for qs in sets:
            qs["questions"] = _rows(conn.execute(
                "SELECT * FROM questions WHERE set_id = ? ORDER BY position", (qs["id"],)
            ).fetchall())
    return sets


def get_question(question_id: int) -> dict | None:
    with connect() as conn:
        return _row(conn.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone())


def session_id_for_question(question_id: int) -> int:
    with connect() as conn:
        return conn.execute(
            "SELECT qs.session_id FROM questions q JOIN question_sets qs ON qs.id = q.set_id WHERE q.id = ?",
            (question_id,),
        ).fetchone()["session_id"]


def save_answer(question_id: int, answer: str) -> None:
    with connect() as conn:
        conn.execute("UPDATE questions SET answer = ?, answered_at = ? WHERE id = ?",
                     (answer, now(), question_id))


# ---------- export ----------

def dump_all() -> dict:
    tables = ["sessions", "queue_items", "snapshots", "ai_calls", "question_sets", "questions"]
    with connect() as conn:
        return {t: _rows(conn.execute(f"SELECT * FROM {t} ORDER BY id").fetchall()) for t in tables}
