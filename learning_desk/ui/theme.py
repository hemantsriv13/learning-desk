"""The shared design system: tokens, layout rules and small presentational helpers.

Only app-authored, static HTML goes through st.html (styles and SVG diagrams). User and model text is
always rendered with st.markdown/st.text, which never allows HTML."""

import base64
import html
import re

import streamlit as st

from .. import pixels, visuals

CSS = """
<style>
/* Black page, graphite cards with a visible edge. Colour carries meaning, never decoration: each track (and
   the page that belongs to it) has one hue, used on its icons and its cards' top edge. Mint is the data and
   progress colour and the one primary action. */
:root {
  --ld-ground: #050505; --ld-panel: #2a2a2a; --ld-raised: #353535; --ld-hover: #313131; --ld-figure: #222222;
  --ld-rule: #444444; --ld-control: #5a5a5a;
  --ld-text: #f4f4f4; --ld-strong: #ffffff; --ld-muted: #c8c8c8; --ld-faint: #aaaaaa;
  /* Panels are nearly opaque over the faint pixel layer, so text contrast is set by the panel alone. */
  --ld-glass: #2a2a2a;
  --ld-data: #3ddc97; --ld-data-soft: rgba(61, 220, 151, .14); --ld-warm: #ffb347; --ld-radius: 14px;
  /* Dark-mode depth is a lit top edge, not a drop shadow. */
  --ld-rim: inset 0 0 0 1px #5a5a5a;  /* cards on a black page carry a visible graphite edge */
}
/* The ground: a desk under a lamp. A cool glow top-left and a warm one top-right fade into the near-black,
   and a faint dot grid sits only behind the page heading. Text never sits on anything busier than that. */
.stApp { --page-hue: #3ddc97; }
.stApp:has(.ld-page.hue-blue) { --page-hue: #7aa2ff; } .stApp:has(.ld-page.hue-amber) { --page-hue: #ffb347; }
.stApp:has(.ld-page.hue-violet) { --page-hue: #b48cff; } .stApp:has(.ld-page.hue-green) { --page-hue: #5ee0e6; }
.stApp:has(.ld-page.hue-coral) { --page-hue: #ff7e6b; } .stApp:has(.ld-page.hue-gray) { --page-hue: #7aa2ff; }
/* A flat black ground; the only moving thing behind content is the faint pixel layer. */
.stApp { background: var(--ld-ground) !important; }
[data-testid="stAppViewContainer"] { background: transparent !important; position: relative; z-index: 1; }
.stApp::before, .stApp::after { content: none; }
[data-testid="stMain"] { position: relative; }
[data-testid="stMainBlockContainer"] { position: relative; }
[data-testid="stSidebar"] { background: #121212 !important; }
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stMainBlockContainer"] { max-width: 1132px; padding-top: 2.5rem; padding-bottom: 5rem; }
h1, h2, h3 { letter-spacing: -0.012em; }
.ld-page h1, .ld-head-title, .ld-idea, .ld-ring-hole b { font-family: "Space Grotesk", "Inter", system-ui, sans-serif; }
p, li { text-wrap: pretty; }
/* Navigation recedes: the active item is its label brightening, nothing else. */
[data-testid="stSidebarNav"] a { background: transparent !important; }
[data-testid="stSidebarNav"] a span { color: var(--ld-muted) !important; }
[data-testid="stSidebarNav"] a:hover span, [data-testid="stSidebarNav"] a[aria-current="page"] span { color: var(--ld-strong) !important; }
[data-testid="stSidebarNav"] a[aria-current="page"] span { font-weight: 600; }
[data-testid="stSidebarNav"] a [data-testid="stIconMaterial"] { color: var(--nav-hue, var(--ld-muted)) !important; }
[data-testid="stSidebarNav"] a[aria-current="page"] { background: color-mix(in srgb, var(--nav-hue, #3ddc97) 12%, transparent) !important; }
[data-testid="stSidebarNav"] a[href$="/explore"] { --nav-hue: #3ddc97; }
[data-testid="stSidebarNav"] a[href$="/library"] { --nav-hue: #ffb347; }
[data-testid="stSidebarNav"] a[href$="/notebook"] { --nav-hue: #b48cff; }
[data-testid="stSidebarNav"] a[href$="/queue"] { --nav-hue: #5ee0e6; }
[data-testid="stSidebarNav"] a[href$="/search"] { --nav-hue: #7aa2ff; }
[data-testid="stSidebarNav"] a[href$="/settings"] { --nav-hue: #b5b5b5; }
[data-testid="stSidebarNav"] li:first-child a:not([href$="/explore"]):not([href$="/library"]):not([href$="/notebook"]):not([href$="/queue"]):not([href$="/search"]):not([href$="/settings"]) { --nav-hue: #3ddc97; }
[data-testid="stSidebarHeader"] { align-items: center; }
[data-testid="stSidebarHeader"]::after { content: "Learning Desk"; color: var(--ld-strong); font-weight: 600;
  font-size: 1.0625rem; letter-spacing: -0.01em; margin-left: .55rem; margin-right: auto; }
/* The one primary action: an inverted pill. Secondary actions stay quiet. */
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {
  background: var(--ld-data) !important; color: var(--ld-ground) !important; border-color: var(--ld-data) !important; }
[data-testid="stBaseButton-primary"] p, [data-testid="stBaseButton-primaryFormSubmit"] p { color: var(--ld-ground) !important; }
[data-testid="stBaseButton-primary"]:hover { background: #6be8b1 !important; border-color: #6be8b1 !important; }
[data-testid="stBaseButton-secondary"] { background: transparent; border-color: var(--ld-control); }
[data-testid="stBaseButton-secondary"]:hover { border-color: var(--ld-muted); background: var(--ld-hover); }
button p { word-break: normal !important; overflow-wrap: normal; }
/* Selections take the page's hue: segmented controls, pills and tabs. */
[data-testid="stBaseButton-segmented_controlActive"], [data-testid="stBaseButton-pillsActive"] {
  background: color-mix(in srgb, var(--page-hue) 16%, var(--ld-panel)) !important;
  border-color: color-mix(in srgb, var(--page-hue) 60%, transparent) !important; color: var(--ld-strong) !important; }
[data-testid="stBaseButton-segmented_controlActive"] p, [data-testid="stBaseButton-pillsActive"] p { color: var(--ld-strong) !important; }
[data-testid="stBaseButton-segmented_controlActive"] [data-testid="stIconMaterial"],
[data-testid="stBaseButton-pillsActive"] [data-testid="stIconMaterial"] { color: var(--page-hue) !important; }
[data-baseweb="tab-highlight"] { background-color: var(--page-hue) !important; }
[data-baseweb="tab"][aria-selected="true"] p { color: var(--ld-strong) !important; }
/* Panels: one lightness step above the ground, no edge. */
[class*="st-key-card"], [class*="st-key-panel"], [class*="st-key-hero"], [class*="st-key-side"],
[class*="st-key-notes"], [class*="st-key-objective"], [class*="st-key-tile"] {
  background: linear-gradient(180deg, rgba(255, 255, 255, .025), rgba(255, 255, 255, 0) 120px), var(--ld-glass);
  border-color: transparent !important; border-radius: var(--ld-radius) !important; box-shadow: var(--ld-rim); }
/* Cards and tiles (topics, tracks, lessons) are a flat fill: no gradient of any kind. */
[class*="st-key-card"], [class*="st-key-tile"], .st-key-panel-tracks { background: var(--ld-glass); }
[class*="st-key-card"] { transition: background-color .15s ease, box-shadow .15s ease; }
[class*="st-key-card"]:focus-within { background: var(--ld-hover); }
@media (hover: hover) and (pointer: fine) {
  [class*="st-key-card"]:hover { background: var(--ld-hover);
    box-shadow: inset 0 1px 0 0 rgba(255, 255, 255, .08), inset 0 0 0 1px rgba(255, 255, 255, .05); } }
/* The Continue panel is one step lighter than other panels: it is the first thing to read on Home. */
[class*="st-key-hero"] { background: var(--ld-raised) !important; }
/* Icon chips: a Material Symbol in a tinted square, the app's one icon family (the same font Streamlit uses). */
.ld-icon { font-family: "Material Symbols Rounded"; font-weight: 400; font-style: normal; font-size: 20px; line-height: 1;
  letter-spacing: normal; text-transform: none; white-space: nowrap; font-feature-settings: "liga";
  -webkit-font-smoothing: antialiased; display: inline-flex; align-items: center; justify-content: center;
  flex: none; width: 34px; height: 34px; border-radius: 10px; background: var(--ld-data-soft); color: var(--ld-data); }
.ld-icon.quiet { background: var(--ld-raised); color: var(--ld-muted); }
.hue-teal { --hue: #3ddc97; } .hue-blue { --hue: #7aa2ff; } .hue-amber { --hue: #ffb347; }
.hue-violet { --hue: #b48cff; } .hue-green { --hue: #5ee0e6; } .hue-coral { --hue: #ff7e6b; } .hue-gray { --hue: #b5b5b5; }
.ld-icon[class*="hue-"] { color: var(--hue); background: color-mix(in srgb, var(--hue) 22%, transparent); }
/* A card whose heading chip has a hue takes that hue as a lit top edge; its fill stays flat. */
[class*="st-key-card"]:has(> [data-testid="stElementContainer"] .ld-head .hue-teal), [class*="st-key-tile"]:has(> [data-testid="stElementContainer"] .ld-head .hue-teal) { --hue: #3ddc97; }
[class*="st-key-card"]:has(> [data-testid="stElementContainer"] .ld-head .hue-blue), [class*="st-key-tile"]:has(> [data-testid="stElementContainer"] .ld-head .hue-blue) { --hue: #7aa2ff; }
[class*="st-key-card"]:has(> [data-testid="stElementContainer"] .ld-head .hue-amber), [class*="st-key-tile"]:has(> [data-testid="stElementContainer"] .ld-head .hue-amber) { --hue: #ffb347; }
[class*="st-key-card"]:has(> [data-testid="stElementContainer"] .ld-head .hue-violet), [class*="st-key-tile"]:has(> [data-testid="stElementContainer"] .ld-head .hue-violet) { --hue: #b48cff; }
[class*="st-key-card"]:has(> [data-testid="stElementContainer"] .ld-head .hue-green), [class*="st-key-tile"]:has(> [data-testid="stElementContainer"] .ld-head .hue-green) { --hue: #5ee0e6; }
[class*="st-key-card"]:has(> [data-testid="stElementContainer"] .ld-head .hue-coral), [class*="st-key-tile"]:has(> [data-testid="stElementContainer"] .ld-head .hue-coral) { --hue: #ff7e6b; }
[class*="st-key-card"]:has(> [data-testid="stElementContainer"] .ld-head [class*="hue-"]),
[class*="st-key-tile"]:has(> [data-testid="stElementContainer"] .ld-head [class*="hue-"]) {
  box-shadow: inset 0 2px 0 0 var(--hue), inset 0 0 0 1px color-mix(in srgb, var(--hue) 35%, #5a5a5a); }
@media (hover: hover) and (pointer: fine) {
  [class*="st-key-card"]:has(> [data-testid="stElementContainer"] .ld-head [class*="hue-"]):hover,
  [class*="st-key-tile"]:has(> [data-testid="stElementContainer"] .ld-head [class*="hue-"]):hover {
    box-shadow: inset 0 2px 0 0 var(--hue),
                inset 0 0 0 1px color-mix(in srgb, var(--hue) 28%, transparent); } }
/* Page header: the page's icon in its hue, the title, and one line on what the page is for. */
.ld-page { display: flex; align-items: center; gap: 1rem; margin: 0 0 .25rem 0; }
.ld-page .ld-icon { width: 52px; height: 52px; font-size: 28px; border-radius: 15px;
  box-shadow: inset 0 1px 0 0 color-mix(in srgb, var(--hue) 45%, transparent); }
.ld-page h1 { color: var(--ld-strong); font-size: 2rem; font-weight: 600; line-height: 1.2; letter-spacing: -0.015em;
  margin: 0; padding: 0; }
.ld-page p { color: var(--ld-muted); font-size: 1rem; line-height: 1.45; margin: .2rem 0 0 0; }
/* Pixel art: drawn at a whole-number scale so every pixel stays square. */
.ld-page-art { margin-left: auto; flex: none; }
.ld-empty { display: flex; align-items: center; gap: .9rem; margin: 0; }
.ld-empty p { color: var(--ld-muted); font-size: .9375rem; line-height: 1.45; margin: 0; }
.ld-art-row { display: flex; align-items: center; gap: 1rem; margin: 0; }
.ld-art-row p { color: var(--ld-muted); margin: 0; }
/* Progress ring: completed in full colour, in progress lighter, the rest a quiet track. It fills once on load. */
@property --ld-p { syntax: "\\3c percentage\\3e"; inherits: false; initial-value: 0%; }
@property --ld-q { syntax: "\\3c percentage\\3e"; inherits: false; initial-value: 0%; }
@keyframes ld-fill { from { --ld-p: 0%; --ld-q: 0%; } }
.ld-progress { display: flex; align-items: center; gap: 1.1rem; }
.ld-ring { flex: none; width: 104px; height: 104px; border-radius: 50%; display: grid; place-items: center;
  background: conic-gradient(var(--ld-data) var(--ld-p), color-mix(in srgb, var(--ld-data) 38%, transparent) var(--ld-p) var(--ld-q),
                              var(--ld-rule) var(--ld-q)); }
.ld-ring-hole { width: 80px; height: 80px; border-radius: 50%; background: var(--ld-panel); display: grid; place-items: center;
  align-content: center; }
.ld-ring-hole b { color: var(--ld-strong); font-size: 1.375rem; font-weight: 600; font-variant-numeric: tabular-nums; line-height: 1; }
.ld-ring-hole span { color: var(--ld-muted); font-size: .75rem; margin-top: .2rem; }
.ld-legend { list-style: none; margin: 0 !important; padding: 0 !important; display: grid; gap: .45rem; }
.ld-legend li { margin: 0 !important; display: flex; align-items: center; gap: .5rem; color: var(--ld-muted); font-size: .9375rem; }
.ld-legend li b { color: var(--ld-strong); font-weight: 600; font-variant-numeric: tabular-nums; margin-left: auto; padding-left: .75rem; }
.ld-legend i { width: 10px; height: 10px; border-radius: 3px; flex: none; }
/* Idea of the day: one key idea from a lesson, set large enough to read at a glance. */
.ld-idea { color: var(--ld-strong); font-size: 1.1875rem; line-height: 1.5; margin: 0; text-wrap: pretty; }
/* Motion, two ideas only: surfaces settle in once when a page first opens (MOTION_CSS), and lit edges
   brighten on hover. */
@keyframes ld-rise { from { opacity: 0; transform: translateY(8px); } }
.ld-icon.warm { background: rgba(255, 179, 71, .14); color: var(--ld-warm); }
.ld-head { display: flex; align-items: center; gap: .7rem; margin: 0; }
.ld-head-text { display: flex; flex-direction: column; gap: .1rem; min-width: 0; }
.ld-head-title { color: var(--ld-strong); font-weight: 600; font-size: 1rem; line-height: 1.3; margin: 0; }
.ld-head-note { color: var(--ld-muted); font-size: .875rem; line-height: 1.4; margin: 0; }
.ld-head.lg .ld-head-title { font-size: 1.125rem; }
.ld-head-art { margin-left: auto; flex: none; }
/* Stat rows: icon, label, value on one line, so four counts read as a list rather than four billboards. */
.ld-stats { list-style: none; margin: 0 !important; padding: 0 !important; display: grid; gap: .25rem; }
.ld-stats li { margin: 0 !important; display: flex; align-items: center; gap: .7rem; padding: .45rem 0; }
.ld-stats li + li { border-top: 1px solid var(--ld-rule); }
.ld-stats .ld-icon { width: 30px; height: 30px; font-size: 18px; border-radius: 9px; }
.ld-stat-label { color: var(--ld-muted); font-size: .9375rem; flex: 1; }
.ld-stat-value { color: var(--ld-strong); font-size: 1.125rem; font-variant-numeric: tabular-nums; }
.ld-stat-value small { color: var(--ld-faint); font-size: .8125rem; margin-left: .2rem; }
/* Section progress: one segment per walkthrough section; segments before your place are filled. */
.ld-steps { display: flex; gap: 4px; margin: 0 !important; padding: 0 !important; list-style: none; }
.ld-steps li { margin: 0 !important; flex: 1; height: 6px; border-radius: 3px; background: var(--ld-control); opacity: .55; }
.ld-steps li.before { background: var(--ld-data); opacity: .55; }
.ld-steps li.here { background: var(--ld-data); opacity: 1; }
.ld-thumb-wrap img { border-radius: 10px; }
[class*="st-key-muted-card"] { background: transparent; border-color: var(--ld-rule) !important; border-radius: var(--ld-radius) !important; }
[class*="st-key-muted-card"] p, [class*="st-key-muted-card"] [data-testid="stCaptionContainer"] { color: var(--ld-faint); }
[class*="st-key-row"] { background: var(--ld-raised); border-color: transparent !important; border-radius: 12px !important; }
[class*="st-key-figure"] { background: var(--ld-figure); border-color: transparent !important; border-radius: var(--ld-radius) !important; }
/* In a stretched panel, only its closing action sits at the foot. */
.st-key-panel-notes > div:last-child, .st-key-panel-path > div:last-child, .st-key-panel-desk > div:last-child,
[class*="st-key-card-next"] > div:last-child, [class*="st-key-card-topic"] > div:last-child,
.st-key-card-idea > div:last-child { margin-top: auto; }
/* The lesson strip: one cell per finished lesson, grouped by topic. */
.ld-strip { display: flex; flex-wrap: nowrap; gap: 8px; margin: 0 !important; padding: 0 !important; list-style: none; }
.ld-strip li { display: flex; gap: 3px; min-width: 0; margin: 0 !important; }
.ld-strip span { display: block; flex: 1 1 0; min-width: 5px; height: 52px; border-radius: 4px; background: var(--ld-rule); }
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
  .ld-page .ld-icon { width: 44px; height: 44px; font-size: 24px; border-radius: 13px; }
  .ld-page-art { display: none; }
  [class*="st-key-prose"] p, [class*="st-key-prose"] li { font-size: 1rem; }
  /* On a phone the Continue panel's picture would sit between the text and the button; drop it. */
  .st-key-hero-continue [data-testid="stColumn"]:has(.ld-thumb-wrap) { display: none; }
  /* Thumb-sized targets on touch screens. */
  [data-testid^="stBaseButton"], [data-testid="stPageLink-NavLink"] { min-height: 44px; }
  .ld-scroll-hint { display: block; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; }
  [data-testid="stAppViewContainer"]::before { animation: none !important; } }
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


# Sent only on the first run of each page in a session, so clicks that rerun the page never replay it.
MOTION_CSS = """<style>
.ld-page, [class*="st-key-hero"], [class*="st-key-panel"], [class*="st-key-card"], [class*="st-key-tile"] {
  animation: ld-rise .38s cubic-bezier(.2, .7, .2, 1) both; }
.ld-ring { animation: ld-fill 1s cubic-bezier(.2, .7, .2, 1) both; }
@media (prefers-reduced-motion: reduce) { * { animation: none !important; } }
</style>"""


# The pixel-art backdrop: one tile from pixels.backdrop_tile, repeated behind the content at 3 screen pixels per
# art pixel, drifting up and left by exactly one tile per loop so the movement never shows a seam.
_TILE_W, _TILE_H = 780, 540
BACKDROP_CSS = f"""<style>
[data-testid="stAppViewContainer"]::before {{ content: ""; position: fixed; z-index: -1; pointer-events: none;
  top: 0; left: 0; width: calc(100vw + {_TILE_W}px); height: calc(100vh + {_TILE_H}px);
  background: url("{pixels.data_uri(pixels.backdrop_tile())}") 0 0 / {_TILE_W}px {_TILE_H}px repeat;
  opacity: .42; will-change: transform; animation: ld-float 260s linear infinite; }}
@keyframes ld-float {{ to {{ transform: translate3d(-{_TILE_W}px, -{_TILE_H}px, 0); }} }}
@media (prefers-reduced-motion: reduce) {{ [data-testid="stAppViewContainer"]::before {{ animation: none; }} }}
</style>"""


def inject() -> None:
    st.html(CSS)
    st.html(BACKDROP_CSS)


def entrance(page: str) -> str:
    """The motion styles on this page's first run in the session, else nothing. Returned rather than rendered
    so it rides inside the page header and never adds (then removes) an element that would shift the layout."""
    flag = f"_entered_{page}"
    if st.session_state.get(flag):
        return ""
    st.session_state[flag] = True
    return MOTION_CSS


def eyebrow(text: str) -> None:
    st.caption(text.upper())


# One hue per track, and the page that belongs to it. Hue names map to .hue-* classes in CSS.
HUES = ("teal", "blue", "amber", "violet", "green", "coral", "gray")
TRACK_HUES = {"Core path": "teal", "Working with model APIs": "blue", "Retrieval and knowledge": "amber",
              "Models and adaptation": "violet", "Agents and systems": "green", "Shipping responsibly": "coral"}


def icon(name: str, tone: str = "", hue: str = "") -> str:
    """A Material Symbol chip. Decorative: every chip sits beside a text label that says the same thing."""
    classes = " ".join(c for c in ("ld-icon", tone, f"hue-{hue}" if hue else "") if c)
    return f'<span class="{classes}" aria-hidden="true">{html.escape(name)}</span>'


def heading(icon_name: str, title: str, note: str = "", tone: str = "", large: bool = False, hue: str = "",
            art: str = "") -> None:
    """A panel heading: icon chip, title and an optional one-line note under it. A hue also tints the card;
    `art` is an optional small pixel figure (from pixels.img) at the right."""
    sub = f'<p class="ld-head-note">{html.escape(note)}</p>' if note else ""
    art = f'<div class="ld-head-art">{art}</div>' if art else ""
    st.html(f'<div class="ld-head{" lg" if large else ""}">{icon(icon_name, tone, hue)}<div class="ld-head-text">'
            f'<p class="ld-head-title">{html.escape(title)}</p>{sub}</div>{art}</div>')


def page_header(title: str, note: str, icon_name: str, hue: str, art: str = "") -> None:
    """The page title with its icon in the page's hue; the hue also tints the glow behind the page.
    `art` is an optional pixel-art image (from pixels.img) shown at the right on wide screens."""
    sub = f"<p>{html.escape(note)}</p>" if note else ""
    art = f'<div class="ld-page-art">{art}</div>' if art else ""
    st.html(f'{entrance(title)}<div class="ld-page hue-{hue}">{icon(icon_name, hue=hue)}'
            f'<div><h1>{html.escape(title)}</h1>{sub}</div>{art}</div>')


def empty_state(text: str) -> None:
    """An empty list: the sleeping cat and one line saying what will appear here."""
    st.html(f'<div class="ld-empty">{pixels.img(pixels.sleeping_cat(), 96)}<p>{html.escape(text)}</p></div>')


def art_row(art: str, text: str = "") -> None:
    """A pixel figure with an optional line beside it."""
    st.html(f'<div class="ld-art-row">{art}{f"<p>{html.escape(text)}</p>" if text else ""}</div>')


def progress_ring(done: int, started: int, total: int) -> None:
    """Completed and in-progress lessons as a ring with a legend that carries the same numbers in text."""
    p, q = (done / total * 100, (done + started) / total * 100) if total else (0, 0)
    label = f"{done} of {total} lessons completed, {started} in progress"
    legend = "".join(f'<li><i style="background:{colour}"></i>{name}<b>{n}</b></li>' for name, n, colour in (
        ("Completed", done, "var(--ld-data)"),
        ("In progress", started, "color-mix(in srgb, var(--ld-data) 38%, transparent)"),
        ("Not started", total - done - started, "var(--ld-rule)")))
    st.html(f'<div class="ld-progress"><div class="ld-ring" role="img" aria-label="{html.escape(label, quote=True)}" '
            f'style="--ld-p:{p:.1f}%;--ld-q:{q:.1f}%"><div class="ld-ring-hole"><b>{round(p)}%</b>'
            f'<span>complete</span></div></div><ul class="ld-legend">{legend}</ul></div>')


def stats(rows: list[tuple]) -> None:
    """Counts as a list of (icon, label, value, unit[, hue]) rows."""
    items = "".join(f'<li>{icon(row[0], "" if len(row) > 4 else "quiet", row[4] if len(row) > 4 else "")}'
                    f'<span class="ld-stat-label">{html.escape(row[1])}</span>'
                    f'<span class="ld-stat-value">{row[2]}<small>{html.escape(row[3])}</small></span></li>'
                    for row in rows)
    st.html(f'<ul class="ld-stats">{items}</ul>')


def steps(total: int, here: int, label: str) -> str:
    """A segmented bar for a place in a sequence; `here` is 0-based, -1 for not started."""
    cells = "".join(f'<li class="{"here" if i == here else "before" if i < here else ""}"></li>' for i in range(total))
    return f'<ul class="ld-steps" role="img" aria-label="{html.escape(label, quote=True)}">{cells}</ul>'


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
