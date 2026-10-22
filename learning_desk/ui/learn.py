"""Explore the curriculum and read built-in lessons. Nothing on these pages calls a model: lessons are
static reviewed content, and the only AI-related action (saving a lesson to the Library) just stores text."""

import streamlit as st

from .. import curriculum, db, visuals
from ..curriculum import LESSONS, OUTLINES, SOURCES, TOPIC_BY_ID, TOPICS, VIEWS
from ..curriculum.model import Lesson
from . import widgets
from .common import go, open_lesson, show_flash
from .theme import LEVEL_COLOURS, badges, status_badge, svg_img

VIEW_ICONS = {"Overview": ":material/dashboard:", "Walkthrough": ":material/route:",
              "Try it": ":material/science:", "Sources": ":material/library_books:"}


# ---------------------------------------------------------------- progress helpers

def status(lesson_id: str, progress: dict | None = None) -> str:
    if lesson_id in OUTLINES:
        return "Outline"
    row = progress.get(lesson_id) if progress is not None else db.lesson_progress(lesson_id)
    if not row:
        return "Ready"
    return "Completed" if row["status"] == "completed" else "In progress"


def all_progress() -> dict:
    return {row["lesson_id"]: row for row in db.lesson_progress()}


def suggestions(progress: dict, n: int = 3) -> list[Lesson]:
    """In-progress lessons first, then unstarted lessons whose prerequisites are complete, in map order."""
    ordered = [LESSONS[lid] for t in TOPICS for lid in t.lessons if lid in LESSONS]
    started = [l for l in ordered if status(l.id, progress) == "In progress"]
    done = {lid for lid in progress if status(lid, progress) == "Completed"}
    ready = [l for l in ordered if l.id not in progress and set(l.prerequisites) <= done]
    return (started + ready)[:n]


def topic_counts(topic_id: str, progress: dict) -> tuple[int, int, int]:
    ids = TOPIC_BY_ID[topic_id].lessons
    ready = [lid for lid in ids if lid in LESSONS]
    completed = [lid for lid in ready if status(lid, progress) == "Completed"]
    return len(ready), len(ids) - len(ready), len(completed)


def lesson_resource(lesson_id: str) -> dict | None:
    rows = db.query("SELECT * FROM resources WHERE tags LIKE ? ORDER BY id", (f"%lesson:{lesson_id}%",))
    return rows[0] if rows else None


# ---------------------------------------------------------------- Explore

def lesson_card(item, progress: dict, ctx: str) -> None:
    label = status(item.id, progress)
    is_outline = item.id in OUTLINES
    with st.container(border=True, key=f"{'muted-card' if is_outline else 'card'}-{ctx}-{item.id}"):
        with st.container(horizontal=True, gap="small"):
            status_badge(label)
            if not is_outline:
                st.badge(item.level, color=LEVEL_COLOURS[item.level])
                st.badge(f"{item.minutes} min", icon=":material/schedule:", color="gray")
        st.markdown(f"**{item.title}**")
        st.caption(item.objective)
        if is_outline:
            st.caption("Planned content, not yet written: " + "; ".join(item.planned) + ".")
        else:
            if item.prerequisites:
                st.caption("Builds on: " + ", ".join(LESSONS[p].title for p in item.prerequisites))
            verb = {"Completed": "Review lesson", "In progress": "Continue lesson"}.get(label, "Open lesson")
            if st.button(verb, key=f"open-{ctx}-{item.id}", icon=":material/arrow_forward:"):
                open_lesson(item.id)


def explore() -> None:
    show_flash()
    progress = all_progress()
    topic_id = st.query_params.get("topic") or st.session_state.get("explore_topic")
    if topic_id in TOPIC_BY_ID:
        st.session_state["explore_topic"] = topic_id
        return topic_page(TOPIC_BY_ID[topic_id], progress)

    st.title("Explore")
    st.write(f"Ten topics for building with language models, from Python data shapes to product trade-offs. "
             f"{len(LESSONS)} lessons are ready to read; the rest are clearly marked outlines.")
    query = st.text_input("Search lessons", placeholder="e.g. tokens, JSON, retrieval, latency",
                          key="explore_search")
    if query.strip():
        found = curriculum.search(query)
        st.caption(f"{len(found)} lesson(s) match “{query.strip()}”.")
        cols = st.columns(2)
        for i, lesson in enumerate(found):
            with cols[i % 2]:
                lesson_card(lesson, progress, "search")
        if not found:
            st.info("No finished lesson matches. Try a broader word, or browse the topics below.",
                    icon=":material/search_off:")
        st.divider()

    picks = suggestions(progress)
    if picks:
        st.subheader("Suggested next")
        cols = st.columns(len(picks))
        for col, lesson in zip(cols, picks):
            with col:
                lesson_card(lesson, progress, "suggested")

    st.subheader("The map")
    st.caption("Each topic lists finished lessons first and planned outlines after. Open any topic; there is no fixed order.")
    cols = st.columns(2)
    for i, topic in enumerate(TOPICS):
        ready, planned, completed = topic_counts(topic.id, progress)
        with cols[i % 2], st.container(border=True, key=f"card-topic-{topic.id}"):
            art, text = st.columns([1, 2.6], vertical_alignment="center")
            with art:
                st.html(svg_img(visuals.thumbnail(topic.id), "", "ld-thumb"))
            with text:
                st.caption(f"TOPIC {topic.number}")
                st.markdown(f":material/{topic.icon}: **{topic.title}**")
                st.caption(topic.blurb)
            st.progress(completed / ready if ready else 0.0,
                        text=f"{completed} of {ready} lessons completed · {planned} planned")
            if st.button("Open topic", key=f"topic-{topic.id}", icon=":material/arrow_forward:"):
                st.session_state["explore_topic"] = topic.id
                st.query_params["topic"] = topic.id
                st.rerun()


def topic_page(topic, progress: dict) -> None:
    if st.button("All topics", icon=":material/arrow_back:", key="back-to-map"):
        st.session_state.pop("explore_topic", None)
        st.query_params.pop("topic", None)
        st.rerun()
    st.caption(f"TOPIC {topic.number} OF {len(TOPICS)}")
    st.title(f":material/{topic.icon}: {topic.title}")
    st.write(topic.blurb)
    st.caption(f"Why it matters: {topic.why}")
    ready, planned, completed = topic_counts(topic.id, progress)
    st.progress(completed / ready if ready else 0.0,
                text=f"{completed} of {ready} finished lessons completed · {planned} outline(s) planned")
    for item in curriculum.topic_items(topic.id):
        lesson_card(item, progress, "topic")
    others = [t for t in TOPICS if t.id != topic.id]
    nxt = next((t for t in others if t.number == topic.number + 1), None)
    if nxt and st.button(f"Next topic: {nxt.title}", key="next-topic", icon=":material/arrow_forward:"):
        st.session_state["explore_topic"] = nxt.id
        st.query_params["topic"] = nxt.id
        st.rerun()


# ---------------------------------------------------------------- Lesson page

def _current_lesson_id() -> str | None:
    wanted = st.query_params.get("id") or st.session_state.get("lesson_id")
    if not wanted:
        active = db.query("SELECT * FROM activity WHERE id=1 AND kind='lesson'")
        wanted = active[0]["target_key"] if active else None
    return wanted


def _set_view(lesson: Lesson, view: str, section: str | None = None) -> None:
    """Callback: change view (and optionally section) and remember the place."""
    st.session_state[f"view_{lesson.id}"] = view
    if section:
        st.session_state[f"section_{lesson.id}"] = section
    db.save_lesson_place(lesson.id, lesson.version, view=view, section=section)


def _save_view(lesson: Lesson) -> None:
    db.save_lesson_place(lesson.id, lesson.version, view=st.session_state[f"view_{lesson.id}"])


def _save_section(lesson: Lesson) -> None:
    db.save_lesson_place(lesson.id, lesson.version, section=st.session_state[f"section_{lesson.id}"])


def _save_note(lesson: Lesson) -> None:
    try:
        db.save_lesson_note(lesson.id, lesson.version, st.session_state[f"note_{lesson.id}"])
        st.session_state[f"note_saved_{lesson.id}"] = db.now()
    except ValueError as exc:
        st.session_state[f"note_error_{lesson.id}"] = str(exc)


def lesson_page() -> None:
    show_flash()
    lesson_id = _current_lesson_id()
    if lesson_id in OUTLINES:
        outline = OUTLINES[lesson_id]
        st.title(outline.title)
        status_badge("Outline")
        st.info("This lesson is planned but not written yet, so there is nothing to read here.",
                icon=":material/edit_note:")
        st.write("**Planned objective:** " + outline.objective)
        st.markdown("\n".join(f"- {p}" for p in outline.planned))
        if st.button("Back to Explore", icon=":material/arrow_back:"):
            go("explore")
        return
    lesson = LESSONS.get(lesson_id or "")
    if lesson is None:
        st.title("Lesson")
        st.info("Choose a lesson from Explore to start reading.", icon=":material/explore:")
        if st.button("Open Explore", type="primary"):
            go("explore")
        return

    st.session_state["lesson_id"] = lesson.id
    if st.query_params.get("id") != lesson.id:
        st.query_params["id"] = lesson.id
    progress = db.lesson_progress(lesson.id)
    if progress is None:
        db.save_lesson_place(lesson.id, lesson.version)
        progress = db.lesson_progress(lesson.id)
    active = db.query("SELECT * FROM activity WHERE id=1")
    if not active or active[0]["kind"] != "lesson" or active[0]["target_key"] != lesson.id:
        db.set_activity("lesson", 0, key=lesson.id)
    view_key, section_key = f"view_{lesson.id}", f"section_{lesson.id}"
    section_ids = [s.id for s in lesson.walkthrough()]
    if view_key not in st.session_state:
        st.session_state[view_key] = progress["view"] if progress["view"] in VIEWS else "Overview"
    if st.session_state.get(section_key) not in section_ids:
        st.session_state[section_key] = progress["section"] if progress["section"] in section_ids else section_ids[0]

    topic = TOPIC_BY_ID[lesson.topic]
    if st.button(f"{topic.title}", icon=":material/arrow_back:", key="back-to-topic", type="tertiary"):
        st.session_state["explore_topic"] = topic.id
        go("explore", topic=topic.id)
    st.title(lesson.title)
    label = status(lesson.id)
    badges((label, *_badge_style(label)), (lesson.level, LEVEL_COLOURS[lesson.level], None),
           (f"{lesson.minutes} min", "gray", ":material/schedule:"),
           ("Original content", "gray", ":material/verified:"))
    st.caption(lesson.summary)

    st.segmented_control("View", VIEWS, key=view_key, required=True, label_visibility="collapsed", wrap=True,
                         format_func=lambda v: f"{VIEW_ICONS[v]} {v}", on_change=_save_view, args=(lesson,))
    main, side = st.columns([2.7, 1], gap="large")
    with main:
        view = st.session_state[view_key]
        if view == "Overview":
            overview(lesson)
        elif view == "Walkthrough":
            walkthrough(lesson)
        elif view == "Try it":
            try_it(lesson)
        else:
            sources_view(lesson)
    with side:
        side_panel(lesson)


def _badge_style(label: str):
    from .theme import STATUS_STYLE
    return STATUS_STYLE[label]


def overview(lesson: Lesson) -> None:
    with st.container(border=True, key=f"objective-{lesson.id}"):
        st.markdown(f":material/flag: **Learning objective**  \n{lesson.objective}")
    if lesson.prerequisites:
        st.markdown("**Before you start**")
        progress = all_progress()
        for pid in lesson.prerequisites:
            prereq = LESSONS[pid]
            c1, c2 = st.columns([3, 1.2], vertical_alignment="center")
            c1.markdown(f"{prereq.title} · *{status(pid, progress).lower()}*")
            if c2.button("Open", key=f"prereq-{pid}"):
                open_lesson(pid)
    else:
        st.caption(":material/check: No prerequisites: a good place to start.")
    with st.container(key=f"prose-intro-{lesson.id}"):
        st.markdown(lesson.intro)
        st.markdown("**Key ideas**")
        st.markdown("\n".join(f"- {idea}" for idea in lesson.key_ideas))
    widgets.render(lesson.overview_visual, key=f"{lesson.id}-overview")
    if lesson.scope:
        st.caption(f":material/travel_explore: **Scope:** {lesson.scope}")
    st.markdown("**Choose how to continue**")
    with st.container(horizontal=True, gap="small"):
        st.button("Walk through it", type="primary", icon=VIEW_ICONS["Walkthrough"], key="go-walk",
                  on_click=_set_view, args=(lesson, "Walkthrough"))
        st.button("Try it first", icon=VIEW_ICONS["Try it"], key="go-try", on_click=_set_view, args=(lesson, "Try it"))
        st.button("See sources", icon=VIEW_ICONS["Sources"], key="go-sources", on_click=_set_view,
                  args=(lesson, "Sources"))
    if lesson.related:
        st.caption("Related: " + " · ".join(LESSONS[r].title for r in lesson.related if r in LESSONS))


def render_section(lesson: Lesson, section, ctx: str) -> None:
    st.subheader(section.title, anchor=f"{lesson.id}-{section.id}")
    with st.container(key=f"prose-{ctx}-{section.id}"):
        st.markdown(section.body)
    if section.visual:
        widgets.render(section.visual, key=f"{lesson.id}-{ctx}-{section.id}")
    if section.table:
        table = section.table
        st.table({col: [row[i] for row in table.rows] for i, col in enumerate(table.columns)}, hide_index=True)
        if table.caption:
            st.caption(table.caption)
    if section.code:
        code = section.code
        st.code(code.source, language=code.language, line_numbers=True, wrap_lines=True)
        if code.caption:
            st.caption(f":material/code: {code.caption}. Shown as text; nothing here is run.")
        if code.notes:
            st.markdown("\n".join(f"- **Line {n}:** {note}" for n, note in code.notes))
    if section.callout:
        st.info(section.callout, icon=":material/lightbulb:")


def walkthrough(lesson: Lesson) -> None:
    sections = lesson.walkthrough()
    titles = {s.id: s.title for s in sections}
    section_key = f"section_{lesson.id}"
    all_key = f"all_sections_{lesson.id}"
    show_all = st.toggle("Show all sections on one page", key=all_key)
    if show_all:
        for section in sections:
            render_section(lesson, section, "all")
            st.divider()
        st.button("Continue to Try it", type="primary", icon=VIEW_ICONS["Try it"], key="walk-try-all",
                  on_click=_set_view, args=(lesson, "Try it"))
        return
    st.pills("Section", [s.id for s in sections], key=section_key, required=True, wrap=True,
             format_func=lambda sid: f"{[s.id for s in sections].index(sid) + 1}. {titles[sid]}",
             on_change=_save_section, args=(lesson,))
    current = st.session_state[section_key]
    index = [s.id for s in sections].index(current)
    render_section(lesson, sections[index], "walk")
    st.divider()
    with st.container(horizontal=True, gap="small"):
        if index > 0:
            prev = sections[index - 1]
            st.button(f"Previous: {prev.title}", icon=":material/arrow_back:", key="walk-prev",
                      on_click=_set_view, args=(lesson, "Walkthrough", prev.id))
        if index < len(sections) - 1:
            nxt = sections[index + 1]
            st.button(f"Next: {nxt.title}", type="primary", icon=":material/arrow_forward:", key="walk-next",
                      on_click=_set_view, args=(lesson, "Walkthrough", nxt.id))
        else:
            st.button("Continue to Try it", type="primary", icon=VIEW_ICONS["Try it"], key="walk-try",
                      on_click=_set_view, args=(lesson, "Try it"))


def _next_check(lesson: Lesson, step: int) -> None:
    key = f"check_pos_{lesson.id}"
    st.session_state[key] = max(0, st.session_state.get(key, 0) + step)


def quick_check(lesson: Lesson) -> None:
    pos_key = f"check_pos_{lesson.id}"
    pos = min(st.session_state.get(pos_key, 0), len(lesson.checks))
    st.subheader("Quick check")
    st.caption("Fixed questions written with the lesson and marked by simple comparison: no model is involved. "
               "Every answer you submit is saved.")
    if pos >= len(lesson.checks):
        attempts = db.check_attempts(lesson.id)
        latest = {}
        for a in attempts:
            latest[a["check_id"]] = a
        right = sum(a["correct"] for a in latest.values())
        st.success(f"Done: {right} of {len(lesson.checks)} matched the expected answer on your latest try.",
                   icon=":material/task_alt:")
        st.button("Go through the questions again", key="check-restart", on_click=_next_check,
                  args=(lesson, -len(lesson.checks)))
        return
    check = lesson.checks[pos]
    st.progress((pos) / len(lesson.checks), text=f"Question {pos + 1} of {len(lesson.checks)}")
    st.markdown(f"**{check.prompt}**")
    result_key = f"check_result_{lesson.id}_{check.id}"
    choice = st.radio("Your answer", check.options, index=None, key=f"check_{lesson.id}_{check.id}")
    if st.button("Check answer", type="primary", key=f"check-submit-{check.id}"):
        if choice is None:
            st.warning("Choose an answer first.", icon=":material/touch_app:")
        else:
            correct = choice == check.answer
            db.add_check_attempt(lesson.id, lesson.version, check.id, choice, correct)
            st.session_state[result_key] = (choice, correct)
    result = st.session_state.get(result_key)
    if result:
        answered, correct = result
        if correct:
            st.success(f"Yes. {check.explanation}", icon=":material/check_circle:")
        else:
            st.warning(f"Not quite: the expected answer is “{check.answer}”. {check.explanation}",
                       icon=":material/help:")
        section = next(s for s in lesson.walkthrough() if s.id == check.section)
        with st.container(horizontal=True, gap="small"):
            st.button(f"Revisit: {section.title}", icon=":material/menu_book:", key=f"revisit-{check.id}",
                      on_click=_set_view, args=(lesson, "Walkthrough", section.id))
            st.button("Next question" if pos < len(lesson.checks) - 1 else "Finish", type="primary",
                      key=f"check-next-{check.id}", on_click=_next_check, args=(lesson, 1))
    earlier = db.check_attempts(lesson.id, check.id)
    if len(earlier) > 1:
        st.caption(f"You have answered this question {len(earlier)} times; every attempt is kept.")


def try_it(lesson: Lesson) -> None:
    activity = lesson.activity
    st.subheader(activity.title)
    with st.container(key=f"prose-try-{lesson.id}"):
        st.markdown("\n".join(f"{i}. {step}" for i, step in enumerate(activity.steps, 1)))
    if activity.widget:
        widgets.render(activity.widget, key=f"{lesson.id}-try")
    if activity.reflection:
        st.info(activity.reflection, icon=":material/psychology:")
    st.divider()
    quick_check(lesson)
    st.divider()
    personalised(lesson)


def personalised(lesson: Lesson) -> None:
    st.subheader("Optional: a personalised AI explanation or quiz")
    resource = lesson_resource(lesson.id)
    st.write("The lesson above is fixed text that makes no model calls. If you want an AI-written explanation "
             "or a generated quiz, save this exact lesson version to your Library first. Generation then "
             "happens only when you press a button there, uses your configured provider (a paid call), and "
             "is labelled as AI output with citations to this version.")
    label = "Open it in the Library" if resource else "Save this lesson to the Library"
    if st.button(label, icon=":material/local_library:", key="lesson-to-library"):
        rid = save_to_library(lesson)
        st.session_state["resource_id"] = rid
        st.session_state.pop("active_quiz", None)
        db.set_activity("resource", rid)
        go("library")


def save_to_library(lesson: Lesson) -> int:
    """Store the lesson text as a Library resource version. No model call; repeat saves reuse the version."""
    resource = lesson_resource(lesson.id)
    rid = resource["id"] if resource else db.save_resource(
        lesson.title, "documentation", "", f"lesson:{lesson.id}, {TOPIC_BY_ID[lesson.topic].title}", lesson.level)
    db.add_content(rid, curriculum.lesson_markdown(lesson), "",
                   f"Learning Desk lesson {lesson.id}, version {lesson.version}: {lesson.provenance.lower()}")
    return rid


def sources_view(lesson: Lesson) -> None:
    with st.container(border=True, key=f"objective-provenance-{lesson.id}"):
        st.markdown(f":material/verified: **About this lesson**  \n{lesson.provenance}. Version {lesson.version}. "
                    f"Links and the specific claims cited below were checked on {lesson.checked}. "
                    "No part of the lesson text was generated during your session.")
    if lesson.scope:
        st.caption(f":material/travel_explore: **General versus specific:** {lesson.scope}")
    st.subheader("Sources")
    for cite in lesson.citations:
        _source_row(cite)
    if lesson.further_reading:
        st.subheader("Deeper reading")
        for cite in lesson.further_reading:
            _source_row(cite)
    st.subheader("Visuals in this lesson")
    used = dict.fromkeys(v for v in [lesson.overview_visual, lesson.activity.widget,
                                     *[s.visual for s in lesson.walkthrough()]] if v)
    for vid in used:
        visual = visuals.VISUALS[vid]
        note = f" Illustrative: {visual.illustrative}" if visual.illustrative else ""
        kind = "interactive example" if visual.interactive else "diagram"
        st.markdown(f"- **{visual.title}**: original {kind} produced by Learning Desk's own code "
                    f"(`learning_desk/visuals.py`, MIT licence); no AI-generated or external images.{note}")
    resource = lesson_resource(lesson.id)
    st.subheader("Personalised AI explanations")
    if not resource:
        st.caption("None. AI explanations exist only if you save this lesson to the Library and request one there.")
        return
    summaries = db.query("SELECT s.kind, s.created_at, v.import_note FROM summaries s JOIN content_versions v "
                         "ON v.id=s.content_version_id WHERE v.resource_id=? ORDER BY s.id", (resource["id"],))
    if summaries:
        for s in summaries:
            st.markdown(f"- AI-generated *{'Quick read' if s['kind'] == 'quick' else 'Explain it'}* from "
                        f"{s['import_note']} ({s['created_at']})")
    else:
        st.caption("Saved to the Library; no AI explanation requested yet.")
    if st.button("Open in the Library", key="sources-library"):
        st.session_state["resource_id"] = resource["id"]
        go("library")


def _source_row(cite) -> None:
    source = SOURCES[cite.source]
    if source.kind == "This app's code":
        head = f"**{source.title}**"
        checked = f":material/check_circle: described behaviour checked against the code {source.checked}"
    else:
        head = f"**[{source.title}]({source.url})** · {source.publisher}"
        checked = (f":material/check_circle: link and cited claim checked {source.checked}" if source.checked
                   else ":material/warning: unverified link")
    st.markdown(f"{head}  \n{cite.supports}  \n:gray[{source.kind} · {checked}]")


def side_panel(lesson: Lesson) -> None:
    with st.container(border=True, key=f"side-{lesson.id}"):
        label = status(lesson.id)
        st.markdown("**Your progress**")
        status_badge(label)
        done = label == "Completed"
        if st.button("Mark as not complete" if done else "Mark lesson complete", key="toggle-complete",
                     icon=":material/undo:" if done else ":material/task_alt:", use_container_width=True):
            db.set_lesson_status(lesson.id, lesson.version, not done)
            st.rerun()
        st.markdown("**In this lesson**")
        current = st.session_state.get(f"section_{lesson.id}")
        in_walk = st.session_state.get(f"view_{lesson.id}") == "Walkthrough"
        for i, section in enumerate(lesson.walkthrough(), 1):
            here = in_walk and section.id == current
            st.button(f"{i}. {section.title}", key=f"toc-{section.id}", type="secondary" if here else "tertiary",
                      on_click=_set_view, args=(lesson, "Walkthrough", section.id),
                      icon=":material/chevron_right:" if here else None)
    with st.container(border=True, key=f"notes-{lesson.id}"):
        note_key = f"note_{lesson.id}"
        if note_key not in st.session_state:
            saved = db.lesson_note(lesson.id)
            st.session_state[note_key] = saved["text"] if saved else ""
        st.text_area("My notes on this lesson", key=note_key, height=180, on_change=_save_note, args=(lesson,),
                     placeholder="Questions, examples, connections… Saved when you click away.")
        error = st.session_state.pop(f"note_error_{lesson.id}", None)
        if error:
            st.error(error)
        saved_at = st.session_state.get(f"note_saved_{lesson.id}")
        st.caption((f":material/save: Saved {saved_at[11:16]}. " if saved_at else "")
                   + "Stored on this computer; never sent to a model. Also listed in Notebook.")
