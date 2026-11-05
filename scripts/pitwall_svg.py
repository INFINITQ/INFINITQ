"""Pit wall SVG kit for the INFINITQ profile README.

Theme, small SVG helpers and one renderer per card. Every renderer returns a
complete SVG document as a string.

GitHub serves README images from a sandbox, so each SVG carries everything
inline: no scripts, no web fonts, no external images. Animations use CSS
keyframes and SMIL, which both run in an SVG shown with <img>. Each element's
resting state is its final, visible state, so a card still reads correctly
wherever animations don't run.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from string import Template
from xml.sax.saxutils import escape

# ---------------------------------------------------------------- theme

LINE = "#2A2A2E"
ROW_LINE = "#1D1D21"
TILE = "#111114"
RED = "#E10600"
WHITE = "#F5F5F5"
GREY = "#A1A1AA"
DIM = "#6B6B76"
PURPLE = "#B25CFF"  # F1 timing colours: purple = fastest overall,
GREEN = "#2EDB6B"   # green = personal best,
YELLOW = "#FFD23F"  # yellow = no improvement
TIMING = {"purple": PURPLE, "green": GREEN, "yellow": YELLOW}
# Team-livery colours, used to tell standings rows apart.
LIVERY = ("#FF8000", "#27F4D2", "#3671C6", "#FF87BC", "#229971", "#64C4FF", "#B6BABD", "#F5D400")
LAMP_ON, LAMP_OFF = "#FF2A1A", "#2A0B09"
MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")

DISPLAY = "'Titillium Web','Arial Narrow','Roboto Condensed','Segoe UI',Arial,sans-serif"
SANS = "'Segoe UI','Helvetica Neue',Roboto,Arial,sans-serif"
MONO = "'JetBrains Mono','Cascadia Mono',Consolas,'SF Mono',Menlo,'DejaVu Sans Mono',monospace"
MONO_EM = 0.6  # width of one monospace glyph in em; textLength pins it exactly

# Team radio strip inside the header: where the typed messages sit.
RADIO_X, RADIO_RIGHT, RADIO_SIZE = 210, 906, 19
RADIO_MAX_CHARS = int((RADIO_RIGHT - RADIO_X) / (RADIO_SIZE * MONO_EM))

BASE_CSS = Template(
    ".d{font-family:$display;font-style:italic;font-weight:800}"
    ".s{font-family:$sans}"
    ".m{font-family:$mono}"
    ".rise{animation:rise .7s cubic-bezier(.2,.8,.2,1) both}"
    ".slide{animation:slide .7s cubic-bezier(.2,.8,.2,1) both}"
    ".fade{animation:fade .8s ease-out both}"
    ".gx{transform-box:fill-box;transform-origin:0 50%;animation:gx 1.1s cubic-bezier(.2,.8,.2,1) both}"
    ".gy{transform-box:fill-box;transform-origin:50% 100%;animation:gy .9s cubic-bezier(.2,.8,.2,1) both}"
    ".draw{animation:draw 2.4s cubic-bezier(.3,.7,.2,1) both}"
    ".pulse{animation:pulse 1.6s ease-in-out infinite}"
    "@keyframes rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}"
    "@keyframes slide{from{opacity:0;transform:translateX(-28px)}to{opacity:1;transform:none}}"
    "@keyframes fade{from{opacity:0}to{opacity:1}}"
    "@keyframes gx{from{transform:scaleX(0)}to{transform:scaleX(1)}}"
    "@keyframes gy{from{transform:scaleY(0)}to{transform:scaleY(1)}}"
    "@keyframes draw{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}"
    "@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}"
    "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
).substitute(display=DISPLAY, sans=SANS, mono=MONO)

COMMON_DEFS = (
    # carbon-fibre weave
    '<pattern id="cf" width="6" height="6" patternUnits="userSpaceOnUse">'
    '<rect width="6" height="6" fill="#0B0B0D"/>'
    '<rect width="3" height="3" fill="#111114"/><rect x="3" y="3" width="3" height="3" fill="#111114"/>'
    '<rect width="3" height="1" fill="#16161A"/><rect x="3" y="3" width="1" height="3" fill="#16161A"/>'
    "</pattern>"
    '<linearGradient id="sheen" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#FFFFFF" stop-opacity=".06"/>'
    '<stop offset=".45" stop-color="#FFFFFF" stop-opacity="0"/>'
    "</linearGradient>"
    '<filter id="glow" x="-50%" y="-50%" width="200%" height="200%">'
    '<feGaussianBlur stdDeviation="3" result="b"/>'
    '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>'
    "</filter>"
)

# Top view of a car pointing along +x, centred on the origin.
CAR = (
    '<g transform="scale(1.35)">'
    f'<ellipse rx="17" ry="8" fill="{RED}" opacity=".35" filter="url(#glow)"/>'
    f'<rect x="-13" y="-6.5" width="3" height="13" rx="1" fill="{WHITE}"/>'
    '<rect x="-11" y="-7.6" width="6" height="3.6" rx="1.2" fill="#0A0A0A" stroke="#666" stroke-width=".6"/>'
    '<rect x="-11" y="4" width="6" height="3.6" rx="1.2" fill="#0A0A0A" stroke="#666" stroke-width=".6"/>'
    '<rect x="5" y="-6.6" width="5" height="3" rx="1" fill="#0A0A0A" stroke="#666" stroke-width=".6"/>'
    '<rect x="5" y="3.6" width="5" height="3" rx="1" fill="#0A0A0A" stroke="#666" stroke-width=".6"/>'
    f'<path d="M-10,-3 L4,-2.6 L13,-1 L13,1 L4,2.6 L-10,3 Z" fill="{RED}"/>'
    f'<rect x="-5" y="-4.4" width="8" height="8.8" rx="2.5" fill="{RED}"/>'
    f'<rect x="12" y="-5.5" width="2.4" height="11" rx="1" fill="{WHITE}"/>'
    f'<rect x="-9" y="-.6" width="20" height="1.2" fill="{WHITE}" opacity=".9"/>'
    '<circle cx="-1" r="1.8" fill="#0A0A0A"/>'
    "</g>"
)


# ---------------------------------------------------------------- helpers

def esc(value) -> str:
    return escape(str(value), {'"': "&quot;"})


def num(x) -> str:
    """A number as an SVG attribute: 12, 12.5, 12.35."""
    if isinstance(x, int):
        return str(x)
    s = f"{x:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def fmt_num(n) -> str:
    return f"{n:,.0f}" if float(n).is_integer() else f"{n:,.1f}"


def readable(color: str | None) -> str:
    """`color`, lightened if it would vanish on the carbon background.

    Some GitHub language colours are near-black (PowerShell is #012456).
    """
    if not color or not color.startswith("#") or len(color) != 7:
        return GREY
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    if 0.2126 * r + 0.7152 * g + 0.0722 * b >= 70:
        return color
    mix = 0.5
    return "#{:02X}{:02X}{:02X}".format(*(round(c + (255 - c) * mix) for c in (r, g, b)))


_NARROW = frozenset("fijlrtI!|.,:;'`() ")
_WIDE = frozenset("mwMWQOGDC@%&")


def text_width(s: str, size: float, mono: bool = False, bold: bool = False) -> float:
    """Rough rendered width of `s`, erring wide so text keeps some slack."""
    if mono:
        return len(s) * size * MONO_EM
    em = 0.0
    for ch in s:
        if ch in _NARROW:
            em += 0.3
        elif ch in _WIDE:
            em += 0.88
        elif ch.isupper() or ch.isdigit():
            em += 0.68
        else:
            em += 0.56
    return em * size * (1.08 if bold else 1.0)


def fit(s: str, max_w: float, size: float, mono: bool = False, bold: bool = False) -> str:
    """Shorten `s` with an ellipsis until it fits in max_w."""
    if text_width(s, size, mono, bold) <= max_w:
        return s
    while s and text_width(s + "…", size, mono, bold) > max_w:
        s = s[:-1]
    return s.rstrip() + "…"


def fit_size(s: str, max_w: float, size: float, min_size: float, bold: bool = False) -> float:
    """Largest font size (down to min_size) at which `s` fits in max_w."""
    while size > min_size and text_width(s, size, bold=bold) > max_w:
        size -= 1
    return size


def text(x, y, s, size, cls="s", fill=WHITE, anchor="start", weight=None,
         spacing=None, length=None, opacity=None, attrs="") -> str:
    a = f'x="{num(x)}" y="{num(y)}" class="{cls}" font-size="{num(size)}" fill="{fill}"'
    if anchor != "start":
        a += f' text-anchor="{anchor}"'
    if weight:
        a += f' font-weight="{weight}"'
    if spacing:
        a += f' letter-spacing="{spacing}"'
    if length:
        a += f' textLength="{num(length)}" lengthAdjust="spacingAndGlyphs"'
    if opacity is not None:
        a += f' opacity="{opacity}"'
    if attrs:
        a += " " + attrs
    return f"<text {a}>{esc(s)}</text>"


def frame(w: int, h: int, r: int = 16) -> str:
    return (
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{r}" fill="url(#cf)"/>'
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{r}" fill="url(#sheen)" stroke="{LINE}"/>'
    )


def doc(w: int, h: int, body: str, *, title: str, desc: str = "", css: str = "", defs: str = "",
        r: int = 16) -> str:
    clip = f'<clipPath id="card"><rect width="{w}" height="{h}" rx="{r}"/></clipPath>'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-labelledby="title desc">'
        f'<title id="title">{esc(title)}</title><desc id="desc">{esc(desc)}</desc>'
        f"<style>{BASE_CSS}{css}</style><defs>{COMMON_DEFS}{clip}{defs}</defs>"
        f"{frame(w, h, r)}{body}</svg>\n"
    )


def tag(x, y, label, fill=RED, size=13, h=24, color=WHITE):
    """A slanted F1-graphics label. Returns (svg, width)."""
    spacing = 1.2
    w = text_width(label, size, bold=True) + spacing * len(label) + 28
    pts = f"{num(x + 7)},{y} {num(x + w)},{y} {num(x + w - 7)},{y + h} {num(x)},{y + h}"
    svg = f'<polygon points="{pts}" fill="{fill}"/>' + text(
        x + w / 2, y + h / 2 + size * 0.36, label, size, cls="d", fill=color, anchor="middle",
        spacing=spacing)
    return svg, w


def pill(x, y, label, size=11.5, h=22, pad=10, color=GREY):
    """A rounded chip. Returns (svg, width)."""
    w = text_width(label, size) + 2 * pad
    svg = (
        f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{h}" rx="{h / 2:g}" '
        f'fill="{TILE}" stroke="{LINE}"/>'
        + text(x + w / 2, y + h / 2 + size * 0.35, label, size, fill=color, anchor="middle")
    )
    return svg, w


def pills(x, y, labels, max_x, gap=6, **kw) -> str:
    out = []
    for label in labels:
        svg, w = pill(x, y, label, **kw)
        if x + w > max_x:
            break
        out.append(svg)
        x += w + gap
    return "".join(out)


def lem_point(cx, cy, a, t):
    """Point on a lemniscate of Bernoulli (the infinity sign)."""
    s, c = math.sin(t), math.cos(t)
    d = 1 + s * s
    return cx + a * c / d, cy + a * s * c / d


def lemniscate(cx, cy, a, n=96):
    return [lem_point(cx, cy, a, 2 * math.pi * i / n) for i in range(n)]


def closed_spline(pts) -> str:
    """Smooth closed path through pts (Catmull-Rom as cubic Béziers)."""
    n = len(pts)
    out = [f"M{pts[0][0]:.2f},{pts[0][1]:.2f}"]
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        out.append(f"C{c1[0]:.2f},{c1[1]:.2f} {c2[0]:.2f},{c2[1]:.2f} {p2[0]:.2f},{p2[1]:.2f}")
    return "".join(out) + "Z"


def polyline(pts) -> str:
    return "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in pts)


def monotone_path(pts) -> str:
    """Smooth path through pts (x ascending) that never overshoots them.

    Fritsch-Carlson monotone cubic interpolation, so a week with 0
    contributions never dips below the baseline.
    """
    n = len(pts)
    if n == 1:
        return f"M{pts[0][0]:.2f},{pts[0][1]:.2f}"
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    delta = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [delta[0]] + [
        0.0 if delta[i - 1] * delta[i] <= 0 else (delta[i - 1] + delta[i]) / 2 for i in range(1, n - 1)
    ] + [delta[-1]]
    for i in range(n - 1):
        if delta[i] == 0:
            m[i] = m[i + 1] = 0.0
            continue
        a, b = m[i] / delta[i], m[i + 1] / delta[i]
        s = a * a + b * b
        if s > 9:
            t = 3 / math.sqrt(s)
            m[i], m[i + 1] = t * a * delta[i], t * b * delta[i]
    out = [f"M{xs[0]:.2f},{ys[0]:.2f}"]
    for i in range(n - 1):
        out.append(
            f"C{xs[i] + h[i] / 3:.2f},{ys[i] + m[i] * h[i] / 3:.2f} "
            f"{xs[i + 1] - h[i] / 3:.2f},{ys[i + 1] - m[i + 1] * h[i] / 3:.2f} "
            f"{xs[i + 1]:.2f},{ys[i + 1]:.2f}"
        )
    return "".join(out)


def discrete(events, period):
    """keyTimes and values for a repeating calcMode="discrete" SMIL animation.

    `events` are (seconds, value) pairs. Times may fall outside [0, period) and
    wrap around; at t=0 the value set by the previous cycle's last event holds.
    """
    latest = {}
    for t, v in events:
        latest[round(t % period, 5) % period] = v
    times = sorted(latest)
    if times[0] > 0:
        latest[0.0] = latest[times[-1]]
        times.insert(0, 0.0)
    return (";".join(f"{t / period:.5f}" for t in times),
            ";".join(num(float(latest[t])) for t in times))


def nice_ceiling(v: float) -> float:
    if v <= 0:
        return 1
    mag = 10 ** math.floor(math.log10(v))
    for m in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if v <= m * mag:
            return m * mag
    return 10 * mag


def ago(when: date | None, today: date) -> str:
    if when is None:
        return "a while ago"
    days = (today - when).days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    for size, unit in ((365, "year"), (30, "month"), (7, "week")):
        if days >= size:
            n = days // size
            return f"{n} {unit}{'s' if n > 1 else ''} ago"
    return f"{days} days ago"


def flag_ind(x, y, w=27, h=18) -> str:
    s = h / 3
    return (
        f'<rect x="{num(x)}" y="{num(y)}" width="{w}" height="{num(s)}" fill="#FF9933"/>'
        f'<rect x="{num(x)}" y="{num(y + s)}" width="{w}" height="{num(s)}" fill="#FFFFFF"/>'
        f'<rect x="{num(x)}" y="{num(y + 2 * s)}" width="{w}" height="{num(s)}" fill="#138808"/>'
        f'<circle cx="{num(x + w / 2)}" cy="{num(y + h / 2)}" r="{num(s * .42)}" fill="none" '
        f'stroke="#000080" stroke-width=".9"/>'
    )


def kerb_band(y, w, h=12, period=24) -> str:
    """Red-and-white kerb stripes; pair with the .kerb animation."""
    stripes = "".join(
        f'<polygon points="{x},{y + h} {num(x + h / 2)},{y} {num(x + period / 2 + h / 2)},{y} '
        f'{num(x + period / 2)},{y + h}" fill="{RED}"/>'
        for x in range(-2 * period, w + 2 * period, period)
    )
    return f'<rect x="0" y="{y}" width="{w}" height="{h}" fill="#EDEDED"/><g class="kerb">{stripes}</g>'


KERB_CSS = ".kerb{animation:kerb .9s linear infinite}@keyframes kerb{to{transform:translateX(-24px)}}"


def waveform(x, cy, bars=7, h=26, color=WHITE) -> str:
    out = []
    for j in range(bars):
        dur = 0.7 + 0.11 * ((j * 3) % 5)
        out.append(
            f'<rect class="wv" style="animation-duration:{dur:.2f}s;animation-delay:{-0.13 * j:.2f}s" '
            f'x="{x + j * 6}" y="{num(cy - h / 2)}" width="3" height="{h}" rx="1.5" fill="{color}"/>'
        )
    return "".join(out)


WAVE_CSS = (
    ".wv{transform-box:fill-box;transform-origin:50% 50%;animation:wv 1s ease-in-out infinite}"
    "@keyframes wv{0%,100%{transform:scaleY(.25)}50%{transform:scaleY(1)}}"
)


def typed_messages(messages, x0, y, size, slot=5.2, type_time=1.4, hold=3.4,
                   color=WHITE, cursor=RED) -> str:
    """Messages that type out one after another, forever (SMIL, discrete steps).

    The cycle starts with the first message fully typed, so anything that
    shows only the first frame still shows a message.
    """
    period = slot * len(messages)
    cw = size * MONO_EM
    out = []
    for i, msg in enumerate(messages):
        chars = len(msg)
        start = i * slot - type_time
        steps = [(start + type_time * k / chars, k * cw + (2 if k else 0)) for k in range(chars + 1)]
        clear = i * slot + hold
        kt, widths = discrete(steps + [(clear, 0)], period)
        ckt, xs = discrete([(t, x0 + w + 1) for t, w in steps] + [(clear, x0)], period)
        okt, shown = discrete([(start, 1), (clear, 0)], period)
        cid = f"msg{i}"
        out.append(
            f'<clipPath id="{cid}"><rect x="{num(x0 - 1)}" y="{num(y - size)}" '
            f'height="{num(size * 1.45)}" width="{num(chars * cw + 2) if i == 0 else 0}">'
            f'<animate attributeName="width" dur="{period:g}s" repeatCount="indefinite" '
            f'calcMode="discrete" keyTimes="{kt}" values="{widths}"/></rect></clipPath>'
            + text(x0, y, msg, size, cls="m", fill=color, length=chars * cw,
                   attrs=f'clip-path="url(#{cid})"')
            + f'<g opacity="0"><animate attributeName="opacity" dur="{period:g}s" '
            f'repeatCount="indefinite" calcMode="discrete" keyTimes="{okt}" values="{shown}"/>'
            f'<rect x="{num(x0)}" y="{num(y - size * .82)}" width="{num(cw * .9)}" '
            f'height="{num(size * 1.05)}" fill="{cursor}">'
            f'<animate attributeName="x" dur="{period:g}s" repeatCount="indefinite" '
            f'calcMode="discrete" keyTimes="{ckt}" values="{xs}"/>'
            '<animate attributeName="opacity" values="1;0" dur="1s" repeatCount="indefinite" '
            'calcMode="discrete"/></rect></g>'
        )
    return "".join(out)


# ---------------------------------------------------------------- static art

def header(cfg) -> str:
    """Banner: start lights, a car lapping an infinity circuit, name, team radio."""
    W, H = 1000, 388
    d = cfg["driver"]

    # circuit
    cx, cy, a = 250, 150, 180
    track = closed_spline(lemniscate(cx, cy, a, 96))
    kerbs = " ".join(
        polyline([lem_point(cx, cy, a, t0 + k / 24) for k in range(25)]) for t0 in (-0.5, math.pi - 0.5)
    )
    t_sf = 0.62  # start/finish line
    (sx, sy), (tx, ty) = lem_point(cx, cy, a, t_sf), lem_point(cx, cy, a, t_sf + 1e-3)
    angle = math.degrees(math.atan2(ty - sy, tx - sx))
    chequer = "".join(
        f'<rect x="{-3 + 3 * c}" y="{num(-10.5 + 3.5 * r)}" width="3" height="3.5" '
        f'fill="{WHITE if (r + c) % 2 else "#0A0A0A"}"/>'
        for r in range(6) for c in range(2)
    )
    lap = 7
    circuit = (
        f'<path d="{kerbs}" fill="none" stroke="{WHITE}" stroke-width="30"/>'
        f'<path d="{kerbs}" fill="none" stroke="{RED}" stroke-width="30" stroke-dasharray="7 7"/>'
        f'<path d="{track}" fill="none" stroke="#D4D4D8" stroke-width="23" stroke-linejoin="round"/>'
        f'<path d="{track}" fill="none" stroke="#1E1E22" stroke-width="19" stroke-linejoin="round"/>'
        f'<path d="{track}" fill="none" stroke="{WHITE}" stroke-opacity=".22" stroke-width="1.2" '
        f'stroke-dasharray="6 9"/>'
        f'<g transform="translate({num(sx)} {num(sy)}) rotate({num(angle)})">{chequer}</g>'
        # light trail that stays glued to the car: same path, same lap time
        f'<path d="{track}" pathLength="1000" fill="none" stroke="{RED}" stroke-width="5" '
        f'stroke-linecap="round" stroke-dasharray="80 920" stroke-dashoffset="80" opacity=".8" '
        f'filter="url(#glow)"><animate attributeName="stroke-dashoffset" from="80" to="-920" '
        f'dur="{lap}s" repeatCount="indefinite"/></path>'
        f'<g opacity="0"><set attributeName="opacity" to="1"/>'
        f'<animateMotion dur="{lap}s" repeatCount="indefinite" rotate="auto" path="{track}"/>{CAR}</g>'
    )

    # start lights: on one by one, then out together
    period, lights_out = 10.0, 6.4
    gantry = []
    for i in range(5):
        px = 642 + i * 60
        kt = f"0;{(1.0 + 0.9 * i) / period:.4f};{lights_out / period:.4f}"
        gantry.append(f'<rect x="{px}" y="18" width="44" height="66" rx="9" fill="#050506" stroke="#26262B"/>')
        for ly in (37, 65):
            gantry.append(
                f'<circle cx="{px + 22}" cy="{ly}" r="14" fill="{LAMP_ON}" opacity="0" filter="url(#glow)">'
                f'<animate attributeName="opacity" dur="{period:g}s" repeatCount="indefinite" '
                f'calcMode="discrete" keyTimes="{kt}" values="0;.6;0"/></circle>'
                f'<circle cx="{px + 22}" cy="{ly}" r="10" fill="{LAMP_OFF}">'
                f'<animate attributeName="fill" dur="{period:g}s" repeatCount="indefinite" '
                f'calcMode="discrete" keyTimes="{kt}" values="{LAMP_OFF};{LAMP_ON};{LAMP_OFF}"/></circle>'
            )
    gantry.append(
        f'<g opacity="0"><animate attributeName="opacity" dur="{period:g}s" repeatCount="indefinite" '
        f'calcMode="discrete" keyTimes="0;{lights_out / period:.4f};{(lights_out + 2.8) / period:.4f}" '
        f'values="0;1;0"/>'
        + text(784, 106, "LIGHTS OUT AND AWAY WE GO", 13, cls="d", anchor="middle", spacing="3")
        + "</g>"
    )

    # The name never animates in: it must be there even in a first-frame snapshot.
    first, last = d["first_name"].upper(), d["last_name"].upper()
    name = (
        "<g>"
        f'<rect class="gy" style="animation-delay:.2s" x="562" y="124" width="6" height="124" fill="{RED}"/>'
        + text(584, 150, first, 24, cls="s", fill=GREY, weight="300", spacing="7")
        + text(580, 214, last, 70, cls="d", length=min(text_width(last, 70, bold=True), 330))
        + text(584, 240, d["tagline"].upper(), 15, cls="d", fill=RED, spacing="4")
        + text(584, 266, fit(d["header_line"], 396, 14.5), 14.5, fill=GREY)
        + "</g>"
    )
    live = (
        f'<circle class="pulse" cx="32" cy="32" r="4.5" fill="{RED}"/>'
        + text(44, 36.5, "LIVE · INFINITQ GRAND PRIX", 11.5, cls="m", fill=GREY, spacing="1")
    )

    # team radio strip
    ry = 302
    radio = (
        f'<g clip-path="url(#card)"><polygon points="0,{ry} 176,{ry} 158,{H} 0,{H}" fill="{RED}"/></g>'
        + text(22, ry + 34, "TEAM", 12, cls="d", spacing="5", opacity=".85")
        + text(20, ry + 66, "RADIO", 30, cls="d")
        + f'<circle class="pulse" cx="198" cy="{ry + 25}" r="4" fill="{RED}"/>'
        + text(RADIO_X, ry + 30, d["code"], 12.5, cls="d", fill=GREY, spacing="2.5")
        + typed_messages(cfg["radio"], RADIO_X, ry + 62, RADIO_SIZE)
        + waveform(928, ry + 43, color=GREY)
    )

    defs = (
        f'<radialGradient id="rg" cx="{cx}" cy="{cy}" r="270" gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="{RED}" stop-opacity=".2"/>'
        f'<stop offset="1" stop-color="{RED}" stop-opacity="0"/></radialGradient>'
    )
    body = (
        f'<rect width="{W}" height="290" fill="url(#rg)" clip-path="url(#card)"/>'
        + circuit + "".join(gantry) + name + live
        + kerb_band(290, W) + radio
    )
    return doc(
        W, H, body, css=KERB_CSS + WAVE_CSS, defs=defs,
        title=f"{d['first_name']} {d['last_name']}: {d['tagline']}",
        desc=(f"F1-style banner. Five start lights go out while a red car laps an infinity-shaped "
              f"circuit. {d['header_line']}. Team radio: " + " / ".join(cfg["radio"])),
    )


def finish(cfg) -> str:
    """Footer: a waving chequered flag."""
    W, H = 1000, 150
    sq, cols, rows = 14, 10, 6
    fx, fy = 62, 30
    css, flag = [], []
    for c in range(cols):
        amp = 0.6 + 0.55 * c
        css.append("@keyframes fl%d{0%%,100%%{transform:translateY(-%.2fpx)}50%%{transform:translateY(%.2fpx)}}"
                   % (c, amp, amp))
        squares = "".join(
            f'<rect x="{fx + c * sq}" y="{fy + r * sq}" width="{sq}" height="{sq}" '
            f'fill="{WHITE if (r + c) % 2 == 0 else "#0A0A0A"}"/>'
            for r in range(rows)
        )
        flag.append(f'<g style="animation:fl{c} 1.3s ease-in-out {-0.11 * c:.2f}s infinite">{squares}</g>')
    tg, _ = tag(240, 30, "CHEQUERED FLAG")
    line1 = "Thanks for stopping by the pit wall."
    body = (
        '<rect x="52" y="22" width="5" height="112" rx="2" fill="#C9C9CF"/>'
        '<circle cx="54.5" cy="21" r="4.5" fill="#E4E4E7"/>'
        + "".join(flag) + tg
        + text(240, 92, line1, 30, cls="d", length=min(text_width(line1, 30, bold=True), 720))
        + text(242, 120, "Cards refresh daily via GitHub Actions · see you at the next race", 14.5, fill=GREY)
    )
    return doc(W, H, body, css="".join(css), title="Chequered flag",
               desc="Thanks for stopping by the pit wall. Cards refresh daily via GitHub Actions.")


def ml_season(cfg) -> str:
    """Championship standings for the applied-ML challenge season."""
    s = cfg["ml_season"]
    rows = s["domains"]
    W = 1000
    y0, rh = 152, 34
    yb = y0 + rh * len(rows) + 18
    H = yb + 96
    title = "APPLIED-ML CHAMPIONSHIP"
    tg, _ = tag(24, 22, f"{s['season']} SEASON")
    head = (
        tg
        + text(24, 86, title, 34, cls="d", length=min(text_width(title, 34, bold=True), 560))
        + text(24, 114, f"{s['total']} challenges across {len(rows)} domains · {s['window']} · "
                        "cloud + local GPUs", 14.5, fill=GREY)
        + '<g filter="url(#glow)">' + text(976, 92, s["total"], 78, cls="d", fill=RED, anchor="end") + "</g>"
        + text(976, 116, "CHALLENGES", 13, cls="d", fill=GREY, anchor="end", spacing="3")
        + text(44, y0 - 10, "POS", 9.5, cls="m", fill=DIM, anchor="end", spacing="1")
        + text(72, y0 - 10, "DOMAIN", 9.5, cls="m", fill=DIM, spacing="1")
        + text(976, y0 - 10, "CHALLENGES", 9.5, cls="m", fill=DIM, anchor="end", spacing="1")
    )
    vmax = max(r["value"] for r in rows) or 1
    table = []
    for i, r in enumerate(rows):
        y = y0 + i * rh
        color = LIVERY[i % len(LIVERY)]
        table.append(
            f'<g class="slide" style="animation-delay:{0.1 + 0.06 * i:.2f}s">'
            + text(44, y + 22, str(i + 1), 16, cls="d", anchor="end")
            + f'<rect x="56" y="{y + 5}" width="4" height="24" rx="1" fill="{color}"/>'
            + text(72, y + 23, fit(r["name"], 250, 15), 15)
            + f'<rect x="336" y="{y + 10}" width="560" height="14" rx="7" fill="#18181B"/>'
            + f'<rect class="gx" style="animation-delay:{0.35 + 0.06 * i:.2f}s" x="336" y="{y + 10}" '
              f'width="{num(560 * r["value"] / vmax)}" height="14" rx="7" fill="{color}"/>'
            + text(976, y + 23, str(r["value"]), 17, cls="d", anchor="end")
            + f'<line x1="24" y1="{y + rh - 1}" x2="976" y2="{y + rh - 1}" stroke="{ROW_LINE}"/>'
            + "</g>"
        )
    bottom = (
        text(24, yb + 22, "GARAGES", 12, cls="d", fill=DIM, spacing="2")
        + pills(120, yb + 6, s["garages"], 976)
        + text(24, yb + 58, "PARTS", 12, cls="d", fill=DIM, spacing="2")
        + pills(120, yb + 42, s["parts"], 976)
        + text(976, H - 14, "≈ count by each challenge's main domain", 10, cls="m", fill=DIM, anchor="end")
    )
    return doc(
        W, H, head + "".join(table) + bottom,
        title=f"{s['season']} applied-ML season: {s['total']} challenges",
        desc="; ".join(f"{r['name']}: {r['value']}" for r in rows)
             + ". Compute: " + ", ".join(s["garages"]) + ". Tools: " + ", ".join(s["parts"]) + ".",
    )


# ---------------------------------------------------------------- live cards

def driver_card(cfg, st) -> str:
    """Driver profile: who I am plus live GitHub numbers."""
    W, H = 1000, 336
    d = cfg["driver"]
    cx, cy, a = 148, 122, 104
    loop = closed_spline(lemniscate(cx, cy, a, 80))
    left = (
        f'<path d="{loop}" fill="none" stroke="{LAMP_OFF}" stroke-width="20" stroke-linejoin="round"/>'
        f'<path d="{loop}" class="draw" pathLength="1" stroke-dasharray="1" fill="none" stroke="{RED}" '
        f'stroke-width="14" stroke-linecap="round" stroke-linejoin="round" filter="url(#glow)"/>'
        f'<g opacity="0"><set attributeName="opacity" to="1" begin="1.4s"/>'
        f'<animateMotion dur="3.4s" begin="1.4s" repeatCount="indefinite" path="{loop}"/>'
        f'<circle r="5.5" fill="{WHITE}" filter="url(#glow)"/></g>'
        + text(cx, 232, d["code"], 24, cls="d", anchor="middle", spacing="6")
        + (flag_ind(cx - 34, 250) if d.get("country") == "IND" else "")
        + text(cx + 2, 264, d.get("country", ""), 15, cls="d", fill=GREY)
        + text(cx, 306, f"UPDATED {st['updated'].strftime('%d')} {MONTHS[st['updated'].month - 1]} "
                        f"{st['updated'].year}", 10, cls="m", fill=DIM, anchor="middle", spacing="1")
        + f'<line x1="296" y1="24" x2="296" y2="{H - 24}" stroke="{LINE}"/>'
    )
    first, last = d["first_name"].upper(), d["last_name"].upper()
    name = (
        "<g>"
        + text(326, 58, first, 21, cls="s", fill=GREY, weight="300", spacing="6")
        + text(322, 114, last, 60, cls="d", length=min(text_width(last, 60, bold=True), 290))
        + text(326, 142, d["tagline"].upper(), 14, cls="d", fill=RED, spacing="4")
        + "</g>"
    )
    facts = list(d["facts"]) + [["SEASON", f"{st['seasons']} · on GitHub since {st['since']}"]]
    fact_rows = "".join(
        text(652, 50 + i * 28, label, 11, cls="d", fill=DIM, spacing="1.5")
        + text(730, 50 + i * 28, fit(value, 976 - 730, 14), 14)
        for i, (label, value) in enumerate(facts[:4])
    )
    tiles = [
        ("LAPS · LAST 12 MONTHS", st["contrib_12mo"], "contributions", RED),
        ("CAREER LAPS", st["contrib_all"], f"contributions since {st['since']}", RED),
        ("RACES ENTERED", st["repos"], "public repositories", RED),
        ("BEST STINT", st["longest"], "days in a row", GREEN),
        ("CURRENT STINT", st["current"], "days in a row", YELLOW),
        ("FASTEST LAP", st["best_day"], "contributions in one day", PURPLE),
    ]
    tw, th, gap, tx0, ty0 = 212, 74, 10, 324, 164
    tile_svg = []
    for i, (label, value, sub, accent) in enumerate(tiles):
        x, y = tx0 + (i % 3) * (tw + gap), ty0 + (i // 3) * (th + gap)
        tile_svg.append(
            f'<g class="rise" style="animation-delay:{0.25 + 0.08 * i:.2f}s">'
            f'<rect x="{x}" y="{y}" width="{tw}" height="{th}" rx="10" fill="{TILE}" stroke="{LINE}"/>'
            f'<rect x="{x}" y="{y + 14}" width="3" height="{th - 28}" rx="1.5" fill="{accent}"/>'
            + text(x + 16, y + 21, label, 11, cls="d", fill=GREY, spacing="1.2")
            + text(x + 16, y + 52, fmt_num(value), 30, cls="d")
            + text(x + 16, y + 66, fit(sub, tw - 28, 10.5, mono=True), 10.5, cls="m", fill=DIM)
            + "</g>"
        )
    body = left + name + f'<g class="fade" style="animation-delay:.3s">{fact_rows}</g>' + "".join(tile_svg)
    return doc(
        W, H, body,
        title=f"Driver profile: {d['first_name']} {d['last_name']} ({d['code']})",
        desc=(f"{d['tagline']}. " + ". ".join(f"{k.title()}: {v}" for k, v in d["facts"])
              + f". {st['contrib_12mo']} contributions in the last 12 months, {st['contrib_all']} since "
                f"{st['since']}, {st['repos']} public repos, longest streak {st['longest']} days, "
                f"current streak {st['current']} days, best day {st['best_day']} contributions."),
    )


def telemetry(st) -> str:
    """Weekly contributions over the last 52 weeks, drawn like a telemetry trace."""
    W, H = 1000, 300
    weeks = st["weeks"]
    vals = [v for _, v in weeks]
    n = len(vals)
    x0, x1, top, base = 58, 970, 96, 248
    ymax = nice_ceiling(max(vals) if vals else 1)
    step = (x1 - x0) / max(n - 1, 1)

    def X(i):
        return x0 + step * i

    def Y(v):
        return base - (base - top) * v / ymax

    pts = [(X(i), Y(v)) for i, v in enumerate(vals)]
    line = monotone_path(pts)
    area = f"{line}L{pts[-1][0]:.2f},{base}L{pts[0][0]:.2f},{base}Z"

    # three "sectors", coloured by which third of the year was busiest
    bounds = [0, n // 3, 2 * n // 3, n]
    totals = [sum(vals[bounds[k]:bounds[k + 1]]) for k in range(3)]
    order = sorted(range(3), key=lambda k: -totals[k])
    colors = {order[0]: PURPLE, order[1]: GREEN, order[2]: YELLOW}
    bands = []
    for k in range(3):
        bx0 = max(x0, X(bounds[k]) - step / 2)
        bx1 = min(x1, X(bounds[k + 1] - 1) + step / 2)
        if k % 2 == 0:
            bands.append(f'<rect x="{num(bx0)}" y="{top - 22}" width="{num(bx1 - bx0)}" '
                         f'height="{base - top + 22}" fill="{WHITE}" fill-opacity=".025"/>')
        bands.append(text(bx0 + 8, top - 8, f"S{k + 1} · {totals[k]}", 12, cls="d", fill=colors[k],
                          spacing="1"))

    grid = []
    for v in (0, ymax / 2, ymax):
        y = Y(v)
        dash = "" if v == 0 else ' stroke-dasharray="3 6"'
        grid.append(f'<line x1="{x0}" y1="{num(y)}" x2="{x1}" y2="{num(y)}" '
                    f'stroke="{LINE if v == 0 else ROW_LINE}"{dash}/>')
        grid.append(text(x0 - 10, y + 4, f"{v:g}", 10.5, cls="m", fill=DIM, anchor="end"))
    prev = None
    for i, (start, _) in enumerate(weeks):
        mid = start + timedelta(days=3)
        if prev is not None and mid.month != prev:
            grid.append(f'<line x1="{num(X(i))}" y1="{top - 22}" x2="{num(X(i))}" y2="{base}" '
                        f'stroke="{WHITE}" stroke-opacity=".035"/>')
            grid.append(text(X(i), base + 20, MONTHS[mid.month - 1], 10.5, cls="m", fill=DIM, anchor="middle"))
        prev = mid.month

    best = max(range(n), key=lambda i: vals[i]) if n else 0
    nx, ny = pts[-1]
    marks = []
    if n and best != n - 1:
        bx, by = pts[best]
        marks.append(
            f'<g class="fade" style="animation-delay:2.2s">'
            f'<circle cx="{num(bx)}" cy="{num(by)}" r="5.5" fill="{PURPLE}" stroke="#0A0A0A" stroke-width="2"/>'
            + text(min(max(bx, x0 + 60), x1 - 60), by - 14, f"BEST WEEK · {vals[best]}", 11, cls="m",
                   fill=PURPLE, anchor="middle")
            + "</g>"
        )
    now_label = f"NOW · {vals[-1]}" + (" · BEST WEEK" if n and best == n - 1 else "")
    now_color = PURPLE if n and best == n - 1 else RED
    marks.append(
        f'<g class="fade" style="animation-delay:2.2s">'
        f'<circle cx="{num(nx)}" cy="{num(ny)}" r="5" fill="none" stroke="{now_color}">'
        '<animate attributeName="r" values="5;16" dur="1.8s" repeatCount="indefinite"/>'
        '<animate attributeName="opacity" values=".9;0" dur="1.8s" repeatCount="indefinite"/></circle>'
        f'<circle cx="{num(nx)}" cy="{num(ny)}" r="5" fill="{now_color}" stroke="#0A0A0A" stroke-width="2"/>'
        + text(nx - 14, ny + 4, now_label, 11, cls="m", fill=now_color, anchor="end")
        + "</g>"
    )

    tg, tgw = tag(24, 22, "TELEMETRY")
    total = sum(vals)
    summary = (
        f'<text x="{x1}" y="39" class="m" font-size="12.5" text-anchor="end">'
        f'<tspan fill="{DIM}">TOTAL </tspan><tspan fill="{WHITE}">{fmt_num(total)}</tspan>'
        f'<tspan fill="{DIM}"> · ACTIVE DAYS </tspan><tspan fill="{WHITE}">{st["active_days"]}</tspan>'
        f'<tspan fill="{DIM}"> · AVG/WEEK </tspan><tspan fill="{WHITE}">{total / max(n, 1):.1f}</tspan>'
        "</text>"
    )
    defs = (
        '<linearGradient id="area" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{RED}" stop-opacity=".38"/>'
        f'<stop offset="1" stop-color="{RED}" stop-opacity="0"/></linearGradient>'
    )
    body = (
        tg + text(24 + tgw + 14, 39, "Contributions per week · last 52 weeks", 15, fill=GREY) + summary
        + "".join(bands) + "".join(grid)
        + f'<path d="{area}" fill="url(#area)" class="fade" style="animation-delay:1s"/>'
        + f'<path d="{line}" class="draw" pathLength="1" stroke-dasharray="1" fill="none" stroke="{RED}" '
          f'stroke-width="2.6" stroke-linejoin="round" stroke-linecap="round" filter="url(#glow)"/>'
        + "".join(marks)
    )
    return doc(
        W, H, body, defs=defs,
        title="Telemetry: contributions per week, last 52 weeks",
        desc=(f"{total} contributions in the last {n} weeks, {st['active_days']} active days. "
              f"Busiest week: {vals[best] if n else 0}. Latest week: {vals[-1] if n else 0}."),
    )


LANG_CODES = {
    "TypeScript": "TYP", "JavaScript": "JVS", "Python": "PYT", "Rust": "RUS", "C++": "CPP", "C": "CLG",
    "C#": "CSH", "Go": "GOL", "Java": "JAV", "HTML": "HTM", "CSS": "CSS", "SCSS": "SCS", "Shell": "SHL",
    "PowerShell": "PWS", "Dockerfile": "DKR", "Jupyter Notebook": "JUP", "Kotlin": "KOT", "Swift": "SWF",
    "Dart": "DRT", "Batchfile": "BAT", "NSIS": "NSI", "Vue": "VUE", "Svelte": "SVL", "Lua": "LUA",
    "Ruby": "RBY", "PHP": "PHP", "Makefile": "MAK", "CMake": "CMK",
}
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def lang_code(name: str) -> str:
    return LANG_CODES.get(name) or ("".join(ch for ch in name.upper() if ch.isalnum())[:3] or "???")


def pit_wall(st) -> str:
    """Languages as an F1 timing tower, next to contributions by weekday."""
    W, H = 1000, 412
    langs, weekdays = st["languages"], st["weekdays"]
    head = (
        f'<rect width="{W}" height="58" fill="#060607" clip-path="url(#card)"/>'
        f'<rect y="58" width="{W}" height="2" fill="{RED}"/>'
        + text(24, 38, "TIMING", 20, cls="d")
        + text(24 + text_width("TIMING", 20, bold=True) + 12, 38, "LANGUAGES", 13, cls="d", fill=GREY,
               spacing="2")
        + text(524, 38, "RACE DAYS", 20, cls="d")
        + text(524 + text_width("RACE DAYS", 20, bold=True) + 12, 38, "BY WEEKDAY", 13, cls="d", fill=GREY,
               spacing="2")
        + f'<line x1="500" y1="76" x2="500" y2="{H - 22}" stroke="{LINE}"/>'
    )

    # timing tower
    tower = [
        text(35, 84, "POS", 9.5, cls="m", fill=DIM, anchor="middle", spacing="1")
        + text(70, 84, "LANGUAGE", 9.5, cls="m", fill=DIM, spacing="1")
        + text(400, 84, "SHARE", 9.5, cls="m", fill=DIM, anchor="end", spacing="1")
        + text(476, 84, "GAP", 9.5, cls="m", fill=DIM, anchor="end", spacing="1")
    ]
    y0, rh = 94, 36
    leader = langs[0]["share"] if langs else 1
    for i, r in enumerate(langs[:8]):
        y = y0 + i * rh
        color = readable(r["color"])
        tower.append(
            f'<g class="slide" style="animation-delay:{0.1 + 0.07 * i:.2f}s">'
            f'<rect x="20" y="{y + 4}" width="30" height="26" rx="4" fill="{RED if i == 0 else "#1A1A1E"}"/>'
            + text(35, y + 22.5, str(i + 1), 15, cls="d", anchor="middle")
            + f'<rect x="58" y="{y + 4}" width="4" height="26" rx="1" fill="{color}"/>'
            + text(70, y + 23, lang_code(r["name"]), 18, cls="d")
            + text(124, y + 18, fit(r["name"], 165, 12), 12, fill=GREY)
            + f'<rect x="124" y="{y + 24}" width="170" height="3" rx="1.5" fill="#1E1E22"/>'
            + f'<rect class="gx" style="animation-delay:{0.4 + 0.07 * i:.2f}s" x="124" y="{y + 24}" '
              f'width="{num(max(2.0, 170 * r["share"] / leader))}" height="3" rx="1.5" fill="{color}"/>'
            + text(400, y + 23, f"{r['share']:.1f}%", 14, cls="m", anchor="end")
            + text(476, y + 23, "LEADER" if i == 0 else f"+{leader - r['share']:.1f}", 11.5, cls="m",
                   fill=GREEN if i == 0 else GREY, anchor="end")
            + f'<line x1="20" y1="{y + 34}" x2="476" y2="{y + 34}" stroke="{ROW_LINE}"/>'
            + "</g>"
        )
    tower.append(text(24, H - 16, fit(f"share = code size × repo count · {st['language_count']} languages "
                                      "· public repos", 456, 10, mono=True), 10, cls="m", fill=DIM))

    # race days
    names = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")
    base, top, left, right = 350, 126, 532, 968
    slot, bw = (right - left) / 7, 34
    vmax = max(weekdays) or 1
    hi, lo = weekdays.index(max(weekdays)), weekdays.index(min(weekdays))
    days = [text(524, 86, "contributions by weekday · last 12 months", 10.5, cls="m", fill=DIM),
            f'<line x1="{left}" y1="{base}" x2="{right}" y2="{base}" stroke="{LINE}"/>']
    for i, v in enumerate(weekdays):
        h = max(2.0, (base - top) * v / vmax)
        x = left + i * slot + (slot - bw) / 2
        color = PURPLE if i == hi else (YELLOW if i == lo else RED)
        days.append(
            f'<rect class="gy" style="animation-delay:{0.2 + 0.06 * i:.2f}s" x="{num(x)}" y="{num(base - h)}" '
            f'width="{bw}" height="{num(h)}" rx="4" fill="{color}"/>'
            + f'<g class="fade" style="animation-delay:{0.9 + 0.06 * i:.2f}s">'
            + text(x + bw / 2, base - h - 8, str(v), 13, cls="m", anchor="middle") + "</g>"
            + text(x + bw / 2, base + 22, names[i], 12.5, cls="d", fill=GREY, anchor="middle", spacing="1")
        )
    days.append(text(524, H - 16, fit(f"busiest: {WEEKDAYS[hi]} ({weekdays[hi]}) · quietest: "
                                      f"{WEEKDAYS[lo]} ({weekdays[lo]})", 452, 10, mono=True),
                     10, cls="m", fill=DIM))
    return doc(
        W, H, head + "".join(tower) + "".join(days),
        title="Timing tower: languages, and contributions by weekday",
        desc=("Languages: " + ", ".join(f"{r['name']} {r['share']:.1f}%" for r in langs[:8])
              + ". Contributions by weekday, Monday first: " + ", ".join(map(str, weekdays)) + "."),
    )


def project_card(p, repo, today: date, owner: str) -> str:
    """One featured project: summary, stack, three 'sector times' and live repo facts."""
    W, H = 480, 276
    accent = p.get("accent", RED)
    title = p["name"].upper()
    body = [f'<rect width="7" height="{H}" fill="{accent}" clip-path="url(#card)"/>',
            text(28, 50, title, fit_size(title, 290, 30, 18, bold=True), cls="d")]
    if repo and repo.get("language"):
        lang = repo["language"]
        body.append(f'<circle cx="{num(W - 24 - text_width(lang, 12) - 10)}" cy="40" r="5" '
                    f'fill="{readable(repo.get("language_color"))}"/>'
                    + text(W - 24, 44, lang, 12, fill=GREY, anchor="end"))
    body.append(text(28, 76, fit(p["summary"], W - 56, 14), 14, fill=GREY))
    body.append(pills(28, 90, p["stack"], W - 24, size=11))

    sw, sy, sh = (W - 56 - 16) / 3, 128, 98
    for k, sec in enumerate(p["sectors"][:3]):
        sx = 28 + k * (sw + 8)
        col = TIMING.get(sec.get("timing"), GREEN)
        body.append(
            f'<g class="fade" style="animation-delay:{0.25 + 0.3 * k:.2f}s">'
            f'<rect x="{num(sx)}" y="{sy}" width="{num(sw)}" height="{sh}" rx="9" fill="{col}" '
            f'fill-opacity=".08" stroke="{col}" stroke-opacity=".35"/>'
            f'<rect x="{num(sx + 10)}" y="{sy}" width="{num(sw - 20)}" height="3" rx="1.5" fill="{col}"/>'
            + text(sx + 12, sy + 22, f"S{k + 1}", 12, cls="d", fill=GREY, spacing="1")
            + text(sx + 12, sy + 53, sec["value"], fit_size(sec["value"], sw - 24, 24, 14, bold=True),
                   cls="d", fill=col)
            + text(sx + 12, sy + 72, fit(sec["label"], sw - 22, 11), 11, opacity=".85")
            + (text(sx + 12, sy + 88, fit(sec["was"], sw - 22, 10, mono=True), 10, cls="m", fill=DIM)
               if sec.get("was") else "")
            + "</g>"
        )

    bits = []
    if repo:
        if repo.get("release"):
            bits.append(repo["release"])
        if repo.get("commits_30d"):
            c = repo["commits_30d"]
            bits.append(f"{c} commit{'' if c == 1 else 's'} in 30 days")
        bits.append(f"pushed {ago(repo.get('pushed'), today)}")
        if repo.get("stars", 0) >= 5:
            bits.append(f"★ {repo['stars']}")
    else:
        bits.append(f"github.com/{owner}/{p['repo']}")
    body.append(text(28, H - 22, fit(" · ".join(bits), W - 56, 11, mono=True), 11, cls="m", fill=DIM))
    return doc(
        W, H, "".join(body),
        title=f"{p['name']}: {p['summary']}",
        desc=("Built with " + ", ".join(p["stack"]) + ". "
              + "; ".join(f"{s['value']} {s['label']}" + (f" ({s['was']})" if s.get("was") else "")
                          for s in p["sectors"]) + "."),
    )
