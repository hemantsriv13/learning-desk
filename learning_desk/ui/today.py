"""Home puts one persisted, explicitly chosen activity first; Notebook gathers personal notes and reviews."""

import json
from datetime import datetime
from html import escape

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


def _greeting(now: datetime) -> str:
    part = "morning" if now.hour < 12 else "afternoon" if now.hour < 18 else "evening"
    return f"Good {part}"


def _tile(label: str, value: int, unit: str, caption: str, key: str) -> None:
    with st.container(border=True, key=f"tile-{key}", height="stretch"):
        st.html(f'<p class="ld-tile-label">{escape(label)}</p>'
                f'<p class="ld-tile-value">{value}<span class="ld-tile-unit">{escape(unit)}</span></p>')
        st.caption(caption)


def lesson_strip(progress: dict) -> str:
    """The signature element: one cell per finished lesson, grouped by topic, filled as you go.
    Built only from curriculum ids and stored statuses, escaped; the visible legend explains it."""
    groups = []
    for topic in TOPICS:
        ids = [lid for lid in topic.lessons if lid in LESSONS]
        states = [learn.status(lid, progress) for lid in ids]
        cells = "".join(f'<span class="{"done" if s == "Completed" else "started" if s == "In progress" else ""}">'
                        f'</span>' for s in states)
        done = states.count("Completed")
        label = f"{topic.title}: {done} of {len(ids)} completed"
        groups.append(f'<li role="img" aria-label="{escape(label, quote=True)}" title="{escape(label, quote=True)}">'
                      f'{cells}</li>')
    return f'<ul class="ld-strip" aria-label="Lessons by topic">{"".join(groups)}</ul>'


def today():
    show_flash()
    now = datetime.now()
    st.title(_greeting(now))
    active = db.query("SELECT * FROM activity WHERE id=1")
    current = (active[0]["kind"], active[0]["target_id"], active[0].get("target_key")) if active else None
    label = activity_label(*current) if current else None
    progress = learn.all_progress()
    completed = sum(1 for lid in progress if learn.status(lid, progress) == "Completed")
    started = sum(1 for lid in progress if learn.status(lid, progress) == "In progress")
    notes = [n for n in db.query("SELECT * FROM lesson_notes ORDER BY updated_at DESC") if n["text"].strip()]
    # The finding, under the title: where Continue goes, and how far through the collection you are.
    where = f"You were in **{label}**." if label else "Nothing is open yet."
    st.markdown(f"{now:%A %d %B} · {where} {completed} of {len(LESSONS)} lessons completed.")

    with st.container(key="tiles"):
        tiles = st.columns(4)
    with tiles[0]:
        _tile("Lessons completed", completed, f" of {len(LESSONS)}", "Marked complete by you", "done")
    with tiles[1]:
        _tile("In progress", started, " lessons", "Your place in each is kept", "open")
    with tiles[2]:
        _tile("Lesson notes", len(notes), "", "Never sent to a model", "notes")
    with tiles[3]:
        _tile("Library", len(db.list_resources()), " resources", "Your own reading", "library")

    main, aside = st.columns([9, 3])
    with main, st.container(border=True, key="hero-continue", height="stretch"):
        st.markdown("**Continue**")
        if label:
            st.markdown(f"### {label}")
            st.caption(activity_context(*current))
            if st.button("Continue learning", type="primary", icon=":material/play_arrow:"):
                resume(*current)
            if current[0] == "lesson" and current[2] in LESSONS:
                lesson = LESSONS[current[2]]
                answered = {a["check_id"] for a in db.check_attempts(lesson.id)}
                sections = [s.title for s in lesson.walkthrough()]
                st.caption(f"{len(sections)} sections: " + " · ".join(sections))
                st.caption(f"Quick check: {len(answered)} of {len(lesson.checks)} questions answered so far.")
        else:
            st.markdown("### Start with the first lesson")
            st.caption(f"{next(iter(LESSONS.values())).title} · about {next(iter(LESSONS.values())).minutes} minutes. "
                       "Or open your Library to read your own material.")
            with st.container(horizontal=True, gap="small"):
                if st.button("Start with the first lesson", type="primary", icon=":material/school:"):
                    open_lesson(next(iter(LESSONS)))
                if st.button("Choose a resource", icon=":material/local_library:"):
                    st.session_state.pop("resource_id", None)
                    st.session_state.pop("active_quiz", None)
                    go("library")
    with aside, st.container(border=True, key="panel-notes", height="stretch"):
        st.markdown("**Recent notes**")
        if not notes:
            st.caption("Notes you write beside a lesson appear here.")
        for note in notes[:2]:
            lesson = curriculum.get(note["lesson_id"])
            st.markdown(f"{lesson.title if lesson else note['lesson_id']}")
            first = note["text"].strip().splitlines()[0]
            st.caption(first if len(first) <= 90 else first[:first.rfind(" ", 0, 88)] + "…")
        if "notebook" in PAGES:
            st.page_link(PAGES["notebook"], label="View all")

    path, nxt = st.columns(2)
    with path, st.container(border=True, key="panel-path", height="stretch"):
        st.markdown("**Your path through the lessons**")
        st.html(lesson_strip(progress))
        st.caption(f"One cell per lesson, grouped by topic. Filled: completed ({completed}). "
                   f"Half: in progress ({started}). Empty: not started ({len(LESSONS) - completed - started}).")
        if "explore" in PAGES:
            st.page_link(PAGES["explore"], label="Open the map of all ten topics", icon=":material/map:")
    with nxt, st.container(border=True, key="panel-next", height="stretch"):
        st.markdown("**Next up**")
        for lesson in learn.suggestions(progress, 2):
            with st.container(border=True, key=f"row-next-{lesson.id}"):
                c1, c2 = st.columns([4, 1.3], vertical_alignment="center")
                c1.markdown(f"{lesson.title}")
                c1.caption(f"{TOPIC_BY_ID[lesson.topic].title} · {lesson.minutes} min · {lesson.level}")
                if c2.button("Open", key=f"next-{lesson.id}"):
                    open_lesson(lesson.id)

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
