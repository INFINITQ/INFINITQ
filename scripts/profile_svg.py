"""Minimal, F1-inspired SVG cards for the INFINITQ profile README.

The look: GitHub's own upright fonts, monochrome ink, plenty of space and one
red accent. The F1 touches stay small: a dot lapping a figure-eight circuit,
S1-S3 sector labels and timing-screen numbers.

Every card is drawn twice, for GitHub's light and dark themes, on a
transparent background; README.md shows the matching one with <picture>.
GitHub serves README images from a sandbox, so each SVG carries everything
inline: no scripts, no web fonts, no external images. Motion (CSS keyframes
and SMIL) is quiet, and every element rests in its final, visible state, so a
card still reads correctly wherever animations don't run.
"""

from __future__ import annotations

import bisect
import math
from dataclasses import dataclass
from datetime import date, timedelta
from xml.sax.saxutils import escape

# ---------------------------------------------------------------- theme


@dataclass(frozen=True)
class Theme:
    name: str
    ink: str     # names, values, the lines that carry data
    muted: str   # body text
    faint: str   # labels, axes, footnotes
    line: str    # hairlines, borders, the circuit
    track: str   # the empty part of a bar
    bg: str      # GitHub's page colour, for small knock-outs
    accent: str  # the one red


LIGHT = Theme("light", ink="#1F2328", muted="#59636E", faint="#818B98", line="#D1D9E0",
              track="#EAEEF2", bg="#FFFFFF", accent="#E10600")
DARK = Theme("dark", ink="#F0F6FC", muted="#9198A1", faint="#6E7681", line="#3D444D",
             track="#21262D", bg="#0D1117", accent="#FF2A1A")
THEMES = (LIGHT, DARK)
GREY = "#8B949E"  # for languages GitHub gives no colour

# GitHub's own font stacks, so the cards read as part of the page.
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"
MONO_EM = 0.6  # width of one monospace glyph in em (SF Mono 0.6, Consolas 0.55)

LABEL_SIZE, LABEL_SPACING = 10.5, 1.4
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

CSS = (
    f".s{{font-family:{SANS}}}.m{{font-family:{MONO}}}.n{{font-variant-numeric:tabular-nums}}"
    ".grow{transform-box:fill-box;transform-origin:0 50%;animation:grow 1.2s cubic-bezier(.2,.8,.2,1) both}"
    ".rise{transform-box:fill-box;transform-origin:50% 100%;animation:rise 1s cubic-bezier(.2,.8,.2,1) both}"
    ".draw{animation:draw 2.6s cubic-bezier(.3,.7,.2,1) both}"
    ".fade{animation:fade 1s ease-out both}"
    ".blink{animation:blink 2.4s ease-in-out infinite}"
    ".still{display:none}"
    "@keyframes grow{from{transform:scaleX(0)}}"
    "@keyframes rise{from{transform:scaleY(0)}}"
    "@keyframes draw{from{stroke-dashoffset:1}}"
    "@keyframes fade{from{opacity:0}}"
    "@keyframes blink{50%{opacity:.2}}"
    # SMIL motion ignores CSS, so reduced motion swaps the moving parts for still ones
    "@media (prefers-reduced-motion:reduce){*{animation:none!important}.moving{display:none}"
    ".still{display:inline}}"
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


_NARROW = frozenset("fijlrtI!|.,:;'`() ")
_WIDE = frozenset("mwMWQOGDC@%&")


def text_width(s: str, size: float, mono: bool = False, bold: bool = False, spacing: float = 0.0) -> float:
    """Rough rendered width of `s`, erring wide so text keeps some slack."""
    if mono:
        return len(s) * (size * MONO_EM + spacing)
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
    return em * size * (1.08 if bold else 1.0) + spacing * len(s)


def fit(s: str, max_w: float, size: float, mono: bool = False, bold: bool = False) -> str:
    """Shorten `s` with an ellipsis until it fits in max_w."""
    if text_width(s, size, mono, bold) <= max_w:
        return s
    while s and text_width(s + "…", size, mono, bold) > max_w:
        s = s[:-1]
    return s.rstrip() + "…"


def text(x, y, s, size, fill, *, cls="s", anchor="start", weight=None, spacing=None, attrs="") -> str:
    a = f'x="{num(x)}" y="{num(y)}" class="{cls}" font-size="{num(size)}" fill="{fill}"'
    if anchor != "start":
        a += f' text-anchor="{anchor}"'
    if weight:
        a += f' font-weight="{weight}"'
    if spacing is not None:
        a += f' letter-spacing="{num(spacing)}"'
    if attrs:
        a += " " + attrs
    return f"<text {a}>{esc(s)}</text>"


def label(x, y, s, fill, *, anchor="start", size=LABEL_SIZE) -> str:
    """Small monospace capitals: the timing-screen voice of every card."""
    return text(x, y, s.upper(), size, fill, cls="m", anchor=anchor, spacing=LABEL_SPACING)


def label_width(s: str, size: float = LABEL_SIZE) -> float:
    return text_width(s, size, mono=True, spacing=LABEL_SPACING)


def eyebrow(x, y, s, t: Theme) -> str:
    """A card's heading: a short red rule, then a label."""
    return (f'<rect x="{num(x)}" y="{num(y - 5)}" width="14" height="2" fill="{t.accent}"/>'
            + label(x + 22, y, s, t.muted))


def hline(x0, x1, y, color) -> str:
    return f'<line x1="{num(x0)}" y1="{num(y)}" x2="{num(x1)}" y2="{num(y)}" stroke="{color}"/>'


def lang_color(color: str | None, t: Theme) -> str:
    """A GitHub language colour, nudged so it still shows on the theme's page.

    A few are near-black (PowerShell is #012456) or near-white.
    """
    if not color or not color.startswith("#") or len(color) != 7:
        return GREY
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    if t.name == "dark" and lum < 70:
        target, mix = 255, 0.5
    elif t.name == "light" and lum > 215:
        target, mix = 0, 0.3
    else:
        return color
    return "#{:02X}{:02X}{:02X}".format(*(round(c + (target - c) * mix) for c in (r, g, b)))


def doc(w: int, h: int, body: str, *, title: str, desc: str, defs: str = "") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-labelledby="title desc">'
        f'<title id="title">{esc(title)}</title><desc id="desc">{esc(desc)}</desc>'
        f"<style>{CSS}</style>"
        + (f"<defs>{defs}</defs>" if defs else "")
        + body + "</svg>\n"
    )


def lem_point(cx, cy, a, t):
    """Point on a lemniscate of Bernoulli (the infinity sign)."""
    s, c = math.sin(t), math.cos(t)
    d = 1 + s * s
    return cx + a * c / d, cy + a * s * c / d


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


def stamp(day: date) -> str:
    return f"{day.day:02d} {MONTHS[day.month - 1]} {day.year}"


# ---------------------------------------------------------------- circuit

def circuit(cx: float, cy: float, a: float, t: Theme, lap: float = 9.0) -> tuple[str, str]:
    """A figure-eight circuit with a bridge where it crosses, like Suzuka,
    and a red dot lapping it. Returns (defs, body)."""
    n = 720
    dense = [lem_point(cx, cy, a, 2 * math.pi * i / n) for i in range(n)]  # starts at the right tip
    track = closed_spline(dense[::6])
    cum = [0.0]
    for i in range(1, n + 1):
        (x0, y0), (x1, y1) = dense[i - 1], dense[i % n]
        cum.append(cum[-1] + math.hypot(x1 - x0, y1 - y0))
    total = cum[-1]

    def at(frac):
        """Point and unit tangent a fraction of the way round the lap."""
        dist = (frac % 1.0) * total
        i = min(bisect.bisect_right(cum, dist) - 1, n - 1)
        (x0, y0), (x1, y1) = dense[i], dense[(i + 1) % n]
        seg = (cum[i + 1] - cum[i]) or 1.0
        u = (dist - cum[i]) / seg
        return x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, (x1 - x0) / seg, (y1 - y0) / seg

    def tick(frac, half, color, width):
        px, py, tx, ty = at(frac)
        return (f'<line x1="{num(px - ty * half)}" y1="{num(py + tx * half)}" x2="{num(px + ty * half)}" '
                f'y2="{num(py - tx * half)}" stroke="{color}" stroke-width="{width}"/>')

    def outward(frac, dist):
        px, py, _, _ = at(frac)
        lobe = cx + (0.58 if px >= cx else -0.58) * a
        dx, dy = px - lobe, py - cy
        d = math.hypot(dx, dy) or 1.0
        return px + dx / d * dist, py + dy / d * dist

    # Each quarter of the lap is the same length, so the crossing sits at 1/4 and 3/4.
    # The 1/4 pass runs over the bridge: a gap is cut from the track under it.
    bridge = polyline([at(0.25 + k * 0.004)[:2] for k in range(-5, 6)])
    pad = 30
    defs = (
        f'<mask id="bridge" maskUnits="userSpaceOnUse" x="{num(cx - a - pad)}" y="{num(cy - a)}" '
        f'width="{num(2 * (a + pad))}" height="{num(2 * a)}">'
        f'<rect x="{num(cx - a - pad)}" y="{num(cy - a)}" width="{num(2 * (a + pad))}" height="{num(2 * a)}" '
        f'fill="#fff"/><path d="{bridge}" fill="none" stroke="#000" stroke-width="11"/></mask>'
    )
    sectors = "".join(
        text(*outward(frac, 15), f"S{k + 1}", 9.5, t.faint, cls="m", anchor="middle",
             attrs='dominant-baseline="central"')
        for k, frac in enumerate((1 / 6, 1 / 2, 5 / 6))
    )
    trail = "".join(
        f'<path d="{track}" pathLength="1000" fill="none" stroke="{t.accent}" stroke-width="3" '
        f'stroke-linecap="round" stroke-opacity="{op}" stroke-dasharray="{d} {1000 - d}" '
        f'stroke-dashoffset="{d}"><animate attributeName="stroke-dashoffset" from="{d}" to="{d - 1000}" '
        f'dur="{lap:g}s" repeatCount="indefinite"/></path>'
        for d, op in ((96, ".12"), (60, ".22"), (28, ".45"))
    )
    sx, sy = dense[0]
    body = (
        f'<path d="{track}" fill="none" stroke="{t.line}" stroke-width="3" mask="url(#bridge)"/>'
        f'<path d="{bridge}" fill="none" stroke="{t.line}" stroke-width="3"/>'
        + tick(1 / 3, 5, t.faint, 1.5) + tick(2 / 3, 5, t.faint, 1.5)
        + tick(0, 8, t.ink, 2) + sectors
        # hidden until SMIL starts, so a renderer without SMIL shows no stray dot
        + f'<g class="moving" opacity="0"><set attributeName="opacity" to="1"/>{trail}'
        f'<g><animateMotion dur="{lap:g}s" repeatCount="indefinite" path="{track}"/>'
        f'<circle r="7" fill="{t.accent}" fill-opacity=".16"/><circle r="3.6" fill="{t.accent}"/></g></g>'
        f'<circle class="still" cx="{num(sx)}" cy="{num(sy)}" r="3.6" fill="{t.accent}"/>'
    )
    return defs, body


# ---------------------------------------------------------------- live cards

def hero(cfg, st, t: Theme) -> str:
    """Name, a figure-eight circuit and the headline GitHub numbers."""
    W, H = 840, 306
    p = cfg["person"]
    name = f"{p['first_name']} {p['last_name']}"
    live = f"live · {stamp(st['updated'])}"
    top = (
        eyebrow(0, 18, p["handle"], t)
        + f'<circle class="blink" cx="{num(W - label_width(live) - 8)}" cy="14.2" r="3" fill="{t.accent}"/>'
        + label(W, 18, live, t.faint, anchor="end")
    )
    ident = (
        text(-1, 92, name, 48, t.ink, weight="600", spacing=-0.8)
        + text(0, 128, p["tagline"], 22, t.muted, weight="300")
        + text(0, 166, p["line"], 14, t.muted)
    )
    defs, track = circuit(652, 104, 168, t)

    ry = 206.5
    rule = hline(0, W, ry, t.line) + f'<rect x="0" y="{num(ry - 1)}" width="32" height="2" fill="{t.accent}"/>'

    def days(n):
        return f"{n} day" + ("" if n == 1 else "s")

    cells = [
        ("contributions", fmt_num(st["contrib_12mo"]), "last 12 months"),
        ("all-time", fmt_num(st["contrib_all"]), f"since {st['since']}"),
        ("active days", fmt_num(st["active_days"]), "last 12 months"),
        ("repositories", fmt_num(st["repos"]), "public"),
        ("longest streak", days(st["longest"]), "all-time"),
        ("current streak", days(st["current"]), "ongoing" if st["current"] else "starts today"),
    ]
    stats = "".join(
        label(i * 140, ry + 30, lab, t.faint)
        + text(i * 140 - 1, ry + 68, value, 30, t.ink, cls="s n", weight="300")
        + text(i * 140, ry + 90, sub, 12, t.faint)
        for i, (lab, value, sub) in enumerate(cells)
    )
    return doc(
        W, H, top + ident + track + rule + stats, defs=defs,
        title=f"{name} ({p['handle']}): {p['tagline']}",
        desc=(f"{p['line']}. A red dot laps a figure-eight circuit. "
              f"{st['contrib_12mo']} contributions in the last 12 months, {st['contrib_all']} since "
              f"{st['since']}, {st['active_days']} active days, {st['repos']} public repositories, "
              f"longest streak {days(st['longest'])}, current streak {days(st['current'])}. "
              f"Updated {stamp(st['updated'])}."),
    )


def telemetry(st, t: Theme) -> str:
    """Contributions per week over the last 52 weeks, as a telemetry trace."""
    W, H = 840, 232
    weeks = st["weeks"]
    vals = [v for _, v in weeks] or [0]
    n = len(vals)
    x0, x1, top, base = 0, W - 6, 72, 184
    ymax = nice_ceiling(max(vals))
    step = (x1 - x0) / max(n - 1, 1)

    def X(i):
        return x0 + step * i

    def Y(v):
        return base - (base - top) * v / ymax

    pts = [(X(i), Y(v)) for i, v in enumerate(vals)]
    line = monotone_path(pts)
    area = f"{line}L{pts[-1][0]:.2f},{base}L{pts[0][0]:.2f},{base}Z"
    total = sum(vals)
    head = (eyebrow(0, 18, "contributions per week", t)
            + label(W, 18, f"avg {total / n:.1f} a week · {st['active_days']} active days", t.faint,
                    anchor="end"))

    # three sectors, like a lap
    bounds = [0, n // 3, 2 * n // 3, n]
    grid = []
    for k in range(3):
        sx = X(bounds[k]) - (step / 2 if k else 0)
        if k:
            grid.append(f'<line x1="{num(sx)}" y1="{top - 30}" x2="{num(sx)}" y2="{base}" stroke="{t.line}" '
                        f'stroke-dasharray="2 4"/>')
        grid.append(label(sx + (8 if k else 0), top - 18,
                          f"S{k + 1} · {sum(vals[bounds[k]:bounds[k + 1]])}", t.faint))
    grid.append(hline(x0, W, base + 0.5, t.line))
    prev = None
    for i, (start, _) in enumerate(weeks):
        mid = start + timedelta(days=3)
        if prev is not None and mid.month != prev and 14 < X(i) < W - 14:
            grid.append(text(X(i), base + 20, MONTHS[mid.month - 1].upper(), 10, t.faint, cls="m",
                             anchor="middle", spacing=1))
        prev = mid.month

    best = max(range(n), key=lambda i: vals[i])
    nx, ny = pts[-1]
    marks = []
    if best != n - 1:
        bx, by = pts[best]
        marks.append(
            f'<g class="fade" style="animation-delay:2.2s">'
            f'<circle cx="{num(bx)}" cy="{num(by)}" r="3.5" fill="{t.bg}" stroke="{t.ink}" stroke-width="1.5"/>'
            + text(min(max(bx, 40), W - 40), by - 11, f"best {vals[best]}", 10, t.muted, cls="m",
                   anchor="middle")
            + "</g>"
        )
    now = f"now {vals[-1]}" + (" · best week" if best == n - 1 else "")
    marks.append(
        f'<g class="fade" style="animation-delay:2.2s">'
        f'<g class="moving"><circle cx="{num(nx)}" cy="{num(ny)}" r="3.5" fill="none" stroke="{t.accent}">'
        '<animate attributeName="r" values="3.5;12" dur="2s" repeatCount="indefinite"/>'
        '<animate attributeName="opacity" values=".8;0" dur="2s" repeatCount="indefinite"/></circle></g>'
        f'<circle cx="{num(nx)}" cy="{num(ny)}" r="3.5" fill="{t.accent}"/>'
        + text(nx - 10, ny - 8, now, 10, t.muted, cls="m", anchor="end")
        + "</g>"
    )
    defs = (
        '<linearGradient id="area" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{t.ink}" stop-opacity=".09"/>'
        f'<stop offset="1" stop-color="{t.ink}" stop-opacity="0"/></linearGradient>'
    )
    body = (
        head + "".join(grid)
        + f'<path d="{area}" fill="url(#area)" class="fade" style="animation-delay:1.2s"/>'
        + f'<path d="{line}" class="draw" pathLength="1" stroke-dasharray="1" fill="none" stroke="{t.ink}" '
          f'stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>'
        + "".join(marks)
    )
    return doc(
        W, H, body, defs=defs,
        title="Contributions per week, last 52 weeks",
        desc=(f"{total} contributions in the last {n} weeks, {st['active_days']} active days. "
              f"Busiest week: {vals[best]}. This week: {vals[-1]}."),
    )


def languages(st, t: Theme) -> str:
    """Languages as a timing tower, next to contributions by weekday."""
    W, H = 840, 236
    langs, weekdays = st["languages"][:6], st["weekdays"]

    # timing tower
    y0, rh, right = 56, 27, 470
    bx0, bx1 = 176, 404
    leader = langs[0]["share"] if langs else 1
    tower = [eyebrow(0, 18, "languages", t), label(right, 18, "share", t.faint, anchor="end")]
    for i, r in enumerate(langs):
        y = y0 + i * rh
        tower.append(
            label(0, y, f"{i + 1:02d}", t.faint)
            + f'<rect x="30" y="{y - 10}" width="2" height="12" fill="{lang_color(r["color"], t)}"/>'
            + text(42, y, fit(r["name"], bx0 - 42 - 12, 13), 13, t.ink)
            + f'<rect x="{bx0}" y="{y - 5}" width="{bx1 - bx0}" height="2" fill="{t.track}"/>'
            + f'<rect class="grow" style="animation-delay:{0.2 + 0.07 * i:.2f}s" x="{bx0}" y="{y - 5}" '
              f'width="{num(max(2.0, (bx1 - bx0) * r["share"] / leader))}" height="2" '
              f'fill="{t.accent if i == 0 else t.muted}"/>'
            + text(right, y, f"{r['share']:.1f}%", 12, t.ink, cls="m n", anchor="end")
        )
    tower.append(text(0, H - 8, fit(f"ranked by code size × repos · {st['language_count']} languages",
                                     right, 10.5, mono=True), 10.5, t.faint, cls="m"))

    # weekdays
    left, base, top = 540, 178, 64
    slot = (W - left) / 7
    vmax = max(weekdays) or 1
    hi = weekdays.index(max(weekdays))
    days = [eyebrow(left, 18, "by weekday", t)]
    for i, v in enumerate(weekdays):
        h = max(2.0, (base - top) * v / vmax)
        x = left + i * slot + slot / 2
        days.append(
            f'<rect class="rise" style="animation-delay:{0.2 + 0.06 * i:.2f}s" x="{num(x - 3)}" '
            f'y="{num(base - h)}" width="6" height="{num(h)}" rx="1" fill="{t.accent if i == hi else t.muted}"/>'
            + text(x, base - h - 8, str(v), 10, t.muted, cls="m n", anchor="middle")
            + label(x, base + 20, WEEKDAYS[i][:3], t.faint, anchor="middle")
        )
    days.append(text(left, H - 8, f"busiest: {WEEKDAYS[hi]}", 10.5, t.faint, cls="m"))
    return doc(
        W, H, "".join(tower) + "".join(days),
        title="Languages, and contributions by weekday",
        desc=("Languages: " + ", ".join(f"{r['name']} {r['share']:.1f}%" for r in langs)
              + ". Contributions by weekday, Monday first: " + ", ".join(map(str, weekdays)) + "."),
    )


def project_card(p, repo, today: date, owner: str, t: Theme) -> str:
    """One featured project: summary, three sector times and live repo facts."""
    W, H, pad = 412, 206, 20
    body = [f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="6" fill="none" stroke="{t.line}"/>']
    when = f"updated {ago(repo.get('pushed'), today)}" if repo else ""
    if when:
        body.append(text(W - pad, 38, when, 12, t.faint, anchor="end"))
        if repo.get("pushed") is not None and (today - repo["pushed"]).days <= 7:
            # pushed this week: the same live dot as the header
            body.append(f'<circle class="blink" cx="{num(W - pad - text_width(when, 12) - 8)}" cy="34" r="3" '
                        f'fill="{t.accent}"/>')
    body.append(text(pad, 38, fit(p["name"], W - 2 * pad - text_width(when, 12) - 30, 18, bold=True), 18,
                     t.ink, weight="600"))
    body.append(text(pad, 60, fit(p["summary"], W - 2 * pad, 13), 13, t.muted))
    body.append(hline(pad, W - pad, 78.5, t.line))
    for k, m in enumerate(p["metrics"][:3]):
        y = 104 + k * 25
        note = m.get("note", "")
        lx = pad + 108
        room = (W - pad - text_width(note, 10.5, mono=True) - 14 if note else W - pad) - lx
        body.append(
            label(pad, y, f"S{k + 1}", t.faint)
            + text(pad + 30, y, m["value"], 14, t.ink, cls="s n", weight="600")
            + text(lx, y, fit(m["label"], room, 13), 13, t.muted)
            + (text(W - pad, y, note, 10.5, t.faint, cls="m", anchor="end") if note else "")
        )
    body.append(hline(pad, W - pad, 168.5, t.line))

    bits = []
    if repo and repo.get("release"):
        bits.append(repo["release"])
    if repo and repo.get("stars", 0) >= 5:
        bits.append(f"★ {repo['stars']}")
    if not repo:
        bits.append(f"github.com/{owner}/{p['repo']}")
    right = " · ".join(bits)
    room = W - 2 * pad - (text_width(right, 10.5, mono=True) + 16 if right else 0)
    if right:
        body.append(text(W - pad, 190, right, 10.5, t.faint, cls="m", anchor="end"))
    body.append(text(pad, 190, fit(" · ".join(p["stack"]), room, 10.5, mono=True), 10.5, t.faint, cls="m"))
    return doc(
        W, H, "".join(body),
        title=f"{p['name']}: {p['summary']}",
        desc=("Built with " + ", ".join(p["stack"]) + ". "
              + "; ".join(f"{m['value']} {m['label']}" + (f" ({m['note']})" if m.get("note") else "")
                          for m in p["metrics"]) + "."),
    )


# ---------------------------------------------------------------- static art

def ml_season(cfg, t: Theme) -> str:
    """The applied-ML challenge season, as championship standings."""
    s = cfg["ml_season"]
    rows = s["domains"]
    W = 840
    y0, rh = 136, 26
    yb = y0 + rh * (len(rows) - 1) + 24.5
    H = int(yb) + 40
    tx = text_width(s["total"], 46) + 14
    head = (
        eyebrow(0, 18, f"season {s['season']}", t)
        + label(W, 18, f"{s['window']} · counted by main domain", t.faint, anchor="end")
        + text(-2, 90, s["total"], 46, t.ink, cls="s n", weight="300", spacing=-1)
        + text(tx, 70, "applied-ML challenges", 16, t.ink, weight="600")
        + text(tx, 90, f"across {len(rows)} domains, on cloud and local GPUs", 13, t.muted)
    )
    vmax = max(r["value"] for r in rows) or 1
    bx0, bx1 = 268, 792
    table = []
    for i, r in enumerate(rows):
        y = y0 + i * rh
        table.append(
            label(0, y, f"{i + 1:02d}", t.faint)
            + text(34, y, fit(r["name"], bx0 - 34 - 16, 13), 13, t.ink)
            + f'<rect x="{bx0}" y="{y - 5}" width="{bx1 - bx0}" height="2" fill="{t.track}"/>'
            + f'<rect class="grow" style="animation-delay:{0.15 + 0.06 * i:.2f}s" x="{bx0}" y="{y - 5}" '
              f'width="{num((bx1 - bx0) * r["value"] / vmax)}" height="2" '
              f'fill="{t.accent if i == 0 else t.muted}"/>'
            + text(W, y, str(r["value"]), 12, t.ink, cls="m n", anchor="end")
        )
    tools = " · ".join(s["tools"])
    compute = " · ".join(s["compute"])
    bottom = (
        hline(0, W, yb, t.line)
        + text(0, yb + 24, fit(tools, W - text_width(compute, 10.5, mono=True) - 24, 10.5, mono=True), 10.5,
               t.muted, cls="m")
        + text(W, yb + 24, compute, 10.5, t.muted, cls="m", anchor="end")
    )
    return doc(
        W, H, head + "".join(table) + bottom,
        title=f"{s['season']} applied-ML season: {s['total']} challenges",
        desc="; ".join(f"{r['name']}: {r['value']}" for r in rows)
             + ". Compute: " + ", ".join(s["compute"]) + ". Tools: " + ", ".join(s["tools"]) + ".",
    )


def footer(t: Theme) -> str:
    """A finish line: a hairline into a small chequered block."""
    W, H = 840, 40
    msg = "Thanks for stopping by."
    sq, cols, rows = 4, 10, 2
    fx, fy = W - cols * sq, 16.5
    chequer = "".join(
        f'<rect x="{fx + c * sq}" y="{num(fy + r * sq)}" width="{sq}" height="{sq}" fill="{t.ink}"/>'
        for r in range(rows) for c in range(cols) if (r + c) % 2 == 0
    )
    body = (
        text(0, 25, msg, 13, t.muted)
        + hline(text_width(msg, 13) + 6, fx - 12, 20.5, t.line)
        + f'<rect x="{num(fx - 12 - 24)}" y="19.5" width="24" height="2" fill="{t.accent}"/>'
        + chequer
    )
    return doc(W, H, body, title="Finish line", desc="Thanks for stopping by.")
