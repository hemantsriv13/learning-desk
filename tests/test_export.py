import json

from learning_desk import ai, db, example, export

from conftest import FEEDBACK_OK, QUESTIONS_OK, REVIEW_OK, REVIEW_V1_OK, make_session, store_v1_review


def test_session_markdown_contains_notes_feedback_and_questions(fake):
    session_id = make_session(notes="My unique note text")
    db.add_queue_item(session_id, "question", "Unique queue question")
    fake.reply(REVIEW_OK)
    ai.review_session(session_id)
    fake.reply(QUESTIONS_OK)
    ai.generate_questions(session_id)
    q = db.list_question_sets(session_id)[0]["questions"][0]
    db.save_answer(q["id"], "My unique answer")
    fake.reply(FEEDBACK_OK)
    ai.answer_feedback(q["id"])

    md = export.session_markdown(session_id)
    for expected in ["# Context windows", "My unique note text", "Unique queue question",
                     REVIEW_OK["main_takeaway"]["text"], REVIEW_OK["next_step"]["text"],
                     "General explanations from the model (not from my notes)",
                     "(notes: S2, S3)", QUESTIONS_OK["questions"][1]["question"], "My unique answer",
                     FEEDBACK_OK["follow_up_exercise"], "_(not answered)_"]:
        assert expected in md, expected


def test_old_format_reviews_are_exported(fake):
    session_id = make_session()
    store_v1_review(session_id)
    md = export.session_markdown(session_id)
    assert "review-v1, older format" in md
    assert REVIEW_V1_OK["summary"] in md and "Possible gaps (hypotheses)" in md
    assert fake.requests == []


def test_json_export_contains_every_table(fake):
    session_id = make_session()
    db.add_queue_item(session_id, "task", "t")
    fake.fail()
    ai.review_session(session_id)  # failed calls are exported too

    data = json.loads(export.all_data_json())
    assert data["app"] == "learning-desk"
    assert {"sessions", "queue_items", "snapshots", "ai_calls", "question_sets", "questions"} <= set(data)
    assert data["sessions"][0]["notes"] == db.get_session(session_id)["notes"]
    assert data["ai_calls"][0]["status"] == "error"


def test_exports_work_without_an_api_key(monkeypatch, fake):
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    session_id = example.create_example_session()
    assert "Fictional example session" in export.session_markdown(session_id)
    assert json.loads(export.all_data_json())["sessions"][0]["is_example"] == 1
    assert fake.requests == []
