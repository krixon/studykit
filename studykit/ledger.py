"""The append-only measurement ledger.

One JSON object per line, one line per measured item per session. Never edited,
only appended. `state.json` and `metrics.json` are both derived from this file,
so it is the single source of truth for everything the engine knows.

A row is stamped with `at`, a full local timestamp with its offset, because when
in the day something was measured is real information and cannot be recovered
later. A row is written as it is measured, so the time is always known.

Scheduling still works in whole days: `Row.date` is derived from `at`, so several
measurements of one facet in one sitting remain one piece of evidence.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .config import StudykitError, day_of, ledger_path, now, valid_at
from .packs import QTYPES, Library

SESSIONS: tuple[str, ...] = ("quiz", "practice", "review", "learn", "study", "drill")

#: Fields a caller may set. Anything derived (strength, interval, due, reps)
#: is computed by the scheduler and is not accepted here.
WRITABLE = (
    "at",
    "pack",
    "session",
    "level",
    "topic",
    "subtopic",
    "qtype",
    "qid",
    "measured",
    "predicted",
    "post",
    "taught",
    "note",
)

DERIVED = ("strength", "interval", "due", "reps", "area")

PROBLEM_PREFIX = "problem:"


@dataclass(frozen=True)
class Row:
    at: str
    pack: str
    session: str
    topic: str
    subtopic: str
    measured: int
    area: str = ""
    level: str = ""
    qtype: str | None = None
    qid: str | None = None
    predicted: int | None = None
    post: int | None = None
    taught: bool = False
    note: str = ""

    @property
    def date(self) -> str:
        """The calendar day. Every scheduling and metrics rule groups on this."""
        return day_of(self.at)

    @property
    def is_problem(self) -> bool:
        return self.topic.startswith(PROBLEM_PREFIX)

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.pack, self.topic, self.subtopic)

    def as_dict(self) -> dict:
        out = {
            "at": self.at,
            "pack": self.pack,
            "session": self.session,
            "level": self.level,
            "area": self.area,
            "topic": self.topic,
            "subtopic": self.subtopic,
            "measured": self.measured,
        }
        for name in ("qtype", "qid", "predicted", "post", "note"):
            value = getattr(self, name)
            if value not in (None, ""):
                out[name] = value
        if self.taught:
            out["taught"] = True
        return out


def _score(value, field: str, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise StudykitError(f"{where}: {field} must be a whole number 1-5, got {value!r}")
    if not 1 <= value <= 5:
        raise StudykitError(f"{where}: {field} must be 1-5, got {value}")
    return value


def validate(entry: dict, library: Library, *, default_level: str = "") -> Row:
    """Turn one caller-supplied dict into a Row, or explain why it cannot.

    Validation is where the engine's rules become mechanical: a measurement has
    to name a facet that actually exists in the pack taxonomy, and no caller can
    write a derived field.
    """
    where = f"row {entry.get('topic', '?')}/{entry.get('subtopic', '?')}"

    for name in DERIVED:
        if name in entry and name != "area":
            raise StudykitError(
                f"{where}: {name!r} is derived from the ledger and cannot be recorded directly"
            )
    unknown = set(entry) - set(WRITABLE) - {"area"}
    if unknown:
        raise StudykitError(f"{where}: unknown field(s) {', '.join(sorted(unknown))}")

    for required in ("pack", "session", "topic", "subtopic", "measured"):
        if entry.get(required) in (None, ""):
            raise StudykitError(f"{where}: missing required field {required!r}")

    at = valid_at(str(entry["at"])) if entry.get("at") else now()
    pack = library.pack(str(entry["pack"]))
    session = str(entry["session"])
    if session not in SESSIONS:
        raise StudykitError(f"{where}: unknown session {session!r}; one of {', '.join(SESSIONS)}")

    topic = str(entry["topic"])
    subtopic = str(entry["subtopic"])
    if topic.startswith(PROBLEM_PREFIX):
        slug = topic[len(PROBLEM_PREFIX) :]
        if slug not in pack.problems:
            raise StudykitError(f"{where}: {pack.name} has no problem {slug!r}")
        area = entry.get("area") or (pack.problems[slug].areas[0] if pack.problems[slug].areas else "")
        if subtopic != "overall":
            raise StudykitError(f"{where}: a problem row must use subtopic `overall`")
    else:
        if topic not in pack.topics:
            raise StudykitError(f"{where}: {pack.name} has no topic {topic!r}")
        known = pack.topics[topic].subtopics
        if subtopic != "overall" and subtopic not in known:
            raise StudykitError(
                f"{where}: {topic!r} has no subtopic {subtopic!r}. Known: {', '.join(known)}"
            )
        area = entry.get("area") or pack.topics[topic].area

    qtype = entry.get("qtype")
    if qtype is not None and qtype not in QTYPES:
        raise StudykitError(f"{where}: unknown qtype {qtype!r}; one of {', '.join(QTYPES)}")

    qid = entry.get("qid")
    if qid:
        if not any(q.id == qid for q in pack.questions):
            raise StudykitError(
                f"{where}: question id {qid!r} is not in the {pack.name} bank. "
                "Bank the question (`study bank add`) before recording it."
            )

    predicted = entry.get("predicted")
    post = entry.get("post")
    return Row(
        at=at,
        pack=pack.name,
        session=session,
        level=str(entry.get("level") or default_level),
        area=area,
        topic=topic,
        subtopic=subtopic,
        qtype=qtype,
        qid=qid,
        measured=_score(entry["measured"], "measured", where),
        predicted=None if predicted is None else _score(predicted, "predicted", where),
        post=None if post is None else _score(post, "post", where),
        taught=bool(entry.get("taught", False)),
        note=str(entry.get("note", "")),
    )


def append(rows: list[Row], path: Path | None = None) -> int:
    path = path or ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row.as_dict(), sort_keys=False) + "\n")
    return len(rows)


def read(path: Path | None = None) -> list[Row]:
    """Every row, oldest first. Ledger order is session order."""
    path = path or ledger_path()
    if not path.exists():
        return []
    rows: list[Row] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise StudykitError(f"{path}:{number}: not valid JSON ({exc})") from exc
        if not raw.get("at"):
            raise StudykitError(
                f"{path}:{number}: row has no `at` timestamp. Ledgers written before "
                "timestamps need migrating, not guessing at."
            )
        rows.append(
            Row(
                at=str(raw["at"]),
                pack=raw.get("pack", ""),
                session=raw.get("session", ""),
                level=raw.get("level", ""),
                area=raw.get("area", ""),
                topic=raw.get("topic", ""),
                subtopic=raw.get("subtopic", ""),
                qtype=raw.get("qtype"),
                qid=raw.get("qid"),
                measured=int(raw["measured"]),
                predicted=raw.get("predicted"),
                post=raw.get("post"),
                taught=bool(raw.get("taught", False)),
                note=raw.get("note", ""),
            )
        )
    rows.sort(key=lambda r: r.at)
    return rows


def question_exposure(rows: list[Row]) -> dict[str, dict]:
    """How often each banked question has been shown, and when it last was.

    Exposure is derived from the ledger rather than stored on the question, so
    the shipped packs stay pristine and portable.
    """
    out: dict[str, dict] = {}
    for row in rows:
        if not row.qid:
            continue
        record = out.setdefault(row.qid, {"reps": 0, "last": "", "scores": []})
        record["reps"] += 1
        record["last"] = max(record["last"], row.date)
        record["scores"].append(row.measured)
    return out
