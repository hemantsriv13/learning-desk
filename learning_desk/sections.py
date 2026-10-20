"""Turn a saved session into a snapshot with numbered sections.

The model receives the notes as [S1], [S2], ... and is asked to cite those numbers.
The app can then show the exact text behind each citation next to the feedback.
This is ordinary code: no AI involved.
"""

import re

FENCE = re.compile(r"^\s*(```|~~~)")


def split_blocks(text: str) -> list[str]:
    """Split Markdown on blank lines, never inside a fenced code block."""
    blocks: list[str] = []
    current: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
        if not in_fence and not line.strip():
            if current:
                blocks.append("\n".join(current))
                current = []
            continue
        current.append(line)
    if current:
        blocks.append("\n".join(current))
    return blocks


def build_snapshot_content(session: dict, queue_items: list[dict]) -> dict:
    """Everything an AI action may see about one session, and nothing else."""
    open_items = [q for q in queue_items if q["status"] == "open"]
    return {
        "session_id": session["id"],
        "title": session["title"],
        "topic": session["topic"],
        "goal": session["goal"],
        "explanation": session["explanation"],
        "notes": session["notes"],
        "sources": session["sources"],
        "open_questions": [q["text"] for q in open_items if q["kind"] == "question"],
        "next_steps": [q["text"] for q in open_items if q["kind"] == "task"],
        "session_updated_at": session["updated_at"],
    }


def number_sections(content: dict) -> list[dict]:
    """Return [{"id": 1, "label": "...", "text": "..."}, ...]. Empty fields are skipped."""
    parts: list[tuple[str, str]] = []
    if content["goal"].strip():
        parts.append(("What I want to understand", content["goal"].strip()))
    if content["explanation"].strip():
        parts.append(("My current explanation", content["explanation"].strip()))
    blocks = split_blocks(content["notes"])
    for i, block in enumerate(blocks, start=1):
        parts.append((f"Notes, block {i} of {len(blocks)}", block))
    if content["sources"].strip():
        parts.append(("Source URLs (not fetched; listed by me)", content["sources"].strip()))
    for q in content["open_questions"]:
        parts.append(("My unresolved question", q))
    for step in content["next_steps"]:
        parts.append(("My planned next step", step))
    return [{"id": i, "label": label, "text": text} for i, (label, text) in enumerate(parts, start=1)]


def render_sections(content: dict, sections: list[dict]) -> str:
    """The text that goes inside the <session> element of the prompt."""
    lines = [f"Title: {content['title'] or '(untitled)'}", f"Topic: {content['topic'] or '(none)'}", ""]
    for s in sections:
        lines.append(f"[S{s['id']}] {s['label']}")
        lines.append(s["text"])
        lines.append("")
    return "\n".join(lines).strip()
