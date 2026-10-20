"""Ordinary software: storage, queue, search, note sections. No AI involved."""

import importlib
import sqlite3

from learning_desk import config, db, sections

from conftest import make_session


def test_saved_session_survives_restart():
    session_id = make_session()
    db.update_session(session_id, {"notes": "Edited after creation"})

    # Simulate a restart: reload the modules and open the file with a fresh, unrelated connection.
    importlib.reload(config)
    importlib.reload(db)
    row = sqlite3.connect(config.db_path()).execute(
        "SELECT title, notes FROM sessions WHERE id = ?", (session_id,)).fetchone()
    assert row == ("Context windows", "Edited after creation")
    assert db.get_session(session_id)["notes"] == "Edited after creation"


def test_update_session_rejects_unknown_fields():
    session_id = make_session()
    try:
        db.update_session(session_id, {"is_example": 1})
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_queue_changes_persist():
    session_id = make_session()
    item = db.add_queue_item(session_id, "question", "What is a token?", "low")
    db.update_queue_item(item, text="What exactly is a token?", priority="high", kind="task")
    db.update_queue_item(item, status="done")

    importlib.reload(db)
    [saved] = db.list_queue(session_id=session_id)
    assert (saved["text"], saved["priority"], saved["kind"], saved["status"]) == \
        ("What exactly is a token?", "high", "task", "done")
    assert saved["completed_at"]

    db.update_queue_item(item, status="open")
    [reopened] = db.list_queue(status="open")
    assert reopened["id"] == item and reopened["completed_at"] is None
    assert reopened["session_title"] == "Context windows"


def test_queue_sorted_by_manual_priority():
    session_id = make_session()
    db.add_queue_item(session_id, "task", "low one", "low")
    db.add_queue_item(session_id, "task", "high one", "high")
    db.add_queue_item(session_id, "task", "normal one", "normal")
    assert [q["text"] for q in db.list_queue()] == ["high one", "normal one", "low one"]


def test_search_titles_topics_and_notes():
    a = make_session(title="Tokenizers", notes="byte pair encoding")
    b = make_session(title="Embeddings", topic="Vectors", notes="cosine similarity is 100% fun")
    assert [s["id"] for s in db.search_sessions("BYTE PAIR")] == [a]
    assert [s["id"] for s in db.search_sessions("vectors")] == [b]
    assert [s["id"] for s in db.search_sessions("100%")] == [b]  # % is literal, not a wildcard
    assert db.search_sessions("%") == [db.get_session(b)]
    assert db.search_sessions("   ") == []


def test_note_blocks_never_split_inside_code_fences():
    blocks = sections.split_blocks("Intro\n\n```python\na = 1\n\nb = 2\n```\n\nOutro")
    assert blocks == ["Intro", "```python\na = 1\n\nb = 2\n```", "Outro"]


def test_numbered_sections_include_queue_items_and_skip_empty_fields():
    session_id = make_session(sources="")
    db.add_queue_item(session_id, "question", "Open question?")
    done = db.add_queue_item(session_id, "task", "Finished task")
    db.update_queue_item(done, status="done")
    content = sections.build_snapshot_content(db.get_session(session_id), db.list_queue(session_id=session_id))
    numbered = sections.number_sections(content)
    labels = [s["label"] for s in numbered]
    assert labels[0] == "What I want to understand"
    assert "Source URLs (not fetched; listed by me)" not in labels
    assert labels[-1] == "My unresolved question"
    assert "Finished task" not in [s["text"] for s in numbered]
    assert [s["id"] for s in numbered] == list(range(1, len(numbered) + 1))
