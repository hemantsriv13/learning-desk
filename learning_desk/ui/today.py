"""Home puts one persisted, explicitly chosen activity first; Notebook gathers personal notes and reviews."""

import json
from datetime import date, datetime
from html import escape

import streamlit as st

from .. import curriculum, db, pixels, visuals
from ..curriculum import LESSONS, TOPIC_BY_ID, TOPICS, TRACK_ORDER
from . import learn
from .common import PAGES, fmt_time, go, open_lesson, open_session, show_flash
from .theme import TRACK_HUES, empty_state, heading, page_header, progress_ring, stats, status_badge, steps, svg_img


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


def _time_icon(now: datetime) -> str:
    return "wb_twilight" if now.hour < 12 else "light_mode" if now.hour < 18 else "dark_mode"


def _shift_idea() -> None:
    st.session_state["idea_shift"] = st.session_state.get("idea_shift", 0) + 1


def _idea_of_the_day() -> None:
    """One key idea from a finished lesson. It changes each day; "Another idea" steps through the rest."""
    ideas = [(lesson, idea) for lesson in LESSONS.values() for idea in lesson.key_ideas]
    lesson, idea = ideas[(date.today().toordinal() * 7 + st.session_state.get("idea_shift", 0)) % len(ideas)]
    with st.container(border=True, key="card-idea", height="stretch"):
        heading("lightbulb", "Idea of the day", f"From {lesson.title}", hue="amber")
        st.html(f'<p class="ld-idea">{escape(idea)}</p>')
        st.html(f'<div class="ld-thumb-wrap">{svg_img(visuals.thumbnail(lesson.topic), "", "ld-thumb")}</div>')
        with st.container(horizontal=True, gap="small"):
            if st.button("Open the lesson", key="idea-open", icon=":material/arrow_forward:"):
                open_lesson(lesson.id)
            st.button("Another idea", key="idea-next", icon=":material/shuffle:", type="tertiary", on_click=_shift_idea)


def _track_tiles(progress: dict) -> None:
    """The six tracks as coloured tiles; each opens Explore filtered to that track."""
    with st.container(border=True, key="panel-tracks", height="stretch"):
        heading("map", "Explore by track", f"{len(TOPICS)} topics in {len(TRACK_ORDER)} tracks", hue="teal")
        cols = st.columns(3)
        for i, name in enumerate(TRACK_ORDER):
            topics = [t for t in TOPICS if t.track == name]
            ready = sum(learn.topic_counts(t.id, progress)[0] for t in topics)
            note = f"{len(topics)} topics · {ready} lessons" if ready else f"{len(topics)} topics · planned"
            with cols[i % 3], st.container(border=True, key=f"tile-track-{i}", height="stretch"):
                # The animated icon sits above the name: beside it, it would squeeze the name in a narrow tile.
                st.html(pixels.img(pixels.TRACK_ICONS[name](), 42))
                heading(learn.TRACK_ICONS[name], name, note, hue=TRACK_HUES[name])
                if st.button("Browse", key=f"track-{i}", icon=":material/arrow_forward:", type="tertiary"):
                    st.session_state["explore_track"] = name
                    st.session_state.pop("explore_topic", None)
                    go("explore")


def _lesson_place(lesson) -> tuple[int, str]:
    """(0-based walkthrough section you are at, -1 before it, the section count after it; a line saying so)."""
    place = db.lesson_progress(lesson.id)
    sections = lesson.walkthrough()
    if not place or place["view"] == "Overview":
        return -1, f"Not into the walkthrough yet · {len(sections)} sections"
    if place["view"] in ("Try it", "Sources"):
        return len(sections), f"Past all {len(sections)} sections · now on {place['view']}"
    ids = [s.id for s in sections]
    index = ids.index(place["section"]) if place["section"] in ids else 0
    return index, f"Section {index + 1} of {len(sections)}: {sections[index].title}"


def _continue_panel(current, label) -> None:
    with st.container(border=True, key="hero-continue", height="stretch"):
        heading("play_circle", "Pick up where you left off" if label else "Start here", hue="teal")
        if label:
            kind, _, key = current
            lesson = LESSONS.get(key) if kind == "lesson" else None
            text, art = st.columns([3, 1], vertical_alignment="center") if lesson else (st.container(), None)
            with text:
                st.markdown(f"### {label}")
                st.caption(activity_context(*current))
                if lesson:
                    st.markdown(lesson.objective)
                    index, where = _lesson_place(lesson)
                    st.html(steps(len(lesson.walkthrough()), index, where))
                    answered = {a["check_id"] for a in db.check_attempts(lesson.id)}
                    st.caption(f"{where} · Quick check: {len(answered)} of {len(lesson.checks)} answered")
            if art is not None:
                with art:
                    st.html(f'<div class="ld-thumb-wrap">{svg_img(visuals.thumbnail(lesson.topic), "", "ld-thumb")}</div>')
            if st.button("Continue learning", type="primary", icon=":material/play_arrow:"):
                resume(*current)
        else:
            first = next(iter(LESSONS.values()))
            text, art = st.columns([3, 1], vertical_alignment="center")
            with text:
                st.markdown(f"### {first.title}")
                st.caption(f"{TOPIC_BY_ID[first.topic].title} · about {first.minutes} minutes · no prerequisites")
                st.markdown(first.objective)
            with art:
                st.html(f'<div class="ld-thumb-wrap">{svg_img(visuals.thumbnail(first.topic), "", "ld-thumb")}</div>')
            with st.container(horizontal=True, gap="small"):
                if st.button("Start with the first lesson", type="primary", icon=":material/school:"):
                    open_lesson(first.id)
                if st.button("Read your own material", icon=":material/collections_bookmark:"):
                    st.session_state.pop("resource_id", None)
                    st.session_state.pop("active_quiz", None)
                    go("library")


def lesson_strip(progress: dict) -> str:
    """The signature element: one cell per finished lesson, grouped by topic, filled as you go.
    Built only from curriculum ids and stored statuses, escaped; the visible legend explains it."""
    groups = []
    for topic in TOPICS:
        ids = [lid for lid in topic.lessons if lid in LESSONS]
        if not ids:  # planned topics have outlines only; there is nothing to fill in yet
            continue
        states = [learn.status(lid, progress) for lid in ids]
        cells = "".join(f'<span class="{"done" if s == "Completed" else "started" if s == "In progress" else ""}">'
                        f'</span>' for s in states)
        done = states.count("Completed")
        label = f"{topic.title}: {done} of {len(ids)} completed"
        groups.append(f'<li style="flex:{len(ids)} 1 0" role="img" aria-label="{escape(label, quote=True)}" title="{escape(label, quote=True)}">'
                      f'{cells}</li>')
    return f'<ul class="ld-strip" aria-label="Lessons by topic">{"".join(groups)}</ul>'


def today():
    show_flash()
    now = datetime.now()
    active = db.query("SELECT * FROM activity WHERE id=1")
    current = (active[0]["kind"], active[0]["target_id"], active[0].get("target_key")) if active else None
    label = activity_label(*current) if current else None
    progress = learn.all_progress()
    completed = sum(1 for lid in progress if learn.status(lid, progress) == "Completed")
    started = sum(1 for lid in progress if learn.status(lid, progress) == "In progress")
    notes = [n for n in db.query("SELECT * FROM lesson_notes ORDER BY updated_at DESC") if n["text"].strip()]
    night = now.hour < 6 or now.hour >= 18
    page_header(_greeting(now), f"{now:%A %d %B} · {completed} of {len(LESSONS)} lessons completed",
                _time_icon(now), "teal", art=pixels.img(pixels.desk_scene(night), 240))

    # Read order: where you left off and how far you are, a fresh idea and the wider map, what comes next,
    # then your own material.
    main, aside = st.columns([2, 1])
    with main:
        _continue_panel(current, label)
    with aside, st.container(border=True, key="panel-path", height="stretch"):
        ready_topics = sum(1 for t in TOPICS if any(lid in LESSONS for lid in t.lessons))
        heading("route", "Your progress", f"{len(LESSONS)} lessons across {ready_topics} topics")
        progress_ring(completed, started, len(LESSONS))
        st.html(lesson_strip(progress))
        st.caption("One bar per lesson, grouped by topic.")
        if "explore" in PAGES:
            st.page_link(PAGES["explore"], label="See all topics", icon=":material/map:")

    idea_col, tracks_col = st.columns([1, 2])
    with idea_col:
        _idea_of_the_day()
    with tracks_col:
        _track_tiles(progress)

    # The lesson already offered in the Continue panel is not repeated here.
    shown = current[2] if current and current[0] == "lesson" and label else (None if label else next(iter(LESSONS)))
    suggested = [l for l in learn.suggestions(progress, 4) if l.id != shown][:3]
    if suggested:
        heading("arrow_forward", "Next up", "Started lessons first, then ones you are ready for",
                large=True)
        cols = st.columns(3)
        for col, lesson in zip(cols, suggested):
            topic = TOPIC_BY_ID[lesson.topic]
            with col, st.container(border=True, key=f"card-next-{lesson.id}", height="stretch"):
                heading(topic.icon, lesson.title, f"{topic.title} · {lesson.minutes} min",
                        hue=TRACK_HUES[topic.track])
                st.html(f'<div class="ld-thumb-wrap">{svg_img(visuals.thumbnail(lesson.topic), "", "ld-thumb")}</div>')
                status_badge(learn.status(lesson.id, progress))
                verb = "Continue" if learn.status(lesson.id, progress) == "In progress" else "Open lesson"
                if st.button(verb, key=f"next-{lesson.id}", icon=":material/arrow_forward:"):
                    open_lesson(lesson.id)
        if len(suggested) < 3 and "explore" in PAGES:
            # Fewer suggestions than slots: the spare slot leads to the full map instead of sitting empty.
            with cols[len(suggested)], st.container(border=True, key="card-next-browse", height="stretch"):
                heading("explore", "Browse all topics", "Lessons can be read in any order", hue="teal")
                st.page_link(PAGES["explore"], label="Open Explore", icon=":material/arrow_forward:")

    heading("edit_note", "Your own material", "Stays on this computer unless you ask for AI help", large=True)
    notes_col, desk_col = st.columns(2)
    with notes_col, st.container(border=True, key="panel-notes", height="stretch"):
        heading("sticky_note_2", "Recent lesson notes", hue="violet")
        if not notes:
            empty_state("Notes you write beside a lesson appear here.")
        for note in notes[:3]:
            lesson = curriculum.get(note["lesson_id"])
            st.markdown(f"{lesson.title if lesson else note['lesson_id']}")
            first = note["text"].strip().splitlines()[0]
            st.caption(first if len(first) <= 90 else first[:first.rfind(" ", 0, 88)] + "…")
        if "notebook" in PAGES:
            st.page_link(PAGES["notebook"], label="All notes in Notebook", icon=":material/book_2:")
    with desk_col, st.container(border=True, key="panel-desk", height="stretch"):
        heading("collections_bookmark", "Library and queue", hue="amber")
        stats([("collections_bookmark", "Library resources", len(db.list_resources()), "", "amber"),
               ("book_2", "Notebook sessions", len(db.list_sessions()), "", "violet"),
               ("sticky_note_2", "Lesson notes", len(notes), "", "violet"),
               ("checklist", "Open questions and tasks", len(db.list_queue(status="open")), "", "green")])
        with st.container(horizontal=True, gap="small"):
            if "library" in PAGES:
                st.page_link(PAGES["library"], label="Library", icon=":material/collections_bookmark:")
            if "queue" in PAGES:
                st.page_link(PAGES["queue"], label="Queue", icon=":material/checklist:")

    with st.expander("Switch to another activity or start a notebook session", icon=":material/swap_horiz:"):
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
    page_header("Notebook", "Your sessions, lesson notes and earlier AI reviews. Opening anything here makes no "
                "model call.", "book_2", "violet", art=pixels.img(pixels.notebook_scene(), 224))
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
            empty_state("Notes you write beside a lesson appear here.")
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
