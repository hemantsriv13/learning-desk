"""Built-in curriculum: content integrity, visual calculations, lesson persistence and pages.
The conftest fake provider fails any test that makes a model call it did not expect."""

import json
import math
import re
import sqlite3

import pytest
from streamlit.testing.v1 import AppTest

from learning_desk import curriculum, db, visuals
from learning_desk.curriculum.model import VIEWS


# ---------------------------------------------------------------- content integrity

def test_collection_is_consistent_and_substantial():
    assert curriculum.PROBLEMS == []
    assert len(curriculum.TOPICS) == 10
    assert len(curriculum.LESSONS) >= 12
    # Every topic has at least one finished lesson, and outlines are never presented as lessons.
    for topic in curriculum.TOPICS:
        assert any(lid in curriculum.LESSONS for lid in topic.lessons), topic.id
    assert not set(curriculum.LESSONS) & set(curriculum.OUTLINES)
    assert all(o.status == "outline" for o in curriculum.OUTLINES.values())


@pytest.mark.parametrize("lesson", list(curriculum.LESSONS.values()), ids=lambda l: l.id)
def test_each_lesson_has_every_required_part(lesson):
    assert lesson.objective and lesson.intro and len(lesson.sections) >= 2
    assert lesson.worked_example.body and lesson.misconception.body
    assert lesson.misconception.title.startswith("Misconception")
    assert lesson.activity.steps and lesson.checks and lesson.citations
    assert lesson.overview_visual in visuals.VISUALS
    assert lesson.provenance.startswith("Original educational content") and lesson.checked
    assert len(curriculum.lesson_markdown(lesson).split()) > 900  # substantive, not a stub
    for section in lesson.walkthrough():
        assert "$" not in section.body  # Streamlit Markdown would render it as maths
        if section.code:
            lines = section.code.source.splitlines()
            assert all(1 <= n <= len(lines) for n, _ in section.code.notes)
            if section.code.language == "json":
                json.loads(section.code.source)
        if section.table:
            assert all(len(row) == len(section.table.columns) for row in section.table.rows)


def test_sources_are_dated_https_or_repository_code():
    for source in curriculum.SOURCES.values():
        assert source.checked, f"{source.id} would be shown as unverified"
        if source.kind == "This app's code":
            assert source.url.startswith("learning_desk/")
        else:
            assert source.url.startswith("https://")
    used = {c.source for l in curriculum.LESSONS.values() for c in (*l.citations, *l.further_reading)}
    assert used == set(curriculum.SOURCES)  # no orphaned or missing sources


def test_app_code_sources_point_at_real_files():
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    for source in curriculum.SOURCES.values():
        if source.kind == "This app's code":
            assert (root / source.url).is_file(), source.url


def test_claims_about_this_app_match_the_code():
    from learning_desk import config, learning, provider

    assert config.DEFAULT_TIMEOUT_SECONDS == 180
    from pathlib import Path
    assert "max_retries=0" in Path(provider.__file__).read_text(encoding="utf-8")
    sent = learning.schema(learning.PracticeSet)
    assert "maxLength" not in json.dumps(sent) and "minLength" not in json.dumps(sent)
    request = provider.build_request(system="s", user_text="u", schema={})
    assert not {"temperature", "top_p", "top_k"} & set(request)
    assert request["output_config"]["format"]["type"] == "json_schema"


def test_search_finds_lessons_by_topic_words():
    assert "embeddings-similarity" in {l.id for l in curriculum.search("cosine")}
    assert curriculum.search("") == []


# ---------------------------------------------------------------- visual calculations

def test_softmax_temperature_and_truncation():
    logits = [s for _, s in visuals.NEXT_TOKEN_LOGITS]
    for t in (0.3, 1.0, 2.0):
        probs = visuals.softmax(logits, t)
        assert math.isclose(sum(probs), 1.0)
        assert sorted(range(len(probs)), key=lambda i: -probs[i]) == list(range(len(probs)))  # order kept
    assert visuals.softmax(logits, 0) == [1.0] + [0.0] * (len(logits) - 1)
    assert visuals.softmax(logits, 0.5)[0] > visuals.softmax(logits, 1.0)[0] > visuals.softmax(logits, 2.0)[0]
    top2 = visuals.filter_top_k(visuals.softmax(logits), 2)
    assert sum(p > 0 for p in top2) == 2 and math.isclose(sum(top2), 1.0)
    nucleus = visuals.filter_top_p(visuals.softmax(logits), 0.9)
    kept = [p for p in visuals.softmax(logits) if p > 0][:sum(p > 0 for p in nucleus)]
    assert sum(kept) >= 0.9 and sum(kept[:-1]) < 0.9  # the smallest set reaching p


def test_cosine_and_lesson_worked_examples():
    assert math.isclose(visuals.cosine((1, 2, 0), (2, 4, 1)), 0.976, abs_tol=5e-4)
    assert visuals.cosine((1, 2, 0), (-2, 1, 0)) == 0
    with pytest.raises(ValueError):
        visuals.cosine((0, 0), (1, 1))
    # The attention lesson's hand calculation.
    q, keys = (1.0, 0.5), [(1, 0), (0, 1), (1, 1)]
    weights = visuals.softmax([sum(a * b for a, b in zip(q, k)) / math.sqrt(2) for k in keys])
    assert [round(w, 3) for w in weights] == [0.32, 0.225, 0.456]


def test_attention_rows_are_causal_distributions():
    for i, row in enumerate(visuals.attention_weights()):
        assert math.isclose(sum(row), 1.0)
        assert all(w == 0 for w in row[i + 1:])
    it = visuals.ATTENTION_TOKENS.index("it")
    row = visuals.attention_weights()[it]
    assert max(range(len(row)), key=row.__getitem__) == visuals.ATTENTION_TOKENS.index("animal")


def test_alt_texts_state_the_computed_numbers():
    probs = visuals.softmax([s for _, s in visuals.NEXT_TOKEN_LOGITS])
    alt = visuals.VISUALS["sampling"].alt
    for (token, _), p in zip(visuals.NEXT_TOKEN_LOGITS, probs):
        assert f"{token} {visuals.pct(p)}" in alt
    assert visuals.pct(0.002) == "under 1%"
    parts = visuals.latency_breakdown(3000, 500)
    assert f"{sum(ms for _, ms in parts) / 1000:.1f} seconds" in visuals.VISUALS["latency_timeline"].alt
    assert "illustrative" in visuals.VISUALS["embedding_map"].illustrative.lower() or \
        "toy" in visuals.VISUALS["embedding_map"].illustrative.lower()
    assert "dimensions" in visuals.VISUALS["embedding_map"].illustrative


@pytest.mark.parametrize("vid", [v for v, vis in visuals.VISUALS.items() if vis.render])
def test_every_diagram_is_accessible_svg(vid):
    svg = visuals.VISUALS[vid].render()
    assert svg.startswith("<svg") and 'role="img"' in svg and "viewBox" in svg
    assert re.search(r"<title id=\"[^\"]+\">[^<]+</title><desc id=\"[^\"]+\">[^<]+</desc>", svg)
    assert visuals.VISUALS[vid].alt and visuals.VISUALS[vid].notice


def test_svg_text_is_escaped():
    assert "&lt;b&gt;" in visuals._t(0, 0, "<b>")


# ---------------------------------------------------------------- storage

def test_v1_database_migrates_to_lesson_tables_and_keeps_rows(tmp_path):
    from learning_desk.migrations import VERSION, apply, migrate

    path = tmp_path / "v1.db"
    with sqlite3.connect(path) as conn:
        conn.executescript(db.SCHEMA)
        conn.execute("INSERT INTO sessions(id,title,created_at,updated_at) VALUES(7,'Kept','t','t')")
    with sqlite3.connect(path) as conn:
        apply(conn)  # an existing installation at version 1
        conn.execute("INSERT INTO activity(id,kind,target_id,updated_at) VALUES(1,'session',7,'t')")
        conn.commit()
    migrate(path)
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == VERSION == 2
        assert conn.execute("SELECT title FROM sessions WHERE id=7").fetchone()[0] == "Kept"
        assert conn.execute("SELECT kind,target_id,target_key FROM activity").fetchone() == ("session", 7, None)
        for table in ("lesson_progress", "lesson_notes", "lesson_check_attempts"):
            conn.execute(f"SELECT * FROM {table}")
    assert path.with_name(path.name + ".pre-learning-v2.bak").exists()
    migrate(path)  # idempotent


def test_lesson_place_notes_and_attempts_persist():
    db.save_lesson_place("json-basics", "v1", view="Walkthrough", section="schema")
    db.set_lesson_status("json-basics", "v1", True)
    db.save_lesson_place("json-basics", "v1", view="Sources")  # moving around keeps completion and section
    row = db.lesson_progress("json-basics")
    assert (row["view"], row["section"], row["status"]) == ("Sources", "schema", "completed")
    db.save_lesson_note("json-basics", "v1", "My note")
    db.save_lesson_note("json-basics", "v1", "Edited note")
    assert db.lesson_note("json-basics")["text"] == "Edited note"
    db.add_check_attempt("json-basics", "v1", "type", "string", False)
    db.add_check_attempt("json-basics", "v1", "type", "date", True)
    attempts = db.check_attempts("json-basics", "type")
    assert [a["correct"] for a in attempts] == [0, 1] and all(a["lesson_version"] == "v1" for a in attempts)
    db.set_activity("lesson", 0, key="json-basics")
    db.init_db()
    assert db.query("SELECT kind,target_key FROM activity")[0] == {"kind": "lesson", "target_key": "json-basics"}
    with pytest.raises(ValueError):
        db.set_activity("lesson", 0)
    exported = db.dump_all()
    assert exported["lesson_notes"][0]["text"] == "Edited note" and len(exported["lesson_check_attempts"]) == 2


# ---------------------------------------------------------------- pages

def _lesson(lesson_id, **state):
    at = AppTest.from_string("from learning_desk import db\nfrom learning_desk.ui import learn\n"
                             "db.init_db()\nlearn.lesson_page()", default_timeout=60)
    at.session_state["lesson_id"] = lesson_id
    for key, value in state.items():
        at.session_state[key] = value
    return at.run()


def test_every_lesson_view_renders_without_model_calls(fake):
    for lesson_id in curriculum.LESSONS:
        for view in VIEWS:
            at = _lesson(lesson_id, **{f"view_{lesson_id}": view})
            assert not at.exception, (lesson_id, view)
            assert not any(m.proto.allow_html for m in at.markdown)
    assert fake.requests == []


def test_view_section_and_notes_survive_a_restart(fake):
    lid = "tokens-context-window"
    at = _lesson(lid)
    next(s for s in at.button_group if s.label == "View").set_value("Walkthrough")
    at.run()
    next(b for b in at.button if b.label.startswith("Next:")).click()
    at.run()
    next(t for t in at.text_area if t.label == "My notes on this lesson").input("Window includes output")
    at.run()
    fresh = _lesson(lid)  # a new browser session reading the same database
    assert fresh.session_state[f"view_{lid}"] == "Walkthrough"
    assert fresh.session_state[f"section_{lid}"] == curriculum.LESSONS[lid].sections[1].id
    assert next(t for t in fresh.text_area if t.label == "My notes on this lesson").value == "Window includes output"
    assert db.query("SELECT * FROM activity")[0]["target_key"] == lid
    assert fake.requests == []


def test_quick_check_records_every_attempt_and_points_back_to_the_section(fake):
    lesson = curriculum.LESSONS["json-basics"]
    check = lesson.checks[0]
    wrong = next(o for o in check.options if o != check.answer)
    at = _lesson(lesson.id, **{f"view_{lesson.id}": "Try it"})
    next(r for r in at.radio if r.label == "Your answer").set_value(wrong)
    next(b for b in at.button if b.label == "Check answer").click()
    at.run()
    assert any("expected answer" in w.value for w in at.warning)
    assert any(b.label.startswith("Revisit:") for b in at.button)
    next(r for r in at.radio if r.label == "Your answer").set_value(check.answer)
    next(b for b in at.button if b.label == "Check answer").click()
    at.run()
    assert any(s.value.startswith("Yes.") for s in at.success)
    assert [a["correct"] for a in db.check_attempts(lesson.id, check.id)] == [0, 1]
    next(b for b in at.button if b.label.startswith("Revisit:")).click()
    at.run()
    assert at.session_state[f"view_{lesson.id}"] == "Walkthrough"
    assert at.session_state[f"section_{lesson.id}"] == check.section
    assert fake.requests == []


def test_outline_is_never_shown_as_a_finished_lesson(fake):
    outline_id = next(iter(curriculum.OUTLINES))
    at = _lesson(outline_id)
    assert not at.exception
    assert any("not written yet" in i.value for i in at.info)
    assert not any(b.label == "View" for b in at.button_group)


def test_explore_and_topic_pages_label_outlines(fake):
    at = AppTest.from_string("from learning_desk import db\nfrom learning_desk.ui import learn\n"
                             "db.init_db()\nlearn.explore()", default_timeout=60)
    at.session_state["explore_topic"] = "python"
    at.run()
    assert not at.exception
    topic = curriculum.TOPIC_BY_ID["python"]
    ready = [lid for lid in topic.lessons if lid in curriculum.LESSONS]
    outlines = [lid for lid in topic.lessons if lid in curriculum.OUTLINES]
    # Only finished lessons can be opened; every outline says it is not written.
    assert sum(b.label in ("Open lesson", "Continue lesson", "Review lesson") for b in at.button) == len(ready)
    assert sum("not yet written" in c.value for c in at.caption) == len(outlines)
    at = AppTest.from_string("from learning_desk import db\nfrom learning_desk.ui import learn\n"
                             "db.init_db()\nlearn.explore()", default_timeout=60).run()
    at.text_input[0].input("retrieval").run()
    assert any("lesson(s) match" in c.value for c in at.caption)


def test_save_lesson_to_library_stores_text_only_once(fake):
    from learning_desk.ui.learn import save_to_library

    lesson = curriculum.LESSONS["retrieval-basics"]
    rid = save_to_library(lesson)
    assert save_to_library(lesson) == rid
    [version] = db.query("SELECT * FROM content_versions WHERE resource_id=?", (rid,))
    assert lesson.version in version["import_note"] and lesson.objective in version["text"]
    assert "lesson:retrieval-basics" in db.query("SELECT tags FROM resources WHERE id=?", (rid,))[0]["tags"]
    assert fake.requests == []


def test_home_continues_a_lesson_and_library_search_finds_lessons(fake):
    db.save_lesson_place("attention-basics", "v", view="Try it")
    db.set_activity("lesson", 0, key="attention-basics")
    home = AppTest.from_string("from learning_desk import db\nfrom learning_desk.ui import today\n"
                               "db.init_db()\ntoday.today()", default_timeout=60).run()
    assert not home.exception
    assert any("Attention: how tokens use other tokens" in m.value for m in home.markdown)
    assert any("Try it" in c.value for c in home.caption)
    assert any(b.label == "Continue learning" for b in home.button)
    library = AppTest.from_string("from learning_desk.ui import library\nlibrary.render()", default_timeout=60).run()
    next(t for t in library.text_input if t.label == "Search resources").input("tokens").run()
    assert any("Built-in lessons" in h.value for h in library.subheader)
    assert fake.requests == []


def test_json_inspector_parses_but_never_runs_input():
    from learning_desk.ui.widgets import inspect_json

    rows, error = inspect_json('{"a": [1, true, null], "b": {"c": "x"}}')
    assert error is None
    assert {(r["Path"], r["Type"]) for r in rows} >= {("$.a[1]", "boolean"), ("$.a[2]", "null"), ("$.b.c", "string")}
    rows, error = inspect_json("__import__('os').system('echo hi')")
    assert rows is None and error.startswith("Not valid JSON")
    assert inspect_json("x" * 20_001)[1].startswith("Paste at most")
