"""What a bank has to supply, measured per level.

A draw walks the due facets and asks each one for a question of the type the mix
wants, so the ceiling on any type is the share of facets that hold one at all. A
level's pool can be 21% judgment and still draw 37%, because a facet is revisited
across sessions; it cannot draw 35% judgment if only 7% of its facets have a
judgment question. Facet coverage is therefore the constraint, and the share of
the pool is not: `select.qtype_weights` decides the mix, so a surplus of one type
is drawn less often rather than crowding the others out.

`senior`, `lead` and `staff` share one target: above mid the intended mix is the
same, and the calibration brief is what separates them.
"""

from __future__ import annotations

from .config import LEVELS
from .packs import QTYPES

_SENIOR_PLUS = {"recall": 10, "discrimination": 25, "judgment": 35, "diagnostic": 15, "numeric": 15}

#: Percentage of a level's draw that should carry each question type.
#: Prose and warrant: docs/question-types.md.
TARGETS: dict[str, dict[str, int]] = {
    "graduate": {"recall": 40, "discrimination": 30, "judgment": 15, "diagnostic": 10, "numeric": 5},
    "mid": {"recall": 25, "discrimination": 30, "judgment": 25, "diagnostic": 10, "numeric": 10},
    "senior": _SENIOR_PLUS,
    "lead": _SENIOR_PLUS,
    "staff": _SENIOR_PLUS,
}

#: Coverage this far below a target makes it unreachable by enough to be worth
#: saying. A facet count a point or two short is not an authoring instruction.
MIN_COVERAGE_RATIO = 0.8

#: A subtopic with one question cannot be re-tested without repeating the stem,
#: so a pool below this per in-scope subtopic cannot sustain spacing.
MIN_PER_SUBTOPIC = 2


def facets(pack, level: str) -> set[tuple[str, str]]:
    """Every in-scope facet at `level`, whether or not it has a question."""
    return {
        (topic.id, subtopic)
        for topic in pack.topics.values()
        if level in topic.levels
        for subtopic in topic.subtopics
    }


def pool(pack, level: str) -> list:
    return [q for q in pack.questions if level in q.levels]


def facet_coverage(pack, level: str) -> dict[str, float]:
    """Percentage of the level's facets holding at least one question of each type."""
    in_scope = facets(pack, level)
    if not in_scope:
        return {}
    covered: dict[str, set] = {qtype: set() for qtype in QTYPES}
    for question in pool(pack, level):
        key = (question.topic, question.subtopic)
        if key in in_scope:
            covered[question.qtype].add(key)
    return {qtype: 100 * len(covered[qtype]) / len(in_scope) for qtype in QTYPES}


def check(pack) -> list[str]:
    """Report where a level cannot supply the mix its draw will ask for.

    Notes only. The targets guide authoring and a pack that predates them is not
    broken, so nothing here can fail `doctor`.
    """
    notes: list[str] = []
    for level in LEVELS:
        if level not in pack.levels:
            continue
        in_scope = facets(pack, level)
        drawable = pool(pack, level)
        if not drawable:
            if in_scope:
                notes.append(f"level {level!r}: no questions, {len(in_scope)} facet(s) in scope")
            continue
        if in_scope and len(drawable) < MIN_PER_SUBTOPIC * len(in_scope):
            notes.append(
                f"level {level!r}: {len(drawable)} questions across {len(in_scope)} in-scope "
                f"facet(s), below {MIN_PER_SUBTOPIC} each"
            )
        coverage = facet_coverage(pack, level)
        target = TARGETS[level]
        short = [
            f"{qtype} in {round(coverage[qtype])}% of facets, mix wants {target[qtype]}%"
            for qtype in QTYPES
            if coverage.get(qtype, 0) < target[qtype] * MIN_COVERAGE_RATIO
        ]
        if short:
            notes.append(f"level {level!r} cannot supply its mix: {'; '.join(short)}")
    return notes
