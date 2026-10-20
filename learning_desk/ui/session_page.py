"""The Session page: editor, AI review, understanding questions, linked queue, export."""

import json

import streamlit as st

from .. import ai, db, export, prompts
from .common import (add_queue_item_form, ai_privacy_note, ai_ready, fmt_time, inspect_call,
                     queue_item_row, safe_md, show_flash, flash)

FIELD_LABELS = {
    "title": "Title",
    "topic": "Topic",
    "goal": "What I want to understand",
    "explanation": "My current explanation",
    "notes": "Notes, observations and code excerpts",
    "sources": "Source URLs (optional)",
}

# ---------------------------------------------------------------- drafts
#
# Text you type lives in st.session_state["drafts"][session_id] until you save.
# Streamlit discards a widget's state when the widget is not drawn (for example
# after you switch pages), so each widget copies its value into the draft as you
# type, and is re-created from the draft when it is drawn again.


def _drafts() -> dict:
    return st.session_state.setdefault("drafts", {})


def _draft(session: dict) -> dict:
    drafts = _drafts()
    if session["id"] not in drafts:
        drafts[session["id"]] = {f: session[f] for f in db.SESSION_FIELDS}
    return drafts[session["id"]]


def _is_dirty(session: dict) -> bool:
    draft = _drafts().get(session["id"])
    return bool(draft) and any(draft[f] != session[f] for f in db.SESSION_FIELDS)


def _save(session: dict) -> str:
    """Write the draft to the database. Returns the saved timestamp."""
    return db.update_session(session["id"], dict(_draft(session)))


def _save_if_dirty(session: dict) -> None:
    if _is_dirty(session):
        ts = _save(session)
        flash("info", f"Saved your changes at {fmt_time(ts)} before sending.")


def _field(session: dict, field: str, *, height: int | None = None, help: str | None = None) -> None:
    key = f"w_{session['id']}_{field}"
    draft = _draft(session)
    if key not in st.session_state:
        st.session_state[key] = draft[field]

    def sync() -> None:
        draft[field] = st.session_state[key]

    if height is None:
        st.text_input(FIELD_LABELS[field], key=key, on_change=sync, help=help)
    else:
        st.text_area(FIELD_LABELS[field], key=key, on_change=sync, height=height, help=help)


# ---------------------------------------------------------------- page


def render() -> None:
    show_flash()
    session_id = st.session_state.get("current_session_id")
    session = db.get_session(session_id) if session_id else None
    if session is None:
        _pick_session()
        return

    st.title(session["title"] or "Untitled session")
    if session["is_example"]:
        st.info("This is a fictional example session created by Learning Desk.")

    notes, review, test, queue, exp = st.tabs(
        ["Notes", "Review this session", "Test my understanding", "Questions & next steps", "Export"])
    with notes:
        _notes_tab(session)
    with review:
        _review_tab(session)
    with test:
        _test_tab(session)
    with queue:
        _queue_tab(session)
    with exp:
        _export_tab(session)


def _pick_session() -> None:
    st.title("Session")
    sessions = db.list_sessions()
    if not sessions:
        st.write("No sessions yet. Start one from Home.")
        return
    choice = st.selectbox("Open a session", [s["id"] for s in sessions],
                          format_func=lambda i: next(s["title"] or "Untitled" for s in sessions if s["id"] == i))
    if st.button("Open"):
        st.session_state["current_session_id"] = choice
        st.rerun()


def _save_bar(session: dict, where: str) -> None:
    cols = st.columns([1, 4])
    if cols[0].button("Save", key=f"save_{where}", type="primary", use_container_width=True):
        ts = _save(session)
        flash("success", f"Saved at {fmt_time(ts)}.")
        st.rerun()
    if _is_dirty(session):
        cols[1].warning(f"Unsaved changes. Last saved {fmt_time(session['updated_at'])}.")
    else:
        cols[1].caption(f"All changes saved. Last saved {fmt_time(session['updated_at'])}.")


def _notes_tab(session: dict) -> None:
    _save_bar(session, "top")
    c1, c2 = st.columns(2)
    with c1:
        _field(session, "title")
    with c2:
        _field(session, "topic")
    _field(session, "goal", height=90)
    _field(session, "explanation", height=150,
           help="Explain it in your own words, as you understand it now. It is fine to be wrong.")
    _field(session, "notes", height=460,
           help="Markdown is supported, including ``` code fences. Pasted code is stored as text and never run.")
    if st.toggle("Preview notes as Markdown", key=f"preview_{session['id']}"):
        with st.container(border=True):
            st.markdown(safe_md(_draft(session)["notes"]) or "_(empty)_")
    _field(session, "sources", height=80,
           help="One URL per line. Listed for your reference; the app never fetches them.")
    st.caption("Unresolved questions and next steps live in the 'Questions & next steps' tab.")
    _save_bar(session, "bottom")


# ---------------------------------------------------------------- review


def _review_tab(session: dict) -> None:
    ai_privacy_note("the saved version of this session (all fields above plus its open questions "
                    "and next steps)")
    if _is_dirty(session):
        st.caption("You have unsaved changes. They will be saved first.")
    if st.button("Review this session", type="primary", disabled=not ai_ready()):
        _save_if_dirty(session)
        with st.spinner("Waiting for the model. This can take up to a minute..."):
            result = ai.review_session(session["id"])
        if result.ok:
            flash("success", "Review received.")
            for w in result.warnings:
                flash("warning", w)
        else:
            flash("error", f"Review failed. Your notes are unchanged. {result.error}")
        st.rerun()

    reviews = db.list_ai_calls(session["id"], action="review", status="ok")
    failures = db.list_ai_calls(session["id"], action="review", status="error")
    if not reviews:
        st.write("No reviews yet.")
    else:
        labels = {c["id"]: f"{fmt_time(c['created_at'])} · snapshot #{c['snapshot_id']}" for c in reviews}
        compare = len(reviews) > 1 and st.toggle("Compare two reviews side by side")
        if compare:
            left, right = st.columns(2)
            with left:
                a = st.selectbox("Review A", list(labels), format_func=labels.get, index=1)
                _render_review(session, next(c for c in reviews if c["id"] == a), compact=True)
            with right:
                b = st.selectbox("Review B", list(labels), format_func=labels.get, index=0)
                _render_review(session, next(c for c in reviews if c["id"] == b), compact=True)
        else:
            chosen = st.selectbox("Showing review from", list(labels), format_func=labels.get)
            _render_review(session, next(c for c in reviews if c["id"] == chosen))
    if failures:
        st.markdown("#### Failed attempts")
        st.caption("Kept for inspection. Nothing from these was used.")
        for call in failures[:5]:
            inspect_call(call)


def _render_review(session: dict, call: dict, compact: bool = False) -> None:
    review = prompts.Review.model_validate_json(call["parsed_json"])
    snapshot = db.get_snapshot(call["snapshot_id"])["content"]
    sections_by_id = {s["id"]: s for s in snapshot["sections"]}
    changed = any(snapshot[f] != session[f] for f in db.SESSION_FIELDS)

    with st.container(border=True):
        st.markdown(f"**AI feedback** · generated by `{call['returned_model'] or call['requested_model']}` "
                    f"on {fmt_time(call['created_at'])} · instructions `{call['prompt_version']}`")
        if changed:
            st.caption("Your notes have changed since this review. Cited text below is from the snapshot "
                       "the model saw, not your current notes.")
        st.markdown(safe_md(review.summary))

        st.markdown("##### Grounded in your notes")
        st.caption("Each point cites the numbered note sections it is based on. Check the cited text.")
        _grounded_list("Observations you recorded", review.observations, sections_by_id)
        _grounded_list("Your interpretations or assumptions", review.interpretations, sections_by_id)
        if review.possible_gaps:
            st.markdown("**Possible gaps or misconceptions** (hypotheses to check, not verdicts)")
            for g in review.possible_gaps:
                st.markdown(safe_md(f"- {g.hypothesis}\n\n  *How to check:* {g.how_to_check}"))
                _cited_text(g.section_refs, sections_by_id)
        _grounded_list("Suggested experiments or questions", review.suggested_experiments, sections_by_id)

    if review.general_explanations:
        with st.container(border=True):
            st.markdown("##### General explanations from the model")
            st.caption("Background the model supplied from its general training. Not from your notes and "
                       "not checked against a source. Verify before relying on it.")
            for g in review.general_explanations:
                st.markdown(safe_md(f"**{g.topic}.** {g.explanation}"))

    if not compact:
        _suggested_steps(session, call, review)
    inspect_call(call)


def _grounded_list(title: str, items, sections_by_id: dict) -> None:
    if not items:
        return
    st.markdown(f"**{title}**")
    for item in items:
        st.markdown(safe_md(f"- {item.text}"))
        _cited_text(item.section_refs, sections_by_id)


def _cited_text(refs: list[int], sections_by_id: dict) -> None:
    if not refs:
        st.caption("No note section cited.")
        return
    with st.expander("Cited: " + ", ".join(f"S{r}" for r in refs)):
        for r in refs:
            s = sections_by_id.get(r)
            if s is None:
                st.warning(f"S{r} does not exist in the snapshot. The model cited a section that is not there.")
            else:
                st.markdown(f"**S{r} · {s['label']}**")
                st.markdown(safe_md(s["text"]))


def _suggested_steps(session: dict, call: dict, review: prompts.Review) -> None:
    if not review.suggested_next_steps:
        return
    st.markdown("##### Suggested next steps")
    st.caption("Edit a suggestion if you like, then add it to your queue. Nothing is added automatically.")
    added = {q["source"] for q in db.list_queue(session_id=session["id"]) if q["source_call_id"] == call["id"]}
    for i, step in enumerate(review.suggested_next_steps):
        source = f"ai_suggestion:{i}"
        key = f"sug_{call['id']}_{i}"
        if source in added:
            st.markdown(safe_md(f"- ~~{step.text}~~ (added to queue)"))
            continue
        cols = st.columns([1.2, 6, 1.4, 1.4])
        kind = cols[0].selectbox("Type", db.QUEUE_KINDS, index=db.QUEUE_KINDS.index(step.kind),
                                 key=f"{key}_kind", label_visibility="collapsed")
        text = cols[1].text_input("Suggestion", value=step.text, key=f"{key}_text", label_visibility="collapsed")
        priority = cols[2].selectbox("Priority", db.PRIORITIES, index=1, key=f"{key}_prio",
                                     label_visibility="collapsed")
        if cols[3].button("Add", key=f"{key}_add", use_container_width=True):
            if text.strip():
                db.add_queue_item(session["id"], kind, text, priority, source=source, source_call_id=call["id"])
                flash("success", "Added to your queue.")
                st.rerun()


# ---------------------------------------------------------------- understanding questions


def _test_tab(session: dict) -> None:
    sets = db.list_question_sets(session["id"])
    ai_privacy_note("the saved version of this session")
    label = "Generate a new set of questions" if sets else "Generate three questions"
    if st.button(label, type="primary", disabled=not ai_ready()):
        _save_if_dirty(session)
        with st.spinner("Writing questions..."):
            result = ai.generate_questions(session["id"])
        if result.ok:
            flash("success", "Questions ready. Answer them before asking for feedback.")
        else:
            flash("error", f"Could not generate questions. Your notes are unchanged. {result.error}")
        st.rerun()

    for call in db.list_ai_calls(session["id"], action="questions", status="error")[:3]:
        inspect_call(call)
    if not sets:
        return

    labels = {s["id"]: f"{fmt_time(s['created_at'])} · snapshot #{s['snapshot_id']}" for s in sets}
    chosen = st.selectbox("Question set", list(labels), format_func=labels.get)
    qset = next(s for s in sets if s["id"] == chosen)
    st.caption("Questions only: no answers or hints were requested. Write your own answer first.")
    for q in qset["questions"]:
        _question_block(session, q)
    inspect_call(db.get_ai_call(qset["ai_call_id"]))


def _question_block(session: dict, q: dict) -> None:
    with st.container(border=True):
        st.markdown(f"**{export.KIND_LABELS.get(q['kind'], q['kind'])} question**")
        st.markdown(safe_md(q["text"]))
        # Same draft pattern as the notes fields, so an unsubmitted answer survives page switches.
        key = f"ans_{q['id']}"
        answer_drafts = st.session_state.setdefault("answer_drafts", {})
        if key not in st.session_state:
            st.session_state[key] = answer_drafts.get(q["id"], q["answer"])

        def sync() -> None:
            answer_drafts[q["id"]] = st.session_state[key]

        st.text_area("Your answer", key=key, height=160, on_change=sync)
        typed = st.session_state[key]
        unsaved = typed != q["answer"]

        cols = st.columns([1, 1.6, 3])
        if cols[0].button("Submit answer", key=f"{key}_save"):
            if not typed.strip():
                st.warning("Write an answer first.")
            else:
                db.save_answer(q["id"], typed)
                answer_drafts.pop(q["id"], None)
                flash("success", "Answer saved.")
                st.rerun()
        can_ask = bool(q["answer"].strip()) and not unsaved and ai_ready()
        if cols[1].button("Get feedback on my answer", key=f"{key}_fb", disabled=not can_ask):
            _save_if_dirty(session)
            with st.spinner("Reading your answer..."):
                result = ai.answer_feedback(q["id"])
            if result.ok:
                flash("success", "Feedback received.")
            else:
                flash("error", f"Feedback failed. Your answer is saved and unchanged. {result.error}")
            st.rerun()
        if unsaved:
            cols[2].caption("Submit your answer to enable feedback.")
        elif not q["answer"].strip():
            cols[2].caption("Feedback becomes available after you submit an answer.")

        calls = db.list_ai_calls(session["id"], action="answer_feedback", question_id=q["id"])
        ok_calls = [c for c in calls if c["status"] == "ok"]
        if ok_calls:
            _render_feedback(q, ok_calls[0])
        for c in calls:
            if c["status"] == "error":
                inspect_call(c)
                break


def _render_feedback(q: dict, call: dict) -> None:
    fb = prompts.AnswerFeedback.model_validate_json(call["parsed_json"])
    with st.container(border=True):
        st.markdown(f"**AI feedback** · `{call['returned_model'] or call['requested_model']}` · "
                    f"{fmt_time(call['created_at'])}")
        sent_text = json.loads(call["request_json"])["messages"][0]["content"]
        if f"<answer>\n{q['answer']}\n</answer>" not in sent_text:
            st.caption("You edited your answer after this feedback was written.")
        st.caption("A second opinion, not a grade. The model can be wrong.")
        st.markdown("**What your answer explains well**")
        st.markdown(safe_md("\n".join(f"- {p}" for p in fb.explains_well) or "_Nothing identified._"))
        st.markdown("**Missing or possibly incorrect**")
        st.markdown(safe_md("\n".join(f"- {m.point} — {m.why}" for m in fb.missing_or_possibly_incorrect)
                            or "_Nothing identified._"))
        st.markdown("**Suggested follow-up exercise**")
        st.markdown(safe_md(fb.follow_up_exercise))
    inspect_call(call)


# ---------------------------------------------------------------- queue and export


def _queue_tab(session: dict) -> None:
    st.caption("Questions and tasks linked to this session. Edits save when you leave a field.")
    items = db.list_queue(session_id=session["id"])
    open_items = [i for i in items if i["status"] == "open"]
    done_items = [i for i in items if i["status"] == "done"]
    if not open_items:
        st.write("Nothing open.")
    for item in open_items:
        queue_item_row(item, ctx="sess", show_session=False)
    add_queue_item_form("sess", session_id=session["id"])
    if done_items:
        with st.expander(f"Completed ({len(done_items)})"):
            for item in done_items:
                queue_item_row(item, ctx="sessdone", show_session=False)


def _export_tab(session: dict) -> None:
    st.write("Download this session as Markdown: your notes, questions and next steps, "
             "AI reviews, understanding questions, answers and feedback. Works offline.")
    if _is_dirty(session):
        st.warning("Unsaved changes are not included. Save first.")
    st.download_button("Download Markdown", data=export.session_markdown(session["id"]),
                       file_name=f"learning-desk-session-{session['id']}.md", mime="text/markdown")
