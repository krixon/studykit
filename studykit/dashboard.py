"""A self-contained HTML dashboard, generated from state and metrics.

One file, no network, no build step, no dependencies: inline CSS, inline SVG,
one small script for tooltips and the theme toggle. Open it with a browser or
email it to yourself.

Chart forms follow the data's job: trend over time is a line, magnitude
comparisons are bars on a single sequential hue, and calibration error is a
diverging bar against a zero baseline because its sign is the whole point.
"""

from __future__ import annotations

import html
import json

from .config import LEVEL_TITLES

# Categorical slots 1 and 2, validated for both surfaces (adjacent and all-pairs).
SERIES = {
    "light": ["#2a78d6", "#eb6834"],
    "dark": ["#3987e5", "#d95926"],
}
# Ordinal blue ramp, no lighter than step 250 on light / no darker than 600 on dark.
ORDINAL = {
    "light": ["#86b6ef", "#5598e7", "#3987e5", "#2a78d6", "#184f95"],
    "dark": ["#184f95", "#256abf", "#2a78d6", "#3987e5", "#5598e7"],
}

PAD_L, PAD_R, PAD_T, PAD_B = 46, 18, 16, 34


def esc(text: object) -> str:
    return html.escape(str(text), quote=True)


# --------------------------------------------------------------------------- #
# svg helpers
# --------------------------------------------------------------------------- #


def _scale(value: float, lo: float, hi: float, out_lo: float, out_hi: float) -> float:
    if hi == lo:
        return (out_lo + out_hi) / 2
    return out_lo + (value - lo) * (out_hi - out_lo) / (hi - lo)


def _cap_path(x: float, y: float, w: float, h: float, radius: float, side: str) -> str:
    """A bar with only its data-end rounded, so the baseline stays square."""
    r = max(0.0, min(radius, h / 2, w))
    if w <= 0:
        return ""
    if side == "right":
        return (
            f"M{x},{y} H{x + w - r} A{r},{r} 0 0 1 {x + w},{y + r} "
            f"V{y + h - r} A{r},{r} 0 0 1 {x + w - r},{y + h} H{x} Z"
        )
    if side == "left":
        return (
            f"M{x + w},{y} H{x + r} A{r},{r} 0 0 0 {x},{y + r} "
            f"V{y + h - r} A{r},{r} 0 0 0 {x + r},{y + h} H{x + w} Z"
        )
    r = max(0.0, min(radius, w / 2, h))
    if side == "bottom":
        # a column hanging below the baseline: round the low end
        return (
            f"M{x},{y} V{y + h - r} A{r},{r} 0 0 0 {x + r},{y + h} "
            f"H{x + w - r} A{r},{r} 0 0 0 {x + w},{y + h - r} V{y} Z"
        )
    return (
        f"M{x},{y + h} V{y + r} A{r},{r} 0 0 1 {x + r},{y} "
        f"H{x + w - r} A{r},{r} 0 0 1 {x + w},{y + r} V{y + h} Z"
    )


def _empty(message: str) -> str:
    return f'<p class="empty">{esc(message)}</p>'


# --------------------------------------------------------------------------- #
# charts
# --------------------------------------------------------------------------- #


def chart_progress(progress: list[dict]) -> str:
    points = [p for p in progress if p["all_facets"] is not None]
    if len(points) < 2:
        return _empty("Two sessions of history and this fills in.")

    width, height = 980, 300
    x0, x1 = PAD_L, width - PAD_R - 46
    y0, y1 = PAD_T, height - PAD_B
    n = len(points)

    def px(index: int) -> float:
        return _scale(index, 0, max(n - 1, 1), x0, x1)

    def py(value: float) -> float:
        return _scale(value, 1, 5, y1, y0)

    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Mean strength over time" preserveAspectRatio="xMidYMid meet">']
    for tick in (1, 2, 3, 4, 5):
        y = py(tick)
        parts.append(f'<line class="grid" x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}"/>')
        parts.append(f'<text class="tick" x="{x0 - 10}" y="{y + 4:.1f}" text-anchor="end">{tick}</text>')

    for key, slot, label in (("all_facets", 0, "all facets"), ("re_measured", 1, "re-measured only")):
        series = [(i, p[key]) for i, p in enumerate(points) if p.get(key) is not None]
        if len(series) < 2:
            continue
        path = " ".join(
            f"{'M' if k == 0 else 'L'}{px(i):.1f},{py(v):.1f}" for k, (i, v) in enumerate(series)
        )
        parts.append(f'<path class="line s{slot}" d="{path}"/>')
        for i, value in series:
            parts.append(
                f'<circle class="dot s{slot}" cx="{px(i):.1f}" cy="{py(value):.1f}" r="4.5" '
                f'data-tip="{esc(points[i]["date"])} &middot; {label} {value:.2f} '
                f'(n={points[i][key + "_n"]})"/>'
            )
        last_index, last_value = series[-1]
        parts.append(
            f'<text class="direct s{slot}" x="{px(last_index) + 10:.1f}" y="{py(last_value) + 4:.1f}">'
            f"{last_value:.1f}</text>"
        )

    for index in {0, n - 1, n // 2}:
        parts.append(
            f'<text class="tick" x="{px(index):.1f}" y="{height - 12}" text-anchor="middle">'
            f'{esc(points[index]["date"][5:])}</text>'
        )
    parts.append("</svg>")

    legend = (
        '<div class="legend">'
        '<span class="key"><i class="swatch s0"></i>all facets</span>'
        '<span class="key"><i class="swatch s1"></i>re-measured only</span>'
        "</div>"
    )
    return legend + "".join(parts)


def chart_hbars(rows: list[tuple[str, float | None, str]], *, maximum: float = 5.0) -> str:
    rows = [r for r in rows if r[1] is not None]
    if not rows:
        return _empty("Nothing measured here yet.")
    row_h, gap = 26, 6
    width = 720
    height = PAD_T + len(rows) * (row_h + gap) + 8
    x0 = 150
    x1 = width - 56

    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" preserveAspectRatio="xMidYMid meet">']
    for index, (label, value, tip) in enumerate(rows):
        y = PAD_T + index * (row_h + gap)
        w = max(_scale(value, 0, maximum, 0, x1 - x0), 2)
        bucket = min(4, max(0, int(round(value)) - 1))
        parts.append(
            f'<path class="bar o{bucket}" d="{_cap_path(x0, y, w, row_h - 4, 4, "right")}" '
            f'data-tip="{esc(tip)}"/>'
        )
        parts.append(
            f'<text class="rowlabel" x="{x0 - 12}" y="{y + row_h / 2:.0f}" text-anchor="end">{esc(label)}</text>'
        )
        parts.append(
            f'<text class="value" x="{x0 + w + 8:.1f}" y="{y + row_h / 2:.0f}">{value:.1f}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def chart_distribution(distribution: dict[str, int]) -> str:
    total = sum(distribution.values())
    if not total:
        return _empty("No facets measured yet.")
    width, height = 620, 240
    x0, x1 = PAD_L, width - PAD_R
    y0, y1 = PAD_T, height - PAD_B
    peak = max(distribution.values()) or 1
    slot = (x1 - x0) / 5

    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Facets by current strength" preserveAspectRatio="xMidYMid meet">']
    parts.append(f'<line class="axis" x1="{x0}" y1="{y1}" x2="{x1}" y2="{y1}"/>')
    for index in range(5):
        score = str(index + 1)
        count = distribution.get(score, 0)
        h = _scale(count, 0, peak, 0, y1 - y0)
        x = x0 + index * slot + 3
        w = slot - 6
        if count:
            parts.append(
                f'<path class="bar o{index}" d="{_cap_path(x, y1 - h, w, h, 4, "top")}" '
                f'data-tip="strength {score}: {count} facet(s), {100 * count / total:.0f}%"/>'
            )
            parts.append(
                f'<text class="value" x="{x + w / 2:.1f}" y="{y1 - h - 7:.1f}" text-anchor="middle">{count}</text>'
            )
        parts.append(
            f'<text class="tick" x="{x + w / 2:.1f}" y="{height - 12}" text-anchor="middle">{score}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def chart_calibration(series: list[dict]) -> str:
    if not series:
        return _empty("No confidence ratings captured. They are optional, and only feed this chart.")
    width, height = 620, 240
    x0, x1 = PAD_L, width - PAD_R
    y0, y1 = PAD_T, height - PAD_B
    span = max(1.0, max(abs(p["error"]) for p in series if p["error"] is not None))
    zero = _scale(0, -span, span, y1, y0)
    slot = (x1 - x0) / max(len(series), 1)

    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Calibration error by session" preserveAspectRatio="xMidYMid meet">']
    parts.append(f'<line class="axis" x1="{x0}" y1="{zero:.1f}" x2="{x1}" y2="{zero:.1f}"/>')
    parts.append(f'<text class="tick" x="{x0 - 10}" y="{zero + 4:.1f}" text-anchor="end">0</text>')
    parts.append(f'<text class="tick" x="{x0 - 10}" y="{y0 + 10}" text-anchor="end">+{span:.0f}</text>')
    parts.append(f'<text class="tick" x="{x0 - 10}" y="{y1}" text-anchor="end">-{span:.0f}</text>')

    for index, point in enumerate(series):
        error = point["error"]
        if error is None:
            continue
        x = x0 + index * slot + 3
        w = max(slot - 6, 3)
        y = _scale(error, -span, span, y1, y0)
        top, h = (y, zero - y) if error >= 0 else (zero, y - zero)
        klass = "over" if error > 0 else "under"
        direction = "overconfident" if error > 0 else "underconfident"
        parts.append(
            f'<path class="bar {klass}" d="{_cap_path(x, top, w, max(h, 2), 4, "top" if error >= 0 else "bottom")}" '
            f'data-tip="{esc(point["date"])} &middot; {error:+.2f} {direction} (n={point["n"]})"/>'
        )
    parts.append("</svg>")
    return "".join(parts)


# --------------------------------------------------------------------------- #
# tables
# --------------------------------------------------------------------------- #


def table(
    headers: list[str], rows: list[list[str]], *, empty: str, wrap_columns: tuple[int, ...] = ()
) -> str:
    """Columns in `wrap_columns` wrap instead of scrolling off the edge."""
    if not rows:
        return _empty(empty)
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = ""
    for row in rows:
        cells = "".join(
            f'<td class="wrapcell">{cell}</td>' if index in wrap_columns else f"<td>{cell}</td>"
            for index, cell in enumerate(row)
        )
        body += f"<tr>{cells}</tr>"
    return f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def strength_chip(value) -> str:
    if value is None:
        return '<span class="chip none">-</span>'
    band = "low" if value <= 2 else "mid" if value == 3 else "high"
    return f'<span class="chip {band}">{value}</span>'


def stat_tile(label: str, value: str, note: str, tone: str = "") -> str:
    return (
        f'<div class="tile{" " + tone if tone else ""}">'
        f'<div class="tile-label">{esc(label)}</div>'
        f'<div class="tile-value">{esc(value)}</div>'
        f'<div class="tile-note">{esc(note)}</div>'
        "</div>"
    )


# --------------------------------------------------------------------------- #
# page
# --------------------------------------------------------------------------- #


def render(state: dict, metrics: dict, recommendation: dict) -> str:
    summary = metrics.get("summary", {})
    items = state.get("items", [])
    facets = [i for i in items if i["kind"] == "facet"]
    overdue = sorted(
        [i for i in facets if i["overdue_days"] > 0], key=lambda i: (-i["overdue_days"], i["strength"])
    )
    gaps = state.get("gaps", [])
    unmeasured = sum(len(g["missing"]) for g in gaps)
    level = state.get("level", "")

    error = summary.get("calibration_error")
    calibration_note = (
        "no confidence ratings yet"
        if error is None
        else "overconfident" if error > 0.25 else "underconfident" if error < -0.25 else "well calibrated"
    )

    tiles = "".join(
        [
            stat_tile(
                "mean strength",
                f"{summary.get('mean_strength') or 0:.2f}",
                f"{summary.get('facets_measured', 0)} facets measured",
            ),
            stat_tile(
                "coverage",
                f"{summary.get('coverage_pct') or 0:.0f}%",
                f"{unmeasured} facets never tested",
                "warn" if unmeasured else "",
            ),
            stat_tile(
                "overdue",
                str(len(overdue)),
                "facets past their interval",
                "warn" if overdue else "",
            ),
            stat_tile(
                "calibration",
                f"{error:+.2f}" if error is not None else "-",
                calibration_note,
                "warn" if error is not None and abs(error) > 0.5 else "",
            ),
        ]
    )

    qtype_rows = [
        (entry["qtype"], entry["mean"], f"{entry['qtype']}: mean {entry['mean']} over {entry['n']} question(s)")
        for entry in metrics.get("by_qtype", [])
    ]
    area_rows = [
        (entry["area"], entry["mean"], f"{entry['area']}: mean {entry['mean']} over {entry['facets']} facet(s)")
        for entry in sorted(metrics.get("by_area", []), key=lambda e: (e["mean"] or 0))
    ]

    overdue_table = table(
        ["", "facet", "late", "reps", "last"],
        [
            [
                strength_chip(item["strength"]),
                esc(item["label"]),
                f"{item['overdue_days']}d",
                str(item["reps"]),
                esc(item["last"]),
            ]
            for item in overdue[:15]
        ],
        empty="Nothing overdue.",
    )

    gaps_table = table(
        ["topic", "unmeasured", "facets"],
        [
            [esc(gap["topic"]), f"{len(gap['missing'])}/{gap['total']}", esc(" · ".join(gap["missing"]))]
            for gap in gaps[:15]
        ],
        empty="Every facet in scope has been measured at least once.",
        wrap_columns=(2,),
    )

    weakest_table = table(
        ["", "facet", "area", "reps", "due"],
        [
            [
                strength_chip(entry["strength"]),
                esc(f"{entry['topic']}/{entry['subtopic']}"),
                esc(entry["area"]),
                str(entry["reps"]),
                esc(entry["due"]),
            ]
            for entry in metrics.get("weakest", [])[:12]
        ],
        empty="No measurements yet.",
    )

    thin = metrics.get("thin_evidence", [])
    thin_table = table(
        ["", "facet", "due"],
        [[strength_chip(e["strength"]), esc(f"{e['topic']}/{e['subtopic']}"), esc(e["due"])] for e in thin[:12]],
        empty="None. Every 4 or 5 rests on more than one answer.",
    )

    problems_table = table(
        ["", "problem", "attempts", "last", "due"],
        [
            [
                strength_chip(entry["score"]),
                esc(entry["slug"]),
                str(entry["attempts"]),
                esc(entry["last"]),
                esc(entry["due"]),
            ]
            for entry in sorted(metrics.get("problems", []), key=lambda p: p["due"])
        ],
        empty="No problems attempted yet. Integration is the untested part.",
    )

    teaching = metrics.get("teaching", {})
    teaching_note = (
        f"{teaching['landed']} of {teaching['n']} weak facets reached 3+ on the variant re-test"
        if teaching.get("n")
        else "No teaching re-tests recorded yet."
    )

    uncovered = metrics.get("uncovered_areas", [])
    uncovered_html = (
        f'<p class="note">Areas with no measurement at all: <strong>{esc(", ".join(uncovered))}</strong></p>'
        if uncovered
        else ""
    )

    return PAGE.format(
        title=f"studykit &middot; {esc(LEVEL_TITLES.get(level, level))}",
        css=CSS,
        script=SCRIPT,
        level=esc(LEVEL_TITLES.get(level, level)),
        generated=esc(state.get("generated", "")),
        packs=esc(", ".join(state.get("packs", []))),
        sessions=summary.get("sessions", 0),
        measurements=summary.get("measurements", 0),
        recommendation=esc(recommendation["headline"]),
        command=esc(recommendation["command"]),
        tiles=tiles,
        progress=chart_progress(metrics.get("progress", [])),
        by_qtype=chart_hbars(qtype_rows),
        by_area=chart_hbars(area_rows),
        distribution=chart_distribution(metrics.get("strength_distribution", {})),
        calibration=chart_calibration(metrics.get("calibration", [])),
        overdue_table=overdue_table,
        gaps_table=gaps_table,
        weakest_table=weakest_table,
        thin_table=thin_table,
        problems_table=problems_table,
        teaching_note=esc(teaching_note),
        uncovered=uncovered_html,
        payload=json.dumps({"state": state, "metrics": metrics}),
    )


CSS = """
:root {
  color-scheme: light;
  --page: #f9f9f7;
  --surface: #fcfcfb;
  --ink: #0b0b0b;
  --ink-2: #52514e;
  --muted: #898781;
  --grid: #e1e0d9;
  --axis: #c3c2b7;
  --border: rgba(11,11,11,0.10);
  --s0: #2a78d6;
  --s1: #eb6834;
  --o0: #86b6ef; --o1: #5598e7; --o2: #3987e5; --o3: #2a78d6; --o4: #184f95;
  --over: #d03b3b;
  --under: #2a78d6;
  --good: #0ca30c;
  --warn: #fab219;
  --crit: #d03b3b;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --page: #0d0d0d; --surface: #1a1a19; --ink: #ffffff; --ink-2: #c3c2b7;
    --muted: #898781; --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,0.10);
    --s0: #3987e5; --s1: #d95926;
    --o0: #184f95; --o1: #256abf; --o2: #2a78d6; --o3: #3987e5; --o4: #5598e7;
    --over: #d03b3b; --under: #3987e5;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --page: #0d0d0d; --surface: #1a1a19; --ink: #ffffff; --ink-2: #c3c2b7;
  --muted: #898781; --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,0.10);
  --s0: #3987e5; --s1: #d95926;
  --o0: #184f95; --o1: #256abf; --o2: #2a78d6; --o3: #3987e5; --o4: #5598e7;
  --over: #d03b3b; --under: #3987e5;
}

* { box-sizing: border-box; }
body {
  margin: 0; padding: 28px 20px 64px;
  background: var(--page); color: var(--ink);
  font: 15px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif;
}
.wrap { max-width: 1560px; margin: 0 auto; }
header { display: flex; flex-wrap: wrap; gap: 12px 20px; align-items: baseline; margin-bottom: 6px; }
h1 { font-size: 20px; margin: 0; letter-spacing: -0.01em; }
h2 { font-size: 14px; margin: 0 0 12px; color: var(--ink-2); font-weight: 600;
     text-transform: uppercase; letter-spacing: 0.07em; }
.meta { color: var(--muted); font-size: 13px; }
.toggle {
  margin-left: auto; background: var(--surface); color: var(--ink-2);
  border: 1px solid var(--border); border-radius: 999px;
  padding: 5px 13px; font: inherit; font-size: 13px; cursor: pointer;
}
.toggle:hover { color: var(--ink); }

.next {
  background: var(--surface); border: 1px solid var(--border); border-left: 3px solid var(--s0);
  border-radius: 10px; padding: 14px 18px; margin: 18px 0 22px;
}
.next b { display: block; font-size: 12px; text-transform: uppercase; letter-spacing: 0.07em;
          color: var(--muted); font-weight: 600; margin-bottom: 3px; }
.next code { font-size: 13px; color: var(--ink-2); }

.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; }
.tile { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 16px 18px; }
.tile-label { font-size: 12px; text-transform: uppercase; letter-spacing: 0.07em; color: var(--muted); }
.tile-value { font-size: 34px; line-height: 1.15; margin: 4px 0 2px; letter-spacing: -0.02em; }
.tile-note { font-size: 13px; color: var(--ink-2); }
.tile.warn .tile-value { color: var(--crit); }

section { background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
          padding: 18px 20px 20px; margin-top: 18px; }
.grid2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 18px; margin-top: 18px; }
.grid2 section { margin-top: 0; }
/* Charts stop growing past their natural size; the extra width goes to the tables,
   which is where it is actually useful. */
svg { width: 100%; max-width: 980px; height: auto; display: block; overflow: visible; }

.grid { stroke: var(--grid); stroke-width: 1; }
.axis { stroke: var(--axis); stroke-width: 1; }
.tick { fill: var(--muted); font-size: 11px; font-variant-numeric: tabular-nums; }
.rowlabel { fill: var(--ink-2); font-size: 12px; dominant-baseline: middle; }
.value { fill: var(--ink-2); font-size: 12px; dominant-baseline: middle; font-variant-numeric: tabular-nums; }
.line { fill: none; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
.dot { stroke: var(--surface); stroke-width: 2; }
.direct { font-size: 12px; font-weight: 600; font-variant-numeric: tabular-nums; }
.s0, .line.s0 { stroke: var(--s0); }
.s1, .line.s1 { stroke: var(--s1); }
circle.s0 { fill: var(--s0); }
circle.s1 { fill: var(--s1); }
text.s0 { fill: var(--s0); stroke: none; }
text.s1 { fill: var(--s1); stroke: none; }
.bar { stroke: var(--surface); stroke-width: 2; }
.bar.o0 { fill: var(--o0); } .bar.o1 { fill: var(--o1); } .bar.o2 { fill: var(--o2); }
.bar.o3 { fill: var(--o3); } .bar.o4 { fill: var(--o4); }
.bar.over { fill: var(--over); } .bar.under { fill: var(--under); }
[data-tip] { cursor: default; }
[data-tip]:hover { filter: brightness(1.12); }

.legend { display: flex; gap: 18px; margin-bottom: 6px; font-size: 13px; color: var(--ink-2); }
.key { display: inline-flex; align-items: center; gap: 7px; }
.swatch { width: 11px; height: 11px; border-radius: 3px; display: inline-block; }
.swatch.s0 { background: var(--s0); } .swatch.s1 { background: var(--s1); }

.scroll { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th { text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 0.07em;
     color: var(--muted); font-weight: 600; padding: 0 12px 8px 0; white-space: nowrap; }
td { padding: 7px 12px 7px 0; border-top: 1px solid var(--grid); color: var(--ink-2);
     white-space: nowrap; font-variant-numeric: tabular-nums; }
td:nth-child(2) { color: var(--ink); }
/* A list of facet names is prose, not a value: let it wrap rather than clip. */
td.wrapcell { white-space: normal; min-width: 22ch; font-variant-numeric: normal; }
.chip { display: inline-block; min-width: 22px; text-align: center; border-radius: 5px;
        padding: 1px 6px; font-size: 12px; font-weight: 600; color: #fff; }
.chip.low { background: var(--crit); }
.chip.mid { background: #b07d00; }
.chip.high { background: var(--good); }
.chip.none { background: var(--axis); color: var(--ink-2); }
.empty { color: var(--muted); font-size: 14px; margin: 6px 0; }
.note { color: var(--ink-2); font-size: 14px; }
footer { margin-top: 28px; color: var(--muted); font-size: 13px; }
#tip {
  position: fixed; pointer-events: none; opacity: 0; transition: opacity .1s;
  background: var(--ink); color: var(--page); padding: 6px 10px; border-radius: 7px;
  font-size: 12.5px; max-width: 300px; z-index: 20;
}
@media print { .toggle { display: none; } body { background: #fff; } }
"""

SCRIPT = """
(function () {
  var root = document.documentElement;
  var button = document.getElementById('theme');
  var stored = null;
  try { stored = localStorage.getItem('studykit-theme'); } catch (e) {}
  if (stored) root.setAttribute('data-theme', stored);
  button.addEventListener('click', function () {
    var dark = getComputedStyle(root).colorScheme === 'dark';
    var next = dark ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    try { localStorage.setItem('studykit-theme', next); } catch (e) {}
  });

  var tip = document.getElementById('tip');
  document.addEventListener('mouseover', function (event) {
    var target = event.target.closest('[data-tip]');
    if (!target) return;
    tip.innerHTML = target.getAttribute('data-tip');
    tip.style.opacity = '1';
  });
  document.addEventListener('mousemove', function (event) {
    if (tip.style.opacity !== '1') return;
    var x = Math.min(event.clientX + 14, window.innerWidth - tip.offsetWidth - 10);
    var y = Math.max(event.clientY - tip.offsetHeight - 12, 8);
    tip.style.left = x + 'px';
    tip.style.top = y + 'px';
  });
  document.addEventListener('mouseout', function (event) {
    if (event.target.closest('[data-tip]')) tip.style.opacity = '0';
  });
})();
"""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>studykit</h1>
  <span class="meta">{level} &middot; {packs} &middot; {generated} &middot; {sessions} sessions, {measurements} measurements</span>
  <button class="toggle" id="theme" type="button">theme</button>
</header>

<div class="next">
  <b>next session</b>
  {recommendation}<br><code>{command}</code>
</div>

<div class="tiles">{tiles}</div>

<section>
  <h2>Mean strength over time</h2>
  {progress}
  <p class="note">All facets moves when new ground is broken as well as when something improves.
  Re-measured only holds the item set fixed to facets tested on two or more separate dates, which is the like-for-like reading.</p>
</section>

<div class="grid2">
  <section>
    <h2>Score by question type</h2>
    {by_qtype}
    <p class="note">High recall with low judgment means the knowledge is there and inert. That needs applied work, not more flashcards.</p>
  </section>
  <section>
    <h2>Strength by area</h2>
    {by_area}
  </section>
</div>

<div class="grid2">
  <section>
    <h2>Facets by current strength</h2>
    {distribution}
  </section>
  <section>
    <h2>Calibration by session</h2>
    {calibration}
    <p class="note">Predicted minus measured. Above the line is overconfidence. Self-reports never touch scheduling.</p>
  </section>
</div>

<div class="grid2">
  <section>
    <h2>Overdue</h2>
    {overdue_table}
  </section>
  <section>
    <h2>Never measured</h2>
    {gaps_table}
    <p class="note">Unknown, not merely stale. Usually the more urgent condition.</p>
  </section>
</div>

<div class="grid2">
  <section>
    <h2>Weakest facets</h2>
    {weakest_table}
  </section>
  <section>
    <h2>Thin evidence</h2>
    {thin_table}
    <p class="note">One rep carrying a 4 or 5. Not mastery, only not-failing-once.</p>
  </section>
</div>

<section>
  <h2>Problems</h2>
  {problems_table}
  <p class="note">{teaching_note}</p>
  {uncovered}
</section>

<footer>
  Generated by studykit from your ledger. Nothing here left your machine.
  <script type="application/json" id="data">{payload}</script>
</footer>
</div>
<div id="tip" role="status"></div>
<script>{script}</script>
</body>
</html>
"""
