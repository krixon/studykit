"""Metrics, computed from the ledger and written to `data/metrics.json`.

Two readings of the progress series: **all facets** moves when new ground is
broken as well as when something improves, because new ground usually means a
low score; **re-measured only** holds the item set to facets tested on two or
more separate dates, which is the like-for-like reading.

Every average uses the cold `measured` field. `post` is never averaged in - it
would flatter the numbers with scores taken after teaching.
"""

from __future__ import annotations

from collections import defaultdict

from .config import today
from .ledger import Row
from .packs import QTYPES, Library
from .schedule import compute_items, live_items, round_half_up


def _mean(values) -> float | None:
    values = list(values)
    return sum(values) / len(values) if values else None


def _round(value: float | None, places: int = 2) -> float | None:
    return None if value is None else round(value, places)


def _live_rows(rows: list[Row]) -> list[Row]:
    """Drop `overall` rows for topics that later gained a real facet breakdown."""
    faceted = {(r.pack, r.topic) for r in rows if r.subtopic != "overall"}
    return [r for r in rows if r.subtopic != "overall" or (r.pack, r.topic) not in faceted]


def _by_facet(rows: list[Row]) -> dict[tuple[str, str, str], dict[str, list[int]]]:
    out: dict[tuple[str, str, str], dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        out[row.key][row.date].append(row.measured)
    return out


def _strength_as_of(by_date: dict[str, list[int]], date: str) -> int | None:
    past = [d for d in by_date if d <= date]
    if not past:
        return None
    latest = max(past)
    return round_half_up(sum(by_date[latest]) / len(by_date[latest]))


def build_metrics(library: Library, rows: list[Row], level: str, as_of: str | None = None) -> dict:
    as_of = as_of or today()
    facet_rows = [r for r in _live_rows(rows) if not r.is_problem]
    problem_rows = [r for r in rows if r.is_problem]
    by_facet = _by_facet(facet_rows)
    dates = sorted({r.date for r in rows})

    repeated = {k for k, v in by_facet.items() if len(v) >= 2}

    progress = []
    for date in dates:
        all_now = [s for k, v in by_facet.items() if (s := _strength_as_of(v, date)) is not None]
        cohort = [
            s for k in repeated if (s := _strength_as_of(by_facet[k], date)) is not None
        ]
        progress.append(
            {
                "date": date,
                "all_facets": _round(_mean(all_now)),
                "all_facets_n": len(all_now),
                "re_measured": _round(_mean(cohort)),
                "re_measured_n": len(cohort),
            }
        )

    items = live_items(compute_items(rows))
    facets = [i for i in items if i.kind == "facet"]

    by_area: dict[str, list[int]] = defaultdict(list)
    for item in facets:
        by_area[item.area or "unclassified"].append(item.strength)

    by_topic: dict[tuple[str, str], list[int]] = defaultdict(list)
    for item in facets:
        by_topic[(item.pack, item.topic)].append(item.strength)

    by_qtype: dict[str, list[int]] = defaultdict(list)
    for row in facet_rows:
        if row.qtype:
            by_qtype[row.qtype].append(row.measured)

    distribution = {str(score): 0 for score in range(1, 6)}
    for item in facets:
        distribution[str(item.strength)] += 1

    calibration_rows = [r for r in rows if r.predicted is not None]
    calibration_series = []
    for date in sorted({r.date for r in calibration_rows}):
        same_day = [r for r in calibration_rows if r.date == date]
        calibration_series.append(
            {
                "date": date,
                "error": _round(_mean(r.predicted - r.measured for r in same_day)),
                "n": len(same_day),
            }
        )

    taught = [r for r in rows if r.post is not None]
    teaching = {
        "n": len(taught),
        "landed": sum(1 for r in taught if r.post >= 3),
        "stuck": sum(1 for r in taught if r.post <= 2),
        "mean_gain": _round(_mean(r.post - r.measured for r in taught)),
    }

    in_scope = [t for t in library.topics(level)]
    total_facets = sum(len(t.subtopics) for t in in_scope)
    measured_facets = {
        (i.pack, i.topic, i.subtopic)
        for i in facets
        if (i.pack, i.topic) in {(t.pack, t.id) for t in in_scope}
    }

    covered_areas = {i.area for i in facets if i.area}
    all_areas = {t.area for t in in_scope if t.area}

    return {
        "generated": as_of,
        "level": level,
        "packs": list(library.enabled_names),
        "summary": {
            "measurements": len(rows),
            "sessions": len(dates),
            "first_session": dates[0] if dates else None,
            "last_session": dates[-1] if dates else None,
            "facets_measured": len(measured_facets),
            "facets_in_scope": total_facets,
            "coverage_pct": _round(100 * len(measured_facets) / total_facets, 1) if total_facets else None,
            "mean_strength": _round(_mean(i.strength for i in facets)),
            "calibration_error": _round(
                _mean(r.predicted - r.measured for r in calibration_rows)
            ),
            "problems_attempted": len({r.topic for r in problem_rows}),
        },
        "progress": progress,
        "by_area": [
            {"area": area, "mean": _round(_mean(scores)), "facets": len(scores)}
            for area, scores in sorted(by_area.items())
        ],
        "by_topic": [
            {
                "pack": pack,
                "topic": topic,
                "mean": _round(_mean(scores)),
                "facets": len(scores),
            }
            for (pack, topic), scores in sorted(by_topic.items())
        ],
        "by_qtype": [
            {"qtype": qtype, "mean": _round(_mean(by_qtype.get(qtype, []))), "n": len(by_qtype.get(qtype, []))}
            for qtype in QTYPES
            if by_qtype.get(qtype)
        ],
        "strength_distribution": distribution,
        "calibration": calibration_series,
        "teaching": teaching,
        "weakest": [
            {
                "pack": i.pack,
                "topic": i.topic,
                "subtopic": i.subtopic,
                "area": i.area,
                "strength": i.strength,
                "reps": i.reps,
                "last": i.last,
                "due": i.due,
            }
            for i in sorted(facets, key=lambda i: (i.strength, i.due))[:12]
        ],
        "thin_evidence": [
            {"pack": i.pack, "topic": i.topic, "subtopic": i.subtopic, "strength": i.strength, "due": i.due}
            for i in facets
            if i.reps == 1 and i.strength >= 4
        ],
        "uncovered_areas": sorted(all_areas - covered_areas),
        "problems": [
            {
                "pack": i.pack,
                "slug": i.label,
                "score": i.strength,
                "attempts": i.reps,
                "last": i.last,
                "due": i.due,
                "history": [{"date": d, "score": s} for d, s in i.history],
            }
            for i in items
            if i.kind == "problem"
        ],
    }
