"""Paths, levels and the user profile.

The data directory sits outside the checkout, so history outlives the install.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

SCHEMA = 1

#: Ordered from least to most senior. Order matters: reports and level bands
#: are rendered in this sequence and `at_least` compares by index.
LEVELS: tuple[str, ...] = ("graduate", "mid", "senior", "lead", "staff")

LEVEL_TITLES: dict[str, str] = {
    "graduate": "Graduate",
    "mid": "Mid",
    "senior": "Senior",
    "lead": "Lead",
    "staff": "Staff+",
}

MODES: tuple[str, ...] = ("coaching", "interview")


class StudykitError(Exception):
    """Anything the user can fix, reported without a traceback."""


class ProfileMissing(StudykitError):
    def __init__(self) -> None:
        super().__init__("No profile yet. Run `./study setup` first.")


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def packs_dir() -> Path:
    env = os.environ.get("STUDYKIT_PACKS")
    return Path(env).expanduser().resolve() if env else repo_root() / "packs"


def user_packs_dir() -> Path:
    return data_dir() / "packs"


def pack_roots() -> list[Path]:
    return [packs_dir(), user_packs_dir()]


def data_dir() -> Path:
    env = os.environ.get("STUDYKIT_DATA")
    if env:
        return Path(env).expanduser().resolve()
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg).expanduser().resolve() / "studykit"
    return Path.home() / ".studykit"


def profile_path() -> Path:
    return data_dir() / "profile.json"


def ledger_path() -> Path:
    return data_dir() / "ledger.jsonl"


def state_path() -> Path:
    return data_dir() / "state.json"


def metrics_path() -> Path:
    return data_dir() / "metrics.json"


def bank_dir() -> Path:
    """User-authored questions, banked mid-session. Overlays the shipped packs."""
    return data_dir() / "bank"


def attempts_dir() -> Path:
    return data_dir() / "attempts"


def dashboard_path() -> Path:
    return data_dir() / "dashboard.html"


def today() -> str:
    """Today as ISO, for `as_of` reasoning. `STUDYKIT_TODAY` overrides."""
    override = os.environ.get("STUDYKIT_TODAY")
    if override:
        return valid_date(override)
    return dt.date.today().isoformat()


def now() -> str:
    """This instant, local, with its offset. What a new ledger row is stamped with.

    `STUDYKIT_NOW` overrides it. `STUDYKIT_TODAY` deliberately does not: a day is
    not a time, and deriving one from the other would be a guess.
    """
    override = os.environ.get("STUDYKIT_NOW")
    if override:
        return valid_at(override)
    return dt.datetime.now().astimezone().replace(microsecond=0).isoformat()


def day_of(at: str) -> str:
    """The calendar day a timestamp falls on. Scheduling works in days."""
    return at[:10]


def valid_date(value: str) -> str:
    try:
        return dt.date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise StudykitError(f"Not an ISO date (YYYY-MM-DD): {value!r}") from exc


def valid_at(value: str) -> str:
    try:
        return dt.datetime.fromisoformat(value).replace(microsecond=0).isoformat()
    except ValueError as exc:
        raise StudykitError(f"Not an ISO timestamp (YYYY-MM-DDTHH:MM:SS): {value!r}") from exc


def add_days(iso: str, days: int) -> str:
    return (dt.date.fromisoformat(iso) + dt.timedelta(days=days)).isoformat()


def days_between(start: str, end: str) -> int:
    return (dt.date.fromisoformat(end) - dt.date.fromisoformat(start)).days


def at_least(level: str, floor: str) -> bool:
    """True when `level` is at or above `floor` in the ladder."""
    return LEVELS.index(level) >= LEVELS.index(floor)


def check_level(level: str) -> str:
    if level not in LEVELS:
        raise StudykitError(f"Unknown level {level!r}. One of: {', '.join(LEVELS)}")
    return level


@dataclass
class Profile:
    level: str = "senior"
    packs: list[str] = field(default_factory=list)
    budget: str = "25m"
    mode: str = "coaching"
    confidence_prompt: bool = True
    #: Where the data directory is carried between machines. Empty means sync is off.
    sync_remote: str = ""
    sync_branch: str = "main"
    #: Pull before a session, push after one.
    sync_auto: bool = False
    created: str = ""
    schema: int = SCHEMA

    @classmethod
    def load(cls) -> "Profile":
        path = profile_path()
        if not path.exists():
            raise ProfileMissing()
        raw = json.loads(path.read_text(encoding="utf-8"))
        known = {f for f in cls.__dataclass_fields__}
        profile = cls(**{k: v for k, v in raw.items() if k in known})
        check_level(profile.level)
        return profile

    def save(self) -> Path:
        path = profile_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": SCHEMA,
            "level": self.level,
            "packs": self.packs,
            "budget": self.budget,
            "mode": self.mode,
            "confidence_prompt": self.confidence_prompt,
            "sync_remote": self.sync_remote,
            "sync_branch": self.sync_branch,
            "sync_auto": self.sync_auto,
            "created": self.created or today(),
        }
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return path


def write_json(path: Path, payload: object) -> Path:
    """Atomic-enough write: temp file in the same directory, then rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def read_json(path: Path, default: object = None) -> object:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))
