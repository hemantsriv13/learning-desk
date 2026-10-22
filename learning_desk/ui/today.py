"""Today prioritizes a single persisted, explicitly chosen activity."""

import streamlit as st
from .. import db
from .common import PAGES, open_session


def resume(kind, target_id):
    db.set_activity(kind, target_id)
    if kind == "session":
        open_session(target_id)
    elif kind == "quiz":
        st.session_state["active_quiz"] = target_id
        st.switch_page(PAGES["library"])
    else:
        st.session_state["resource_id"] = target_id
        st.session_state.pop("active_quiz", None)
        st.switch_page(PAGES["library"])


def activity_label(kind, target_id):
    table = {"resource": "resources", "session": "sessions", "quiz": "question_sets"}[
        kind
    ]
    rows = db.query(f"SELECT * FROM {table} WHERE id=?", (target_id,))
    if not rows:
        return None
    row = rows[0]
    if kind == "quiz":
        progress = db.query("SELECT * FROM quiz_progress WHERE set_id=?", (target_id,))
        if progress and progress[0]["finished"]:
            return None
        return f"Quiz {target_id} · question {(progress[0]['position'] + 1) if progress else 1}"
    if kind == "resource" and (row["archived"] or row["status"] == "Finished"):
        return None
    return row["title"] or "Untitled notebook session"


def today():
    st.title("Today")
    active = db.query("SELECT * FROM activity WHERE id=1")
    label = (
        activity_label(active[0]["kind"], active[0]["target_id"]) if active else None
    )
    if label:
        st.write(label)
        if st.button("Continue learning", type="primary"):
            resume(active[0]["kind"], active[0]["target_id"])
    else:
        st.write("Choose one thing to explore.")
        if st.button("Choose a resource", type="primary"):
            st.session_state.pop("resource_id", None)
            st.session_state.pop("active_quiz", None)
            st.switch_page(PAGES["library"])
    with st.expander("Choose or change activity"):
        resources = db.list_resources()
        unfinished = db.query(
            "SELECT qs.* FROM question_sets qs LEFT JOIN quiz_progress p ON p.set_id=qs.id WHERE COALESCE(p.finished,0)=0 ORDER BY qs.id DESC"
        )
        sessions = db.list_sessions()
        choices = [
            ("resource", r["id"], r["title"])
            for r in resources
            if r["status"] != "Finished"
        ]
        choices += [
            ("quiz", q["id"], f"Quiz {q['id']} · {q['created_at']}") for q in unfinished
        ]
        choices += [
            ("session", s["id"], s["title"] or "Untitled session") for s in sessions
        ]
        if choices:
            chosen = st.selectbox(
                "Activity",
                range(len(choices)),
                format_func=lambda i: f"{choices[i][0]} · {choices[i][2]}",
            )
            if st.button("Make this my current activity"):
                kind, tid, _ = choices[chosen]
                resume(kind, tid)
        with st.form("today_new_session"):
            title = st.text_input("New notebook session title")
            topic = st.text_input("Topic (optional)")
            if st.form_submit_button("Start session"):
                open_session(
                    db.create_session(title=title.strip(), topic=topic.strip())
                )


def notebook():
    st.title("Notebook")
    sessions = db.list_sessions()
    if sessions:
        sid = st.selectbox(
            "Session",
            [s["id"] for s in sessions],
            format_func=lambda i: next(
                s["title"] or "Untitled session" for s in sessions if s["id"] == i
            ),
        )
        if st.button("Open session", type="primary"):
            open_session(sid)
    with st.expander("Start a notebook session", expanded=not sessions):
        with st.form("notebook_new"):
            title = st.text_input("Title")
            topic = st.text_input("Topic")
            if st.form_submit_button("Start session"):
                open_session(
                    db.create_session(title=title.strip(), topic=topic.strip())
                )
