"""Versioned, additive migrations. All pending steps are rehearsed on a copy before live changes."""

import sqlite3
from contextlib import closing
from pathlib import Path

VERSION = 2


def apply(conn):
    conn.execute("BEGIN IMMEDIATE")
    # These three parent columns must allow resource-only records. Preserve all columns,
    # rows and primary keys; foreign keys are checked after the transaction.
    for table, columns in {
        "ai_calls": ["session_id"],
        "question_sets": ["session_id", "snapshot_id"],
    }.items():
        sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE name=?", (table,)
        ).fetchone()[0]
        for column in columns:
            import re

            sql = re.sub(rf"({column}\s+INTEGER)\s+NOT NULL", r"\1", sql)
        sql = sql.replace(f"CREATE TABLE {table}", f"CREATE TABLE {table}_new", 1)
        conn.execute(sql)
        conn.execute(f"INSERT INTO {table}_new SELECT * FROM {table}")
        conn.execute(f"DROP TABLE {table}")
        conn.execute(f"ALTER TABLE {table}_new RENAME TO {table}")
    additions = {
        "ai_calls": [
            "content_version_id INTEGER REFERENCES content_versions(id)",
            "attempt_id INTEGER REFERENCES answer_attempts(id)",
        ],
        "question_sets": [
            "content_version_id INTEGER REFERENCES content_versions(id)",
            "difficulty TEXT",
            "practice_goal TEXT",
        ],
        "questions": [
            "question_type TEXT DEFAULT 'short_answer'",
            "difficulty TEXT",
            "practice_goal TEXT",
            "options_json TEXT DEFAULT '[]'",
            "expected_answer TEXT DEFAULT ''",
            "refs_json TEXT DEFAULT '[]'",
            "hint TEXT DEFAULT ''",
        ],
    }
    for table, fields in additions.items():
        for field in fields:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {field}")
    script = """
CREATE TABLE resources (
 id INTEGER PRIMARY KEY, title TEXT NOT NULL, url TEXT NOT NULL DEFAULT '',
 resource_type TEXT NOT NULL, tags TEXT NOT NULL DEFAULT '', level TEXT NOT NULL DEFAULT 'introductory',
 status TEXT NOT NULL DEFAULT 'Saved', archived INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE content_versions (
 id INTEGER PRIMARY KEY, resource_id INTEGER NOT NULL REFERENCES resources(id),
 text TEXT NOT NULL, source_url TEXT NOT NULL DEFAULT '', import_note TEXT NOT NULL DEFAULT '',
 content_hash TEXT NOT NULL, links_json TEXT NOT NULL DEFAULT '[]', created_at TEXT NOT NULL);
CREATE TABLE resource_sessions (
 id INTEGER PRIMARY KEY, resource_id INTEGER NOT NULL REFERENCES resources(id),
 session_id INTEGER NOT NULL REFERENCES sessions(id), UNIQUE(resource_id,session_id));
CREATE TABLE summaries (
 id INTEGER PRIMARY KEY, content_version_id INTEGER NOT NULL REFERENCES content_versions(id),
 kind TEXT NOT NULL, ai_call_id INTEGER NOT NULL REFERENCES ai_calls(id),
 result_json TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(content_version_id,kind));
CREATE TABLE answer_attempts (
 id INTEGER PRIMARY KEY, question_id INTEGER NOT NULL REFERENCES questions(id), answer TEXT NOT NULL,
 created_at TEXT NOT NULL, provenance TEXT NOT NULL DEFAULT 'submitted');
CREATE TABLE attempt_feedback (
 id INTEGER PRIMARY KEY, attempt_id INTEGER NOT NULL REFERENCES answer_attempts(id),
 ai_call_id INTEGER REFERENCES ai_calls(id), feedback_json TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE issue_reports (
 id INTEGER PRIMARY KEY, question_id INTEGER NOT NULL REFERENCES questions(id),
 attempt_id INTEGER REFERENCES answer_attempts(id), feedback_id INTEGER REFERENCES attempt_feedback(id),
 text TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE activity (
 id INTEGER PRIMARY KEY CHECK(id=1), kind TEXT NOT NULL, target_id INTEGER NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE reader_progress (
 id INTEGER PRIMARY KEY, resource_id INTEGER NOT NULL UNIQUE REFERENCES resources(id),
 content_version_id INTEGER NOT NULL REFERENCES content_versions(id), mode TEXT NOT NULL DEFAULT 'Original text');
CREATE TABLE quiz_progress (
 id INTEGER PRIMARY KEY, set_id INTEGER NOT NULL UNIQUE REFERENCES question_sets(id),
 position INTEGER NOT NULL DEFAULT 0, finished INTEGER NOT NULL DEFAULT 0);
"""
    for statement in script.split(";"):
        if statement.strip():
            conn.execute(statement)
    # Recover evaluated answers from the recorded request, never from the current answer.
    import json, re

    for call in conn.execute(
        "SELECT id,question_id,request_json,parsed_json,created_at FROM ai_calls WHERE action='answer_feedback' AND question_id IS NOT NULL"
    ).fetchall():
        try:
            req = json.loads(call[2] or "{}")
            content = req["messages"][0]["content"]
            if isinstance(content, list):
                content = "\n".join(x.get("text", "") for x in content)
            matches = re.findall(r"<answer>\n(.*?)\n</answer>", content, re.S)
            if len(matches) != 1:
                continue
        except (KeyError, IndexError, AttributeError, TypeError, ValueError):
            continue
        attempt = conn.execute(
            "INSERT INTO answer_attempts(question_id,answer,created_at,provenance) VALUES(?,?,?,?)",
            (call[1], matches[0], call[4], "recovered from recorded request"),
        ).lastrowid
        conn.execute("UPDATE ai_calls SET attempt_id=? WHERE id=?", (attempt, call[0]))
        if call[3]:
            conn.execute(
                "INSERT INTO attempt_feedback(attempt_id,ai_call_id,feedback_json,created_at) VALUES(?,?,?,?)",
                (attempt, call[0], call[3], call[4]),
            )
    for q in conn.execute(
        "SELECT id,answer,answered_at FROM questions WHERE answer<>''"
    ).fetchall():
        recovered = conn.execute(
            "SELECT answer FROM answer_attempts WHERE question_id=? ORDER BY id DESC LIMIT 1",
            (q[0],),
        ).fetchone()
        if not recovered or recovered[0] != q[1]:
            conn.execute(
                "INSERT INTO answer_attempts(question_id,answer,created_at,provenance) VALUES(?,?,?,?)",
                (
                    q[0],
                    q[1],
                    q[2] or "unknown",
                    "legacy saved answer; earlier submissions unavailable",
                ),
            )
    conn.execute("PRAGMA user_version=1")
    errors = conn.execute("PRAGMA foreign_key_check").fetchall()
    if errors:
        raise RuntimeError(f"Migration foreign key check failed: {errors}")
    conn.commit()


def apply_v2(conn):
    """Curriculum progress. Additive only: new tables and one nullable column."""
    conn.execute("BEGIN IMMEDIATE")
    # Lessons are identified by text ids, so lesson activity stores its id in target_key.
    conn.execute("ALTER TABLE activity ADD COLUMN target_key TEXT")
    script = """
CREATE TABLE lesson_progress (
 id INTEGER PRIMARY KEY, lesson_id TEXT NOT NULL UNIQUE, lesson_version TEXT NOT NULL,
 view TEXT NOT NULL DEFAULT 'Overview', section TEXT NOT NULL DEFAULT '',
 status TEXT NOT NULL DEFAULT 'started' CHECK (status IN ('started', 'completed')),
 started_at TEXT NOT NULL, updated_at TEXT NOT NULL, completed_at TEXT);
CREATE TABLE lesson_notes (
 id INTEGER PRIMARY KEY, lesson_id TEXT NOT NULL UNIQUE, text TEXT NOT NULL DEFAULT '',
 lesson_version TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE lesson_check_attempts (
 id INTEGER PRIMARY KEY, lesson_id TEXT NOT NULL, lesson_version TEXT NOT NULL, check_id TEXT NOT NULL,
 answer TEXT NOT NULL, correct INTEGER NOT NULL CHECK (correct IN (0, 1)), created_at TEXT NOT NULL);
CREATE INDEX lesson_check_attempts_lookup ON lesson_check_attempts(lesson_id, check_id);
"""
    for statement in script.split(";"):
        if statement.strip():
            conn.execute(statement)
    conn.execute("PRAGMA user_version=2")
    errors = conn.execute("PRAGMA foreign_key_check").fetchall()
    if errors:
        raise RuntimeError(f"Migration foreign key check failed: {errors}")
    conn.commit()


def _steps():
    # Looked up at call time so tests can substitute a failing step.
    return [(1, apply), (2, apply_v2)]


def migrate(path):
    path = Path(path)
    with closing(sqlite3.connect(path)) as src:
        current = src.execute("PRAGMA user_version").fetchone()[0]
        pending = [(version, step) for version, step in _steps() if version > current]
        if not pending:
            return
        # One backup of the state before this upgrade, named after the first pending version.
        # SQLite backup includes committed WAL data. Earlier backups are never overwritten.
        first = pending[0][0]
        backup = path.with_name(f"{path.name}.pre-learning-v{first}.bak")
        if backup.exists():
            from datetime import datetime

            backup = path.with_name(
                f"{path.name}.pre-learning-v{first}-{datetime.now().strftime('%Y%m%d%H%M%S%f')}.bak"
            )
        with closing(sqlite3.connect(backup)) as dest:
            src.backup(dest)
        rehearsal = path.with_name(path.name + ".migration-check")
        try:
            with closing(sqlite3.connect(rehearsal)) as test:
                src.backup(test)
                for _, step in pending:
                    step(test)
                if test.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise RuntimeError("Migration integrity check failed")
            for _, step in pending:
                step(src)
        finally:
            rehearsal.unlink(missing_ok=True)
