"""Home, Queue, Search & export, and Settings/About pages. None of these call the model."""

import streamlit as st

from .. import config, db, example, export, prompts, provider
from .common import add_queue_item_form, fmt_time, open_session, queue_item_row, show_flash


def home() -> None:
    show_flash()
    st.title("Learning Desk")

    with st.form("new_session", border=True):
        st.markdown("**Start a session**")
        c1, c2 = st.columns(2)
        title = c1.text_input("Title", placeholder="e.g. How tokenizers split text")
        topic = c2.text_input("Topic", placeholder="e.g. Tokenization")
        if st.form_submit_button("Start session", type="primary"):
            session_id = db.create_session(title=title.strip(), topic=topic.strip())
            open_session(session_id)

    left, right = st.columns([3, 2], gap="large")
    with left:
        st.subheader("Recent sessions")
        sessions = db.list_sessions(limit=None if st.toggle("Show all") else 8)
        if not sessions:
            st.write("No sessions yet.")
        for s in sessions:
            c1, c2 = st.columns([5, 1])
            c1.markdown(f"**{s['title'] or 'Untitled session'}**  \n"
                        f"{s['topic'] or 'No topic'} · saved {fmt_time(s['updated_at'])}")
            if c2.button("Open", key=f"open_{s['id']}"):
                open_session(s["id"])

    with right:
        st.subheader("Open questions & next steps")
        items = db.list_queue(status="open")
        if not items:
            st.write("Nothing in your queue.")
        for item in items[:10]:
            with st.container(border=True):
                st.markdown(f"**{item['kind'].capitalize()}** · {item['priority']} priority  \n{item['text']}")
                if item["session_id"]:
                    st.caption(f"from: {item['session_title'] or 'Untitled session'}")
                    if st.button("Open session", key=f"home_q{item['id']}"):
                        open_session(item["session_id"])
        if len(items) > 10:
            st.caption(f"{len(items) - 10} more in Queue.")

    st.divider()
    st.caption(f"Your data is stored only on this computer, in `{config.db_path()}`. "
               f"When you use an AI feature, that session's saved content is sent to {provider.PROVIDER_NAME}.")


def queue() -> None:
    show_flash()
    st.title("Next-session queue")
    st.caption("Ordered by the priority you choose. No reminders or scheduling. Edits save when you leave a field.")
    sessions = db.list_sessions()
    open_items = db.list_queue(status="open")
    if not open_items:
        st.write("Nothing open.")
    for item in open_items:
        with st.container(border=True):
            queue_item_row(item, ctx="queue", show_session=True)
    add_queue_item_form("queue", sessions=sessions)
    done_items = db.list_queue(status="done")
    if done_items:
        with st.expander(f"Completed ({len(done_items)})"):
            for item in done_items:
                queue_item_row(item, ctx="queuedone", show_session=False)


def search() -> None:
    show_flash()
    st.title("Search & export")
    query = st.text_input("Search titles, topics and notes", placeholder="Plain text, not case-sensitive")
    if query.strip():
        results = db.search_sessions(query)
        st.caption(f"{len(results)} session(s) contain “{query.strip()}”.")
        for s in results:
            with st.container(border=True):
                c1, c2 = st.columns([5, 1])
                c1.markdown(f"**{s['title'] or 'Untitled session'}** · {s['topic'] or 'No topic'}")
                c1.caption(_snippet(s, query.strip()))
                if c2.button("Open", key=f"search_{s['id']}"):
                    open_session(s["id"])

    st.divider()
    st.subheader("Export everything")
    st.write("All sessions, queue items, snapshots, AI call records, questions and answers as one JSON file. "
             "Works without an API key or internet connection.")
    st.download_button("Download all data (JSON)", data=export.all_data_json(),
                       file_name=f"learning-desk-export-{db.now()[:10]}.json", mime="application/json")


def _snippet(session: dict, query: str, width: int = 80) -> str:
    for field in db.SESSION_FIELDS:
        text = session[field]
        pos = text.lower().find(query.lower())
        if pos >= 0:
            start = max(0, pos - width // 2)
            excerpt = text[start:pos + len(query) + width // 2].replace("\n", " ")
            return f"in {field}: …{excerpt}…"
    return ""


def settings() -> None:
    show_flash()
    st.title("Settings & About")

    st.subheader("AI provider")
    key_state = "set" if config.api_key_present() else "NOT set (AI features are disabled)"
    st.table({
        "Setting": ["Provider", "API key (ANTHROPIC_API_KEY)", "Model (LEARNING_DESK_MODEL)",
                    "Effort (LEARNING_DESK_EFFORT)", "Max output tokens", "Timeout", "Automatic retries"],
        "Value": [provider.PROVIDER_NAME, key_state, config.model(), config.effort() or "(not sent)",
                  str(config.max_tokens()), f"{config.timeout_seconds():.0f} s", "none"],
    })
    st.caption("Change these in the .env file or environment, then restart the app. The key itself is never "
               "shown, stored or logged by this app. A configured model name is only checked when you make a call.")

    st.subheader("Your data")
    st.markdown(f"""
- Stored in one SQLite file: `{config.db_path()}`.
- **Back up**: close the app, then copy that file somewhere safe. Or use *Search & export → Download all data*.
- **Restore**: put the copied file back at the same path.
- Exports are downloads from your browser; the app does not upload them anywhere.
""")

    st.subheader("Privacy and AI behaviour")
    st.markdown(f"""
- The app calls {provider.PROVIDER_NAME} **only when you click** *Review this session*, *Generate questions*
  or *Get feedback on my answer*. Opening or browsing pages never calls the model.
- Each call sends the **saved** version of the current session only (plus your answer, for feedback).
  Other sessions are never sent. There is no memory across sessions.
- Your notes are wrapped in a `<session>` element and the instructions tell the model to treat them as data.
  This **reduces, but does not prevent**, prompt injection: text you paste could still influence the output.
- Pasted code is stored as text and never executed.
- Replies must match a schema. If one does not, it is rejected and shown as an error; nothing is invented to
  replace it. Every call, including failures, is listed under *Inspect AI call*.
- Instruction versions in use: `{prompts.REVIEW_VERSION}`, `{prompts.QUESTIONS_VERSION}`, `{prompts.FEEDBACK_VERSION}`.
""")

    st.subheader("Lessons, sources and visuals")
    from .. import curriculum

    checked = sorted({s.checked for s in curriculum.SOURCES.values() if s.checked})
    unverified = [s for s in curriculum.SOURCES.values() if not s.checked]
    st.markdown(f"""
- **{len(curriculum.LESSONS)} built-in lessons** and {len(curriculum.OUTLINES)} planned outlines. Lesson text is
  original educational content shipped with the app; opening a lesson never calls a model.
- **Sources**: {len(curriculum.SOURCES)} references (official documentation, standards, provider documentation and
  research papers). Links and the claims cited from them were checked on {", ".join(checked) or "—"}.
  {"Unverified links: " + str(len(unverified)) + "." if unverified else "No unverified links."}
  Provider documentation changes often; each lesson marks provider-specific details.
- **Visuals**: every diagram and chart is original, drawn by `learning_desk/visuals.py` and covered by this
  repository's MIT licence. No photographs, stock images, hotlinked assets or AI-generated images are used.
  Illustrative data (toy embeddings, invented scores, latency rates) is labelled beside each visual.
- **Personalised explanations** exist only if you save a lesson to the Library and press a generate button there;
  they are labelled as AI output and tied to the saved lesson version.
""")

    st.subheader("Example session")
    st.write("Creates a clearly labelled fictional session so you can try the workflow.")
    if st.button("Load fictional example session"):
        open_session(example.create_example_session())


    with st.expander('Reported questions and feedback'):
        reports=db.query('SELECT * FROM issue_reports ORDER BY id DESC')
        if reports:
            st.dataframe(reports,hide_index=True)
        else:
            st.caption('No reports saved.')
