"""
Builds the animated profile images from the same geometry as the website
(loukas-vetoulis.github.io, js/stillness.js).

  assets/stillness.svg      the header: name, the form's journey, the quote
  assets/link-*.svg         the three links

Text is converted to outlines (Jost), because an SVG shown as an image on
GitHub cannot load web fonts. Run:  python3 tools/build.py path/to/Jost-Light.ttf path/to/Jost-Regular.ttf
"""
import math, sys, pathlib
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

OUT = pathlib.Path(__file__).resolve().parent.parent / "assets"
OUT.mkdir(exist_ok=True)
LIGHT, REGULAR = (TTFont(p) for p in sys.argv[1:3])

BG, INK, MUTED = "#0a0a0a", "#ece8df", "#8a867e"

# ---------------------------------------------------------------- text → paths
def text_path(font, s, size, x, y, tracking=0.0, anchor="middle"):
    gs, cmap, hmtx = font.getGlyphSet(), font.getBestCmap(), font["hmtx"]
    scale = size / font["head"].unitsPerEm
    track = tracking * size
    names = [cmap[ord(c)] for c in s]
    widths = [hmtx[n][0] * scale for n in names]
    total = sum(widths) + track * (len(s) - 1)
    cx = {"middle": x - total / 2, "start": x, "end": x - total}[anchor]
    pen = SVGPathPen(gs)
    for n, w in zip(names, widths):
        gs[n].draw(TransformPen(pen, (scale, 0, 0, -scale, cx, y)))
        cx += w + track
    return pen.getCommands(), total

# ---------------------------------------------------------------- the shapes
N = 900
TAU = math.tau
golden = math.pi * (3 - math.sqrt(5))

def fill(gen):
    pts = []
    for i in range(N):
        side = -1 if i % 2 else 1
        u = (i // 2) / (N / 2 - 1)
        pts.append(gen(i, u, side))
    return pts

def sphere_at(i, u):
    y = -1 + 2 * u
    r = math.sqrt(max(0, 1 - y * y))
    a = golden * i
    return (math.cos(a) * r, y, math.sin(a) * r)

def globe_at(i, u, side=1):
    x, y, z = sphere_at(i, u)
    if i % 2 == 0:
        step = math.pi / 6
        a = round(math.atan2(z, x) / step) * step
        r = math.hypot(x, z)
        return (math.cos(a) * r, y, math.sin(a) * r)
    step = math.pi / 12
    lat = max(-5, min(5, round(math.asin(max(-1, min(1, y))) / step))) * step
    a = math.atan2(z, x)
    return (math.cos(a) * math.cos(lat), math.sin(lat), math.sin(a) * math.cos(lat))

def point_at(r):
    return fill(lambda i, u, s: tuple(c * r for c in sphere_at(i, u)))

shapes = {
    "point":   point_at(0.018),
    "inhale":  point_at(0.030),
    "line":    fill(lambda i, u, s: (0, -1 + 2 * u, 0)),
    "circle":  fill(lambda i, u, s: (s * math.cos(-math.pi / 2 + math.pi * u), math.sin(-math.pi / 2 + math.pi * u), 0)),
    "sphere":  fill(lambda i, u, s: sphere_at(i, u)),
    "globe":   fill(globe_at),
}

# Athens: the globe point nearest 37.98° N, 23.72° E becomes Athens
LAT, LON = math.radians(37.98), math.radians(23.72)
home = (math.cos(LAT) * math.cos(LON), -math.sin(LAT), math.cos(LAT) * math.sin(LON))
HOME = min(range(N), key=lambda i: sum((a - b) ** 2 for a, b in zip(shapes["globe"][i], home)))
shapes["globe"][HOME] = home

# ---------------------------------------------------------------- the journey
W, H = 800, 600
CX, CY, R = W / 2, 292, 150
T = 26  # seconds per loop

# (time, shape, rotY, tiltX)
FACE = LON + math.pi / 2
KEYS = [
    (0.0,  "point",  0.0,  0.35),
    (1.6,  "inhale", 0.0,  0.35),
    (3.2,  "point",  0.0,  0.35),
    (5.2,  "line",   0.0,  0.35),
    (6.6,  "line",   0.0,  0.35),
    (8.6,  "circle", 0.0,  0.0),
    (10.0, "circle", 0.0,  0.0),
    (12.2, "sphere", 0.5,  0.35),
    (13.4, "sphere", 0.8,  0.35),
    (15.6, "globe",  FACE - 0.6, 0.35),
    (18.0, "globe",  FACE - 0.15, LAT * 0.8),
    (20.6, "globe",  FACE,  LAT),
    (24.0, "point",  FACE,  0.35),
    (24.8, "inhale", FACE,  0.35),
    (26.0, "point",  FACE,  0.35),
]

def project(p, rotY, tiltX):
    x0, y0, z0 = p
    c, s = math.cos(rotY), math.sin(rotY)
    x1 = x0 * c + z0 * s
    z1 = -x0 * s + z0 * c
    cx, sx = math.cos(tiltX), math.sin(tiltX)
    y2 = y0 * cx - z1 * sx
    z2 = y0 * sx + z1 * cx
    persp = 3.2 / (3.2 + z2)
    depth = (1 - z2) / 2
    return x1 * R * persp, y2 * R * persp, 0.14 + 0.82 * depth * depth, (0.55 + depth * 0.7) * persp

css, dots = [], []
for i in range(N):
    frames = []
    for t, shape, ry, tx in KEYS:
        x, y, a, s = project(shapes[shape][i], ry, tx)
        if i == HOME and shape == "globe":
            a, s = 1.0, 2.4
        frames.append(f"{t / T * 100:.1f}%{{translate:{x:.1f}px {y:.1f}px;scale:{s:.1f};opacity:{a:.1f}}}")
    css.append(f"@keyframes k{i}{{{''.join(frames)}}}.d{i}{{animation:k{i} {T}s ease-in-out infinite}}")
    dots.append(f'<circle class="d{i}" r="1.1"/>')

# ---------------------------------------------------------------- the words
name, _ = text_path(LIGHT, "LOUKAS-NIKOLAOS VETOULIS", 13, CX, 64, tracking=0.42)
title, _ = text_path(LIGHT, "SOFTWARE ENGINEER", 10.5, CX, 92, tracking=0.38)
quote, _ = text_path(LIGHT, "The world is yours.", 34, CX, 540, tracking=0.01)

def window(t0, t1, t2, t3):  # fade in t0→t1, hold, fade out t2→t3 (seconds)
    p = lambda t: f"{t / T * 100:.2f}%"
    return f"0%,{p(t0)}{{opacity:0}}{p(t1)},{p(t2)}{{opacity:1}}{p(t3)},100%{{opacity:0}}"

header = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Loukas-Nikolaos Vetoulis. Software engineer. A still point becomes a line, a circle, a sphere and the world. The world is yours.">
<defs>
  <radialGradient id="v" cx="50%" cy="48%" r="70%"><stop offset="55%" stop-color="#000" stop-opacity="0"/><stop offset="100%" stop-color="#000" stop-opacity=".6"/></radialGradient>
  <linearGradient id="ax" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{INK}" stop-opacity="0"/><stop offset=".14" stop-color="{INK}" stop-opacity=".16"/>
    <stop offset=".3" stop-color="{INK}" stop-opacity="0"/><stop offset=".72" stop-color="{INK}" stop-opacity="0"/>
    <stop offset=".88" stop-color="{INK}" stop-opacity=".16"/><stop offset="1" stop-color="{INK}" stop-opacity="0"/>
  </linearGradient>
  <filter id="g"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" stitchTiles="stitch"/><feColorMatrix type="saturate" values="0"/></filter>
</defs>
<style>
  circle{{fill:{INK}}}
  .q{{animation:q {T}s ease-in-out infinite}}
  @keyframes q{{{window(15.8, 17.8, 21.6, 23.2)}}}
  .cue{{animation:c 3.2s ease-in-out infinite;transform-origin:{CX}px {H - 64}px}}
  @keyframes c{{0%{{opacity:0;transform:scaleY(0)}}30%,70%{{opacity:.7;transform:scaleY(1)}}100%{{opacity:0;transform:translateY(14px)}}}}
  {"".join(css)}
  @media (prefers-reduced-motion: reduce){{*{{animation:none!important}}}}
</style>
<rect width="{W}" height="{H}" rx="20" fill="{BG}"/>
<rect x="{CX - 0.5}" y="0" width="1" height="{H}" fill="url(#ax)"/>
<path d="{name}" fill="{MUTED}"/>
<path d="{title}" fill="{MUTED}" opacity=".7"/>
<g transform="translate({CX} {CY})">{"".join(dots)}</g>
<path class="q" d="{quote}" fill="{INK}"/>
<rect width="{W}" height="{H}" rx="20" fill="url(#v)"/>
<rect width="{W}" height="{H}" rx="20" filter="url(#g)" opacity=".05"/>
</svg>'''
(OUT / "stillness.svg").write_text(header)

# ---------------------------------------------------------------- the links
def link(label, fname, delay):
    w, h = 200, 56
    d, tw = text_path(LIGHT, label, 11, 0, 0, tracking=0.34)
    dot_gap = 16
    start = (w - (tw + dot_gap)) / 2
    d, _ = text_path(LIGHT, label, 11, start + dot_gap, h / 2 + 4, tracking=0.34, anchor="start")
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{label.title()}">
<style>
  .p{{animation:b 10s ease-in-out {delay}s infinite;transform-origin:{start + 2.5:.1f}px {h / 2:.1f}px}}
  @keyframes b{{0%,100%{{transform:scale(.6);opacity:.45}}50%{{transform:scale(1.15);opacity:1}}}}
  @media (prefers-reduced-motion: reduce){{.p{{animation:none}}}}
</style>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{(h - 1) / 2}" fill="{BG}" stroke="{INK}" stroke-opacity=".16"/>
<circle class="p" cx="{start + 2.5:.1f}" cy="{h / 2:.1f}" r="2.5" fill="{INK}"/>
<path d="{d}" fill="{INK}" opacity=".82"/>
</svg>'''
    (OUT / fname).write_text(svg)

link("SITE", "link-site.svg", 0)
link("LINKEDIN", "link-linkedin.svg", 0.6)
link("EMAIL", "link-email.svg", 1.2)

for f in sorted(OUT.glob("*.svg")):
    print(f.name, f"{f.stat().st_size / 1024:.0f} KB")
