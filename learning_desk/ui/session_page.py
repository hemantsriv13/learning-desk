"""The Session page: editor, AI review, understanding questions, linked queue, export."""

import json

import streamlit as st

from .. import ai, db, export, prompts
from .common import (add_queue_item_form, ai_privacy_note, ai_ready, call_details, fmt_time,
                     inspect_call, queue_item_row, safe_md, show_flash, flash)

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
#
# The review tab shows one review at a time in a short, focused form: main takeaway, at most one
# thing to clarify, and one next step. Everything else sits in two collapsed sections. Opening
# them only reveals content that is already stored; it never contacts the model.
#
# Reviews stored in the old review-v1 format (summary plus several lists) are shown as they were
# stored, marked "older format".


def _pick_key(session: dict) -> str:
    return f"review_pick_{session['id']}"


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
            st.session_state.pop(_pick_key(session), None)  # show the new review
            flash("success", "Review received.")
            for w in result.warnings:
                flash("warning", w)
        else:
            flash("error", f"Review failed. Your notes are unchanged. {result.error}")
        st.rerun()

    reviews = db.list_ai_calls(session["id"], action="review", status="ok")
    failures = db.list_ai_calls(session["id"], action="review", status="error")
    labels = {c["id"]: _review_label(c) for c in reviews}
    call = None
    if not reviews:
        st.write("No reviews yet.")
    else:
        # The history picker lives in "Technical details" further down; read its last value here.
        chosen = st.session_state.get(_pick_key(session))
        call = next((c for c in reviews if c["id"] == chosen), reviews[0])
        review = prompts.parse_stored_review(call["prompt_version"], call["parsed_json"])
        snapshot = db.get_snapshot(call["snapshot_id"])["content"]
        sections_by_id = {s["id"]: s for s in snapshot["sections"]}
        changed = any(snapshot[f] != session[f] for f in db.SESSION_FIELDS)
        _render_focus(session, call, review, sections_by_id, changed)
        with st.expander("Supporting evidence"):
            _render_supporting(session, call, review, sections_by_id)
    if reviews or failures:
        with st.expander("Technical details"):
            _technical_details(session, call, reviews, labels, failures)


def _is_legacy(review) -> bool:
    return isinstance(review, prompts.ReviewV1)


def _review_label(call: dict) -> str:
    older = " · older format" if call["prompt_version"] == "review-v1" else ""
    return f"{fmt_time(call['created_at'])} · snapshot #{call['snapshot_id']}{older}"


def _refs_label(refs: list[int]) -> str:
    return f" _({', '.join(f'S{r}' for r in refs)})_" if refs else ""


def _render_focus(session: dict, call: dict, review, sections_by_id: dict, changed: bool) -> None:
    with st.container(border=True):
        older = " · older format" if _is_legacy(review) else ""
        st.markdown(f"**AI review** · {fmt_time(call['created_at'])}{older}")
        if changed:
            st.caption("Your notes have changed since this review. Cited text is from the snapshot "
                       "the model saw, not your current notes.")
        if _is_legacy(review):
            st.caption("Written before reviews were shortened, and shown as it was stored. "
                       "Its full lists are under Supporting evidence.")
            st.markdown("##### Summary")
            st.markdown(safe_md(review.summary))
            return

        st.markdown("##### Main takeaway")
        st.markdown(_emphasised(review.main_takeaway.text, review.main_takeaway.emphasis, "blue"))
        _cited_text(review.main_takeaway.section_refs, sections_by_id)
        if review.clarification:
            st.markdown("##### One thing to clarify")
            st.markdown(_emphasised(review.clarification.text, review.clarification.emphasis, "orange"))
            _cited_text(review.clarification.section_refs, sections_by_id)
        st.markdown("##### Next step")
        _next_step(session, call, review.next_step)


def _emphasised(text: str, phrase: str | None, colour: str) -> str:
    """Markdown for `text` with one phrase in bold and an accent colour. The colour names map to
    blueTextColor / orangeTextColor in .streamlit/config.toml; the model only chooses which words.
    A phrase that fails prompts.emphasis_problem() is ignored and the text is shown plain."""
    if prompts.emphasis_problem(text, phrase):
        return safe_md(text)
    start = text.find(phrase)
    end = start + len(phrase)
    return f"{safe_md(text[:start])}:{colour}[**{phrase}**]{safe_md(text[end:])}"


def _next_step(session: dict, call: dict, step: prompts.FocusedNextStep) -> None:
    st.markdown(f"**{step.kind.capitalize()}:** " + _emphasised(step.text, step.emphasis, "blue"))
    source = "ai_suggestion:next_step"
    saved = any(q["source"] == source and q["source_call_id"] == call["id"]
                for q in db.list_queue(session_id=session["id"]))
    if saved:
        st.caption("Saved to your queue.")
    elif st.button("Save to my queue", key=f"save_step_{call['id']}"):
        db.add_queue_item(session["id"], step.kind, step.text, "normal", source=source, source_call_id=call["id"])
        flash("success", "Saved to your queue.")
        st.rerun()


def _cited_text(refs: list[int], sections_by_id: dict) -> None:
    if not refs:
        st.caption("No note section cited.")
        return
    with st.expander("Cited: " + ", ".join(f"S{r}" for r in refs)):
        _section_texts(refs, sections_by_id)


def _section_texts(refs: list[int], sections_by_id: dict) -> None:
    for r in dict.fromkeys(refs):
        s = sections_by_id.get(r)
        if s is None:
            st.warning(f"S{r} does not exist in the snapshot. The model cited a section that is not there.")
        else:
            st.markdown(f"**S{r} · {s['label']}**")
            st.markdown(safe_md(s["text"]))


def _render_supporting(session: dict, call: dict, review, sections_by_id: dict) -> None:
    if _is_legacy(review):
        _legacy_lists(review)
    elif review.supporting_evidence:
        st.markdown("**From your notes**")
        st.markdown(safe_md("\n".join(f"- {i.text}{_refs_label(i.section_refs)}"
                                      for i in review.supporting_evidence)))

    if review.general_explanations:
        st.markdown("**From the model's general knowledge**")
        st.caption("Not from your notes and not checked against a source. Verify before relying on it.")
        st.markdown(safe_md("\n".join(f"- **{g.topic}.** {g.explanation}" for g in review.general_explanations)))

    refs = sorted(set(review.all_refs()))
    if refs:
        st.markdown("**Cited note sections**")
        st.caption("The text the model was given, from the snapshot it reviewed.")
        with st.container(border=True):
            _section_texts(refs, sections_by_id)
    elif _is_legacy(review) or not (review.supporting_evidence or review.general_explanations):
        st.caption("No note sections were cited.")

    if _is_legacy(review):
        _suggested_steps(session, call, review)


def _legacy_lists(review: prompts.ReviewV1) -> None:
    for title, items in (("Observations you recorded", review.observations),
                         ("Your interpretations or assumptions", review.interpretations),
                         ("Suggested experiments or questions", review.suggested_experiments)):
        if items:
            st.markdown(f"**{title}**")
            st.markdown(safe_md("\n".join(f"- {i.text}{_refs_label(i.section_refs)}" for i in items)))
    if review.possible_gaps:
        st.markdown("**Possible gaps or misconceptions** (hypotheses to check, not verdicts)")
        st.markdown(safe_md("\n".join(f"- {g.hypothesis} *How to check:* {g.how_to_check}"
                                      f"{_refs_label(g.section_refs)}" for g in review.possible_gaps)))


def _suggested_steps(session: dict, call: dict, review: prompts.ReviewV1) -> None:
    if not review.suggested_next_steps:
        return
    st.markdown("**Suggested next steps** (older format)")
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


def _technical_details(session: dict, call: dict | None, reviews: list[dict], labels: dict,
                       failures: list[dict]) -> None:
    if reviews:
        st.markdown("**Review history**")
        if len(reviews) == 1:
            st.caption("Only one review so far.")
        else:
            st.selectbox("Review shown above", list(labels), format_func=labels.get, key=_pick_key(session))
            if st.toggle("Compare two reviews side by side", key=f"compare_{session['id']}"):
                left, right = st.columns(2)
                with left:
                    a = st.selectbox("Review A", list(labels), format_func=labels.get, index=1)
                    _render_plain(next(c for c in reviews if c["id"] == a))
                with right:
                    b = st.selectbox("Review B", list(labels), format_func=labels.get, index=0)
                    _render_plain(next(c for c in reviews if c["id"] == b))
        st.markdown(f"**AI call for the review shown above** (#{call['id']})")
        call_details(call)
    if failures:
        st.markdown("**Failed attempts**")
        st.caption("Kept for inspection. Nothing from these was used.")
        failure_labels = {c["id"]: f"#{c['id']} · {fmt_time(c['created_at'])}" for c in failures}
        pick = st.selectbox("Failed attempt", list(failure_labels), format_func=failure_labels.get,
                            key=f"failure_pick_{session['id']}")
        call_details(next(c for c in failures if c["id"] == pick))


def _render_plain(call: dict) -> None:
    """A compact, read-only view for side-by-side comparison."""
    review = prompts.parse_stored_review(call["prompt_version"], call["parsed_json"])
    with st.container(border=True):
        st.caption(f"{_review_label(call)} · instructions `{call['prompt_version']}`")
        if _is_legacy(review):
            st.markdown(safe_md(review.summary))
            st.caption("Older format. Show it above to see its full lists.")
            return
        st.markdown(safe_md(f"**Main takeaway:** {review.main_takeaway.text}"
                            f"{_refs_label(review.main_takeaway.section_refs)}"))
        if review.clarification:
            st.markdown(safe_md(f"**One thing to clarify:** {review.clarification.text}"
                                f"{_refs_label(review.clarification.section_refs)}"))
        st.markdown(safe_md(f"**Next step ({review.next_step.kind}):** {review.next_step.text}"))


# ---------------------------------------------------------------- understanding questions


def _test_tab(session: dict) -> None:
    from .practice import quiz_setup, open_quiz
    quiz_setup(session_id=session['id'], before_generate=lambda: _save_if_dirty(session))
    for qs in db.list_question_sets(session['id']):
        call = db.get_ai_call(qs['ai_call_id'])
        if call['action'] == 'quiz':
            if st.button(f"Open saved quiz {qs['id']} | {qs['created_at']}"):
                open_quiz(qs['id'])
    with st.expander('Earlier notebook question format'):
        _legacy_test_tab(session)


def _legacy_test_tab(session: dict) -> None:
    sets = [qs for qs in db.list_question_sets(session["id"])
            if db.get_ai_call(qs['ai_call_id'])['action'] != 'quiz']
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
    db.execute('INSERT OR IGNORE INTO quiz_progress(set_id) VALUES(?)', (qset['id'],))
    progress = db.query('SELECT * FROM quiz_progress WHERE set_id=?', (qset['id'],))[0]
    pos = min(progress['position'], len(qset['questions'])-1)
    st.caption(f"Question {pos+1} of {len(qset['questions'])}")
    _question_block(session, qset['questions'][pos])
    if st.button('Next question' if pos<len(qset['questions'])-1 else 'Back to first question'):
        db.execute('UPDATE quiz_progress SET position=? WHERE set_id=?', ((pos+1)%len(qset['questions']),qset['id']))
        db.set_activity('quiz',qset['id'])
        st.rerun()
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
            chosen_call=st.selectbox('Feedback record', [c['id'] for c in ok_calls],
                                     format_func=lambda i: next(f"{c['created_at']} | attempt {c['attempt_id'] or 'unrecoverable'}" for c in ok_calls if c['id']==i),key=f"feedback_record_{q['id']}")
            _render_feedback(q, next(c for c in ok_calls if c['id']==chosen_call))
        with st.expander('Submitted answer history'):
            from .practice import attempt_history
            qs=db.query('SELECT * FROM question_sets WHERE id=?',(q['set_id'],))[0]
            attempt_history(q,qs)
        from .practice import report
        history=db.attempts(q['id'])
        report(q['id'],history[-1]['id'] if history else None)
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
        if call.get('attempt_id'):
            evaluated = db.query('SELECT * FROM answer_attempts WHERE id=?', (call['attempt_id'],))
            if evaluated:
                st.caption(f"Evaluated attempt {call['attempt_id']}")
                st.text(evaluated[0]['answer'])
        else:
            st.caption('Historical answer association could not be reconstructed from stored records.')
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
