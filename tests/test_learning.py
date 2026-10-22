import socket
import sqlite3
import pytest
from learning_desk import db, importer


def test_library_versions_links_archive_and_restart():
    rid = db.save_resource("Functions", "documentation", tags="python")
    v1 = db.add_content(rid, "Functions take arguments.")
    v2 = db.add_content(rid, "Functions take arguments and return values.")
    assert v1 != v2
    assert db.add_content(rid, "Functions take arguments.") == v1
    sid = db.create_session(title="My experiment")
    db.execute(
        "INSERT INTO resource_sessions(resource_id,session_id) VALUES(?,?)", (rid, sid)
    )
    db.set_activity("resource", rid)
    db.init_db()
    assert db.query("SELECT * FROM activity")[0]["target_id"] == rid
    assert len(db.list_resources("PYTHON")) == 1
    db.save_resource("Functions", "documentation", resource_id=rid, archived=True)
    assert not db.list_resources()
    assert len(db.query("SELECT * FROM content_versions")) == 2
    assert db.query("PRAGMA foreign_key_check") == []


def test_legacy_migration_rehearsed_and_preserves_rows(tmp_path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as conn:
        conn.executescript(db.SCHEMA)
        conn.execute(
            "INSERT INTO sessions(id,title,created_at,updated_at) VALUES(42,'Old notes','then','then')"
        )
    from learning_desk.migrations import migrate

    migrate(path)
    with sqlite3.connect(path) as conn:
        assert (
            conn.execute("SELECT title FROM sessions WHERE id=42").fetchone()[0]
            == "Old notes"
        )
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
    assert path.with_name(path.name + ".pre-learning-v1.bak").exists()
    assert not path.with_name(path.name + ".migration-check").exists()
    migrate(path)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.org",
        "http://user:pass@example.org",
        "http://example.org:8000",
    ],
)
def test_import_rejects_invalid_urls(url):
    with pytest.raises(ValueError):
        importer.destination(url)


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",
        "10.0.0.1",
        "169.254.169.254",
        "::1",
        "192.168.1.1",
        "0.0.0.0",
        "224.0.0.1",
    ],
)
def test_import_rejects_private_destinations(monkeypatch, ip):
    monkeypatch.setattr(
        socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", (ip, 80))]
    )
    with pytest.raises(ValueError):
        importer.destination("https://example.org")


def test_summary_explicit_cached_and_versioned(fake):
    from learning_desk import learning

    rid = db.save_resource("Functions", "pasted")
    v1 = db.add_content(
        rid, "A function can return a value.\n\nA missing return yields None."
    )
    payload = {
        "source_summary": [
            {
                "text": "Functions may return a value; without a return they yield None.",
                "section_refs": [1, 2],
            }
        ],
        "added_explanation": "",
        "example": "",
    }
    fake.reply(payload)
    assert learning.summarize(v1, "quick").ok
    assert learning.summarize(v1, "quick").ok
    assert len(fake.requests) == 1
    v2 = db.add_content(rid, "An updated source with a changed qualification.")
    assert not db.query("SELECT * FROM summaries WHERE content_version_id=?", (v2,))
    assert db.query("SELECT * FROM ai_calls")[0]["session_id"] is None
    assert db.query("SELECT * FROM ai_calls")[0]["content_version_id"] == v1
    assert "missing return" in fake.requests[0]["messages"][0]["content"]


def test_summary_invalid_citation_is_logged_but_not_saved(fake):
    from learning_desk import learning

    rid = db.save_resource("A", "pasted")
    vid = db.add_content(rid, "Source data.")
    fake.reply(
        {
            "source_summary": [{"text": "Unsupported claim", "section_refs": [999]}],
            "added_explanation": "",
            "example": "",
        }
    )
    assert not learning.summarize(vid, "quick").ok
    assert not db.query("SELECT * FROM summaries")
    assert db.query("SELECT * FROM ai_calls")[0]["status"] == "error"


def quiz_payload():
    return {
        "questions": [
            {
                "question": f"Question {i}?",
                "question_type": "multiple_choice" if i == 0 else "short_answer",
                "options": ["Return", "Print", "Store", "Loop"] if i == 0 else [],
                "expected_answer": "Return"
                if i == 0
                else "Describe the return value and its qualifications.",
                "section_refs": [1],
                "hint": "Consider the return statement.",
            }
            for i in range(3)
        ]
    }


def test_quiz_grounded_attempt_feedback_pairing(fake):
    from learning_desk import learning, export

    rid = db.save_resource("Return values", "pasted")
    vid = db.add_content(rid, "A return statement returns a value.")
    fake.reply(quiz_payload())
    assert learning.generate_quiz(
        version_id=vid, difficulty="advanced", practice_goal="Diagnose"
    ).ok
    qs = db.query("SELECT * FROM question_sets")[0]
    assert qs["session_id"] is None and qs["content_version_id"] == vid
    q = db.query("SELECT * FROM questions ORDER BY id")[0]
    a1 = db.submit_attempt(q["id"], "Print")
    f1 = learning.grade(a1)
    a2 = db.submit_attempt(q["id"], "Return")
    f2 = learning.grade(a2)
    assert "Does not match" in f1["feedback"] and f2["feedback"].startswith("Matches")
    assert len(fake.requests) == 1
    q2 = db.query("SELECT * FROM questions ORDER BY id")[1]
    a3 = db.submit_attempt(q2["id"], "My original response")
    db.add_content(rid, "Newer material must not be sent.")
    fake.reply(
        {
            "feedback": "Compare your answer to the return statement.",
            "section_refs": [1],
            "uncertainty": "The rubric may be incomplete.",
        }
    )
    learning.grade(a3)
    assert "Newer material" not in fake.requests[-1]["messages"][0]["content"]
    assert "My original response" in fake.requests[-1]["messages"][0]["content"]
    a4 = db.submit_attempt(q2["id"], "My revised response")
    assert db.query("SELECT * FROM ai_calls ORDER BY id DESC")[0]["attempt_id"] == a3
    assert not db.query("SELECT * FROM attempt_feedback WHERE attempt_id=?", (a4,))
    learning.grade(a3)
    assert len(fake.requests) == 2
    md = export.resource_markdown(rid)
    assert f"for attempt {a3}" in md and "A return statement returns a value." in md


def test_old_feedback_uses_question_snapshot_and_exports_exact_attempt(fake):
    from learning_desk import ai, export
    from conftest import make_session, QUESTIONS_OK, FEEDBACK_OK

    sid = make_session(notes="ORIGINAL SOURCE")
    fake.reply(QUESTIONS_OK)
    ai.generate_questions(sid)
    q = db.list_question_sets(sid)[0]["questions"][0]
    db.update_session(sid, {"notes": "LATEST NOTES MUST NOT BE USED"})
    db.save_answer(q["id"], "OLD ANSWER")
    fake.reply(FEEDBACK_OK)
    result = ai.answer_feedback(q["id"])
    db.save_answer(q["id"], "LATEST ANSWER")
    assert "ORIGINAL SOURCE" in fake.requests[-1]["messages"][0]["content"]
    assert (
        "LATEST NOTES MUST NOT BE USED"
        not in fake.requests[-1]["messages"][0]["content"]
    )
    call = db.get_ai_call(result.call_id)
    a = db.query("SELECT * FROM answer_attempts WHERE id=?", (call["attempt_id"],))[0]
    assert a["answer"] == "OLD ANSWER"
    md = export.session_markdown(sid)
    assert "evaluated answer:\n\nOLD ANSWER" in md
    assert "Original source snapshots for citations" in md and "ORIGINAL SOURCE" in md


def _page(name, **state):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_string(
        f"from learning_desk.ui import {name}\n{name}.render()"
        if name == "library"
        else f"from learning_desk.ui import today\ntoday.{name}()",
        default_timeout=30,
    )
    for key, value in state.items():
        at.session_state[key] = value
    return at.run()


def test_reader_navigation_and_resume_without_calls(fake):
    rid = db.save_resource("Reader source", "pasted")
    db.add_content(rid, "A function returns a value.\n\nNo return yields None.")
    db.set_activity("resource", rid)
    at = _page("library", resource_id=rid)
    assert not at.exception
    next(r for r in at.radio if r.label == "Read").set_value("Quick read")
    at.run()
    assert not at.exception and not fake.requests
    fake.reply(
        {
            "source_summary": [
                {"text": "A function can return a value.", "section_refs": [1]}
            ],
            "added_explanation": "",
            "example": "",
        }
    )
    next(b for b in at.button if b.label == "Generate quick read").click()
    at.run()
    at.run()
    assert not at.exception and len(fake.requests) == 1
    next(r for r in at.radio if r.label == "Read").set_value("Original text")
    at.run()
    next(r for r in at.radio if r.label == "Read").set_value("Quick read")
    at.run()
    assert len(fake.requests) == 1
    fresh = _page("today")
    assert not fresh.exception
    assert any(b.label == "Continue learning" for b in fresh.button)
    assert any("Reader source" in m.value for m in fresh.markdown)


def test_one_question_ui_and_restart_attempt_history(fake):
    from learning_desk import learning

    rid = db.save_resource("Quiz source", "pasted")
    vid = db.add_content(rid, "A return statement returns a value.")
    fake.reply(quiz_payload())
    learning.generate_quiz(version_id=vid)
    qs = db.query("SELECT * FROM question_sets")[0]
    at = _page("library", active_quiz=qs["id"])
    assert not at.exception
    assert "Question 0?" in " ".join(m.value for m in at.markdown)
    assert "Question 1?" not in " ".join(m.value for m in at.markdown)
    next(r for r in at.radio if r.label == "Your answer").set_value("Return")
    next(b for b in at.button if b.label == "Submit answer").click()
    at.run()
    assert not at.exception
    assert len(db.query("SELECT * FROM answer_attempts")) == 1
    next(b for b in at.button if b.label == "Next question").click()
    at.run()
    assert not at.exception
    assert "Question 1?" in " ".join(m.value for m in at.markdown)
    fresh = _page("library", active_quiz=qs["id"])
    assert not fresh.exception
    assert "Question 1?" in " ".join(m.value for m in fresh.markdown)
    assert len(fake.requests) == 1


class MockResponse:
    def __init__(self, status=200, headers=None, body=b""):
        self.status = status
        self.headers = headers or {}
        self.body = body

    def getheader(self, key, default=None):
        return self.headers.get(key, default)

    def read(self, size):
        chunk = self.body[:size]
        self.body = self.body[size:]
        return chunk


def mock_http(monkeypatch, responses):
    class Sock:
        def close(self):
            pass

    class Conn:
        def __init__(self, *a, **k):
            self.sock = None

        def request(self, *a, **k):
            pass

        def getresponse(self):
            return responses.pop(0)

        def close(self):
            pass

    monkeypatch.setattr(importer.socket, "create_connection", lambda *a, **k: Sock())
    monkeypatch.setattr(
        importer.socket,
        "getaddrinfo",
        lambda host, *a, **k: [
            (
                2,
                1,
                6,
                "",
                ("127.0.0.1" if host == "private.test" else "93.184.216.34", 80),
            )
        ],
    )
    monkeypatch.setattr(importer.http.client, "HTTPConnection", Conn)


def test_redirect_target_revalidated(monkeypatch):
    responses = [MockResponse(302, {"Location": "http://private.test/secret"})]
    mock_http(monkeypatch, responses)
    with pytest.raises(ValueError, match="blocked"):
        importer.import_url("http://public.test/article")


@pytest.mark.parametrize(
    "response,message",
    [
        (MockResponse(401), "HTTP 401"),
        (MockResponse(200, {"Content-Type": "application/pdf"}), "Only HTML"),
        (
            MockResponse(
                200, {"Content-Type": "text/html", "Content-Length": "2000001"}
            ),
            "too large",
        ),
        (
            MockResponse(200, {"Content-Type": "text/html"}, b"<p>Sign in</p>"),
            "Too little",
        ),
        (
            MockResponse(
                200, {"Content-Type": "text/html", "Content-Encoding": "gzip"}
            ),
            "Compressed",
        ),
    ],
)
def test_import_graceful_failures(monkeypatch, response, message):
    mock_http(monkeypatch, [response])
    with pytest.raises(ValueError, match=message):
        importer.import_url("http://public.test/page")


def test_import_extracts_only_text_and_real_links(monkeypatch):
    html = (
        "<html><script>secret_script()</script><nav>navigation</nav><article><p>"
        + ("Useful text about functions. " * 15)
        + '</p><a href="/docs">Further documentation</a><a href="javascript:alert(1)">bad</a></article></html>'
    ).encode()
    mock_http(monkeypatch, [MockResponse(200, {"Content-Type": "text/html"}, html)])
    imported = importer.import_url("http://public.test/page")
    assert "Useful text" in imported["text"]
    assert (
        "secret_script" not in imported["text"] and "navigation" not in imported["text"]
    )
    assert imported["links"] == ["http://public.test/docs"]
    assert "completeness" in imported["note"]


def test_migration_recovers_only_supported_answer_associations(tmp_path):
    import json
    from learning_desk.migrations import migrate

    path = tmp_path / "history.db"
    with sqlite3.connect(path) as conn:
        conn.executescript(db.SCHEMA)
        conn.execute(
            "INSERT INTO sessions(id,title,created_at,updated_at) VALUES(1,'History','t','t')"
        )
        conn.execute(
            "INSERT INTO snapshots(id,session_id,content_hash,content_json,created_at) VALUES(1,1,'h','{}','t')"
        )
        conn.execute(
            "INSERT INTO ai_calls(id,session_id,action,prompt_version,status,created_at) VALUES(1,1,'questions','q','ok','t')"
        )
        conn.execute(
            "INSERT INTO question_sets(id,session_id,snapshot_id,ai_call_id,created_at) VALUES(1,1,1,1,'t')"
        )
        conn.execute(
            "INSERT INTO questions(id,set_id,position,kind,text,answer,answered_at) VALUES(1,1,0,'explanation','Q','Latest answer','t2')"
        )
        request = json.dumps(
            {
                "messages": [
                    {"content": "<answer>\nEvaluated historical answer\n</answer>"}
                ]
            }
        )
        conn.execute(
            "INSERT INTO ai_calls(id,session_id,question_id,action,prompt_version,status,request_json,parsed_json,created_at) VALUES(2,1,1,'answer_feedback','f','ok',?,'{}','t1')",
            (request,),
        )
        conn.execute(
            "INSERT INTO ai_calls(id,session_id,question_id,action,prompt_version,status,request_json,created_at) VALUES(3,1,1,'answer_feedback','f','ok','{}','t1')"
        )
    migrate(path)
    with sqlite3.connect(path) as conn:
        linked = conn.execute(
            "SELECT a.answer FROM answer_attempts a JOIN ai_calls c ON c.attempt_id=a.id WHERE c.id=2"
        ).fetchone()[0]
        assert linked == "Evaluated historical answer"
        assert (
            conn.execute("SELECT attempt_id FROM ai_calls WHERE id=3").fetchone()[0]
            is None
        )
        assert (
            conn.execute(
                "SELECT answer FROM answer_attempts ORDER BY id DESC LIMIT 1"
            ).fetchone()[0]
            == "Latest answer"
        )


def test_reader_remembers_version_and_view(fake):
    from learning_desk.ui.today import activity_label

    rid = db.save_resource("Versions", "pasted")
    old = db.add_content(rid, "Old version.")
    db.add_content(rid, "New version.")
    db.execute(
        "INSERT INTO reader_progress(resource_id,content_version_id,mode) VALUES(?,?,?)",
        (rid, old, "Quick read"),
    )
    at = _page("library", resource_id=rid)
    assert not at.exception
    assert next(s for s in at.selectbox if s.label == "Content version").value == old
    assert next(r for r in at.radio if r.label == "Read").value == "Quick read"
    assert not fake.requests
    assert activity_label("resource", rid) == "Versions"
    db.save_resource("Versions", "pasted", resource_id=rid, status="Finished")
    assert activity_label("resource", rid) is None


def test_failed_rehearsal_does_not_change_original(tmp_path, monkeypatch):
    from learning_desk import migrations

    path = tmp_path / "original.db"
    with sqlite3.connect(path) as conn:
        conn.executescript(db.SCHEMA)
        conn.execute(
            "INSERT INTO sessions(id,title,created_at,updated_at) VALUES(1,'Keep this','t','t')"
        )
    before = path.read_bytes()

    def fail(conn):
        conn.execute("BEGIN")
        conn.execute("UPDATE sessions SET title='incorrect'")
        raise RuntimeError("Simulated migration failure")

    monkeypatch.setattr(migrations, "apply", fail)
    with pytest.raises(RuntimeError, match="Simulated"):
        migrations.migrate(path)
    assert path.read_bytes() == before
    assert path.with_name(path.name + ".pre-learning-v1.bak").exists()


def test_unsafe_source_rendering_and_no_opening_calls(fake):
    rid = db.save_resource("Untrusted", "pasted")
    db.add_content(
        rid,
        '<script>alert(1)</script>\n\n![tracker](https://example.org/tracker.png)\n\n```python\nraise Exception("Do not execute")\n```',
    )
    at = _page("library", resource_id=rid)
    assert not at.exception and not fake.requests
    source = " ".join(m.value for m in at.markdown)
    assert r"\![tracker]" in source
    assert not any(m.proto.allow_html for m in at.markdown)


def test_generation_bounds_fail_before_provider_call(fake):
    from learning_desk import learning

    rid = db.save_resource("Long", "pasted")
    vid = db.add_content(rid, "\n\n".join("Passage " + str(i) for i in range(501)))
    with pytest.raises(ValueError, match="too long"):
        learning.summarize(vid, "quick")
    assert not fake.requests


def test_feedback_cache_and_legacy_unknown_labels(fake):
    from learning_desk import ai
    from conftest import make_session, QUESTIONS_OK, FEEDBACK_OK

    sid = make_session()
    fake.reply(QUESTIONS_OK)
    ai.generate_questions(sid)
    qs = db.list_question_sets(sid)[0]
    q = qs["questions"][0]
    assert qs["difficulty"] is None and q["practice_goal"] is None
    db.save_answer(q["id"], "An answer")
    fake.reply(FEEDBACK_OK)
    first = ai.answer_feedback(q["id"])
    second = ai.answer_feedback(q["id"])
    assert first.call_id == second.call_id and len(fake.requests) == 2


def test_quiz_keys_hidden_even_in_technical_inspection(fake):
    from learning_desk import learning

    rid = db.save_resource("Key safety", "pasted")
    vid = db.add_content(rid, "A return statement returns a value.")
    payload = quiz_payload()
    payload["questions"][0]["expected_answer"] = "secret-key-option"
    payload["questions"][0]["options"][0] = "secret-key-option"
    fake.reply(payload)
    learning.generate_quiz(version_id=vid)
    qs = db.query("SELECT * FROM question_sets")[0]
    at = _page("library", active_quiz=qs["id"])
    assert not at.exception
    assert not any("secret-key-option" in c.value for c in at.code)
    assert any("hidden until this quiz is finished" in c.value for c in at.caption)
    db.execute("UPDATE quiz_progress SET finished=1 WHERE set_id=?", (qs["id"],))
    at.run()
    assert not at.exception
    assert any("secret-key-option" in c.value for c in at.code)


def test_notebook_quiz_saves_draft_before_snapshot(fake):
    from streamlit.testing.v1 import AppTest
    from conftest import make_session

    sid = make_session(notes="Original saved notes")
    at = AppTest.from_string(
        "from learning_desk.ui import session_page\nsession_page.render()",
        default_timeout=30,
    )
    at.session_state["current_session_id"] = sid
    at.run()
    next(
        t for t in at.text_area if t.label == "Notes, observations and code excerpts"
    ).input("Unsaved notebook quiz source")
    at.run()
    fake.reply(quiz_payload())
    next(b for b in at.button if b.label == "Start three-question quiz").click()
    at.run()
    assert not at.exception
    assert db.get_session(sid)["notes"] == "Unsaved notebook quiz source"
    qs = db.list_question_sets(sid)[0]
    assert (
        db.get_snapshot(qs["snapshot_id"])["content"]["notes"]
        == "Unsaved notebook quiz source"
    )
    assert "Unsaved notebook quiz source" in fake.requests[-1]["messages"][0]["content"]


def test_oversized_source_buttons_show_message_without_calls(fake):
    rid = db.save_resource("Large source", "pasted")
    db.add_content(rid, "\n\n".join("Passage " + str(i) for i in range(501)))
    at = _page("library", resource_id=rid)
    next(r for r in at.radio if r.label == "Read").set_value("Quick read")
    at.run()
    next(b for b in at.button if b.label == "Generate quick read").click()
    at.run()
    assert not at.exception
    assert any("too long" in w.value for w in at.warning)
    next(r for r in at.radio if r.label == "Read").set_value("Check my understanding")
    at.run()
    next(b for b in at.button if b.label == "Start three-question quiz").click()
    at.run()
    assert not at.exception
    assert any("too long" in w.value for w in at.warning)
    assert not fake.requests
