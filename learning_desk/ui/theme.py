"""The shared design system: tokens, layout rules and small presentational helpers.

Only app-authored, static HTML goes through st.html (styles and SVG diagrams). User and model text is
always rendered with st.markdown/st.text, which never allows HTML."""

import base64
import html
import re

import streamlit as st

from .. import visuals

CSS = """
<style>
/* True-black flat, warm: one ground, elevation by lightness alone (no borders or shadows on cards),
   teal only on data and progress, the one primary action an inverted pill. */
:root {
  --ld-ground: #0e0d0c; --ld-panel: #181716; --ld-raised: #211f1d; --ld-hover: #1d1b19; --ld-figure: #161513;
  --ld-rule: #2b2826; --ld-control: #4a4642;
  --ld-text: #ebebe9; --ld-strong: #ffffff; --ld-muted: #b8b4ae; --ld-faint: #98948e;
  --ld-data: #6db3c4; --ld-radius: 14px;
}
[data-testid="stMainBlockContainer"] { max-width: 1132px; padding-top: 2.5rem; padding-bottom: 5rem; }
h1, h2, h3 { letter-spacing: -0.012em; }
p, li { text-wrap: pretty; }
/* Navigation recedes: the active item is its label brightening, nothing else. */
[data-testid="stSidebarNav"] a { background: transparent !important; }
[data-testid="stSidebarNav"] a span { color: var(--ld-muted) !important; }
[data-testid="stSidebarNav"] a:hover span, [data-testid="stSidebarNav"] a[aria-current="page"] span { color: var(--ld-strong) !important; }
[data-testid="stSidebarNav"] a[aria-current="page"] span { font-weight: 600; }
[data-testid="stSidebarHeader"] { align-items: center; }
[data-testid="stSidebarHeader"]::after { content: "Learning Desk"; color: var(--ld-strong); font-weight: 600;
  font-size: 1.0625rem; letter-spacing: -0.01em; margin-left: .55rem; margin-right: auto; }
/* The one primary action: an inverted pill. Secondary actions stay quiet. */
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {
  background: var(--ld-text) !important; color: var(--ld-ground) !important; border-color: var(--ld-text) !important; }
[data-testid="stBaseButton-primary"] p, [data-testid="stBaseButton-primaryFormSubmit"] p { color: var(--ld-ground) !important; }
[data-testid="stBaseButton-primary"]:hover { background: var(--ld-strong) !important; }
[data-testid="stBaseButton-secondary"] { background: transparent; border-color: var(--ld-control); }
[data-testid="stBaseButton-secondary"]:hover { border-color: var(--ld-muted); background: var(--ld-hover); }
button p { word-break: normal !important; overflow-wrap: normal; }
/* Selections are brightness, not colour: segmented controls, pills and tabs. */
[data-testid="stBaseButton-segmented_controlActive"], [data-testid="stBaseButton-pillsActive"] {
  background: var(--ld-raised) !important; border-color: var(--ld-muted) !important; color: var(--ld-strong) !important; }
[data-testid="stBaseButton-segmented_controlActive"] p, [data-testid="stBaseButton-pillsActive"] p { color: var(--ld-strong) !important; }
[data-baseweb="tab-highlight"] { background-color: var(--ld-text) !important; }
[data-baseweb="tab"][aria-selected="true"] p { color: var(--ld-strong) !important; }
/* Panels: one lightness step above the ground, no edge. */
[class*="st-key-card"], [class*="st-key-panel"], [class*="st-key-hero"], [class*="st-key-side"],
[class*="st-key-notes"], [class*="st-key-objective"], [class*="st-key-tile"] {
  background: var(--ld-panel); border-color: transparent !important; border-radius: var(--ld-radius) !important; }
[class*="st-key-card"] { transition: background-color .15s ease; }
[class*="st-key-card"]:hover, [class*="st-key-card"]:focus-within { background: var(--ld-hover); }
[class*="st-key-muted-card"] { background: transparent; border-color: var(--ld-rule) !important; border-radius: var(--ld-radius) !important; }
[class*="st-key-muted-card"] p, [class*="st-key-muted-card"] [data-testid="stCaptionContainer"] { color: var(--ld-faint); }
[class*="st-key-row"] { background: var(--ld-raised); border-color: transparent !important; border-radius: 12px !important; }
[class*="st-key-figure"] { background: var(--ld-figure); border-color: transparent !important; border-radius: var(--ld-radius) !important; }
/* In a stretched panel, only its closing action sits at the foot. */
.st-key-panel-notes > div:last-child, .st-key-panel-path > div:last-child { margin-top: auto; }
/* Count tiles: label above, value in regular weight with tabular figures. */
.ld-tile-label { color: var(--ld-muted); font-size: .875rem; margin: 0; }
.ld-tile-value { color: var(--ld-strong); font-size: 1.75rem; font-weight: 400; font-variant-numeric: tabular-nums;
  line-height: 1.15; margin: .35rem 0 .2rem 0; }
.ld-tile-unit { color: var(--ld-faint); font-size: 1rem; }
/* The lesson strip: one cell per finished lesson, grouped by topic. */
.ld-strip { display: flex; flex-wrap: nowrap; justify-content: space-between; gap: 8px; margin: .5rem 0 .75rem 0;
  padding: 0; list-style: none; }
.ld-strip li { display: flex; gap: 3px; }
.ld-strip span { display: block; width: clamp(12px, 1.6vw, 22px); height: 64px; border-radius: 5px; background: var(--ld-raised); }
.ld-strip span { position: relative; overflow: hidden; }
.ld-strip span.started::after { content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 45%;
  background: var(--ld-data); }
.ld-strip span.done { background: var(--ld-data); }
/* Comfortable reading measure for lesson and reader prose. */
[class*="st-key-prose"] { max-width: 46rem; }
[class*="st-key-prose"] p, [class*="st-key-prose"] li { font-size: 1.0625rem; line-height: 1.7; }
.ld-figure { margin: 0; overflow-x: auto; }
.ld-figure img { min-width: 520px; }
.ld-scroll-hint { display: none; color: var(--ld-muted); font-size: .8125rem; margin: .25rem 0 0 0; }
/* Lesson contents: left-aligned, wrapping entries. */
[class*="st-key-side"] [data-testid="stButton"] button { justify-content: flex-start; text-align: left; width: 100%; }
[class*="st-key-side"] [data-testid="stButton"] button p { text-align: left; }
:focus-visible { outline: 2px solid var(--ld-text) !important; outline-offset: 2px; }
@media (max-width: 640px) {
  [data-testid="stMainBlockContainer"] { padding: 3.75rem 1rem 4rem 1rem; }
  h1 { font-size: 1.5rem !important; }
  /* Count tiles become a 2 x 2 grid on a phone. */
  .st-key-tiles [data-testid="stHorizontalBlock"] { flex-flow: row wrap !important; gap: .75rem !important; }
  .st-key-tiles [data-testid="stColumn"] { flex: 1 1 calc(50% - .375rem) !important; min-width: calc(50% - .375rem) !important; width: calc(50% - .375rem) !important; }
  .ld-tile-value { font-size: 1.5rem; }
  [class*="st-key-prose"] p, [class*="st-key-prose"] li { font-size: 1rem; }
  .ld-scroll-hint { display: block; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>
"""

# Levels are information, not status: one neutral colour.
LEVEL_COLOURS = {"introductory": "gray", "intermediate": "gray", "advanced": "gray"}
STATUS_STYLE = {  # label -> (badge colour, Material icon)
    "Completed": ("green", ":material/check_circle:"),
    "In progress": ("primary", ":material/play_circle:"),
    "Ready": ("gray", ":material/menu_book:"),
    "Outline": ("orange", ":material/edit_note:"),
    "Saved": ("gray", ":material/bookmark:"),
    "Reading": ("primary", ":material/auto_stories:"),
    "Finished": ("green", ":material/check_circle:"),
}
RESOURCE_ICONS = {"reference": ":material/link:", "documentation": ":material/description:",
                  "article": ":material/article:", "pasted": ":material/content_paste:"}


def svg_img(svg: str, alt: str, css_class: str = "ld-figure-img") -> str:
    """Streamlit sanitises inline SVG away, so diagrams are embedded as images. The alt attribute
    carries the full text alternative for screen readers."""
    data = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    natural = re.search(r'viewBox="0 0 (\d+)', svg)
    cap = f"max-width:{int(natural.group(1)) * 1.2:.0f}px;" if natural else ""
    return (f'<img class="{css_class}" src="data:image/svg+xml;base64,{data}" alt="{html.escape(alt, quote=True)}" '
            f'style="width:100%;{cap}height:auto;display:block;margin:0 auto">')


def inject() -> None:
    st.html(CSS)


def eyebrow(text: str) -> None:
    st.caption(text.upper())


def status_badge(label: str) -> None:
    colour, icon = STATUS_STYLE.get(label, ("gray", None))
    st.badge(label, icon=icon, color=colour)


def badges(*items: tuple[str, str, str | None]) -> None:
    """A wrapping row of (label, colour, icon) badges."""
    with st.container(horizontal=True, gap="small"):
        for label, colour, icon in items:
            st.badge(label, icon=icon, color=colour)


def figure(visual_id: str, svg: str | None = None, key: str = "") -> None:
    """A diagram with its title, what-to-notice note, illustrative label and text alternative.
    The SVG is generated by our own code; nothing user-supplied is interpolated unescaped."""
    visual = visuals.VISUALS[visual_id]
    description = visual.alt
    if svg is None:
        svg = visual.render()
    else:  # an interactive state: describe what is actually drawn, taken from the SVG's own <desc>
        match = re.search(r"<desc[^>]*>(.*?)</desc>", svg, re.S)
        description = html.unescape(match.group(1)) if match else visual.alt
    with st.container(border=True, key=f"figure-{key or visual_id}"):
        st.markdown(f"**{visual.title}**")
        st.html(f'<figure class="ld-figure">{svg_img(svg, description)}</figure>'
                '<p class="ld-scroll-hint">Scroll sideways to see the whole diagram, or open the text description.</p>')
        st.caption(f":material/visibility: **What to notice:** {visual.notice}")
        if visual.illustrative:
            st.caption(f":material/info: **Illustrative:** {visual.illustrative}")
        with st.expander("Text description of this diagram"):
            st.write(description)
