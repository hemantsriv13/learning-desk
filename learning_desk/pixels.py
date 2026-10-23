"""Original pixel-art figures, drawn in code: each sprite is a grid of palette letters turned into SVG
rectangles (runs of one colour become one rect). Animation is CSS inside the SVG, so it still plays when
Streamlit shows the SVG as an image (inline SVG is sanitised away). Frames swap with stepped keyframes, the
same way a sprite sheet does; a reduced-motion rule inside each SVG shows the first frame and stops.

All figures are decorative and sit next to text that says the same thing, so they carry empty alt text."""

import base64
from html import escape

# One palette for every figure, built from the app's hues so the art belongs to the same system.
PALETTE = {
    "K": "#0f1220",  # darkest line
    "S": "#f2c7a5", "s": "#d9a07f", "r": "#ff9a8a",  # skin, skin shade, blush
    "H": "#5b3a29", "h": "#7a4f38",  # hair
    "E": "#1a1d2b", "w": "#ffffff",  # eyes, eye glint
    "m": "#b5654f",  # mouth
    "T": "#3ddc97", "t": "#22a06b",  # shirt / mint
    "L": "#bdbab2", "l": "#5a5751",  # light and dark grey
    "G": "#7aa2ff",  # screen glow / blue
    "D": "#9a6a48", "d": "#6b4430",  # wood
    "M": "#ff7e6b", "k": "#5a3a2a",  # mug, coffee
    "W": "rgba(236, 238, 245, .55)",  # steam
    "P": "#5fd38d", "p": "#2f9a5c",  # plant
    "O": "#ffb347", "o": "#c98420",  # pot / amber
    "Y": "#ffd98a", "y": "#ffb347",  # lamp light, lamp body / gold shade
    "V": "#b48cff", "B": "#7aa2ff", "R": "#ff7e6b", "A": "#ffb347", "N": "#5ee0e6",  # book spines
    "b": "#6fa8e8", "c": "#9cc6f0",  # day sky
    "n": "#2e3038", "*": "#ffffff",  # night sky, star
    "C": "#ffb347", "Z": "#d0d0d0",  # cat, sleep letters
    "Q": "#ffd166",  # trophy gold
}


def sprite(grid, x=0, y=0, cls="", palette=None):
    """A grid of palette letters as SVG rects; '.' is transparent."""
    palette = palette or PALETTE
    rects = []
    for r, row in enumerate(grid):
        c = 0
        while c < len(row):
            ch = row[c]
            run = 1
            while c + run < len(row) and row[c + run] == ch:
                run += 1
            if ch != ".":
                rects.append(f'<rect x="{x + c}" y="{y + r}" width="{run}" height="1" fill="{palette[ch]}"/>')
            c += run
    attr = f' class="{cls}"' if cls else ""
    return f"<g{attr}>{''.join(rects)}</g>"


def frames_css(name, count, seconds, delay=0.0):
    """Keyframes that show frame i of `count` during its slice of the loop, with hard cuts (steps)."""
    out = []
    for i in range(count):
        start, end = i / count * 100, (i + 1) / count * 100
        keys = [f"0%{{opacity:{1 if i == 0 else 0}}}"]
        if i:
            keys.append(f"{start:.2f}%{{opacity:1}}")
        keys.append(f"{end:.2f}%{{opacity:0}}" if i < count - 1 else "100%{opacity:1}")
        out.append(f"@keyframes {name}{i}{{{''.join(keys)}}}"
                   f".{name}{i}{{opacity:{1 if i == 0 else 0};animation:{name}{i} {seconds}s steps(1,end) {delay}s infinite}}")
    return "".join(out)


def svg(width, height, body, css):
    reduced = "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" shape-rendering="crispEdges" '
            f'aria-hidden="true"><style>{css}{reduced}</style>{body}</svg>')


def img(markup, width, css_class="ld-pixel"):
    """The SVG as an image at a whole-number scale of its pixel grid, so pixels stay square."""
    data = base64.b64encode(markup.encode("utf-8")).decode("ascii")
    return (f'<img class="{escape(css_class)}" src="data:image/svg+xml;base64,{data}" alt="" '
            f'style="width:{width}px;max-width:100%;height:auto;display:block">')


# ---------------------------------------------------------------- the learning desk (Home)

HEAD = (
    "....HHHH....",
    "..HHHHHHHH..",
    ".HHHHHHHHHH.",
    ".HHhhHHHHHH.",
    "HHHSSSSSSHHH",
    "HHSSSSSSSSHH",
    "HSSwESSwESSH",
    "HSSEESSEESSH",
    ".SSSSSSSSSS.",
    ".SSrSSSSrSS.",
    "..SSSmmSSS..",
    "...SSSSSS...",
    "....ssss....",
    "..TTTTTTTT..",
    ".TTTTttTTTT.",
    "TTTTTTTTTTTT",
    "TTTTTTTTTTTT",
    "TTTTTTTTTTTT",
)
BLINK = ("...SS..SS...", "...EE..EE...")
LAPTOP = (
    "llllllllllllllllll",
    "lLLLLLLLLLLLLLLLLl",
    "lLLLLLLLGGLLLLLLLl",
    "lLLLLLLLGGLLLLLLLl",
    "lLLLLLLLLLLLLLLLLl",
    "llllllllllllllllll",
)
MUG = ("MkkkM..", "MMMMMM.", "MMMMM.M", "MMMMMM.", ".MMM...")
STEAM = (
    (".W...", "..W..", ".W...", "..W..", ".W...", "....."),
    ("..W..", ".W...", "..W..", ".W...", ".....", "....."),
    ("...W.", "..W..", ".W...", "..W..", ".W...", "..W.."),
)
PLANT = (
    ("...P...", ".P.PP..", ".PPpP.P", "..PpPPP", "P.PpP..", ".PPpPP."),
    ("....P..", "..P.PP.", ".PPpPP.", "..PpPPP", "P.PpP..", ".PPpPP."),
)
POT = ("OOOOOOO", ".OOOOO.", ".OoOOO.", ".OOOOO.", "..OOO..")
LAMP_HEAD = ("..yyyy.", ".yyyyyy", "YYYY...")
SPARK = (".Y.", "YYY", ".Y.")


def desk_scene(night: bool) -> str:
    """A small figure typing at a laptop at a desk: the app's namesake. 60 x 36 pixels."""
    sky = "n" if night else "b"
    window = ["llllllllllllll"] + [f"l{sky * 6}l{sky * 6}l" for _ in range(5)] + ["llllllllllllll"] + \
             [f"l{sky * 6}l{sky * 6}l" for _ in range(4)] + ["llllllllllllll"]
    if night:
        sky_art = (sprite(("YY.", "Y..", "YY."), 6, 5)  # crescent moon
                   + sprite(("*",), 11, 3, "tw0") + sprite(("*",), 14, 9, "tw1") + sprite(("*",), 6, 10, "tw0")
                   + sprite(("*",), 13, 5, "tw1"))
        sky_css = frames_css("tw", 2, 2.4)
    else:
        sky_art = (sprite((".YY.", "YYYY", "YYYY", ".YY."), 5, 5)  # sun
                   + f'<g class="cloud">{sprite((".WWW..", "WWWWWW"), 11, 9)}</g>')
        sky_css = ".cloud{animation:cloud 14s steps(10,end) infinite alternate}" \
                  "@keyframes cloud{from{transform:translateX(-3px)}to{transform:translateX(2px)}}"
    books = "".join(sprite((c * w,) * h + (("L" * w),), x, 13 - h - 1) for x, w, h, c in (
        (42, 2, 6, "T"), (44, 2, 7, "B"), (46, 2, 5, "A"), (48, 1, 6, "V"), (49, 2, 7, "N"), (51, 2, 6, "R")))
    # Lamplight: a glow round the bulb and a warm pool on the desk below it (a beam drawn on a dark wall
    # reads as a grey wedge, so the light shows where it lands instead).
    cone = ('<rect x="44" y="18" width="3" height="1" fill="#fff1c9"/>'
            '<rect x="38" y="26" width="14" height="1" fill="#c99566"/>'
            '<rect x="41" y="26" width="8" height="1" fill="#e2b07e"/>')
    hands = (sprite(("SS", "ss"), 19, 24, "ty0") + sprite(("SS", "ss"), 39, 22, "ty0")
             + sprite(("SS", "ss"), 19, 22, "ty1") + sprite(("SS", "ss"), 39, 24, "ty1"))
    body = "".join((
        f'<clipPath id="pane"><rect x="4" y="4" width="12" height="10"/></clipPath>',
        sprite(window, 3, 3), f'<g clip-path="url(#pane)">{sky_art}</g>',
        books, sprite(("d" * 17,), 41, 13), sprite(("d", "d"), 43, 14), sprite(("d", "d"), 55, 14),
        sprite(HEAD, 24, 4), sprite(BLINK, 24, 10, "blink"),
        sprite(LAPTOP, 21, 20), hands,
        sprite(MUG, 4, 21), "".join(sprite(f, 4, 15, f"st{i}") for i, f in enumerate(STEAM)),
        "".join(sprite(f, 12, 15, f"pl{i}") for i, f in enumerate(PLANT)), sprite(POT, 12, 21),
        sprite(LAMP_HEAD, 44, 16), sprite(("y",) * 6, 50, 19), sprite(("yyyyyy",), 47, 25),
        sprite(("D" * 56,), 2, 26), sprite(("d" * 56,), 2, 27),
        f'<g class="cone">{cone}</g>',
        sprite(("dd",) * 8, 4, 28), sprite(("dd",) * 8, 54, 28),
        "".join(f'<g class="up up{i}">{sprite(SPARK, x, y)}</g>' for i, (x, y) in enumerate(((19, 17), (38, 16), (30, 1)))),
    ))
    css = (frames_css("ty", 2, .5) + frames_css("st", 3, 1.5) + frames_css("pl", 2, 2.4) + sky_css
           + ".blink{opacity:0;animation:blink 4.5s steps(1,end) infinite}"
             "@keyframes blink{0%{opacity:0}94%{opacity:1}97%{opacity:0}}"
           + ".cone{animation:glow 3.2s ease-in-out infinite alternate}@keyframes glow{from{opacity:.65}to{opacity:1}}"
           + ".up{opacity:0;animation:up 4.2s steps(6,end) infinite}.up1{animation-delay:1.4s}.up2{animation-delay:2.8s}"
             "@keyframes up{0%{opacity:0;transform:translateY(0)}20%{opacity:1}80%{opacity:1}"
             "100%{opacity:0;transform:translateY(-6px)}}")
    return svg(60, 36, body, css)


# ---------------------------------------------------------------- sleeping cat (empty states)

CAT = (
    ("..C...C.........", "..CC.CC.........", ".CCCCCCCCCCC....", ".CKCCCKCCCCCC...",
     ".CCCrCCCCCCCCC..", "..CCCCCCCCCCCCC.", "..CCCCCCCCCCCoCC", "...CCCCCCCCCCCC."),
    ("................", "..C...C.........", ".CCC.CCCCCCC....", ".CKCCCKCCCCCC...",
     ".CCCrCCCCCCCCC..", "..CCCCCCCCCCCCC.", "..CCCCCCCCCCCoCC", "...CCCCCCCCCCCC."),
)


def sleeping_cat() -> str:
    """A cat asleep in a loaf, breathing, with Zs drifting up. 24 x 14 pixels."""
    body = ("".join(sprite(f, 2, 5, f"br{i}") for i, f in enumerate(CAT))
            + sprite(("ZZZ", ".Z.", "ZZZ"), 15, 2, "z z0") + sprite(("ZZ", "ZZ"), 19, 0, "z z1"))
    css = (frames_css("br", 2, 2.6)
           + ".z{opacity:0;animation:z 3.6s steps(4,end) infinite}.z1{animation-delay:1.8s}"
             "@keyframes z{0%{opacity:0;transform:translate(0,2px)}25%{opacity:1}75%{opacity:1}"
             "100%{opacity:0;transform:translate(2px,-2px)}}")
    return svg(24, 14, body, css)


# ---------------------------------------------------------------- trophy (lesson complete)

TROPHY = (
    "..QQQQQQQQQQ..", "QQQwQQQQQQQQQQ", "Q.QwQQQQQQQQ.Q", "Q.QQQQQQQQQQ.Q", ".QQQQQQQQQQQQ.",
    "...QQQQQQQQ...", "....QQQQQQ....", ".....yQQy.....", "......QQ......", "......QQ......",
    ".....yQQy.....", "....dddddd....", "...dddddddd...",
)


def trophy() -> str:
    """A gold cup with sparkles that twinkle in turn. 22 x 17 pixels."""
    body = (sprite(TROPHY, 4, 3)
            + sprite(SPARK, 0, 1, "sp0") + sprite(SPARK, 19, 4, "sp1") + sprite(SPARK, 1, 11, "sp2")
            + sprite(("w",), 18, 13, "sp0") + sprite(("w",), 3, 7, "sp1"))
    return svg(22, 17, body, frames_css("sp", 3, 1.8))


# ---------------------------------------------------------------- robot builder (planned topics)

ROBOT = (
    "......R.......", "......l.......", "...LLLLLLL....", "..LLLLLLLLL...", "..LGGLLLGGL...",
    "..LLLLLLLLL...", "..LLlllllLL...", "...LLLLLLL....", "....lllll.....", "..TTTTTTTTT...",
    ".LTTTTTTTTTL..", ".LTTyTTyTTTL..", ".LTTTTTTTTTL..", "..TTTTTTTTT...", "..ll.....ll...",
    ".lll.....lll..",
)


def robot_builder() -> str:
    """A robot hammering a brick: work in progress. 22 x 18 pixels."""
    hammer_up = sprite(("ddd", "ddd", ".D.", ".D.", ".D."), 11, 7)
    hammer_down = sprite(("DDDdd", "...dd"), 12, 12)
    body = (sprite(ROBOT, 0, 2) + sprite(("OOOO", "OooO", "OOOO"), 16, 14)
            + f'<g class="hm0">{hammer_up}</g><g class="hm1">{hammer_down}{sprite((".Y.Y", "Y.Y."), 18, 11)}</g>'
            + sprite(("R",), 6, 2, "an"))
    css = frames_css("hm", 2, .9) + ".an{animation:an 1.8s steps(1,end) infinite}@keyframes an{50%{opacity:.2}}"
    return svg(22, 18, body, css)


# ---------------------------------------------------------------- backdrop (behind every page)

BACKDROP_PALETTE = {  # the track colours, drawn faint by the layer's opacity
    "1": "#f0f0f0", "2": "#ffb347", "3": "#ff7e6b", "4": "#3ddc97", "5": "#7aa2ff", "6": "#b48cff",  # stars
    "c": "#5a5a5a",  # cloud
    "V": "#b48cff", "R": "#ff7e6b", "w": "#f0f0f0", "d": "#4a4a4a",  # book
    "Y": "#ffd166", "y": "#ffb347", "L": "#b5b5b5", "l": "#7a7a7a",  # bulb
    "O": "#5ee0e6", "o": "#2aa7ad", "P": "#ff7e6b",  # planet and ring
    "H": "#ff7e6b",  # heart
    "S": "#f2c7a5", "A": "#ffb347", "k": "#3a3a3a",  # pencil
    "B": "#7aa2ff", "G": "#3ddc97", "F": "#ffb347",  # rocket body, window, flame
}
ROCKET = ("..w..", ".www.", ".wBw.", ".www.", "RwwwR", "R.F.R", "..F..")
BOOK2 = ("GGGGGGw", "GGGGGGw", "GwwwwGw", "GGGGGGw", "ddddddd")
CLOUD = ("...cccc.....", ".ccccccccc..", "cccccccccccc", ".cccccccccc.")
BOOK = ("VVVVVVw", "VVVVVVw", "VRRRRVw", "VVVVVVw", "ddddddd")
BULB = (".YYY.", "YYwYY", "YYYYY", ".YyY.", ".LLL.", "..l..")
PLANET = ("...OOOO...", "..OOOOoO..", "PPPPPPPPPP", "..OoOOOO..", "...OOOO...")
HEART = (".H.H.", "HHHHH", ".HHH.", "..H..")
PENCIL = ("SAAAAAAk", "SAAAAAAk")
STAR = (".x.", "xxx", ".x.")


def _paint(grid, x, y, palette):
    rects = []
    for r, row in enumerate(grid):
        c = 0
        while c < len(row):
            ch = row[c]
            run = 1
            while c + run < len(row) and row[c + run] == ch:
                run += 1
            if ch != ".":
                rects.append(f'<rect x="{x + c}" y="{y + r}" width="{run}" height="1" fill="{palette[ch]}"/>')
            c += run
    return "".join(rects)


def backdrop_tile() -> str:
    """One 260 x 180 tile of night-sky pixel art that repeats behind every page. Stars twinkle in turn,
    clouds sway and the small objects bob; the page moves the whole tiled layer slowly on top of that."""
    stars = ((14, 10, "1"), (60, 26, "2"), (104, 8, "3"), (150, 30, "5"), (212, 14, "4"), (244, 52, "6"),
             (30, 74, "3"), (88, 96, "1"), (176, 84, "5"), (226, 120, "1"), (12, 140, "4"), (128, 150, "6"),
             (196, 164, "1"), (70, 160, "2"), (100, 70, "4"), (238, 96, "3"))
    dots = ((40, 40), (120, 60), (170, 50), (240, 90), (20, 110), (100, 130), (160, 120), (210, 150), (54, 128),
            (140, 20), (80, 12), (250, 170))
    parts = []
    for i, (x, y, colour) in enumerate(stars):
        grid = tuple(row.replace("x", colour) for row in STAR)
        parts.append(f'<g class="tw tw{i % 4}">{_paint(grid, x, y, BACKDROP_PALETTE)}</g>')
    parts += [f'<rect x="{x}" y="{y}" width="1" height="1" fill="#e8e3d6" opacity=".7"/>' for x, y in dots]
    parts.append(f'<g class="sway">{_paint(CLOUD, 34, 44, BACKDROP_PALETTE)}</g>')
    parts.append(f'<g class="sway s2">{_paint(CLOUD, 186, 136, BACKDROP_PALETTE)}</g>')
    for i, (grid, x, y) in enumerate(((BOOK, 120, 34), (BULB, 200, 64), (PLANET, 60, 112), (HEART, 160, 100),
                                      (PENCIL, 230, 26), (BOOK2, 20, 160), (ROCKET, 84, 40), (ROCKET, 150, 150),
                                      (HEART, 40, 22), (BULB, 110, 104))):
        parts.append(f'<g class="bob b{i % 3}">{_paint(grid, x, y, BACKDROP_PALETTE)}</g>')
    css = ("".join(f".tw{i}{{animation:tw 3.2s steps(1,end) {i * .8:.1f}s infinite}}" for i in range(4))
           + "@keyframes tw{0%{opacity:1}70%{opacity:.25}85%{opacity:1}}"
           + ".sway{animation:sway 6s steps(1,end) infinite}.s2{animation-delay:3s}"
             "@keyframes sway{50%{transform:translateX(2px)}}"
           + ".bob{animation:bob 2.4s steps(1,end) infinite}.b1{animation-delay:.8s}.b2{animation-delay:1.6s}"
             "@keyframes bob{50%{transform:translateY(-1px)}}")
    return svg(260, 180, "".join(parts), css)


def data_uri(markup: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(markup.encode("utf-8")).decode("ascii")


# ---------------------------------------------------------------- track icons (14 x 14)

TRACK_PALETTE = {
    "#": "#111111", "w": "#f0f0f0", "e": "#1a1a1a", "y": "#fff3b0", "z": "rgba(255, 243, 176, .35)",
    "k": "#5a5a5a", "K": "#8a8a8a",
    "g": "#3ddc97", "G": "#22a06b", "b": "#7aa2ff", "B": "#4a6fd1", "a": "#ffb347", "A": "#c98420",
    "v": "#b48cff", "V": "#7d55d6", "c": "#5ee0e6", "C": "#2aa7ad", "r": "#ff7e6b", "R": "#d1503e",
}


def _icon(body, css):
    return svg(14, 14, body, css)


def _p(grid, x=0, y=0, cls=""):
    return sprite(grid, x, y, cls, TRACK_PALETTE)


def icon_core() -> str:
    """An open book whose right page turns."""
    book = ("wwwwwwGGwwwwww", "wwkkkwGGwkkkww", "wwwwwwGGwwwwww", "wwkkkwGGwkkkww", "wwwwwwGGwwwwww",
            "wwkkwwGGwwkkww", "gwwwwwGGwwwwwg", ".gggggggggggg.")
    flip = ("........wwww..", ".......wwkkw..", "......wwwww...")
    return _icon(_p(book, 0, 4) + _p(flip, 0, 1, "pg1"), frames_css("pg", 2, 1.6))


def icon_apis() -> str:
    """An antenna sending signal waves outward."""
    mast = _p(("..ww..", "..bb..", "...K..", "...k..", "...k..", "...k..", "...k..", "..k.k.", ".k...k", "kkkkkk"), 4, 3)
    inner = _p(("b......b", ".b....b.", "b......b"), 3, 2, "sg1")
    outer = (_p(("b......b", ".b....b.", "b......b"), 3, 2, "sg2")
             + _p(("b..........b", ".b........b.", ".b........b.", "b..........b"), 1, 1, "sg2"))
    return _icon(mast + inner + outer, frames_css("sg", 3, 1.8))


def icon_retrieval() -> str:
    """A magnifier over a page of lines, with a glint that moves."""
    page = _p(("wwwwwww", "wkkkkkw", "wwwwwww", "wkkkkww", "wwwwwww", "wkkkkkw", "wwwwwww", "wkkkwww", "wwwwwww"), 0, 2)
    lens = _p(("..aaa..", ".azzza.", "azzzzza", "azzzzza", "azzzzza", ".azzza.", "..aaa.."), 5, 3)
    handle = _p(("AA.", "AAA", ".AA"), 11, 10)
    return _icon(page + lens + handle + _p(("w",), 7, 5, "gl0") + _p(("w",), 9, 7, "gl1"), frames_css("gl", 2, 1.4))


def icon_models() -> str:
    """A chip whose core lights blink in turn."""
    pins = "".join(_p(("K", "K"), x, 0) + _p(("K", "K"), x, 12) for x in (3, 5, 8, 10)) + \
        "".join(_p(("KK",), 0, y) + _p(("KK",), 12, y) for y in (3, 5, 8, 10))
    body = _p(("VVVVVVVVVV",) + ("VvvvvvvvvV",) * 8 + ("VVVVVVVVVV",), 2, 2)
    core = _p(("VVVV",) * 4, 5, 5)
    lights = _p(("g..", "...", "..g"), 5, 5, "ch0") + _p(("..g", "...", "g.."), 6, 6, "ch1")
    return _icon(pins + body + core + lights, frames_css("ch", 2, 1.2))


def icon_agents() -> str:
    """A robot head that blinks, antenna light pulsing."""
    head = _p(("CCCCCCCCCC",) + ("CccccccccC",) * 6 + ("CCCCCCCCCC",), 2, 4)
    eyes = _p(("ee..ee",), 4, 6) + _p(("ee..ee",), 4, 7, "bl")
    mouth = _p(("CCCC",), 5, 9)
    ears = _p(("KK", "KK", "KK"), 0, 6) + _p(("KK", "KK", "KK"), 12, 6)
    antenna = _p(("k", "k"), 6, 2) + _p(("rr",), 6, 1, "an") + _p(("k",), 7, 2)
    css = (".bl{animation:bl 3s steps(1,end) infinite}@keyframes bl{0%{opacity:1}90%{opacity:0}96%{opacity:1}}"
           ".an{animation:an 1.6s steps(1,end) infinite}@keyframes an{50%{opacity:.25}}")
    return _icon(head + eyes + mouth + ears + antenna, css)


def icon_shipping() -> str:
    """A shield with a tick and a shine that sweeps across."""
    shield = _p((".rrrrrrrrrrrr.", "rrrrrrrrrrrrrr", "rrrrrrrrrrrwrr", "rrrrrrrrrrwwrr", "rrwrrrrrrwwrrr",
                 "rrwwrrrrwwrrrr", ".rrwwrrwwrrrr.", ".rrrwwwwrrrrr.", "..rrrwwrrrrr..", "...rrrrrrrr...",
                 "....rrrrrr....", ".....rrrr.....", "......rr......"), 0, 0)
    shine = "".join(_p(("y.", ".y"), 2 + i * 3, 1, f"sh{i}") for i in range(3))
    return _icon(shield + shine, frames_css("sh", 3, 2.1))


TRACK_ICONS = {"Core path": icon_core, "Working with model APIs": icon_apis, "Retrieval and knowledge": icon_retrieval,
               "Models and adaptation": icon_models, "Agents and systems": icon_agents,
               "Shipping responsibly": icon_shipping}


# ---------------------------------------------------------------- page header scenes (56 x 32)

SCENE_PALETTE = {
    **TRACK_PALETTE, "S": "#f2c7a5", "E": "#1a1a1a", "T": "#3ddc97", "d": "#6b4430", "D": "#9a6a48",
    "h": "#1f5a3a", "H": "#2f7d4f", "p": "#5fd38d", "P": "#2f9a5c", "n": "#f4efe2", "l": "#c9d6f5", "s": "#c9c1ad",
    "x": "#2a2a2a", "X": "#4a4a4a", "q": "#1c1c1c",
}


def _s(grid, x=0, y=0, cls=""):
    return sprite(grid, x, y, cls, SCENE_PALETTE)


def _rect(x, y, w, h, colour, cls=""):
    attr = f' class="{cls}"' if cls else ""
    return f'<rect{attr} x="{x}" y="{y}" width="{w}" height="{h}" fill="{SCENE_PALETTE.get(colour, colour)}"/>'


def _stars(points, cls="tw"):
    return "".join(_rect(x, y, 1, 1, "w", f"{cls}{i % 2}") for i, (x, y) in enumerate(points))


def explore_scene() -> str:
    """An explorer walking a dotted trail over the hills to a waving flag."""
    hills = ("".join(_rect(28 - i * 3, 22 + i, 6 + i * 6, 1, "h") for i in range(10))
             + "".join(_rect(42 - i * 2, 15 + i, 4 + i * 4, 1, "H") for i in range(17))
             + _rect(0, 29, 56, 3, "h"))
    tree = _s(("..p..", ".ppp.", "ppppp", ".ppp.", "ppppp", "..d.."), 49, 11)
    path = "".join(_rect(x, y, 1, 1, "a") for x, y in ((6, 30), (9, 29), (12, 28), (15, 28), (19, 27), (23, 26),
                                                       (27, 25), (31, 23), (34, 21), (37, 19), (40, 17)))
    pole = _rect(43, 6, 1, 10, "w")
    flag = (_s(("rrrrrr", "rrrrr.", "rrrrrr", "rrrr.."), 44, 6, "fl0")
            + _s(("rrrrr.", "rrrrrr", "rrrrr.", "rrrrrr"), 44, 6, "fl1"))
    walker = _s((".aaaa.", "aaaaaa", ".SSSS.", ".SESE.", ".SSSS.", "ATTTT.", "ATTTT.", ".TTTT."), 16, 18)
    legs = _s((".k..k.", "k....k"), 16, 26, "lg0") + _s(("..kk..", "..kk.."), 16, 26, "lg1")
    moon = _s(("aa.", "a..", "aa."), 50, 2)
    body = (_stars(((8, 3), (20, 6), (30, 2), (36, 9), (52, 12), (3, 10)))
            + moon + hills + tree + path + pole + flag + walker + legs)
    css = frames_css("fl", 2, .8) + frames_css("lg", 2, .6) + frames_css("tw", 2, 2.2)
    return svg(56, 32, body, css)


def library_scene() -> str:
    """A bookshelf in the track colours, a cat asleep on top, one book wiggling with a sparkle."""
    frame = _rect(6, 9, 44, 23, "d") + _rect(7, 10, 42, 21, "q")
    boards = _rect(6, 17, 44, 1, "D") + _rect(6, 25, 44, 1, "D") + _rect(6, 9, 44, 1, "D")
    colours, books, i = "gbavcr", "", 0
    for top, tall in ((10, 5), (18, 5), (26, 3)):
        x = 8
        while x < 47:
            w, h = 2 + (i % 2), tall + (i * 7 % 3) - (1 if top == 26 and i % 3 == 0 else 0)
            if not (top == 18 and 30 <= x <= 34):
                bottom = 31 if top == 26 else top + 7
                books += _rect(x, bottom - h, w, h, colours[i % 6]) + _rect(x, bottom - h + 1, w, 1, "w")
            x += w + (1 if i % 4 == 3 else 0)
            i += 1
    wiggle = f'<g class="wig">{_rect(31, 20, 3, 5, "a")}{_rect(31, 21, 3, 1, "w")}</g>'
    spark = _s((".y.", "yyy", ".y."), 35, 18, "sp0") + _s(("y",), 30, 19, "sp1")
    cat = "".join(sprite(f, 30, 1, f"br{j}") for j, f in enumerate(CAT))
    css = (frames_css("br", 2, 2.6) + frames_css("sp", 2, 1.2)
           + ".wig{animation:wig 1.6s steps(1,end) infinite}@keyframes wig{50%{transform:translateX(1px)}}")
    return svg(56, 32, frame + boards + books + wiggle + spark + cat, css)


def notebook_scene() -> str:
    """An open notebook; a pencil writes the right-hand page one line at a time."""
    cover = _rect(5, 5, 46, 24, "b") + _rect(6, 6, 44, 22, "n") + _rect(27, 6, 2, 22, "s")
    lines = "".join(_rect(8, y, 17, 1, "l") + _rect(31, y, 17, 1, "l") for y in (10, 13, 16, 19, 22, 25))
    written = "".join(_rect(8, y - 1, w, 1, "x") for y, w in ((10, 15), (13, 12), (16, 16), (19, 9)))
    right = [(31, 9, 14), (31, 12, 11), (31, 15, 15), (31, 18, 8)]
    frames = ""
    for f in range(5):
        strokes = "".join(_rect(x, y, w, 1, "x") for x, y, w in right[:f])
        px, py = (right[f - 1][0] + right[f - 1][2], right[f - 1][1] - 2) if f else (31, 7)
        pencil = _s((".wAAAAAr", "kwAAAAAr", ".wAAAAAr"), px, py)
        frames += f'<g class="wr{f}">{strokes}{pencil}</g>'
    return svg(56, 32, cover + lines + written + frames, frames_css("wr", 5, 4.0))


def queue_scene() -> str:
    """A clipboard whose tasks get ticked off one after another."""
    board = _rect(14, 3, 28, 29, "d") + _rect(17, 7, 22, 23, "w") + _rect(22, 1, 12, 4, "K") + _rect(24, 0, 8, 2, "k")
    rows = (10, 15, 20, 25)
    boxes = "".join(_rect(19, y, 4, 4, "k") + _rect(20, y + 1, 2, 2, "w") + _rect(25, y + 1, 11 - (i % 2) * 3, 2, "K")
                    for i, y in enumerate(rows))
    tick = ("....g", "...gg", "g.gg.", "ggg..")
    frames = "".join(f'<g class="tk{f}">{"".join(_s(tick, 19, y - 1) for y in rows[:f])}</g>' for f in range(5))
    return svg(56, 32, board + boxes + frames, frames_css("tk", 5, 4.5))


def search_scene() -> str:
    """A magnifier sweeping back and forth over a stack of documents."""
    docs = ""
    for i, (x, y) in enumerate(((10, 8), (14, 5), (18, 2))):
        docs += _rect(x, y, 22, 26, "K" if i < 2 else "w")
    docs += "".join(_rect(21, yy, w, 1, "k") for yy, w in ((7, 14), (10, 16), (16, 15), (19, 9), (22, 14), (25, 12)))
    docs += _rect(21, 13, 11, 1, "a")
    lens = _s(("..aaaaa..", ".azzzzza.", "azzzzzzza", "azzzwzzza", "azzzzzzza", "azzzzzzza", ".azzzzza.",
               "..aaaaa..", "......AAA", ".......AA"), 14, 9)
    css = ".sw{animation:sw 3.2s steps(4,end) infinite alternate}@keyframes sw{to{transform:translateX(20px)}}"
    return svg(56, 32, docs + f'<g class="sw">{lens}</g>', css)


def settings_scene() -> str:
    """A control panel: sliders that move, lights that blink, a gear that turns."""
    panel = _rect(3, 3, 50, 26, "X") + _rect(4, 4, 48, 24, "x")
    sliders = ""
    for i, (y, colour) in enumerate(((9, "g"), (15, "b"), (21, "a"))):
        sliders += _rect(8, y + 1, 24, 1, "K") + f'<g class="sl sl{i}">{_rect(8, y, 3, 3, colour)}</g>'
    leds = "".join(_rect(37 + i * 4, 8, 2, 2, c, f"ld{i}") for i, c in enumerate("gar"))
    gear_a = ("...KKK...", ".K.KKK.K.", "..KKKKK..", "KKKK.KKKK", "KKK...KKK", "KKKK.KKKK", "..KKKKK..",
              ".K.KKK.K.", "...KKK...")
    gear_b = (".KK...KK.", ".KKKKKKK.", "..KKKKK..", ".KKK.KKK.", ".KK...KK.", ".KKK.KKK.", "..KKKKK..",
              ".KKKKKKK.", ".KK...KK.")
    gear = _s(gear_a, 39, 15, "gr0") + _s(gear_b, 39, 15, "gr1")
    css = ("".join(f".sl{i}{{animation:sl {d}s steps(6,end) infinite alternate}}" for i, d in enumerate((2.4, 3.0, 2.0)))
           + "@keyframes sl{to{transform:translateX(20px)}}"
           + "".join(f".ld{i}{{animation:ld 1.8s steps(1,end) {i * .6:.1f}s infinite}}" for i in range(3))
           + "@keyframes ld{50%{opacity:.2}}" + frames_css("gr", 2, .8))
    return svg(56, 32, panel + sliders + leds + gear, css)
