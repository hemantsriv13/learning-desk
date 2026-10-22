"""Home puts one persisted, explicitly chosen activity first; Notebook gathers personal notes and reviews."""

import json

import streamlit as st

from .. import curriculum, db
from ..curriculum import LESSONS, TOPIC_BY_ID, TOPICS
from . import learn
from .common import PAGES, fmt_time, go, open_lesson, open_session, show_flash


def resume(kind, target_id, key=None):
    db.set_activity(kind, target_id, key=key)
    if kind == "lesson":
        open_lesson(key)
    elif kind == "session":
        open_session(target_id)
    elif kind == "quiz":
        st.session_state["active_quiz"] = target_id
        go("library")
    else:
        st.session_state["resource_id"] = target_id
        st.session_state.pop("active_quiz", None)
        go("library")


def activity_label(kind, target_id, key=None):
    if kind == "lesson":
        lesson = LESSONS.get(key or "")
        return lesson.title if lesson else None
    table = {"resource": "resources", "session": "sessions", "quiz": "question_sets"}[kind]
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


def activity_context(kind, target_id, key=None) -> str:
    """One line saying where you will land, so the Continue button is predictable."""
    if kind == "lesson":
        lesson = LESSONS[key]
        place = db.lesson_progress(key)
        view = place["view"] if place else "Overview"
        where = view
        if place and view == "Walkthrough":
            section = next((s for s in lesson.walkthrough() if s.id == place["section"]), None)
            if section:
                where = f"Walkthrough · {section.title}"
        return f"Lesson · {TOPIC_BY_ID[lesson.topic].title} · {where}"
    if kind == "resource":
        place = db.query("SELECT mode FROM reader_progress WHERE resource_id=?", (target_id,))
        return "Library resource" + (f" · {place[0]['mode']}" if place else "")
    if kind == "quiz":
        return "Practice quiz · one question at a time"
    return "Notebook session"


def today():
    show_flash()
    st.title("Home")
    active = db.query("SELECT * FROM activity WHERE id=1")
    current = (active[0]["kind"], active[0]["target_id"], active[0].get("target_key")) if active else None
    label = activity_label(*current) if current else None
    with st.container(border=True, key="hero-continue"):
        st.caption("CONTINUE LEARNING")
        if label:
            st.markdown(f"### {label}")
            st.caption(activity_context(*current))
            if st.button("Continue learning", type="primary", icon=":material/play_arrow:"):
                resume(*current)
        else:
            st.markdown("### Pick something to start")
            st.caption("Read a built-in lesson, or open your Library to read your own material.")
            with st.container(horizontal=True, gap="small"):
                if st.button("Start with the first lesson", type="primary", icon=":material/school:"):
                    open_lesson(next(iter(LESSONS)))
                if st.button("Choose a resource", icon=":material/local_library:"):
                    st.session_state.pop("resource_id", None)
                    st.session_state.pop("active_quiz", None)
                    go("library")

    progress = learn.all_progress()
    started_topics = [t for t in TOPICS if any(lid in progress for lid in t.lessons)]
    if started_topics:
        st.subheader("Your topics")
        cols = st.columns(2)
        for i, topic in enumerate(started_topics[:4]):
            ready, planned, completed = learn.topic_counts(topic.id, progress)
            with cols[i % 2], st.container(border=True, key=f"card-home-topic-{topic.id}"):
                st.markdown(f":material/{topic.icon}: **{topic.title}**")
                st.progress(completed / ready if ready else 0.0, text=f"{completed} of {ready} lessons completed")
                if st.button("Open topic", key=f"home-topic-{topic.id}"):
                    st.session_state["explore_topic"] = topic.id
                    go("explore", topic=topic.id)

    st.subheader("Explore")
    st.caption(f"{len(LESSONS)} illustrated lessons across {len(TOPICS)} topics, each with a walkthrough, "
               "something to try, and checked sources.")
    picks = learn.suggestions(progress)
    cols = st.columns(len(picks) or 1)
    for col, lesson in zip(cols, picks):
        with col:
            learn.lesson_card(lesson, progress, "home")
    if "explore" in PAGES:
        st.page_link(PAGES["explore"], label="See the full map of topics", icon=":material/map:")

    with st.expander("Choose or change activity"):
        resources = db.list_resources()
        unfinished = db.query(
            "SELECT qs.* FROM question_sets qs LEFT JOIN quiz_progress p ON p.set_id=qs.id "
            "WHERE COALESCE(p.finished,0)=0 ORDER BY qs.id DESC")
        sessions = db.list_sessions()
        choices = [("lesson", 0, lid, LESSONS[lid].title) for lid in progress if lid in LESSONS]
        choices += [("resource", r["id"], None, r["title"]) for r in resources if r["status"] != "Finished"]
        choices += [("quiz", q["id"], None, f"Quiz {q['id']} · {q['created_at']}") for q in unfinished]
        choices += [("session", s["id"], None, s["title"] or "Untitled session") for s in sessions]
        if choices:
            chosen = st.selectbox("Activity", range(len(choices)),
                                  format_func=lambda i: f"{choices[i][0]} · {choices[i][3]}")
            if st.button("Make this my current activity"):
                kind, tid, key, _ = choices[chosen]
                resume(kind, tid, key)
        with st.form("today_new_session"):
            title = st.text_input("New notebook session title")
            topic = st.text_input("Topic (optional)")
            if st.form_submit_button("Start session"):
                open_session(db.create_session(title=title.strip(), topic=topic.strip()))


def _review_text(call) -> str:
    try:
        parsed = json.loads(call["parsed_json"] or "{}")
    except ValueError:
        return ""
    takeaway = parsed.get("main_takeaway")
    if isinstance(takeaway, dict):
        return takeaway.get("text", "")
    return parsed.get("summary", "")


def notebook():
    show_flash()
    st.title("Notebook")
    st.caption("Your own notes, lesson notes, and earlier AI reviews in one place. Opening anything here "
               "makes no model call.")
    sessions_tab, lessons_tab, reviews_tab = st.tabs(
        [":material/edit_note: Sessions", ":material/sticky_note_2: Lesson notes", ":material/rate_review: Reviews"])
    with sessions_tab:
        sessions = db.list_sessions()
        if sessions:
            query = st.text_input("Filter sessions", placeholder="Title or topic", key="notebook_filter")
            shown = [s for s in sessions
                     if query.casefold() in f"{s['title']} {s['topic']}".casefold()]
            if not shown:
                st.caption(f"No session title or topic contains “{query}”. Search & export searches note text too.")
            counts = {r["session_id"]: r["n"] for r in db.query(
                "SELECT session_id, COUNT(*) AS n FROM ai_calls WHERE action='review' AND status='ok' "
                "GROUP BY session_id")}
            cols = st.columns(2)
            for i, s in enumerate(shown):
                with cols[i % 2], st.container(border=True, key=f"card-session-{s['id']}"):
                    st.markdown(f"**{s['title'] or 'Untitled session'}**")
                    reviews = counts.get(s["id"], 0)
                    st.caption(f"{s['topic'] or 'No topic'} · saved {fmt_time(s['updated_at'])}"
                               + (f" · {reviews} review(s)" if reviews else ""))
                    if st.button("Open session", key=f"nb-open-{s['id']}"):
                        open_session(s["id"])
        else:
            st.info("No notebook sessions yet. Start one below to capture what you are working on.",
                    icon=":material/edit_note:")
        with st.expander("Start a notebook session", expanded=not sessions):
            with st.form("notebook_new"):
                title = st.text_input("Title")
                topic = st.text_input("Topic")
                if st.form_submit_button("Start session"):
                    open_session(db.create_session(title=title.strip(), topic=topic.strip()))
    with lessons_tab:
        notes = [n for n in db.query("SELECT * FROM lesson_notes ORDER BY updated_at DESC") if n["text"].strip()]
        if not notes:
            st.caption("Notes you write beside a lesson appear here.")
        for note in notes:
            lesson = curriculum.get(note["lesson_id"])
            with st.container(border=True, key=f"card-note-{note['lesson_id']}"):
                st.markdown(f"**{lesson.title if lesson else note['lesson_id']}**")
                st.caption(f"Updated {fmt_time(note['updated_at'])} · written against lesson version "
                           f"{note['lesson_version']}")
                st.text(note["text"][:600] + ("…" if len(note["text"]) > 600 else ""))
                if lesson and note["lesson_id"] in LESSONS and st.button("Open lesson", key=f"nb-lesson-{note['lesson_id']}"):
                    open_lesson(note["lesson_id"])
    with reviews_tab:
        calls = db.query("SELECT c.*, s.title AS session_title FROM ai_calls c JOIN sessions s ON s.id=c.session_id "
                         "WHERE c.action='review' AND c.status='ok' ORDER BY c.id DESC LIMIT 20")
        if not calls:
            st.caption("Reviews you request for notebook sessions appear here. They are AI-generated.")
        for call in calls:
            with st.container(border=True, key=f"card-review-{call['id']}"):
                st.markdown(f"**{call['session_title'] or 'Untitled session'}**")
                st.caption(f"AI-generated review · {fmt_time(call['created_at'])} · {call['prompt_version']}")
                text = _review_text(call)
                if text:
                    from .common import safe_md
                    st.markdown(safe_md(text))
                if st.button("Open session", key=f"nb-review-{call['id']}"):
                    open_session(call["session_id"])
