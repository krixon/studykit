"""Queue ordering, question drawing and session composition.

The user says how long they have; this module decides what they work on,
deterministically, so the same inputs always compose the same session.
"""

from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass

from . import balance
from .config import StudykitError, today
from .ledger import PROBLEM_PREFIX, Row, question_exposure
from .packs import QTYPES, Library, Question
from .schedule import Item, compute_items, live_items

#: Rough minutes per quiz question, including the follow-up a weak answer earns.
MINUTES_PER_QUESTION = 1.8
RECORDING_RESERVE = 2
#: Minutes held back for the quiz set before other blocks may claim any budget.
#: The quiz set is the only block with breadth: a targeted block measures one
#: facet, a quiz set measures six, so without it the due queue never drains.
QUIZ_FLOOR = 10
#: Below this there is no quiz set worth running, so the budget goes elsewhere.
MIN_QUIZ_FLOOR = 4
#: Below this, a full problem cannot be run honestly, so the budget goes to retrieval.
PROBLEM_FLOOR = 30
#: Every block cost here is an estimate, so packing to the exact minute is false
#: precision. A session may run this far over what was asked; `plan` reports it.
OVERRUN_FRACTION = 0.1
MIN_OVERRUN = 2
#: Every Nth slot at the head of the queue is held for a never-measured facet.
#: Priority bands alone starve discovery: any non-empty backlog precedes every
#: unmeasured facet, so the weakness found in the first few sessions is the only
#: weakness that is ever worked on.
EXPLORATION_EVERY = 3

#: Measurements, across all types, before the ledger outweighs the level's prior.
#: Small enough that a few sessions move the mix, large enough that three lucky
#: answers do not.
PRIOR_STRENGTH = 50
#: Stands in for a type with no measurements, so an untested type is treated as
#: neither mastered nor urgent.
NEUTRAL_MEAN = 3.0
MAX_SCORE = 5

BUDGET_WORDS = {
    "quick": 10,
    "short": 10,
    "half day": 180,
    "halfday": 180,
    "full day": 360,
    "fullday": 360,
    "all day": 360,
    "open": 60,
    "open-ended": 60,
}

#: `minutes` is the planning cost.
TECHNIQUES: list[dict] = [
    {"name": "quiz-set", "targets": "retrieval, discrimination", "minutes": 12},
    {"name": "contrasting-cases", "targets": "conflation", "minutes": 10},
    {"name": "estimation-drill", "targets": "quantification", "minutes": 5},
    {"name": "diagnostic-inversion", "targets": "symptom to cause", "minutes": 10},
    {"name": "teach-back", "targets": "illusion of explanatory depth", "minutes": 12},
    {"name": "faded-worked-example", "targets": "rebuilding a weak facet", "minutes": 25},
    {"name": "learn", "targets": "building a facet that is not there yet", "minutes": 30},
    {"name": "full-problem", "targets": "far transfer, integration", "minutes": 50},
    {"name": "cold-re-attempt", "targets": "durability", "minutes": 45},
    {"name": "card-writing", "targets": "consolidation", "minutes": 20},
]

TECHNIQUE_BY_NAME = {t["name"]: t for t in TECHNIQUES}


def parse_budget(text: str | None, default: str = "25m") -> int:
    """Minutes from whatever the user said. `None` falls back to the profile."""
    raw = (text or default).strip().lower()
    if raw in BUDGET_WORDS:
        return BUDGET_WORDS[raw]
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(m|min|mins|minutes|h|hr|hrs|hours)?", raw)
    if not match:
        raise StudykitError(
            f"Cannot read a budget from {text!r}. Try `15m`, `1h`, `half day`, or a plain number of minutes."
        )
    amount = float(match.group(1))
    unit = match.group(2) or "m"
    minutes = amount * 60 if unit.startswith("h") else amount
    if minutes < 5:
        raise StudykitError("A session under five minutes cannot measure anything useful.")
    return int(minutes)


@dataclass
class QueueEntry:
    reason: str  # overdue | unmeasured | due | fresh
    priority: int
    pack: str
    topic: str
    subtopic: str
    area: str = ""
    strength: int | None = None
    reps: int = 0
    due: str = ""
    overdue_days: int = 0

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.pack, self.topic, self.subtopic)

    def as_dict(self) -> dict:
        return {
            "reason": self.reason,
            "pack": self.pack,
            "topic": self.topic,
            "subtopic": self.subtopic,
            "area": self.area,
            "strength": self.strength,
            "reps": self.reps,
            "due": self.due,
            "overdue_days": self.overdue_days,
        }


def build_queue(library: Library, rows: list[Row], level: str, as_of: str | None = None) -> list[QueueEntry]:
    """Ordered work list.

    Overdue beats due-today, and within a band staleness leads. Weakness is not
    ranked on again here because `schedule` has already priced it into the due
    date, resetting a 1-2 to a one-day interval; ranking on it twice is what lets
    a bad score buy its own topic repeat airtime. Discovery is woven into the
    head by `_weave_unmeasured` rather than queued behind the backlog.
    """
    as_of = as_of or today()
    items = live_items(compute_items(rows))
    measured = {(i.pack, i.topic, i.subtopic) for i in items}
    entries: list[QueueEntry] = []

    in_scope_topics = {(t.pack, t.id): t for t in library.topics(level)}

    for item in items:
        if item.kind == "problem":
            continue
        if (item.pack, item.topic) not in in_scope_topics:
            continue
        overdue = item.overdue_days(as_of)
        if overdue > 0:
            reason, priority = "overdue", 0
        elif overdue == 0:
            reason, priority = "due", 2
        else:
            reason, priority = "fresh", 3
        entries.append(
            QueueEntry(
                reason=reason,
                priority=priority,
                pack=item.pack,
                topic=item.topic,
                subtopic=item.subtopic,
                area=item.area,
                strength=item.strength,
                reps=item.reps,
                due=item.due,
                overdue_days=max(overdue, 0),
            )
        )

    for (pack_name, topic_id), topic in in_scope_topics.items():
        for subtopic in topic.subtopics:
            if (pack_name, topic_id, subtopic) in measured:
                continue
            entries.append(
                QueueEntry(
                    reason="unmeasured",
                    priority=1,
                    pack=pack_name,
                    topic=topic_id,
                    subtopic=subtopic,
                    area=topic.area,
                )
            )

    entries.sort(
        key=lambda e: (
            e.priority,
            -(e.overdue_days),
            e.strength if e.strength is not None else 0,
            e.topic,
            e.subtopic,
        )
    )
    return _weave_unmeasured(_spread_topics(entries))


def _weave_unmeasured(entries: list[QueueEntry]) -> list[QueueEntry]:
    """Hold every `EXPLORATION_EVERY`th slot for a facet never measured.

    Degrades at both ends: with nothing unmeasured this returns the review order
    untouched, and with nothing to review it returns pure discovery.
    """
    unmeasured = [e for e in entries if e.reason == "unmeasured"]
    review = [e for e in entries if e.reason != "unmeasured"]
    if not unmeasured or not review:
        return entries
    out: list[QueueEntry] = []
    while unmeasured or review:
        pool = unmeasured if (len(out) + 1) % EXPLORATION_EVERY == 0 and unmeasured else review
        out.append((pool or unmeasured).pop(0))
    return out


def _spread_topics(entries: list[QueueEntry]) -> list[QueueEntry]:
    """Rotate through topics within each priority band, keeping the band order.

    Without this, a queue of never-measured facets comes out grouped by topic,
    and a session drawn from the head of it quizzes two topics rather than eight.
    """
    out: list[QueueEntry] = []
    for priority in sorted({e.priority for e in entries}):
        band = [e for e in entries if e.priority == priority]
        by_topic: dict[tuple[str, str], list[QueueEntry]] = {}
        for entry in band:
            by_topic.setdefault((entry.pack, entry.topic), []).append(entry)
        # topics enter the rotation in the order their strongest claim appeared
        order = list(by_topic)
        while order:
            for key in list(order):
                bucket = by_topic[key]
                out.append(bucket.pop(0))
                if not bucket:
                    order.remove(key)
    return out


def _question_rank(question: Question, exposure: dict, as_of: str, level: str = "") -> tuple:
    """Least-seen first, then the level it was written for, then the id.

    The level term is a preference, not a filter. A question tagged elsewhere is
    reachable once the ones written for this level have been seen, which is what
    keeps a graduate off a staff stem while the graduate supply lasts.
    """
    record = exposure.get(question.id)
    reps = record["reps"] if record else 0
    last = record["last"] if record else ""
    off_level = 0 if not level or level in question.levels else 1
    return (reps, last, off_level, question.id)


def qtype_weights(level: str, rows: list[Row]) -> dict[str, float]:
    """The share of a draw each question type should take, summing to 1.

    The level's target mix is the prior; measured means move it, so a type
    answered well loses share and a weak one gains it. `PRIOR_STRENGTH` decides
    how much evidence that takes, which is why an early session looks like the
    level's defaults and a later one looks like the person.
    """
    prior = {qtype: balance.TARGETS[level][qtype] / 100 for qtype in QTYPES}
    scores: dict[str, list[int]] = {}
    for row in rows:
        if row.qtype in prior:
            scores.setdefault(row.qtype, []).append(row.measured)
    total = sum(len(v) for v in scores.values())
    if not total:
        return prior

    # Weighting the prior by need keeps a 5%-target type from taking over a draw
    # on the strength of one bad answer.
    need = {
        qtype: max(
            MAX_SCORE - (sum(scores[qtype]) / len(scores[qtype]) if scores.get(qtype) else NEUTRAL_MEAN),
            0.0,
        )
        for qtype in QTYPES
    }
    weighted = {qtype: prior[qtype] * need[qtype] for qtype in QTYPES}
    scale = sum(weighted.values())
    if not scale:
        return prior
    evidence = total / (total + PRIOR_STRENGTH)
    return {
        qtype: (1 - evidence) * prior[qtype] + evidence * weighted[qtype] / scale
        for qtype in QTYPES
    }


def _wanted_qtype(counts: dict[str, int], drawn: int, weights: dict[str, float], available: set) -> str:
    """Whichever available type is furthest behind its share of the draw."""
    return max(
        available,
        key=lambda qtype: (
            weights[qtype] * (drawn + 1) - counts.get(qtype, 0),
            weights[qtype],
            qtype,
        ),
    )


def draw_questions(
    library: Library,
    rows: list[Row],
    level: str,
    targets: list[QueueEntry],
    count: int,
    *,
    as_of: str | None = None,
    seed: int | None = None,
    exclude: set[str] | None = None,
) -> tuple[list[Question], list[QueueEntry]]:
    """Pick `count` questions across the target facets, plus the facets with none.

    The facet decides what is asked about, `qtype_weights` decides what kind of
    question asks it, and exposure decides which one within that kind. Nothing
    here excludes a question for being tagged below the level: a graduate recall
    question is reachable at staff, it just has to win a slot on the mix rather
    than on never having been seen.

    Returns the drawn questions and the targets that had no question left to
    draw, which the caller turns into an instruction to author some.
    """
    as_of = as_of or today()
    exposure = question_exposure(rows)
    shown_today = {r.qid for r in rows if r.date == as_of and r.qid}
    used: set[str] = set(exclude or ()) | shown_today
    weights = qtype_weights(level, rows)

    by_facet: dict[tuple[str, str, str], list[Question]] = {}
    for question in library.questions(level):
        by_facet.setdefault((question.pack, question.topic, question.subtopic), []).append(question)

    rng = random.Random(seed if seed is not None else f"{as_of}:{len(rows)}")
    picked: list[Question] = []
    counts: dict[str, int] = {}
    starved: list[QueueEntry] = []
    rounds = 0
    remaining = list(targets)

    while len(picked) < count and remaining and rounds < 6:
        rounds += 1
        next_round: list[QueueEntry] = []
        for entry in remaining:
            if len(picked) >= count:
                next_round.append(entry)
                continue
            pool = [
                q
                for q in by_facet.get((entry.pack, entry.topic, entry.subtopic), [])
                if q.id not in used
            ]
            if not pool:
                if rounds == 1:
                    starved.append(entry)
                continue
            wanted = _wanted_qtype(counts, len(picked), weights, {q.qtype for q in pool})
            candidates = [q for q in pool if q.qtype == wanted]
            candidates.sort(key=lambda q: _question_rank(q, exposure, as_of, level))
            best_rank = _question_rank(candidates[0], exposure, as_of, level)[:3]
            tied = [
                q for q in candidates if _question_rank(q, exposure, as_of, level)[:3] == best_rank
            ]
            choice = rng.choice(tied)
            used.add(choice.id)
            counts[wanted] = counts.get(wanted, 0) + 1
            picked.append(choice)
            next_round.append(entry)
        remaining = next_round

    return interleave(picked, rng), starved


def interleave(questions: list[Question], rng: random.Random) -> list[Question]:
    """Blocked practice inflates in-session performance and depresses retention."""
    remaining = list(questions)
    rng.shuffle(remaining)
    out: list[Question] = []
    while remaining:
        candidate = next(
            (q for q in remaining if not out or q.topic != out[-1].topic),
            remaining[0],
        )
        remaining.remove(candidate)
        out.append(candidate)
    return out


def _weakest(entries: list[QueueEntry]) -> QueueEntry | None:
    scored = [e for e in entries if e.strength is not None]
    return min(scored, key=lambda e: (e.strength, -e.overdue_days), default=None)


def _quiz_floor(queue: list[QueueEntry]) -> int:
    """Only what the queue can actually fill. A drained queue reserves nothing."""
    servable = [e for e in queue if e.reason in {"overdue", "due", "unmeasured"}]
    if not servable:
        return 0
    return min(QUIZ_FLOOR, int(len(servable) * MINUTES_PER_QUESTION) + 2)


def _priority_split(candidates: list[dict]) -> tuple[list[dict], list[dict]]:
    """The top diagnosis and its cheaper alternatives; everything else."""
    if not candidates:
        return [], []
    alt = candidates[0].get("alt")
    head = [b for b in candidates if b.get("alt") == alt] if alt else candidates[:1]
    return head, [b for b in candidates if not any(b is h for h in head)]


def _last_post(rows: list[Row]) -> dict[tuple[str, str, str], int]:
    """The most recent post-teaching score per facet."""
    latest: dict[tuple[str, str, str], tuple[str, int]] = {}
    for row in rows:
        if row.post is None:
            continue
        seen = latest.get(row.key)
        if seen is None or row.at >= seen[0]:
            latest[row.key] = (row.at, row.post)
    return {key: post for key, (_, post) in latest.items()}


def qtype_means(rows: list[Row]) -> dict[str, float]:
    buckets: dict[str, list[int]] = {}
    for row in rows:
        if row.qtype:
            buckets.setdefault(row.qtype, []).append(row.measured)
    return {k: sum(v) / len(v) for k, v in buckets.items() if v}


def choose_problem(
    library: Library,
    rows: list[Row],
    level: str,
    as_of: str | None = None,
    max_minutes: int | None = None,
    exclude: set[str] | None = None,
) -> dict | None:
    """A due re-attempt beats a new problem; otherwise the least-covered area.

    `max_minutes` keeps the composer honest: a 60 minute problem inside a 45
    minute session either overruns or gets cut short, and neither measures
    integration.
    """
    as_of = as_of or today()
    taken = exclude or set()
    fits = lambda p: (max_minutes is None or p.minutes <= max_minutes) and p.slug not in taken
    items = {i.label: i for i in compute_items(rows) if i.kind == "problem"}
    due = [i for i in items.values() if i.overdue_days(as_of) >= 0]
    due.sort(key=lambda i: (-i.overdue_days(as_of), i.strength))
    for item in due:
        try:
            pack, problem = library.find_problem(item.label, item.pack)
        except StudykitError:
            continue
        if level not in problem.levels or not fits(problem):
            continue
        return {
            "pack": pack.name,
            "slug": problem.slug,
            "title": problem.title,
            "minutes": problem.minutes,
            "mode": "cold-re-attempt",
            "previous_score": item.strength,
            "last_attempted": item.last,
        }

    unattempted = [p for p in library.problems(level) if p.slug not in items and fits(p)]
    if not unattempted:
        return None
    weak_areas = {e.area for e in build_queue(library, rows, level, as_of)[:12]}
    unattempted.sort(key=lambda p: (0 if set(p.areas) & weak_areas else 1, p.minutes, p.slug))
    chosen = unattempted[0]
    return {
        "pack": chosen.pack,
        "slug": chosen.slug,
        "title": chosen.title,
        "minutes": chosen.minutes,
        "mode": "first-attempt",
        "previous_score": None,
        "last_attempted": None,
    }


def compose(
    library: Library,
    rows: list[Row],
    level: str,
    minutes: int,
    *,
    as_of: str | None = None,
    seed: int | None = None,
    allow_problem: bool = True,
) -> dict:
    """Fill the box. Hardest-first, interleaved, with the last two minutes reserved."""
    as_of = as_of or today()
    queue = build_queue(library, rows, level, as_of)
    overrun = max(MIN_OVERRUN, math.ceil(minutes * OVERRUN_FRACTION))
    budget = max(minutes + overrun - RECORDING_RESERVE, 5)
    floor = _quiz_floor(queue)

    candidates = _targeted_blocks(library, rows, level, queue)
    targeted: list[dict] = []
    skipped: list[dict] = []
    satisfied: set[str] = set()
    max_targeted = 1 if minutes < 30 else 2 if minutes < 60 else 3

    def claim_targeted(pool: list[dict], reserve: int) -> None:
        nonlocal budget
        for block in pool:
            alt = block.get("alt")
            if alt is not None and alt in satisfied:
                continue
            if len(targeted) >= max_targeted:
                continue
            # `skipped` carries only what the budget could not hold, so the note
            # it drives never blames the budget for a full session.
            if block["minutes"] > max(budget - reserve, 0):
                skipped.append(block)
                continue
            block.pop("alt", None)
            targeted.append(block)
            budget -= block["minutes"]
            if alt is not None:
                satisfied.add(alt)

    # The strongest diagnosis outranks far transfer and claims first, but not at
    # the cost of the quiz floor: a session that rebuilds one facet and asks three
    # questions cannot find the gap it should rebuild next.
    head, tail = _priority_split(candidates)
    claim_targeted(head, floor)

    # A half day spent entirely on retrieval measures the cheap thing.
    max_problems = 0 if not allow_problem else 1 if minutes < 120 else 2 if minutes < 300 else 3
    problem_blocks: list[dict] = []
    chosen_slugs: set[str] = set()
    while len(problem_blocks) < max_problems and budget - floor >= PROBLEM_FLOOR:
        problem = choose_problem(
            library, rows, level, as_of, max_minutes=budget - floor, exclude=chosen_slugs
        )
        if problem is None:
            break
        chosen_slugs.add(problem["slug"])
        cost = min(problem["minutes"], budget)
        problem_blocks.append(
            {
                "type": "cold-re-attempt" if problem["mode"] == "cold-re-attempt" else "full-problem",
                "minutes": cost,
                "targets": TECHNIQUE_BY_NAME["full-problem"]["targets"],
                "problem": problem,
                "instruction": (
                    "Run with the `practice` protocol. Show the candidate-facing prompt only "
                    f"(`./study problem {problem['slug']}`); hold the interviewer notes "
                    f"(`./study problem {problem['slug']} --notes`) until the attempt is over."
                ),
            }
        )
        budget -= cost

    claim_targeted(tail, floor)

    blocks: list[dict] = []
    if floor and budget >= MIN_QUIZ_FLOOR:
        ceiling = 20 if minutes >= 120 else 14
        count = max(2, min(ceiling, int(budget / MINUTES_PER_QUESTION)))
        if problem_blocks:
            count = min(count, 8)
        questions, starved = draw_questions(
            library, rows, level, queue[: count * 2], count, as_of=as_of, seed=seed
        )
        cost = min(int(len(questions) * MINUTES_PER_QUESTION) + 2, budget)
        blocks.append(
            {
                "type": "quiz-set",
                "minutes": cost,
                "targets": TECHNIQUE_BY_NAME["quiz-set"]["targets"],
                "questions": [q.as_dict() for q in questions],
                "author_for": [e.as_dict() for e in starved],
                "instruction": (
                    "Run with the `quiz` protocol: one at a time, take a predicted confidence "
                    "if offered freely, score cold before teaching anything, then follow the ladder. "
                    "Never say which topic a question is from."
                ),
            }
        )
        budget -= cost

    blocks.extend(targeted)
    blocks.extend(problem_blocks)

    notes: list[str] = []

    def focus_key(block: dict) -> tuple[str, str, str] | None:
        focus = block.get("focus")
        return None if focus is None else (focus["pack"], focus["topic"], focus["subtopic"])

    worked = {focus_key(b) for b in targeted}
    dropped = next(
        (
            b
            for b in skipped
            if focus_key(b) is not None
            and focus_key(b) not in worked
            and b.get("alt") not in satisfied
        ),
        None,
    )
    if dropped is not None:
        focus = dropped["focus"]
        notes.append(
            f"{focus['topic']}/{focus['subtopic']} is at strength {focus['strength']}, and the "
            f"{dropped['minutes']} minutes of {dropped['type']} it needs do not fit this budget. "
            f"The quiz set will measure the same gap again. Plan a longer session for it."
        )

    # A long budget can outrun the queue and the problem bank.
    if budget >= 20 and not any(b["type"] == "card-writing" for b in blocks):
        weakest = _weakest(queue) or (queue[0] if queue else None)
        if weakest is not None:
            cost = min(budget, TECHNIQUE_BY_NAME["card-writing"]["minutes"])
            blocks.append(
                {
                    "type": "card-writing",
                    "minutes": cost,
                    "targets": TECHNIQUE_BY_NAME["card-writing"]["targets"],
                    "focus": weakest.as_dict(),
                    "card": f"./study card {weakest.topic} --pack {weakest.pack}",
                    "instruction": (
                        f"Consolidate {weakest.topic}. Read the card, then have the user rewrite the "
                        "weakest section from memory and compare. Where the card turns out to be thin, "
                        "extend it - a question you cannot answer from the card is a card problem."
                    ),
                }
            )
            budget -= cost
    if budget >= 15:
        exhausted = []
        if max_problems and len(problem_blocks) < max_problems:
            exhausted.append("no further problems available at this level")
        if len(targeted) < max_targeted:
            exhausted.append("no further diagnosis-driven blocks are triggered")
        reason = "; ".join(exhausted) or "the due queue is shorter than the budget"
        notes.append(
            f"{budget} minutes unallocated: {reason}. Take the time back, or spend it on "
            "an out-of-scope topic deliberately."
        )

    pack_names = sorted({b.get("problem", {}).get("pack", "") for b in blocks} - {""}) or list(
        library.enabled_names
    )
    calibration = {}
    for name in library.enabled_names:
        brief = library.pack(name).calibration_for(level)
        if brief:
            calibration[name] = brief

    return {
        "date": as_of,
        "level": level,
        "budget_minutes": minutes,
        "planned_minutes": sum(b["minutes"] for b in blocks) + RECORDING_RESERVE,
        "recording_reserve": RECORDING_RESERVE,
        "overrun_allowance": overrun,
        "calibration": calibration,
        "blocks": blocks,
        "queue_preview": [e.as_dict() for e in queue[:10]],
        "notes": notes,
        "unused_minutes": max(budget, 0),
        "packs": pack_names,
    }


def _targeted_blocks(
    library: Library, rows: list[Row], level: str, queue: list[QueueEntry]
) -> list[dict]:
    """Blocks that fire on a specific diagnosis, strongest signal first."""
    out: list[dict] = []
    weak = [e for e in queue if e.strength is not None and e.strength <= 2]
    conflated = [e for e in weak if e.strength == 2]
    means = qtype_means(rows)
    predicted_gap = _calibration_gap(rows)
    last_post = _last_post(rows)
    claimed: set[tuple[str, str, str]] = set()

    def card_ref(entry: QueueEntry) -> str:
        return f"./study card {entry.topic} --pack {entry.pack}"

    def take(pool: list[QueueEntry]) -> QueueEntry | None:
        """The weakest unclaimed facet in the pool, so two blocks never target one facet."""
        entry = _weakest([e for e in pool if e.key not in claimed])
        if entry is not None:
            claimed.add(entry.key)
        return entry

    # Retrieval practice needs something to retrieve. A facet that has never
    # survived a rep, or whose last re-test after teaching came back weak, has
    # nothing to draw on, and quizzing it again measures the same gap.
    empty = [e for e in weak if e.reps <= 1 or last_post.get(e.key, 5) <= 2]
    taught = take(empty)
    if taught is not None:
        entry = taught
        out.append(
            {
                "type": "learn",
                "alt": f"teach:{entry.key}",
                "minutes": TECHNIQUE_BY_NAME["learn"]["minutes"],
                "targets": TECHNIQUE_BY_NAME["learn"]["targets"],
                "focus": entry.as_dict(),
                "card": card_ref(entry),
                "instruction": (
                    f"Run with the `learn` protocol on {entry.topic}/{entry.subtopic}. Cold probe "
                    "the facet first, teach only what the probe exposes, then re-test on variants "
                    "spaced from the teaching. Record the cold score as `measured` and the variant "
                    "as `post`."
                ),
            }
        )
    def faded_block(entry: QueueEntry, alt: str | None = None) -> dict:
        return {
            "type": "faded-worked-example",
            "alt": alt,
            "minutes": TECHNIQUE_BY_NAME["faded-worked-example"]["minutes"],
            "targets": TECHNIQUE_BY_NAME["faded-worked-example"]["targets"],
            "focus": entry.as_dict(),
            "card": card_ref(entry),
            "instruction": (
                "Work a complete concrete example out loud with the numbers, then re-run a "
                "variant with parts removed for the user to fill. Re-test on a variant, not "
                "the same case."
            ),
        }

    # The same facet at a lower price, for a budget that cannot hold the learn
    # block. Only one of the pair is ever taken.
    if taught is not None:
        out.append(faded_block(taught, alt=f"teach:{taught.key}"))
    entry = take(weak)
    if entry is not None:
        out.append(faded_block(entry))
    entry = take(conflated)
    if entry is not None:
        out.append(
            {
                "type": "contrasting-cases",
                "minutes": TECHNIQUE_BY_NAME["contrasting-cases"]["minutes"],
                "targets": TECHNIQUE_BY_NAME["contrasting-cases"]["targets"],
                "focus": entry.as_dict(),
                "card": card_ref(entry),
                "instruction": (
                    "Present two or three cases that share surface features and differ in deep "
                    "structure. Ask what separates them before explaining anything."
                ),
            }
        )
    if means.get("numeric") is not None and means["numeric"] < min(
        (v for k, v in means.items() if k != "numeric"), default=5
    ):
        out.append(
            {
                "type": "estimation-drill",
                "minutes": TECHNIQUE_BY_NAME["estimation-drill"]["minutes"],
                "targets": TECHNIQUE_BY_NAME["estimation-drill"]["targets"],
                "instruction": (
                    "Three back-of-envelope estimates, out loud, with the arithmetic made explicit. "
                    "Numeric scores are lagging the other question types."
                ),
            }
        )
    if predicted_gap is not None and predicted_gap > 0.5:
        out.append(
            {
                "type": "teach-back",
                "minutes": TECHNIQUE_BY_NAME["teach-back"]["minutes"],
                "targets": TECHNIQUE_BY_NAME["teach-back"]["targets"],
                "instruction": (
                    f"Confidence is running {predicted_gap:.1f} above measured. Pick a facet rated "
                    "high and have the user explain it end to end to a competent engineer who has "
                    "not met it. Stop them where the mechanism goes vague."
                ),
            }
        )
    entry = take([e for e in queue if e.strength == 3])
    if entry is not None:
        out.append(
            {
                "type": "diagnostic-inversion",
                "minutes": TECHNIQUE_BY_NAME["diagnostic-inversion"]["minutes"],
                "targets": TECHNIQUE_BY_NAME["diagnostic-inversion"]["targets"],
                "focus": entry.as_dict(),
                "card": card_ref(entry),
                "instruction": "Give symptoms only and ask for the mechanism. Reverse the direction of reasoning.",
            }
        )
    no_card = [
        e
        for e in queue
        if e.reason == "unmeasured"
        and library.find_topic(e.topic, e.pack)[1].card is None
    ]
    if no_card:
        entry = no_card[0]
        out.append(
            {
                "type": "card-writing",
                "minutes": TECHNIQUE_BY_NAME["card-writing"]["minutes"],
                "targets": TECHNIQUE_BY_NAME["card-writing"]["targets"],
                "focus": entry.as_dict(),
                "instruction": f"No card exists for {entry.topic}. Write one from the template before quizzing it.",
            }
        )
    return out


def recommend(library: Library, rows: list[Row], level: str, as_of: str | None = None) -> dict:
    """One suggested next session."""
    as_of = as_of or today()
    queue = build_queue(library, rows, level, as_of)
    weak = [e for e in queue if e.strength is not None and e.strength <= 2]
    overdue = [e for e in queue if e.reason == "overdue"]
    unmeasured = [e for e in queue if e.reason == "unmeasured"]
    strong = [e for e in queue if e.strength is not None and e.strength >= 4]

    def out(minutes: int, headline: str) -> dict:
        return {
            "budget_minutes": minutes,
            "headline": headline,
            "command": f"./study plan {minutes}m",
        }

    if not rows:
        return out(15, "first session - a mixed set to find the floor, no teaching until it is scored")
    if weak:
        entry = weak[0]
        return out(
            25,
            f"worked example on {entry.topic}/{entry.subtopic} (strength {entry.strength}), "
            "then a mixed set with a variant re-test",
        )
    if len(overdue) >= 6:
        return out(25, f"{len(overdue)} facets overdue - a mixed set, weakest first")
    if unmeasured:
        return out(
            15,
            f"{len(unmeasured)} facets never measured - quiz the unknown before revisiting the known",
        )
    if len(strong) >= 4 and choose_problem(library, rows, level, as_of):
        return out(60, "enough facets at 4+ to be worth a full problem - integration is the untested part")
    if overdue:
        return out(15, f"{len(overdue)} facets overdue - a short mixed set clears it")
    return out(10, "nothing due; a short interleaved set keeps the intervals honest")


def _calibration_gap(rows: list[Row]) -> float | None:
    pairs = [(r.predicted, r.measured) for r in rows if r.predicted is not None]
    if not pairs:
        return None
    return sum(p - m for p, m in pairs) / len(pairs)
