"""Export the curriculum and pixel art for the Android app: python tools/export_mobile.py

Writes mobile/assets/content.json. The phone app reads only this file, so lessons are written once (in
learning_desk/curriculum) and both apps show the same content. Pixel art is exported as its first frame,
because React Native's SVG renderer does not run the CSS animations inside the SVGs."""

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from learning_desk import curriculum, pixels, visuals  # noqa: E402
from learning_desk.curriculum import LESSONS, OUTLINES, TOPICS, TRACK_ORDER  # noqa: E402

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
# Classes that are later animation frames or briefly-shown overlays; the first frame stays.
LATER_FRAME = re.compile(r"^[a-z]+[1-9]$")
OVERLAYS = {"blink", "up", "z", "bl"}
TRACK_HUES = {"Core path": "#3ddc97", "Working with model APIs": "#7aa2ff", "Retrieval and knowledge": "#ffb347",
              "Models and adaptation": "#b48cff", "Agents and systems": "#5ee0e6", "Shipping responsibly": "#ff7e6b"}


def still(svg: str) -> str:
    """The first frame of an animated pixel SVG, without its <style>."""
    root = ET.fromstring(svg)
    for parent in list(root.iter()):
        for child in list(parent):
            classes = set((child.get("class") or "").split())
            if child.tag == f"{{{SVG_NS}}}style" or classes & OVERLAYS or any(LATER_FRAME.match(c) for c in classes):
                parent.remove(child)
    for el in root.iter():
        el.attrib.pop("class", None)
    return ET.tostring(root, encoding="unicode")


def lesson_json(lesson):
    sections = []
    for s in lesson.walkthrough():
        visual = visuals.VISUALS.get(s.visual) if s.visual else None
        sections.append({
            "id": s.id, "title": s.title, "body": s.body, "callout": s.callout,
            "code": s.code.source if s.code else "",
            "table": {"columns": list(s.table.columns), "rows": [list(r) for r in s.table.rows]} if s.table else None,
            "figure": {"title": visual.title, "svg": visual.render(), "notice": visual.notice}
            if visual and visual.render and not visual.interactive else None,
            "interactive": bool(visual and visual.interactive),
        })
    return {
        "id": lesson.id, "title": lesson.title, "topic": lesson.topic, "minutes": lesson.minutes,
        "level": lesson.level, "summary": lesson.summary, "objective": lesson.objective, "intro": lesson.intro,
        "keyIdeas": list(lesson.key_ideas), "sections": sections,
        "activity": {"title": lesson.activity.title, "steps": list(lesson.activity.steps)},
        "checks": [{"id": c.id, "prompt": c.prompt, "options": list(c.options), "answer": c.answer,
                    "explanation": c.explanation, "section": c.section} for c in lesson.checks],
        "version": lesson.version,
    }


def main():
    content = {
        "tracks": [{"name": t, "hue": TRACK_HUES[t], "icon": still(pixels.TRACK_ICONS[t]())} for t in TRACK_ORDER],
        "topics": [{
            "id": t.id, "number": t.number, "title": t.title, "blurb": t.blurb, "why": t.why, "track": t.track,
            "thumb": visuals.thumbnail(t.id),
            "items": [{"id": i, "kind": "lesson" if i in LESSONS else "outline", "title": curriculum.get(i).title,
                       "objective": curriculum.get(i).objective,
                       "planned": list(OUTLINES[i].planned) if i in OUTLINES else []} for i in t.lessons],
        } for t in TOPICS],
        "lessons": {lid: lesson_json(lesson) for lid, lesson in LESSONS.items()},
        "art": {name: still(fn()) for name, fn in {
            "deskDay": lambda: pixels.desk_scene(False), "deskNight": lambda: pixels.desk_scene(True),
            "cat": pixels.sleeping_cat, "trophy": pixels.trophy, "robot": pixels.robot_builder,
            "explore": pixels.explore_scene, "library": pixels.library_scene, "notebook": pixels.notebook_scene,
        }.items()},
    }
    out = ROOT / "mobile" / "assets" / "content.json"
    out.write_text(json.dumps(content, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}: {len(content['topics'])} topics, {len(content['lessons'])} lessons, "
          f"{out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
