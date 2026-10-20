"""Drive the real Streamlit pages headlessly (streamlit.testing). The provider is fake;
the conftest guard fails any test that triggers a model call it did not queue."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from learning_desk import ai, db

from conftest import FEEDBACK_OK, QUESTIONS_OK, REVIEW_OK, REVIEW_V1_OK, make_session, store_v1_review, store_v2_review

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


def _markdown(at: AppTest) -> str:
    return " ".join(m.value for m in at.markdown)


def _expander(at: AppTest, label: str):
    return next(e for e in at.expander if e.label == label)


def test_new_review_shows_focused_view_with_details_collapsed(fake):
    session_id = make_session()
    fake.reply(REVIEW_OK)
    ai.review_session(session_id)
    at = _open_session(session_id)
    assert not at.exception

    focus = _markdown(at)
    for heading in ("Main takeaway", "One thing to clarify", "Next step"):
        assert heading in focus, heading
    assert "The API does not remember earlier requests" in focus
    for old_list in ("Possible gaps", "Observations you recorded", "Suggested experiments", "Suggested next steps"):
        assert old_list not in focus, old_list
    assert not any("older format" in m.value for m in at.markdown)
    # Citations sit beside the takeaway and the clarification.
    labels = [e.label for e in at.expander]
    assert "Cited: S3" in labels and "Cited: S2, S3" in labels
    # Supporting evidence and technical details are in collapsed sections.
    evidence = " ".join(m.value for m in _expander(at, "Supporting evidence").markdown)
    assert REVIEW_OK["supporting_evidence"][0]["text"] in evidence
    assert "From the model's general knowledge" in evidence
    technical = _expander(at, "Technical details")
    assert any("Raw response" in m.value for m in technical.markdown)
    assert len(fake.requests) == 1


def test_one_phrase_per_section_is_highlighted(fake):
    session_id = make_session()
    fake.reply(REVIEW_OK)
    ai.review_session(session_id)
    at = _open_session(session_id)
    assert not at.exception
    md = _markdown(at)
    assert ":blue[**the client resends the history**]" in md
    assert ":orange[**the server stores history**]" in md
    assert ":blue[**Send the same question twice**]" in md
    assert md.count(":blue[") == 2 and md.count(":orange[") == 1
    # The labels stay, so colour is never the only signal.
    for heading in ("Main takeaway", "One thing to clarify", "Next step", "**Task:**"):
        assert heading in md
    assert len(fake.requests) == 1


def test_unusable_emphasis_is_shown_as_plain_text(fake):
    session_id = make_session()
    fake.reply({**REVIEW_OK,
                "main_takeaway": {**REVIEW_OK["main_takeaway"], "emphasis": "words the model made up"},
                "clarification": {**REVIEW_OK["clarification"], "emphasis": "[S2]"},
                "next_step": {**REVIEW_OK["next_step"], "emphasis": None}})
    ai.review_session(session_id)
    at = _open_session(session_id)
    assert not at.exception and not at.error
    md = _markdown(at)
    assert ":blue[" not in md and ":orange[" not in md
    assert REVIEW_OK["main_takeaway"]["text"] in md and REVIEW_OK["clarification"]["text"] in md
    assert REVIEW_OK["next_step"]["text"] in md
    # The ignored highlights are noted only inside Technical details.
    assert any("Highlight for" in w.value for w in _expander(at, "Technical details").warning)
    assert len(fake.requests) == 1


def test_emphasis_keeps_the_rest_of_the_text_safe():
    from learning_desk.ui.session_page import _emphasised
    text = "See ![x](http://evil.example/p.png) then check the cached history first."
    out = _emphasised(text, "check the cached history", "blue")
    assert ":blue[**check the cached history**]" in out
    assert "\\![x]" in out and " ![x]" not in out  # images stay disabled around the highlight


def test_review_without_emphasis_fields_still_opens(fake):
    session_id = make_session()
    store_v2_review(session_id)
    at = _open_session(session_id)
    assert not at.exception
    md = _markdown(at)
    assert REVIEW_OK["main_takeaway"]["text"] in md and ":blue[" not in md
    assert "older format" not in md
    assert fake.requests == []


def test_clarification_is_left_out_when_there_is_none(fake):
    session_id = make_session()
    fake.reply({**REVIEW_OK, "clarification": None})
    ai.review_session(session_id)
    at = _open_session(session_id)
    assert not at.exception
    assert "One thing to clarify" not in _markdown(at)
    assert "Main takeaway" in _markdown(at) and "Next step" in _markdown(at)


def test_next_step_is_saved_to_queue_only_on_click(fake):
    session_id = make_session()
    fake.reply(REVIEW_OK)
    ai.review_session(session_id)
    at = _open_session(session_id)
    assert db.list_queue(session_id=session_id) == []  # nothing added automatically

    _button(at, "Save to my queue").click()
    at.run()
    [item] = db.list_queue(session_id=session_id)
    assert item["text"] == REVIEW_OK["next_step"]["text"] and item["kind"] == "task"
    assert item["priority"] == "normal" and item["source"] == "ai_suggestion:next_step"
    assert not any(b.label == "Save to my queue" for b in at.button)  # cannot be added twice
    at.run()
    assert len(db.list_queue(session_id=session_id)) == 1
    assert len(fake.requests) == 1


def test_old_format_review_still_opens(fake):
    session_id = make_session()
    store_v1_review(session_id)
    at = _open_session(session_id)
    assert not at.exception
    assert any("older format" in m.value for m in at.markdown)
    assert REVIEW_V1_OK["summary"] in _markdown(at)
    evidence = " ".join(m.value for m in _expander(at, "Supporting evidence").markdown)
    assert "Possible gaps or misconceptions" in evidence
    # Its suggested next steps can still be added, one click each.
    _button(at, "Add").click()
    at.run()
    [item] = db.list_queue(session_id=session_id)
    assert item["source"] == "ai_suggestion:0" and item["text"] == REVIEW_V1_OK["suggested_next_steps"][0]["text"]
    assert fake.requests == []


def test_history_and_comparison_make_no_model_calls(fake):
    session_id = make_session()
    store_v1_review(session_id)
    fake.reply(REVIEW_OK)
    ai.review_session(session_id)
    at = _open_session(session_id)
    assert "The API does not remember earlier requests" in _markdown(at)  # newest is shown first

    older = db.list_ai_calls(session_id, action="review", status="ok")[1]["id"]
    next(s for s in at.selectbox if s.label == "Review shown above").set_value(older)
    at.run()
    assert not at.exception
    assert REVIEW_V1_OK["summary"] in _markdown(at)

    next(t for t in at.toggle if t.label == "Compare two reviews side by side").set_value(True)
    at.run()
    assert not at.exception
    assert len(fake.requests) == 1  # only the review created above


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
