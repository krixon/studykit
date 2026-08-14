"""Bank composition, measured per level rather than per pack.

A question declares the levels it suits, so one bank holds a different drawable
pool for each level and each pool has its own target mix. A pack that reads
balanced in aggregate can still be almost all recall at graduate, which is the
drift this module exists to catch.

`senior`, `lead` and `staff` share one target: above mid the intended mix is the
same, and the calibration brief is what separates them.
"""

from __future__ import annotations

import collections

from .config import LEVELS
from .packs import QTYPES

_SENIOR_PLUS = {"recall": 10, "discrimination": 25, "judgment": 35, "diagnostic": 15, "numeric": 15}

#: Percentage of a level's drawable pool that should carry each question type.
#: Prose and warrant: docs/question-types.md.
TARGETS: dict[str, dict[str, int]] = {
    "graduate": {"recall": 40, "discrimination": 30, "judgment": 15, "diagnostic": 10, "numeric": 5},
    "mid": {"recall": 25, "discrimination": 30, "judgment": 25, "diagnostic": 10, "numeric": 10},
    "senior": _SENIOR_PLUS,
    "lead": _SENIOR_PLUS,
    "staff": _SENIOR_PLUS,
}

#: The targets are an authoring guide, not a quota, so only report a share this
#: far off it. Tight enough to catch a pool at 73% recall against 40, loose
#: enough that hitting the table to the point is not the goal.
TOLERANCE = 10

#: A subtopic with one question cannot be re-tested without repeating the stem,
#: so a pool below this per in-scope subtopic cannot sustain spacing.
MIN_PER_SUBTOPIC = 2


def pool(pack, level: str) -> list:
    return [q for q in pack.questions if level in q.levels]


def mix(questions: list) -> dict[str, int]:
    """Percentage of `questions` carrying each type, or {} if there are none."""
    if not questions:
        return {}
    counts = collections.Counter(q.qtype for q in questions)
    return {qtype: round(100 * counts[qtype] / len(questions)) for qtype in QTYPES}


def _in_scope_subtopics(pack, level: str) -> int:
    return sum(len(t.subtopics) for t in pack.topics.values() if level in t.levels)


def check(pack) -> list[str]:
    """Report where a level's pool departs from its target mix.

    Notes only. The targets guide authoring and a pack that predates them is not
    broken, so nothing here can fail `doctor`.
    """
    notes: list[str] = []
    for level in LEVELS:
        if level not in pack.levels:
            continue
        drawable = pool(pack, level)
        subtopics = _in_scope_subtopics(pack, level)
        if not drawable:
            if subtopics:
                notes.append(f"level {level!r}: no questions, {subtopics} subtopic(s) in scope")
            continue
        if subtopics and len(drawable) < MIN_PER_SUBTOPIC * subtopics:
            notes.append(
                f"level {level!r}: {len(drawable)} questions across {subtopics} in-scope "
                f"subtopic(s), below {MIN_PER_SUBTOPIC} each"
            )
        shares = mix(drawable)
        target = TARGETS[level]
        off = [
            f"{qtype} {shares[qtype]}% vs {target[qtype]}%"
            for qtype in QTYPES
            if abs(shares[qtype] - target[qtype]) > TOLERANCE
        ]
        if off:
            notes.append(f"level {level!r} mix ({len(drawable)} questions): {', '.join(off)}")
    return notes
