"""Drive the real Streamlit pages headlessly (streamlit.testing). The provider is fake;
the conftest guard fails any test that triggers a model call it did not queue."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from learning_desk import ai, db

from conftest import FEEDBACK_OK, QUESTIONS_OK, REVIEW_OK, make_session

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def _session_script():
    from learning_desk import db
    from learning_desk.ui import session_page
    db.init_db()
    session_page.render()


def _other_page(name: str) -> AppTest:
    return AppTest.from_string(
        "from learning_desk import db\n"
        "from learning_desk.ui import other_pages\n"
        "db.init_db()\n"
        f"other_pages.{name}()\n", default_timeout=30)


def _open_session(session_id: int) -> AppTest:
    at = AppTest.from_function(_session_script, default_timeout=30)
    at.session_state["current_session_id"] = session_id
    return at.run()


def _button(at: AppTest, label: str):
    return next(b for b in at.button if b.label == label)


def _text_area(at: AppTest, label: str):
    return next(t for t in at.text_area if t.label == label)


def test_browsing_every_page_makes_no_model_calls(fake):
    session_id = make_session()
    fake.reply(REVIEW_OK)
    ai.review_session(session_id)
    fake.reply(QUESTIONS_OK)
    ai.generate_questions(session_id)
    q = db.list_question_sets(session_id)[0]["questions"][0]
    db.save_answer(q["id"], "answer")
    fake.reply(FEEDBACK_OK)
    ai.answer_feedback(q["id"])
    db.add_queue_item(session_id, "task", "something")
    calls_before = len(fake.requests)

    home = AppTest.from_file(APP, default_timeout=30).run()
    assert not home.exception
    for name in ("home", "queue", "search", "settings"):
        page = _other_page(name).run()
        assert not page.exception, name
    at = _open_session(session_id)
    assert not at.exception
    at.run()  # an ordinary rerun
    assert not at.exception
    assert len(fake.requests) == calls_before  # nothing new was sent


def test_unsaved_text_survives_reruns_and_save_persists(fake):
    session_id = make_session(notes="original")
    at = _open_session(session_id)
    _text_area(at, "Notes, observations and code excerpts").input("typed but not saved")
    at.run()
    at.run()
    assert _text_area(at, "Notes, observations and code excerpts").value == "typed but not saved"
    assert any("Unsaved changes" in w.value for w in at.warning)
    assert db.get_session(session_id)["notes"] == "original"

    _button(at, "Save").click()
    at.run()
    assert db.get_session(session_id)["notes"] == "typed but not saved"
    assert any("Saved at" in s.value for s in at.success)


def test_failed_review_saves_first_and_keeps_text(fake):
    session_id = make_session(notes="original")
    at = _open_session(session_id)
    _text_area(at, "Notes, observations and code excerpts").input("new thoughts")
    fake.fail("Simulated outage")
    _button(at, "Review this session").click()
    at.run()

    assert any("Review failed" in e.value for e in at.error)
    assert db.get_session(session_id)["notes"] == "new thoughts"  # saved before the call
    assert _text_area(at, "Notes, observations and code excerpts").value == "new thoughts"
    assert fake.requests and "new thoughts" in fake.requests[0]["messages"][0]["content"]


def test_review_shows_grounded_and_general_parts_separately(fake):
    session_id = make_session()
    fake.reply(REVIEW_OK)
    ai.review_session(session_id)
    at = _open_session(session_id)
    markdown = " ".join(m.value for m in at.markdown)
    assert "Grounded in your notes" in markdown
    assert "General explanations from the model" in markdown
    assert "Possible gaps or misconceptions" in markdown
    # Suggestions are only offered, not added.
    assert db.list_queue(session_id=session_id) == []
    _button(at, "Add").click()
    at.run()
    [item] = db.list_queue(session_id=session_id)
    assert item["source"] == "ai_suggestion:0" and item["text"] == REVIEW_OK["suggested_next_steps"][0]["text"]


def test_feedback_button_locked_until_answer_submitted(fake):
    session_id = make_session()
    fake.reply(QUESTIONS_OK)
    ai.generate_questions(session_id)
    at = _open_session(session_id)
    feedback_buttons = [b for b in at.button if b.label == "Get feedback on my answer"]
    assert len(feedback_buttons) == 3 and all(b.disabled for b in feedback_buttons)
    assert not any("Explains well" in m.value for m in at.markdown)

    _text_area(at, "Your answer").input("Because each request is independent.")
    at.run()
    assert _button(at, "Get feedback on my answer").disabled  # typed but not submitted
    _button(at, "Submit answer").click()
    at.run()
    assert not _button(at, "Get feedback on my answer").disabled

    fake.reply(FEEDBACK_OK)
    _button(at, "Get feedback on my answer").click()
    at.run()
    assert any("What your answer explains well" in m.value for m in at.markdown)
    assert len(fake.requests) == 2


def test_rerun_does_not_regenerate_questions(fake):
    session_id = make_session()
    at = _open_session(session_id)
    fake.reply(QUESTIONS_OK)
    _button(at, "Generate three questions").click()
    at.run()
    at.run()
    at.run()
    assert len(fake.requests) == 1
    assert len(db.list_question_sets(session_id)) == 1


def test_ai_buttons_disabled_without_key(monkeypatch, fake):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    at = _open_session(make_session())
    assert _button(at, "Review this session").disabled
    assert _button(at, "Generate three questions").disabled
    assert not _button(at, "Save").disabled


def test_session_created_in_ui_is_there_after_restart(fake):
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.text_input[0].input("Attention heads")
    at.text_input[1].input("Transformers")
    next(b for b in at.button if b.label == "Start session").click()
    at.run()
    # A brand-new app instance reading the same database file.
    fresh = AppTest.from_file(APP, default_timeout=30).run()
    assert any("Attention heads" in m.value for m in fresh.markdown)
