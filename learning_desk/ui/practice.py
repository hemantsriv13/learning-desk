"""One question at a time, with immutable attempts and evidence attached to feedback."""

import json
import streamlit as st
from .. import db, learning
from .common import ai_ready, ai_privacy_note, inspect_call, safe_md


def open_quiz(set_id):
    db.set_activity("quiz", set_id)
    st.session_state["active_quiz"] = set_id
    from .common import PAGES

    if "library" in PAGES:
        st.switch_page(PAGES["library"])
    st.rerun()


def quiz_setup(version_id=None, session_id=None, before_generate=None):
    difficulty = st.selectbox(
        "Difficulty", ["introductory", "intermediate", "advanced"]
    )
    goal = st.selectbox("Practice goal", ["Understand", "Apply", "Diagnose"])
    st.caption("Three AI-generated questions. One shown at a time; no mastery score.")
    ai_privacy_note("this exact source version or saved session snapshot")
    if st.button("Start three-question quiz", type="primary", disabled=not ai_ready()):
        try:
            if before_generate:
                before_generate()
            with st.spinner("Writing questions..."):
                result = learning.generate_quiz(
                    version_id=version_id,
                    session_id=session_id,
                    difficulty=difficulty,
                    practice_goal=goal,
                )
        except ValueError as exc:
            st.warning(str(exc))
            return
        if result.ok:
            set_id = db.query(
                "SELECT id FROM question_sets WHERE ai_call_id=?", (result.call_id,)
            )[0]["id"]
            open_quiz(set_id)
        else:
            st.error(result.error)
            inspect_call(db.get_ai_call(result.call_id))


def render_quiz(set_id):
    rows = db.query("SELECT * FROM question_sets WHERE id=?", (set_id,))
    if not rows:
        st.warning("Quiz unavailable.")
        return
    qs = rows[0]
    questions = db.query(
        "SELECT * FROM questions WHERE set_id=? ORDER BY position", (set_id,)
    )
    if not questions:
        st.warning("No questions stored.")
        return
    db.execute("INSERT OR IGNORE INTO quiz_progress(set_id) VALUES(?)", (set_id,))
    progress = db.query("SELECT * FROM quiz_progress WHERE set_id=?", (set_id,))[0]
    pos = min(progress["position"], len(questions) - 1)
    st.subheader("Practise")
    st.caption(
        f"AI-generated · {qs['difficulty']} · {qs['practice_goal']} · source "
        + (
            f"content version {qs['content_version_id']}"
            if qs["content_version_id"]
            else f"snapshot {qs['snapshot_id']}"
        )
    )
    if progress["finished"]:
        st.write(
            "Quiz finished. Your attempts are saved for review. This is practice, not a mastery assessment."
        )
        with st.expander("Review previous attempts", expanded=True):
            for q in questions:
                st.write(q["text"])
                attempt_history(q, qs)
        if st.button("Revisit questions"):
            db.execute(
                "UPDATE quiz_progress SET position=0,finished=0 WHERE set_id=?",
                (set_id,),
            )
            db.set_activity("quiz", set_id)
            st.rerun()
        inspect_call(db.get_ai_call(qs["ai_call_id"]))
        return
    q = questions[pos]
    st.progress(pos / len(questions), text=f"Question {pos + 1} of {len(questions)}")
    st.markdown(safe_md(q["text"]))
    with st.popover("Open the source", icon=":material/menu_book:"):
        # Open-book practice: the exact source this quiz was generated from, without marking
        # which passages the question cites (those appear with the feedback).
        st.caption("The exact source version or notebook snapshot this question was generated from.")
        try:
            for passage in learning.source(content_version_id=qs["content_version_id"],
                                           snapshot_id=qs["snapshot_id"]):
                st.caption(f"S{passage['id']}")
                st.text(passage["text"])
        except ValueError as exc:
            st.warning(str(exc))
    options = json.loads(q["options_json"])
    with st.form(f"attempt_{q['id']}", clear_on_submit=False):
        answer = (
            st.radio("Your answer", options, index=None, key=f"quiz_answer_{q['id']}")
            if q["question_type"] == "multiple_choice"
            else st.text_area("Your answer", key=f"quiz_answer_{q['id']}")
        )
        if st.form_submit_button("Submit answer", type="primary"):
            try:
                attempt_id = db.submit_attempt(q["id"], answer or "")
                if q["question_type"] == "multiple_choice":
                    learning.grade(attempt_id)
                st.rerun()
            except ValueError as exc:
                st.warning(str(exc))
    if q["hint"]:
        with st.expander("Optional hint"):
            st.markdown(safe_md(q["hint"]))
    attempts = db.attempts(q["id"])
    if attempts:
        latest = attempts[-1]
        feedback = db.query(
            "SELECT * FROM attempt_feedback WHERE attempt_id=? ORDER BY id",
            (latest["id"],),
        )
        if not feedback:
            if q["expected_answer"]:
                if st.button(
                    "Get feedback on this submitted answer", disabled=not ai_ready()
                ):
                    try:
                        with st.spinner("Checking this answer against the source…"):
                            learning.grade(latest["id"])
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
            else:
                # Original notebook questions keep their original schema and AI action.
                if st.button(
                    "Get feedback on this submitted answer", disabled=not ai_ready()
                ):
                    from .. import ai

                    result = ai.answer_feedback(q["id"])
                    if result.ok:
                        st.rerun()
                    else:
                        st.error(result.error)
        attempt_history(q, qs, latest_only=True)
        if st.button("Finish quiz" if pos == len(questions) - 1 else "Next question"):
            finished = pos == len(questions) - 1
            db.execute(
                "UPDATE quiz_progress SET position=?,finished=? WHERE set_id=?",
                (pos if finished else pos + 1, int(finished), set_id),
            )
            if finished:
                if qs["content_version_id"]:
                    rid = db.query(
                        "SELECT resource_id FROM content_versions WHERE id=?",
                        (qs["content_version_id"],),
                    )[0]["resource_id"]
                    db.set_activity("resource", rid)
                elif qs["session_id"]:
                    db.set_activity("session", qs["session_id"])
            st.rerun()
    with st.expander("Earlier questions and attempts"):
        for prior in questions[:pos]:
            st.write(prior["text"])
            attempt_history(prior, qs)
    report(q["id"], attempts[-1]["id"] if attempts else None)
    with st.expander("Quiz technical details"):
        from .common import call_details

        call_details(db.get_ai_call(qs["ai_call_id"]))


def attempt_history(q, qs, latest_only=False):
    from .library import evidence

    attempts = db.attempts(q["id"])
    shown = attempts[-1:] if latest_only else attempts
    for attempt in shown:
        st.caption(
            f"Attempt {attempt['id']} · {attempt['created_at']} · {attempt['provenance']}"
        )
        st.text(attempt["answer"])
        feedbacks = db.query(
            "SELECT * FROM attempt_feedback WHERE attempt_id=? ORDER BY id",
            (attempt["id"],),
        )
        for feedback in feedbacks:
            result = json.loads(feedback["feedback_json"])
            st.caption(
                "AI-generated feedback"
                if feedback["ai_call_id"]
                else "Deterministic comparison with an AI-generated key"
            )
            if "feedback" in result:
                st.markdown(safe_md(result["feedback"]))
                if result.get("uncertainty"):
                    st.caption(result["uncertainty"])
                refs = result["section_refs"]
            else:
                st.write("Explains well: " + "; ".join(result.get("explains_well", [])))
                st.write(
                    "Missing or possibly incorrect: "
                    + "; ".join(
                        m["point"] + " — " + m["why"]
                        for m in result.get("missing_or_possibly_incorrect", [])
                    )
                )
                refs = []
            # Avoid nested expanders when the history itself is expanded.
            if st.checkbox(
                "Show supporting evidence",
                key=f"evidence_{feedback['id']}_{latest_only}",
            ):
                evidence(
                    learning.source(
                        content_version_id=qs["content_version_id"],
                        snapshot_id=qs["snapshot_id"],
                    ),
                    refs,
                )
                if q["expected_answer"]:
                    st.caption("Saved answer key / assessment rubric (AI-generated)")
                    st.text(q["expected_answer"])
            if feedback["ai_call_id"]:
                call = db.get_ai_call(feedback["ai_call_id"])
                if st.checkbox(
                    "Inspect feedback call",
                    key=f"inspect_feedback_{feedback['id']}_{latest_only}",
                ):
                    from .common import call_details

                    call_details(call)
    if latest_only and len(attempts) > 1:
        with st.expander("Previous attempts for this question"):
            attempt_history(q, qs)


def report(question_id, attempt_id=None):
    with st.expander("This question or feedback seems wrong"):
        text = st.text_area("What seems wrong?", key=f"report_{question_id}")
        feedbacks = (
            db.query(
                "SELECT id FROM attempt_feedback WHERE attempt_id=? ORDER BY id DESC",
                (attempt_id,),
            )
            if attempt_id
            else []
        )
        if st.button("Save report", key=f"save_report_{question_id}"):
            if text.strip():
                db.execute(
                    "INSERT INTO issue_reports(question_id,attempt_id,feedback_id,text,created_at) VALUES(?,?,?,?,?)",
                    (
                        question_id,
                        attempt_id,
                        feedbacks[0]["id"] if feedbacks else None,
                        text.strip(),
                        db.now(),
                    ),
                )
                st.success("Saved for later review. It will not trigger a model call.")
            else:
                st.warning("Describe the issue first.")
