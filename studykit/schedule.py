"""Scheduling: the only implementation of the interval algorithm."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .config import add_days, days_between, today
from .ledger import PROBLEM_PREFIX, Row
from .packs import Library

MULTIPLIER: dict[int, float] = {3: 1.6, 4: 2.2, 5: 3.0}
REPS_CAP: dict[int, int] = {1: 3, 2: 10}
CEILING_DAYS = 120
FIRST_INTERVAL = 2


def round_half_up(value: float) -> int:
    return math.floor(value + 0.5)


@dataclass
class Item:
    pack: str
    topic: str
    subtopic: str
    area: str = ""
    kind: str = "facet"  # "facet" or "problem"
    strength: int = 0
    reps: int = 0
    last: str = ""
    interval: int = FIRST_INTERVAL
    due: str = ""
    history: list[tuple[str, int]] = field(default_factory=list)

    @property
    def label(self) -> str:
        if self.kind == "problem":
            return self.topic[len(PROBLEM_PREFIX) :]
        return f"{self.topic}/{self.subtopic}"

    def overdue_days(self, as_of: str) -> int:
        return days_between(self.due, as_of) if self.due else 0

    def as_dict(self, as_of: str) -> dict:
        return {
            "kind": self.kind,
            "pack": self.pack,
            "area": self.area,
            "topic": self.topic,
            "subtopic": self.subtopic,
            "label": self.label,
            "strength": self.strength,
            "reps": self.reps,
            "last": self.last,
            "interval": self.interval,
            "due": self.due,
            "overdue_days": self.overdue_days(as_of),
        }


def next_interval(previous: int, strength: int, reps: int, *, is_problem: bool) -> int:
    """One step of the interval function. Pure, so the tests can pin it."""
    if strength <= 2:
        interval = 1
    else:
        interval = round_half_up(previous * MULTIPLIER[strength])
        if strength == 3:
            interval = max(interval, 2)
    if not is_problem:
        interval = min(interval, REPS_CAP.get(reps, CEILING_DAYS))
    return min(interval, CEILING_DAYS)


def compute_items(rows: list[Row]) -> list[Item]:
    """Fold the ledger into current state, oldest measurement first."""
    sessions: dict[tuple[str, str, str], dict[str, list[int]]] = {}
    meta: dict[tuple[str, str, str], str] = {}
    for row in rows:
        by_date = sessions.setdefault(row.key, {})
        by_date.setdefault(row.date, []).append(row.measured)
        meta[row.key] = row.area or meta.get(row.key, "")

    items: list[Item] = []
    for key, by_date in sessions.items():
        pack, topic, subtopic = key
        item = Item(pack=pack, topic=topic, subtopic=subtopic, area=meta.get(key, ""))
        item.kind = "problem" if topic.startswith(PROBLEM_PREFIX) else "facet"
        interval = FIRST_INTERVAL
        for date in sorted(by_date):
            scores = by_date[date]
            strength = round_half_up(sum(scores) / len(scores))
            item.reps += 1
            item.strength = strength
            item.last = date
            interval = next_interval(interval, strength, item.reps, is_problem=item.kind == "problem")
            item.history.append((date, strength))
        item.interval = interval
        item.due = add_days(item.last, interval)
        items.append(item)
    return items


def live_items(items: list[Item]) -> list[Item]:
    """Drop `overall` rows once the same topic has any facet-level evidence.

    An `overall` score is a stand-in for a breakdown. The moment a real breakdown
    exists it stops meaning anything, and leaving it in the queue double-counts.
    """
    faceted = {
        (item.pack, item.topic) for item in items if item.subtopic != "overall"
    }
    return [
        item
        for item in items
        if item.subtopic != "overall" or (item.pack, item.topic) not in faceted
    ]


def find_gaps(library: Library, items: list[Item], level: str) -> list[dict]:
    """Facets in the taxonomy with no direct measurement at all, for this level.

    Unmeasured is not the same as overdue. An overdue facet has a known strength
    that may have decayed; an unmeasured one is simply unknown, which is usually
    the more urgent condition.
    """
    measured = {(item.pack, item.topic, item.subtopic) for item in items}
    gaps: list[dict] = []
    for pack in library.enabled:
        for topic in pack.topics.values():
            if level not in topic.levels:
                continue
            missing = [s for s in topic.subtopics if (pack.name, topic.id, s) not in measured]
            if missing:
                gaps.append(
                    {
                        "pack": pack.name,
                        "topic": topic.id,
                        "title": topic.title,
                        "area": topic.area,
                        "missing": missing,
                        "total": len(topic.subtopics),
                        "has_card": topic.card is not None,
                    }
                )
    gaps.sort(key=lambda g: (-len(g["missing"]), g["topic"]))
    return gaps


def unattempted_problems(library: Library, items: list[Item], level: str) -> list[dict]:
    attempted = {
        (item.pack, item.topic[len(PROBLEM_PREFIX) :])
        for item in items
        if item.kind == "problem"
    }
    out = []
    for problem in library.problems(level):
        if (problem.pack, problem.slug) not in attempted:
            out.append(
                {
                    "pack": problem.pack,
                    "slug": problem.slug,
                    "title": problem.title,
                    "areas": list(problem.areas),
                    "minutes": problem.minutes,
                }
            )
    return out


def build_state(library: Library, rows: list[Row], level: str, as_of: str | None = None) -> dict:
    as_of = as_of or today()
    items = live_items(compute_items(rows))
    items.sort(key=lambda i: (i.due, i.strength))
    return {
        "generated": as_of,
        "level": level,
        "packs": list(library.enabled_names),
        "items": [item.as_dict(as_of) for item in items],
        "gaps": find_gaps(library, items, level),
        "unattempted_problems": unattempted_problems(library, items, level),
    }


def topic_due(items: list[Item]) -> dict[tuple[str, str], str]:
    """A topic is due when its earliest-due facet is. Never done while one is stale."""
    out: dict[tuple[str, str], str] = {}
    for item in items:
        if item.kind != "facet":
            continue
        key = (item.pack, item.topic)
        if key not in out or item.due < out[key]:
            out[key] = item.due
    return out
