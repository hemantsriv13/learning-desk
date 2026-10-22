"""Small UI helpers shared by the pages."""

import json
import re

import streamlit as st

from .. import config, db, provider

# Filled in by app.py on every run so pages can link to each other.
PAGES: dict = {}


def fmt_time(ts: str | None) -> str:
    return ts.replace("T", " ") if ts else "-"


def safe_md(text: str) -> str:
    """Markdown without remote images. Streamlit already refuses raw HTML (we never pass
    unsafe_allow_html). Images are disabled too, because an image URL in model output
    would make your browser contact that address as soon as the page renders."""
    return re.sub(r"!\[", r"\\![", text or "")


def open_session(session_id: int) -> None:
    db.set_activity("session", session_id)
    st.session_state["current_session_id"] = session_id
    st.switch_page(PAGES["session"])


def flash(kind: str, message: str) -> None:
    """Show a message on the next run (survives st.rerun / page switches)."""
    st.session_state.setdefault("flash", []).append((kind, message))


def show_flash() -> None:
    for kind, message in st.session_state.pop("flash", []):
        getattr(st, kind)(message)


def ai_ready() -> bool:
    return config.api_key_present()


def ai_privacy_note(what: str) -> None:
    st.caption(
        f"Clicking sends {what} to {provider.PROVIDER_NAME} (model `{config.model()}`). "
        "Nothing is sent until you click. Your notes stay on this computer otherwise."
    )
    if not ai_ready():
        st.info("AI features are off because ANTHROPIC_API_KEY is not set. "
                "Everything else (notes, queue, search, export) works without it. See Settings.")


def inspect_call(call: dict) -> None:
    """The 'Inspect AI call' panel: what the app sent and received, nothing invented."""
    label = f"Inspect AI call #{call['id']} ({call['action']}, {call['status']})"
    with st.expander(label):
        call_details(call)


def call_details(call: dict) -> None:
    """The body of the inspect panel, for use inside a container that is already collapsible
    (Streamlit does not allow an expander inside another expander)."""
    st.caption("This shows the application's input and output for this call. "
               "It does not show the model's internal reasoning.")
    usage = "not reported"
    if call["input_tokens"] is not None or call["output_tokens"] is not None:
        usage = f"{call['input_tokens']} input / {call['output_tokens']} output (reported by provider)"
    rows = [
        ("Action", call["action"]),
        ("Instruction version", call["prompt_version"]),
        ("Status", call["status"]),
        ("Time", fmt_time(call["created_at"])),
        ("Requested model", call["requested_model"]),
        ("Returned model", call["returned_model"] or "not returned"),
        ("Elapsed", f"{call['elapsed_ms'] / 1000:.1f} s" if call["elapsed_ms"] is not None else "-"),
        ("Tokens", usage),
        ("Stop reason", call["stop_reason"] or "-"),
        ("Session snapshot", f"#{call['snapshot_id']}"),
    ]
    st.table({"Field": [r[0] for r in rows], "Value": [str(r[1]) for r in rows]})
    if call["error"]:
        st.error(call["error"])
    if call["warnings_json"]:
        for w in json.loads(call["warnings_json"]):
            st.warning(w)
    st.markdown("**Request sent** (credentials are never included)")
    st.code(call["request_json"] or "", language="json", wrap_lines=True)
    st.markdown("**Raw response**")
    # Quiz generation records contain answer keys. Keep those hidden until completion,
    # including when the record is opened from the reader's general call history.
    hide_keys=False
    if call['action']=='quiz':
        progress=db.query('SELECT p.finished FROM question_sets qs LEFT JOIN quiz_progress p ON p.set_id=qs.id WHERE qs.ai_call_id=?',(call['id'],))
        hide_keys=not progress or not progress[0]['finished']
    if hide_keys:
        st.caption('Generation response contains answer keys and is hidden until this quiz is finished. Complete records remain available in archival exports.')
    else:
        st.code(call["raw_response"] or "(no response received)", language="json", wrap_lines=True)
    if call["usage_json"]:
        st.markdown("**Usage as reported by the provider**")
        st.code(call["usage_json"], language="json")


def queue_item_row(item: dict, ctx: str, show_session: bool) -> None:
    """One editable queue item. Edits are saved to the database as soon as you leave the field."""
    key = f"{ctx}_q{item['id']}"

    def save(field: str) -> None:
        value = st.session_state[f"{key}_{field}"]
        if field == "text" and not value.strip():
            flash("warning", "An item cannot be empty; the change was not saved.")
            st.session_state[f"{key}_{field}"] = item["text"]
            return
        db.update_queue_item(item["id"], **{field: value})

    for field in ("kind", "text", "priority"):
        st.session_state.setdefault(f"{key}_{field}", item[field])

    done = item["status"] == "done"
    cols = st.columns([1.2, 6, 1.4, 1.3])
    cols[0].selectbox("Type", db.QUEUE_KINDS, key=f"{key}_kind", on_change=save, args=("kind",),
                      label_visibility="collapsed", disabled=done)
    cols[1].text_input("Text", key=f"{key}_text", on_change=save, args=("text",),
                       label_visibility="collapsed", disabled=done)
    cols[2].selectbox("Priority", db.PRIORITIES, key=f"{key}_priority", on_change=save, args=("priority",),
                      label_visibility="collapsed", disabled=done)
    if cols[3].button("Reopen" if done else "Done", key=f"{key}_toggle", use_container_width=True):
        db.update_queue_item(item["id"], status="open" if done else "done")
        st.rerun()

    meta = []
    if show_session and item["session_id"]:
        meta.append(f"from: {item['session_title'] or 'Untitled session'}")
    if item["source"].startswith("ai_suggestion"):
        meta.append("accepted from an AI suggestion")
    meta.append(f"completed {fmt_time(item['completed_at'])}" if done else f"added {fmt_time(item['created_at'])}")
    st.caption(" · ".join(meta))
    if show_session and item["session_id"]:
        if st.button("Open session", key=f"{key}_open"):
            open_session(item["session_id"])


def add_queue_item_form(ctx: str, session_id: int | None = None, sessions: list[dict] | None = None) -> None:
    with st.form(f"{ctx}_add_item", clear_on_submit=True, border=True):
        st.markdown("**Add a question or task**")
        cols = st.columns([1.2, 6, 1.4])
        kind = cols[0].selectbox("Type", db.QUEUE_KINDS)
        text = cols[1].text_input("Text")
        priority = cols[2].selectbox("Priority", db.PRIORITIES, index=1)
        chosen = session_id
        if sessions is not None:
            options = [None] + [s["id"] for s in sessions]
            titles = {s["id"]: s["title"] or "Untitled session" for s in sessions}
            chosen = st.selectbox("Linked session", options,
                                  format_func=lambda i: "(none)" if i is None else titles[i])
        if st.form_submit_button("Add"):
            if text.strip():
                db.add_queue_item(chosen, kind, text, priority)
                flash("success", "Added to your queue.")
                st.rerun()
            else:
                st.warning("Write something first.")
