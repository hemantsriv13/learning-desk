"""The built-in curriculum: reviewed static lessons, planned outlines and their sources.

Nothing here calls a model. Personalised explanations are generated only when the learner explicitly
saves a lesson to the Library and asks for one there, and they are labelled as AI output."""

from .. import visuals
from . import lessons_building, lessons_foundations, lessons_models, lessons_retrieval
from .model import ORIGINAL, VIEWS, Lesson, Outline, Topic, validate
from .sources import SOURCES
from .topics import CORE, OUTLINES, TOPICS, TRACK_ORDER

LESSONS: dict[str, Lesson] = {
    lesson.id: lesson
    for module in (lessons_foundations, lessons_models, lessons_retrieval, lessons_building)
    for lesson in module.LESSONS
}
TOPIC_BY_ID: dict[str, Topic] = {t.id: t for t in TOPICS}

PROBLEMS = validate(TOPICS, LESSONS, OUTLINES, SOURCES, visuals.VISUALS)
if PROBLEMS:  # a content error is a programming error: fail at import, in tests and at start-up
    raise ValueError("Curriculum is inconsistent:\n" + "\n".join(PROBLEMS))


def get(lesson_id: str) -> Lesson | Outline | None:
    return LESSONS.get(lesson_id) or OUTLINES.get(lesson_id)


def topic_items(topic_id: str) -> list[Lesson | Outline]:
    return [get(lid) for lid in TOPIC_BY_ID[topic_id].lessons]


def search(query: str) -> list[Lesson]:
    """Case-insensitive match over finished lessons' titles, summaries, key ideas and topic."""
    q = query.strip().casefold()
    if not q:
        return []
    found = []
    for lesson in LESSONS.values():
        text = " ".join((lesson.title, lesson.summary, lesson.objective, *lesson.key_ideas,
                         TOPIC_BY_ID[lesson.topic].title)).casefold()
        if q in text:
            found.append(lesson)
    return found


def lesson_markdown(lesson: Lesson) -> str:
    """The whole lesson as plain Markdown: used when the learner saves it to the Library (so optional
    AI explanations are grounded in this exact version) and for export."""
    out = [f"# {lesson.title}", "",
           f"Lesson `{lesson.id}`, version {lesson.version}. {lesson.provenance}. "
           f"Sources checked {lesson.checked}.", "",
           f"**Objective:** {lesson.objective}", "", lesson.intro, "", "## Key ideas", ""]
    out += [f"- {idea}" for idea in lesson.key_ideas]
    for section in lesson.walkthrough():
        out += ["", f"## {section.title}", "", section.body]
        if section.visual:
            visual = visuals.VISUALS[section.visual]
            out += ["", f"Diagram — {visual.title}: {visual.alt}"]
            if visual.illustrative:
                out += ["", f"({visual.illustrative})"]
        if section.table:
            table = section.table
            out += ["", "| " + " | ".join(table.columns) + " |", "|" + "---|" * len(table.columns)]
            out += ["| " + " | ".join(row) + " |" for row in table.rows]
        if section.code:
            out += ["", f"```{section.code.language}", section.code.source, "```"]
            out += [f"- Line {n}: {note}" for n, note in section.code.notes]
        if section.callout:
            out += ["", f"> {section.callout}"]
    out += ["", f"## Try it: {lesson.activity.title}", ""]
    out += [f"{i}. {step}" for i, step in enumerate(lesson.activity.steps, 1)]
    if lesson.scope:
        out += ["", f"**Scope:** {lesson.scope}"]
    out += ["", "## Sources", ""]
    for cite in (*lesson.citations, *lesson.further_reading):
        source = SOURCES[cite.source]
        out.append(f"- {source.title} ({source.publisher}) {source.url}: {cite.supports}")
    return "\n".join(out) + "\n"


__all__ = ["LESSONS", "OUTLINES", "TOPICS", "TOPIC_BY_ID", "CORE", "TRACK_ORDER", "SOURCES", "VIEWS", "ORIGINAL", "get",
           "topic_items", "search", "lesson_markdown"]
