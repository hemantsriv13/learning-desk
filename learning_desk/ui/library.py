"""Calm Library and focused reader. All network and AI work is button-triggered."""

import json
from urllib.parse import urlsplit
import streamlit as st
from .. import db, importer, learning
from .common import ai_ready, ai_privacy_note, inspect_call, safe_md

LEVELS = ["introductory", "intermediate", "advanced"]
TYPES = ["reference", "documentation", "article", "pasted"]


def web_link(label, url):
    try:
        p = urlsplit(url)
        if (
            p.scheme in ("http", "https")
            and p.hostname
            and not p.username
            and not p.password
        ):
            st.link_button(label, url)
    except ValueError:
        pass


def open_resource(rid):
    db.set_activity("resource", rid)
    st.session_state["resource_id"] = rid
    st.session_state.pop("active_quiz", None)
    st.rerun()


def render():
    st.title("Library")
    quiz = st.session_state.get("active_quiz")
    if quiz:
        from .practice import render_quiz

        if st.button("Back to Library"):
            st.session_state.pop("active_quiz", None)
            st.rerun()
        render_quiz(quiz)
        return
    rid = st.session_state.get("resource_id")
    if rid:
        if st.button("Back to Library"):
            st.session_state.pop("resource_id", None)
            st.rerun()
        reader(rid)
        return
    query = st.text_input(
        "Search resources", placeholder="Title, topic, tags, level or status"
    )
    archived = st.toggle("Show archived resources")
    resources = db.list_resources(query, archived)
    if not resources:
        st.write("No resources here yet. Save a link or paste some material below.")
    for r in resources:
        with st.container(border=True):
            versions = db.query(
                "SELECT id FROM content_versions WHERE resource_id=?", (r["id"],)
            )
            st.write(r["title"])
            st.caption(
                f"{r['status']} · {r['level']} · {r['resource_type']} · "
                + (
                    "Content saved"
                    if versions
                    else "Bookmark only — content not imported"
                )
            )
            if st.button("Open", key=f"resource_{r['id']}"):
                open_resource(r["id"])
    with st.expander("Add a resource", expanded=not resources):
        with st.form("add_resource"):
            title = st.text_input("Title")
            url = st.text_input("URL (optional)")
            kind = st.selectbox("Resource type", TYPES)
            tags = st.text_input("Topic / tags")
            level = st.selectbox("Level", LEVELS)
            text = st.text_area("Pasted text or Markdown (optional)", height=180)
            if st.form_submit_button("Save resource"):
                try:
                    if url and (
                        urlsplit(url).scheme not in ("http", "https")
                        or not urlsplit(url).hostname
                    ):
                        raise ValueError("Use an HTTP or HTTPS source link")
                    if len(text) > 100000:
                        raise ValueError("Paste at most 100,000 characters")
                    rid = db.save_resource(title, kind, url, tags, level)
                    if text.strip():
                        db.add_content(rid, text, url)
                    open_resource(rid)
                except ValueError as exc:
                    st.error(str(exc))
    with st.expander("Optional starter learning path"):
        from ..starter import PATH

        st.caption(
            "Optional starter suggestions, separate from your history. Links are bookmarks until explicitly imported."
        )
        for item in PATH:
            st.write(item["title"])
            st.caption(item["note"])
            for title, url in item["links"]:
                web_link(title, url)
            if st.button("Save this starter bookmark", key=item["title"]):
                title, url = item["links"][0]
                rid = db.save_resource(
                    item["title"], "documentation", url, tags="starter"
                )
                open_resource(rid)


def reader(rid):
    rows = db.query("SELECT * FROM resources WHERE id=?", (rid,))
    if not rows:
        st.warning("Resource is unavailable.")
        return
    r = rows[0]
    st.subheader(r["title"])
    web_link("Open original source", r["url"])
    versions = db.query(
        "SELECT * FROM content_versions WHERE resource_id=? ORDER BY id DESC", (rid,)
    )
    with st.expander("Resource details, status and notebook links"):
        with st.form(f"edit_resource_{rid}"):
            title = st.text_input("Title", r["title"])
            url = st.text_input("Source URL", r["url"])
            kind = st.selectbox("Type", TYPES, index=TYPES.index(r["resource_type"]))
            tags = st.text_input("Topic / tags", r["tags"])
            level = st.selectbox("Level", LEVELS, index=LEVELS.index(r["level"]))
            status = st.selectbox(
                "Status",
                ["Saved", "Reading", "Finished"],
                index=["Saved", "Reading", "Finished"].index(r["status"]),
            )
            archived = st.checkbox("Archived", bool(r["archived"]))
            if st.form_submit_button("Save details"):
                try:
                    db.save_resource(
                        title, kind, url, tags, level, status, rid, archived
                    )
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        sessions = db.list_sessions()
        if sessions:
            sid = st.selectbox(
                "Link to notebook session",
                [s["id"] for s in sessions],
                format_func=lambda i: next(
                    s["title"] or "Untitled session" for s in sessions if s["id"] == i
                ),
            )
            if st.button("Link resource"):
                db.execute(
                    "INSERT OR IGNORE INTO resource_sessions(resource_id,session_id) VALUES(?,?)",
                    (rid, sid),
                )
                st.success("Linked.")
        for link in db.query(
            "SELECT s.* FROM sessions s JOIN resource_sessions rs ON rs.session_id=s.id WHERE rs.resource_id=?",
            (rid,),
        ):
            st.caption("Linked: " + (link["title"] or "Untitled session"))
            if st.button("Open notebook session", key=f"linked_{link['id']}"):
                from .common import open_session

                open_session(link["id"])
    if not versions:
        st.info(
            "Bookmark saved. Content has not been imported. Import the public page or paste its text below."
        )
    with st.expander("Import or add a content version", expanded=not versions):
        st.caption(
            "Imports make a web request only when clicked. No login, paywall bypass, PDF or browser automation. Earlier versions remain saved."
        )
        if r["url"] and st.button("Import public page"):
            try:
                with st.spinner("Importing public text…"):
                    imported = importer.import_url(r["url"])
                    vid = db.add_content(
                        rid,
                        imported["text"],
                        imported["url"],
                        imported["note"],
                        imported["links"],
                    )
                st.session_state[f"version_{rid}"] = vid
                st.rerun()
            except Exception as exc:
                st.warning(
                    f"Could not import this page: {exc}. Paste the intended text below."
                )
        with st.form(f"paste_{rid}", clear_on_submit=True):
            text = st.text_area("Paste learning material", height=200)
            if st.form_submit_button("Save new text version"):
                try:
                    vid = db.add_content(rid, text, r["url"])
                    st.session_state[f"version_{rid}"] = vid
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
    if not versions:
        return
    persisted = db.query("SELECT * FROM reader_progress WHERE resource_id=?", (rid,))
    ids = [v["id"] for v in versions]
    if persisted and f"version_{rid}" not in st.session_state:
        st.session_state[f"version_{rid}"] = persisted[0]["content_version_id"]
    if st.session_state.get(f"version_{rid}") not in ids:
        st.session_state[f"version_{rid}"] = ids[0]
    vid = st.selectbox(
        "Content version",
        ids,
        key=f"version_{rid}",
        format_func=lambda i: (
            f"Version {i} · " + next(v["created_at"] for v in versions if v["id"] == i)
        ),
    )
    v = next(v for v in versions if v["id"] == vid)
    st.caption(v["import_note"])
    web_link("Source for this exact version", v["source_url"])
    modes = ["Original text", "Quick read", "Explain it", "Check my understanding"]
    mode = st.radio(
        "Read",
        modes,
        index=modes.index(persisted[0]["mode"])
        if persisted and persisted[0]["mode"] in modes
        else 0,
        horizontal=True,
        key=f"read_mode_{rid}",
    )
    if (
        not persisted
        or persisted[0]["content_version_id"] != vid
        or persisted[0]["mode"] != mode
    ):
        db.execute(
            "INSERT INTO reader_progress(resource_id,content_version_id,mode) VALUES(?,?,?) ON CONFLICT(resource_id) DO UPDATE SET content_version_id=excluded.content_version_id,mode=excluded.mode",
            (rid, vid, mode),
        )
    if mode == "Original text":
        st.markdown(safe_md(v["text"]))
    elif mode in ("Quick read", "Explain it"):
        kind = "quick" if mode == "Quick read" else "explain"
        summaries = db.query(
            "SELECT * FROM summaries WHERE content_version_id=? AND kind=?", (vid, kind)
        )
        if not summaries:
            st.write("A saved summary will appear here after you request one.")
            ai_privacy_note("this content version only")
            if st.button(
                "Generate " + mode.lower(), type="primary", disabled=not ai_ready()
            ):
                try:
                    with st.spinner("Preparing reading..."):
                        result = learning.summarize(vid, kind)
                except ValueError as exc:
                    st.warning(str(exc))
                    return
                if result.ok:
                    st.rerun()
                else:
                    st.error(result.error)
        else:
            saved = summaries[0]
            result = json.loads(saved["result_json"])
            st.caption(
                "AI-generated · source-supported summary; citations are passage references, not proof of correctness."
            )
            for paragraph in result["source_summary"]:
                st.markdown(safe_md(paragraph["text"]))
            if result["added_explanation"]:
                st.caption("Added explanation from the model")
                st.markdown(safe_md(result["added_explanation"]))
            if result["example"]:
                st.caption("Teaching example added by the model")
                st.markdown(safe_md(result["example"]))
            with st.expander("Supporting source passages"):
                evidence(
                    learning.source(content_version_id=vid),
                    [
                        ref
                        for p in result["source_summary"]
                        for ref in p["section_refs"]
                    ],
                )
            inspect_call(db.get_ai_call(saved["ai_call_id"]))
    else:
        from .practice import quiz_setup

        quiz_setup(version_id=vid)
    with st.expander("Further reading — saved or extracted links"):
        st.caption(
            "These pages have not been read for this summary. Extracted links come from this exact source version."
        )
        for i, url in enumerate(json.loads(v["links_json"])):
            web_link(f"Extracted link {i + 1}: {url[:90]}", url)
        for other in db.list_resources()[:30]:
            if other["id"] != rid and other["url"]:
                web_link("Saved resource: " + other["title"], other["url"])
    with st.expander("Previous quizzes for this version"):
        from .practice import open_quiz

        for qs in db.query(
            "SELECT * FROM question_sets WHERE content_version_id=? ORDER BY id DESC",
            (vid,),
        ):
            if st.button(
                f"Open quiz {qs['id']} · {qs['created_at']}", key=f"pastquiz_{qs['id']}"
            ):
                open_quiz(qs["id"])
    with st.expander("AI call history for this version"):
        from .common import call_details

        calls = db.query(
            "SELECT * FROM ai_calls WHERE content_version_id=? ORDER BY id DESC", (vid,)
        )
        if calls:
            call_id = st.selectbox(
                "Call record",
                [c["id"] for c in calls],
                format_func=lambda i: next(
                    f"{c['id']} | {c['action']} | {c['status']}"
                    for c in calls
                    if c["id"] == i
                ),
            )
            call_details(next(c for c in calls if c["id"] == call_id))
        else:
            st.caption("No model calls for this version.")
    with st.expander("Export this resource"):
        st.caption("Archival export includes answer keys and assessment rubrics.")
        from ..export import resource_markdown

        st.download_button(
            "Download resource (Markdown)",
            resource_markdown(rid),
            file_name=f"resource-{rid}.md",
        )


def evidence(numbered, refs):
    for ref in dict.fromkeys(refs):
        passage = next((s for s in numbered if s["id"] == ref), None)
        st.caption(f"S{ref}")
        st.text(passage["text"] if passage else "Reference unavailable")
