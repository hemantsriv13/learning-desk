"""Typed lesson content. Lessons are static, reviewed text shipped with the app: no model call
creates or changes them. validate() checks the whole collection when the app or tests load it."""

from dataclasses import dataclass, field

LEVELS = ("introductory", "intermediate", "advanced")
VIEWS = ("Overview", "Walkthrough", "Try it", "Sources")
SOURCE_KINDS = ("Official documentation", "Provider documentation", "Standard", "Research paper",
                "Engineering article", "This app's code")
ORIGINAL = "Original educational content written for Learning Desk"


@dataclass(frozen=True)
class Source:
    id: str
    title: str
    url: str
    publisher: str
    kind: str
    # ISO date on which the link was opened and the cited claims were checked against it.
    # None means not verified: the UI then labels the link as unverified.
    checked: str | None


@dataclass(frozen=True)
class Citation:
    source: str  # Source.id
    supports: str  # what this source is cited for in this lesson


@dataclass(frozen=True)
class Code:
    language: str
    source: str
    # (line number, explanation); shown beside the code, never executed.
    notes: tuple[tuple[int, str], ...] = ()
    caption: str = ""


@dataclass(frozen=True)
class Table:
    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    caption: str = ""


@dataclass(frozen=True)
class Section:
    id: str
    title: str
    body: str  # Markdown, rendered without HTML
    visual: str | None = None  # id in visuals.VISUALS
    code: Code | None = None
    table: Table | None = None
    callout: str = ""  # one short "keep in mind" line


@dataclass(frozen=True)
class Check:
    """A deterministic multiple-choice check: graded by comparison, no model involved."""
    id: str
    prompt: str
    options: tuple[str, ...]
    answer: str
    explanation: str
    section: str  # Section.id where this is taught, so feedback can point back to it


@dataclass(frozen=True)
class Activity:
    title: str
    steps: tuple[str, ...]
    widget: str | None = None  # interactive visual id shown with the activity
    reflection: str = ""


@dataclass(frozen=True)
class Lesson:
    id: str
    topic: str
    title: str
    summary: str
    level: str
    minutes: int
    objective: str
    intro: str
    key_ideas: tuple[str, ...]
    overview_visual: str
    sections: tuple[Section, ...]
    worked_example: Section
    misconception: Section
    activity: Activity
    checks: tuple[Check, ...]
    citations: tuple[Citation, ...]
    further_reading: tuple[Citation, ...] = ()
    prerequisites: tuple[str, ...] = ()
    related: tuple[str, ...] = ()
    scope: str = ""  # what is general, and what is provider- or app-specific
    version: str = "2026-10-23.1"
    checked: str = "2026-10-23"
    provenance: str = ORIGINAL
    status: str = "complete"

    def walkthrough(self) -> tuple[Section, ...]:
        return (*self.sections, self.worked_example, self.misconception)


@dataclass(frozen=True)
class Outline:
    """A planned lesson. Shown as an outline only, never as finished content."""
    id: str
    topic: str
    title: str
    objective: str
    planned: tuple[str, ...]
    status: str = "outline"


@dataclass(frozen=True)
class Topic:
    id: str
    number: int
    title: str
    icon: str  # Material icon name, e.g. "data_object"
    blurb: str
    why: str
    lessons: tuple[str, ...] = field(default_factory=tuple)  # lesson and outline ids, in order


def validate(topics, lessons, outlines, sources, visuals) -> list[str]:
    """Problems with the collection, as readable strings. An empty list means it is consistent."""
    problems = []
    ids = set(lessons) | set(outlines)
    if len(ids) != len(lessons) + len(outlines):
        problems.append("A lesson id is used for both a lesson and an outline")
    for topic in topics:
        for lid in topic.lessons:
            if lid not in ids:
                problems.append(f"{topic.id}: unknown lesson {lid}")
            elif (lessons.get(lid) or outlines.get(lid)).topic != topic.id:
                problems.append(f"{lid}: listed under {topic.id} but belongs elsewhere")
    listed = {lid for t in topics for lid in t.lessons}
    problems += [f"{lid}: not listed in any topic" for lid in ids - listed]
    for lesson in lessons.values():
        where = lesson.id
        if lesson.level not in LEVELS:
            problems.append(f"{where}: unknown level")
        for text, name in ((lesson.objective, "objective"), (lesson.intro, "intro"),
                           (lesson.summary, "summary")):
            if not text.strip():
                problems.append(f"{where}: empty {name}")
        if len(lesson.sections) < 2:
            problems.append(f"{where}: needs at least two explanation sections")
        if not lesson.key_ideas:
            problems.append(f"{where}: no key ideas")
        if not lesson.activity.steps:
            problems.append(f"{where}: activity has no steps")
        if not lesson.checks:
            problems.append(f"{where}: no practice check")
        if not lesson.citations:
            problems.append(f"{where}: no sources")
        section_ids = [s.id for s in lesson.walkthrough()]
        if len(set(section_ids)) != len(section_ids):
            problems.append(f"{where}: duplicate section ids")
        for vid in [lesson.overview_visual, lesson.activity.widget,
                    *[s.visual for s in lesson.walkthrough()]]:
            if vid and vid not in visuals:
                problems.append(f"{where}: unknown visual {vid}")
        for check in lesson.checks:
            if check.answer not in check.options or len(set(check.options)) != len(check.options):
                problems.append(f"{where}/{check.id}: answer must be exactly one distinct option")
            if check.section not in section_ids:
                problems.append(f"{where}/{check.id}: unknown section {check.section}")
        for cite in (*lesson.citations, *lesson.further_reading):
            if cite.source not in sources:
                problems.append(f"{where}: unknown source {cite.source}")
        for other in (*lesson.prerequisites, *lesson.related):
            if other not in ids:
                problems.append(f"{where}: unknown linked lesson {other}")
    for source in sources.values():
        if source.kind not in SOURCE_KINDS:
            problems.append(f"{source.id}: unknown source kind")
        if source.kind != "This app's code" and not source.url.startswith("https://"):
            problems.append(f"{source.id}: external sources must use https")
    return problems
