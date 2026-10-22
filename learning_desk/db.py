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
    from .migrations import migrate
    migrate(config.db_path())


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
    return submit_attempt(question_id, answer)


# ---------- export ----------

def dump_all() -> dict:
    tables = ["sessions", "queue_items", "snapshots", "ai_calls", "question_sets", "questions", "resources", "content_versions", "resource_sessions", "summaries", "answer_attempts", "attempt_feedback", "issue_reports", "activity", "quiz_progress", "reader_progress", "lesson_progress", "lesson_notes", "lesson_check_attempts"]
    with connect() as conn:
        return {t: _rows(conn.execute(f"SELECT * FROM {t} ORDER BY id").fetchall()) for t in tables}

# ---------- connected learning ----------

def query(sql, params=()):
    with connect() as conn:
        return _rows(conn.execute(sql, params).fetchall())


def execute(sql, params=()):
    with connect() as conn:
        return conn.execute(sql, params).lastrowid


def save_resource(title, resource_type='reference', url='', tags='', level='introductory',
                  status='Saved', resource_id=None, archived=False):
    if not title.strip():
        raise ValueError('A title is required')
    if resource_type not in ('reference', 'documentation', 'article', 'pasted'):
        raise ValueError('Unknown resource type')
    if level not in ('introductory', 'intermediate', 'advanced') or status not in ('Saved','Reading','Finished'):
        raise ValueError('Invalid level or status')
    values = (title.strip(), url.strip(), resource_type, tags, level, status, int(archived), now())
    if resource_id:
        execute('UPDATE resources SET title=?,url=?,resource_type=?,tags=?,level=?,status=?,archived=?,updated_at=? WHERE id=?', values+(resource_id,))
        return resource_id
    return execute('INSERT INTO resources(title,url,resource_type,tags,level,status,archived,updated_at,created_at) VALUES(?,?,?,?,?,?,?,?,?)', values+(now(),))


def list_resources(search='', archived=False):
    return [r for r in query('SELECT * FROM resources WHERE archived=? ORDER BY updated_at DESC,id DESC',(int(archived),))
            if search.casefold() in ' '.join(str(r[k]) for k in ('title','url','tags','resource_type','level','status')).casefold()]


def add_content(resource_id, text, source_url='', import_note='Pasted by learner', links=None):
    text = text.strip()
    if not text or len(text)>100000:
        raise ValueError('Content must contain 1–100,000 characters')
    digest = hashlib.sha256(text.encode()).hexdigest()
    rows = query('SELECT id FROM content_versions WHERE resource_id=? AND content_hash=? AND source_url=?',(resource_id,digest,source_url))
    if rows:
        return rows[0]['id']
    return execute('INSERT INTO content_versions(resource_id,text,source_url,import_note,content_hash,created_at,links_json) VALUES(?,?,?,?,?,?,?)',
                   (resource_id,text,source_url,import_note,digest,now(),json.dumps(links or [])))


def set_activity(kind, target_id, key=None):
    """The one current activity. Lessons have text ids, stored in target_key (target_id is 0)."""
    if kind not in ('resource','quiz','session','lesson'):
        raise ValueError('Invalid activity')
    if (kind == 'lesson') != (key is not None):
        raise ValueError('Lesson activity needs a lesson id, and only lessons use one')
    execute('INSERT INTO activity(id,kind,target_id,target_key,updated_at) VALUES(1,?,?,?,?) ON CONFLICT(id) DO UPDATE SET kind=excluded.kind,target_id=excluded.target_id,target_key=excluded.target_key,updated_at=excluded.updated_at', (kind,target_id,key,now()))


def attempts(question_id):
    return query('SELECT * FROM answer_attempts WHERE question_id=? ORDER BY id',(question_id,))


def submit_attempt(question_id, answer):
    if not answer.strip():
        raise ValueError('Write or select an answer first')
    with connect() as conn:
        attempt_id = conn.execute('INSERT INTO answer_attempts(question_id,answer,created_at) VALUES(?,?,?)', (question_id,answer,now())).lastrowid
        conn.execute('UPDATE questions SET answer=?,answered_at=? WHERE id=?',(answer,now(),question_id))
    set_activity('quiz', get_question(question_id)['set_id'])
    return attempt_id


# ---------- built-in lessons ----------

def lesson_progress(lesson_id=None):
    """One lesson's progress row (or None), or every row when lesson_id is None."""
    if lesson_id is None:
        return query('SELECT * FROM lesson_progress ORDER BY updated_at DESC, id DESC')
    rows = query('SELECT * FROM lesson_progress WHERE lesson_id=?', (lesson_id,))
    return rows[0] if rows else None


def save_lesson_place(lesson_id, version, view=None, section=None):
    """Remember where the learner is. Creates the row on first visit; never lowers the status."""
    ts = now()
    execute('INSERT INTO lesson_progress(lesson_id,lesson_version,view,section,started_at,updated_at) '
            "VALUES(?,?,COALESCE(?, 'Overview'),COALESCE(?, ''),?,?) ON CONFLICT(lesson_id) DO UPDATE SET "
            'lesson_version=excluded.lesson_version,view=COALESCE(?, view),section=COALESCE(?, section),'
            'updated_at=excluded.updated_at', (lesson_id, version, view, section, ts, ts, view, section))


def set_lesson_status(lesson_id, version, completed):
    save_lesson_place(lesson_id, version)
    execute('UPDATE lesson_progress SET status=?,completed_at=? WHERE lesson_id=?',
            ('completed' if completed else 'started', now() if completed else None, lesson_id))


def lesson_note(lesson_id):
    rows = query('SELECT * FROM lesson_notes WHERE lesson_id=?', (lesson_id,))
    return rows[0] if rows else None


def save_lesson_note(lesson_id, version, text):
    if len(text) > 100000:
        raise ValueError('Notes are limited to 100,000 characters')
    execute('INSERT INTO lesson_notes(lesson_id,text,lesson_version,updated_at) VALUES(?,?,?,?) '
            'ON CONFLICT(lesson_id) DO UPDATE SET text=excluded.text,lesson_version=excluded.lesson_version,'
            'updated_at=excluded.updated_at', (lesson_id, text, version, now()))


def add_check_attempt(lesson_id, version, check_id, answer, correct):
    """Every submission is kept, with the lesson version it was answered against."""
    return execute('INSERT INTO lesson_check_attempts(lesson_id,lesson_version,check_id,answer,correct,created_at) '
                   'VALUES(?,?,?,?,?,?)', (lesson_id, version, check_id, answer, int(bool(correct)), now()))


def check_attempts(lesson_id, check_id=None):
    if check_id is None:
        return query('SELECT * FROM lesson_check_attempts WHERE lesson_id=? ORDER BY id', (lesson_id,))
    return query('SELECT * FROM lesson_check_attempts WHERE lesson_id=? AND check_id=? ORDER BY id',
                 (lesson_id, check_id))
