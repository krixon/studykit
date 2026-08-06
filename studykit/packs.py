"""Loading packs: taxonomy, cards, question banks and problems.

A pack is content only. It declares what there is to learn; the engine owns
scheduling and scoring. Packs are never written to during a session - questions
generated mid-session land in the user's bank overlay under the data directory.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .config import LEVELS, StudykitError, bank_dir, check_level, packs_dir

QTYPES: tuple[str, ...] = ("recall", "discrimination", "judgment", "diagnostic", "numeric")

#: Marker that splits a problem's candidate-facing ask from anything else in the
#: same file. Notes live in a separate file entirely; this is belt and braces.
NOTES_FILE = "notes.md"
PROMPT_FILE = "prompt.md"


@dataclass(frozen=True)
class Question:
    id: str
    pack: str
    topic: str
    subtopic: str
    qtype: str
    levels: tuple[str, ...]
    q: str
    a: str
    origin: str = "pack"  # "pack" or "bank"

    def as_dict(self, *, with_answer: bool = True) -> dict:
        out = {
            "id": self.id,
            "pack": self.pack,
            "topic": self.topic,
            "subtopic": self.subtopic,
            "qtype": self.qtype,
            "q": self.q,
        }
        if with_answer:
            out["a"] = self.a
        return out


@dataclass(frozen=True)
class Topic:
    id: str
    pack: str
    title: str
    area: str
    prefix: str
    levels: tuple[str, ...]
    subtopics: tuple[str, ...]
    card: Path | None


@dataclass(frozen=True)
class Problem:
    slug: str
    pack: str
    title: str
    areas: tuple[str, ...]
    levels: tuple[str, ...]
    minutes: int
    directory: Path

    @property
    def prompt_path(self) -> Path:
        return self.directory / PROMPT_FILE

    @property
    def notes_path(self) -> Path:
        return self.directory / NOTES_FILE


@dataclass
class Pack:
    name: str
    title: str
    description: str
    levels: tuple[str, ...]
    areas: tuple[str, ...]
    root: Path
    topics: dict[str, Topic] = field(default_factory=dict)
    problems: dict[str, Problem] = field(default_factory=dict)
    calibration: dict[str, dict] = field(default_factory=dict)
    questions: list[Question] = field(default_factory=list)

    def topic(self, topic_id: str) -> Topic:
        if topic_id not in self.topics:
            raise StudykitError(f"{self.name}: no topic {topic_id!r}")
        return self.topics[topic_id]

    def calibration_for(self, level: str) -> dict:
        return self.calibration.get(level, {})

    def questions_for(self, topic_id: str) -> list[Question]:
        return [q for q in self.questions if q.topic == topic_id]


def _as_tuple(value, name: str, path: Path) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise StudykitError(f"{path}: {name} must be a list of strings")
    return tuple(value)


def _check_levels(levels: tuple[str, ...], where: str) -> tuple[str, ...]:
    for level in levels:
        if level not in LEVELS:
            raise StudykitError(f"{where}: unknown level {level!r}")
    return levels


def load_pack(root: Path) -> Pack:
    manifest = root / "pack.toml"
    if not manifest.exists():
        raise StudykitError(f"{root}: no pack.toml")
    with manifest.open("rb") as handle:
        raw = tomllib.load(handle)

    meta = raw.get("pack") or {}
    name = meta.get("name") or root.name
    pack = Pack(
        name=name,
        title=meta.get("title", name),
        description=meta.get("description", ""),
        levels=_check_levels(_as_tuple(meta.get("levels"), "pack.levels", manifest) or LEVELS, str(manifest)),
        areas=_as_tuple(meta.get("areas"), "pack.areas", manifest),
        root=root,
        calibration=raw.get("calibration", {}),
    )

    for entry in raw.get("topic", []):
        topic_id = entry.get("id")
        if not topic_id:
            raise StudykitError(f"{manifest}: a [[topic]] is missing `id`")
        card = root / "cards" / f"{topic_id}.md"
        pack.topics[topic_id] = Topic(
            id=topic_id,
            pack=name,
            title=entry.get("title", topic_id),
            area=entry.get("area", ""),
            prefix=entry.get("prefix", topic_id[:2]),
            levels=_check_levels(
                _as_tuple(entry.get("levels"), "topic.levels", manifest) or pack.levels,
                f"{manifest} topic {topic_id}",
            ),
            subtopics=_as_tuple(entry.get("subtopics"), "topic.subtopics", manifest),
            card=card if card.exists() else None,
        )

    for entry in raw.get("problem", []):
        slug = entry.get("slug")
        if not slug:
            raise StudykitError(f"{manifest}: a [[problem]] is missing `slug`")
        pack.problems[slug] = Problem(
            slug=slug,
            pack=name,
            title=entry.get("title", slug),
            areas=_as_tuple(entry.get("areas"), "problem.areas", manifest),
            levels=_check_levels(
                _as_tuple(entry.get("levels"), "problem.levels", manifest) or pack.levels,
                f"{manifest} problem {slug}",
            ),
            minutes=int(entry.get("minutes", 45)),
            directory=root / "problems" / slug,
        )

    pack.questions = _load_questions(pack)
    return pack


def _load_questions(pack: Pack) -> list[Question]:
    questions: list[Question] = []
    seen: dict[str, Path] = {}
    sources = [(pack.root / "questions", "pack"), (bank_dir() / pack.name, "bank")]
    for directory, origin in sources:
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.toml")):
            for question in _read_bank(path, pack, origin):
                if question.id in seen:
                    raise StudykitError(
                        f"duplicate question id {question.id!r} in {path} "
                        f"(already defined in {seen[question.id]})"
                    )
                seen[question.id] = path
                questions.append(question)
    return questions


def _read_bank(path: Path, pack: Pack, origin: str) -> list[Question]:
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    default_topic = raw.get("topic") or path.stem
    out: list[Question] = []
    for entry in raw.get("q", []):
        topic = entry.get("topic", default_topic)
        missing = [k for k in ("id", "qtype", "subtopic", "q", "a") if not entry.get(k)]
        if missing:
            raise StudykitError(f"{path}: question missing {', '.join(missing)}")
        if entry["qtype"] not in QTYPES:
            raise StudykitError(f"{path}: {entry['id']} has unknown qtype {entry['qtype']!r}")
        levels = _check_levels(
            _as_tuple(entry.get("levels"), "q.levels", path) or pack.levels, f"{path} {entry['id']}"
        )
        out.append(
            Question(
                id=entry["id"],
                pack=pack.name,
                topic=topic,
                subtopic=entry["subtopic"],
                qtype=entry["qtype"],
                levels=levels,
                q=entry["q"].strip(),
                a=entry["a"].strip(),
                origin=origin,
            )
        )
    return out


class Library:
    """Every pack on disk, with the user's enabled subset addressable."""

    def __init__(self, packs: dict[str, Pack], enabled: list[str] | None = None) -> None:
        self.all = packs
        self.enabled_names = [n for n in (enabled or list(packs)) if n in packs]

    @property
    def enabled(self) -> list[Pack]:
        return [self.all[name] for name in self.enabled_names]

    def pack(self, name: str) -> Pack:
        if name not in self.all:
            known = ", ".join(sorted(self.all)) or "none installed"
            raise StudykitError(f"No pack {name!r}. Available: {known}")
        return self.all[name]

    def topics(self, level: str | None = None) -> list[Topic]:
        out: list[Topic] = []
        for pack in self.enabled:
            for topic in pack.topics.values():
                if level is None or level in topic.levels:
                    out.append(topic)
        return out

    def problems(self, level: str | None = None) -> list[Problem]:
        out: list[Problem] = []
        for pack in self.enabled:
            for problem in pack.problems.values():
                if level is None or level in problem.levels:
                    out.append(problem)
        return out

    def questions(self, level: str | None = None) -> list[Question]:
        out: list[Question] = []
        for pack in self.enabled:
            for question in pack.questions:
                if level is None or level in question.levels:
                    out.append(question)
        return out

    def find_topic(self, topic_id: str, pack_name: str | None = None) -> tuple[Pack, Topic]:
        matches = [
            (pack, pack.topics[topic_id])
            for pack in (self.enabled if pack_name is None else [self.pack(pack_name)])
            if topic_id in pack.topics
        ]
        if not matches:
            raise StudykitError(f"No topic {topic_id!r} in the enabled packs")
        if len(matches) > 1:
            names = ", ".join(pack.name for pack, _ in matches)
            raise StudykitError(f"Topic {topic_id!r} exists in several packs ({names}); pass --pack")
        return matches[0]

    def find_problem(self, slug: str, pack_name: str | None = None) -> tuple[Pack, Problem]:
        matches = [
            (pack, pack.problems[slug])
            for pack in (self.enabled if pack_name is None else [self.pack(pack_name)])
            if slug in pack.problems
        ]
        if not matches:
            raise StudykitError(f"No problem {slug!r} in the enabled packs")
        if len(matches) > 1:
            names = ", ".join(pack.name for pack, _ in matches)
            raise StudykitError(f"Problem {slug!r} exists in several packs ({names}); pass --pack")
        return matches[0]


def load_library(enabled: list[str] | None = None) -> Library:
    root = packs_dir()
    if not root.is_dir():
        raise StudykitError(f"No packs directory at {root}")
    packs: dict[str, Pack] = {}
    for child in sorted(root.iterdir()):
        if (child / "pack.toml").exists():
            pack = load_pack(child)
            packs[pack.name] = pack
    if not packs:
        raise StudykitError(f"No packs found under {root}")
    return Library(packs, enabled)


def check_level_arg(level: str) -> str:
    return check_level(level)
