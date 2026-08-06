"""Command line interface.

Two audiences, one surface. A human runs `status`, `progress` and `dashboard`;
a coaching agent runs `plan`, `card`, `problem`, `bank add` and `record`.

Agent-facing commands emit JSON so nothing has to be parsed out of prose, and
they emit only what the next step needs. `plan` returns question text but refers
to cards and problem prompts by command rather than inlining them, because most
sessions never open them.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import webbrowser
from pathlib import Path

from . import dashboard as dashboard_mod
from . import metrics as metrics_mod
from . import report, select, tomlwrite
from .config import (
    LEVEL_TITLES,
    LEVELS,
    MODES,
    Profile,
    ProfileMissing,
    StudykitError,
    attempts_dir,
    bank_dir,
    check_level,
    dashboard_path,
    data_dir,
    ledger_path,
    metrics_path,
    packs_dir,
    read_json,
    state_path,
    today,
    valid_date,
    write_json,
)
from .ledger import PROBLEM_PREFIX, SESSIONS, append, read, validate
from .packs import QTYPES, Library, load_library
from .schedule import build_state, compute_items

VERSION = "1.0.0"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def emit(payload: object) -> None:
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")


def load_profile_or_default(args) -> Profile:
    try:
        profile = Profile.load()
    except ProfileMissing:
        if getattr(args, "level", None):
            profile = Profile(level=check_level(args.level), packs=[])
        else:
            raise
    if getattr(args, "level", None):
        profile.level = check_level(args.level)
    if getattr(args, "pack", None):
        profile.packs = [args.pack]
    return profile


def library_for(profile: Profile) -> Library:
    return load_library(profile.packs or None)


def read_payload(args) -> object:
    """JSON from --json, --file, or stdin."""
    if getattr(args, "json_text", None):
        text = args.json_text
    elif getattr(args, "file", None):
        text = Path(args.file).read_text(encoding="utf-8")
    else:
        if sys.stdin.isatty():
            raise StudykitError("Nothing on stdin. Pass --json, --file, or pipe JSON in.")
        text = sys.stdin.read()
    if not text.strip():
        raise StudykitError("Empty input.")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise StudykitError(f"Input is not valid JSON: {exc}") from exc


def rebuild(profile: Profile, library: Library, as_of: str) -> tuple[dict, dict]:
    rows = read()
    state = build_state(library, rows, profile.level, as_of)
    metrics = metrics_mod.build_metrics(library, rows, profile.level, as_of)
    write_json(state_path(), state)
    write_json(metrics_path(), metrics)
    return state, metrics


def ensure_state(profile: Profile, library: Library, as_of: str) -> tuple[dict, dict]:
    """State is cheap to rebuild, so always rebuild rather than trusting a stale file."""
    return rebuild(profile, library, as_of)


# --------------------------------------------------------------------------- #
# setup
# --------------------------------------------------------------------------- #


def _ask(prompt: str, options: list[str], default: str) -> str:
    print(f"\n{prompt}")
    for index, option in enumerate(options, start=1):
        marker = " (default)" if option == default else ""
        print(f"  {index}. {option}{marker}")
    while True:
        raw = input(f"> [{default}] ").strip()
        if not raw:
            return default
        if raw in options:
            return raw
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print("Not one of those. Enter a number or the name.")


def _ask_many(prompt: str, options: list[str], default: list[str]) -> list[str]:
    print(f"\n{prompt}")
    for index, option in enumerate(options, start=1):
        marker = " (default)" if option in default else ""
        print(f"  {index}. {option}{marker}")
    print("  Comma-separated numbers or names. `all` for everything.")
    while True:
        raw = input(f"> [{', '.join(default)}] ").strip()
        if not raw:
            return default
        if raw.lower() == "all":
            return list(options)
        chosen = []
        for part in raw.split(","):
            part = part.strip()
            if part in options:
                chosen.append(part)
            elif part.isdigit() and 1 <= int(part) <= len(options):
                chosen.append(options[int(part) - 1])
            else:
                chosen = []
                break
        if chosen:
            return list(dict.fromkeys(chosen))
        print("Not recognised. Try again.")


def cmd_setup(args) -> int:
    existing = None
    if Path(str(dashboard_path().parent / "profile.json")).exists():
        try:
            existing = Profile.load()
        except StudykitError:
            existing = None
    if existing and not args.force and not args.level:
        print(
            f"A profile already exists (level {existing.level}, packs "
            f"{', '.join(existing.packs) or 'all'}).\nRe-run with --force to change it, "
            "or use `./study config set level senior`."
        )
        return 0

    available = sorted(load_library().all)
    interactive = sys.stdin.isatty() and not args.non_interactive and not args.level

    if interactive:
        print("studykit setup\n" + "=" * 14)
        print(
            "\nTwo answers and you are practising. Both are changeable later with "
            "`./study config set`."
        )
        level = _ask(
            "What level are you working at? This sets the interviewer bar and filters "
            "the question bank.",
            list(LEVELS),
            existing.level if existing else "senior",
        )
        packs = _ask_many(
            "Which packs do you want in rotation?",
            available,
            existing.packs if existing and existing.packs else available[:1],
        )
        budget = _ask(
            "Typical session length? Used when you say `study` with no budget.",
            ["10m", "25m", "45m", "60m"],
            existing.budget if existing else "25m",
        )
        mode = _ask(
            "Default mode for full problems? Coaching gives inline hints and feedback; "
            "interview holds everything to the end.",
            list(MODES),
            existing.mode if existing else "coaching",
        )
    else:
        level = check_level(args.level or (existing.level if existing else "senior"))
        packs = (
            [p.strip() for p in args.packs.split(",") if p.strip()]
            if args.packs
            else (existing.packs if existing and existing.packs else available[:1])
        )
        budget = args.budget or (existing.budget if existing else "25m")
        mode = args.mode or (existing.mode if existing else "coaching")

    unknown = [p for p in packs if p not in available]
    if unknown:
        raise StudykitError(f"Unknown pack(s): {', '.join(unknown)}. Available: {', '.join(available)}")
    if mode not in MODES:
        raise StudykitError(f"Unknown mode {mode!r}; one of {', '.join(MODES)}")

    profile = Profile(
        level=level,
        packs=packs,
        budget=budget,
        mode=mode,
        confidence_prompt=not args.no_confidence,
        created=(existing.created if existing else today()),
    )
    profile.save()
    for directory in (bank_dir(), attempts_dir()):
        directory.mkdir(parents=True, exist_ok=True)
    ledger_path().touch()

    library = library_for(profile)
    state, metrics = rebuild(profile, library, today())
    recommendation = select.recommend(library, read(), profile.level)

    print()
    print(report.rule("ready"))
    print(f"  level     {LEVEL_TITLES[level]}")
    print(f"  packs     {', '.join(packs)}")
    print(f"  data      {data_dir()}  (git-ignored, yours alone)")
    print(
        f"  in scope  {metrics['summary']['facets_in_scope']} facets, "
        f"{len(library.questions(level))} questions, {len(library.problems(level))} problems"
    )
    print()
    print("  Start a session by telling your coding agent: `study 25m`, `quiz`, or `practice`.")
    print(f"  Or drive it directly: {recommendation['command']}")
    print()
    return 0


# --------------------------------------------------------------------------- #
# reading commands
# --------------------------------------------------------------------------- #


def cmd_status(args) -> int:
    profile = load_profile_or_default(args)
    library = library_for(profile)
    as_of = args.date or today()
    state, metrics = ensure_state(profile, library, as_of)
    recommendation = select.recommend(library, read(), profile.level, as_of)
    if args.json:
        emit({"state": state, "summary": metrics["summary"], "recommendation": recommendation})
    else:
        print(report.render_status(state, metrics, recommendation))
    return 0


def cmd_progress(args) -> int:
    profile = load_profile_or_default(args)
    library = library_for(profile)
    as_of = args.date or today()
    state, metrics = ensure_state(profile, library, as_of)
    recommendation = select.recommend(library, read(), profile.level, as_of)
    if args.json:
        emit({"state": state, "metrics": metrics, "recommendation": recommendation})
    else:
        print(report.render_progress(state, metrics, recommendation))
    return 0


def cmd_queue(args) -> int:
    profile = load_profile_or_default(args)
    library = library_for(profile)
    as_of = args.date or today()
    entries = [e.as_dict() for e in select.build_queue(library, read(), profile.level, as_of)]
    if args.json:
        emit({"date": as_of, "level": profile.level, "queue": entries})
    else:
        print(report.render_queue(entries, args.limit))
    return 0


def cmd_plan(args) -> int:
    profile = load_profile_or_default(args)
    library = library_for(profile)
    as_of = args.date or today()
    minutes = select.parse_budget(args.budget, profile.budget)
    plan = select.compose(
        library,
        read(),
        profile.level,
        minutes,
        as_of=as_of,
        seed=args.seed,
        allow_problem=not args.no_problem,
    )
    plan["mode"] = args.mode or profile.mode
    plan["confidence_prompt"] = profile.confidence_prompt
    emit(plan)
    return 0


def cmd_questions(args) -> int:
    profile = load_profile_or_default(args)
    library = library_for(profile)
    as_of = args.date or today()
    rows = read()

    if args.topic or args.subtopic or args.qtype:
        pool = [
            q
            for q in library.questions(profile.level)
            if (not args.topic or q.topic == args.topic)
            and (not args.subtopic or q.subtopic == args.subtopic)
            and (not args.qtype or q.qtype == args.qtype)
        ]
        if not pool:
            raise StudykitError("No banked questions match that filter at this level.")
        exposure = {q.id: q for q in pool}
        chosen = sorted(pool, key=lambda q: q.id)[: args.count]
        emit(
            {
                "date": as_of,
                "level": profile.level,
                "questions": [q.as_dict() for q in chosen],
                "author_for": [],
            }
        )
        return 0

    targets = select.build_queue(library, rows, profile.level, as_of)[: args.count * 2]
    questions, starved = select.draw_questions(
        library, rows, profile.level, targets, args.count, as_of=as_of, seed=args.seed
    )
    emit(
        {
            "date": as_of,
            "level": profile.level,
            "questions": [q.as_dict() for q in questions],
            "author_for": [e.as_dict() for e in starved],
        }
    )
    return 0


def cmd_card(args) -> int:
    profile = load_profile_or_default(args)
    library = library_for(profile)
    pack, topic = library.find_topic(args.topic, args.pack)
    if topic.card is None:
        raise StudykitError(
            f"No card for {topic.id} in {pack.name}. Write one at "
            f"{pack.root / 'cards' / (topic.id + '.md')} using templates/knowledge-card.md."
        )
    text = topic.card.read_text(encoding="utf-8")
    if args.json:
        emit(
            {
                "pack": pack.name,
                "topic": topic.id,
                "title": topic.title,
                "area": topic.area,
                "subtopics": list(topic.subtopics),
                "path": str(topic.card),
                "card": text,
            }
        )
    else:
        sys.stdout.write(text)
    return 0


def cmd_problem(args) -> int:
    profile = load_profile_or_default(args)
    library = library_for(profile)
    as_of = args.date or today()

    if args.list or not args.slug:
        if args.slug is None and not args.list:
            chosen = select.choose_problem(library, read(), profile.level, as_of)
            if chosen is None:
                raise StudykitError("No problem available at this level. Try `./study problem --list`.")
            args.slug = chosen["slug"]
            args.pack = chosen["pack"]
        else:
            items = {i.label: i for i in compute_items(read()) if i.kind == "problem"}
            listing = [
                {
                    "pack": p.pack,
                    "slug": p.slug,
                    "title": p.title,
                    "areas": list(p.areas),
                    "minutes": p.minutes,
                    "attempts": items[p.slug].reps if p.slug in items else 0,
                    "best": max((s for _, s in items[p.slug].history), default=None)
                    if p.slug in items
                    else None,
                    "due": items[p.slug].due if p.slug in items else None,
                }
                for p in library.problems(profile.level)
            ]
            emit({"level": profile.level, "problems": listing})
            return 0

    pack, problem = library.find_problem(args.slug, args.pack)
    path = problem.notes_path if args.notes else problem.prompt_path
    if not path.exists():
        raise StudykitError(f"{pack.name}/{problem.slug}: missing {path.name}")
    if args.json:
        emit(
            {
                "pack": pack.name,
                "slug": problem.slug,
                "title": problem.title,
                "areas": list(problem.areas),
                "minutes": problem.minutes,
                "kind": "notes" if args.notes else "prompt",
                "text": path.read_text(encoding="utf-8"),
            }
        )
    else:
        if args.notes:
            print(report.style("INTERVIEWER NOTES - not to be shown before the attempt", "bold", "yellow"))
            print()
        sys.stdout.write(path.read_text(encoding="utf-8"))
    return 0


def cmd_packs(args) -> int:
    profile = load_profile_or_default(args)
    library = load_library(None if args.all else profile.packs or None)
    as_of = args.date or today()
    state = build_state(library_for(profile), read(), profile.level, as_of)
    if args.json:
        emit(
            {
                "level": profile.level,
                "enabled": profile.packs,
                "packs": [
                    {
                        "name": pack.name,
                        "title": pack.title,
                        "description": pack.description,
                        "areas": list(pack.areas),
                        "levels": list(pack.levels),
                        "topics": [
                            {
                                "id": t.id,
                                "title": t.title,
                                "area": t.area,
                                "levels": list(t.levels),
                                "subtopics": list(t.subtopics),
                                "has_card": t.card is not None,
                                "questions": len(
                                    [q for q in pack.questions if q.topic == t.id and profile.level in q.levels]
                                ),
                            }
                            for t in pack.topics.values()
                        ],
                        "problems": [
                            {"slug": p.slug, "title": p.title, "areas": list(p.areas), "minutes": p.minutes}
                            for p in pack.problems.values()
                        ],
                    }
                    for pack in library.all.values()
                ],
            }
        )
    else:
        print(report.render_packs(library, profile.level, state))
    return 0


def cmd_levels(args) -> int:
    profile = None
    try:
        profile = Profile.load()
    except ProfileMissing:
        pass
    library = load_library(profile.packs if profile else None)
    payload = {
        "levels": list(LEVELS),
        "current": profile.level if profile else None,
        "calibration": {
            pack.name: {level: pack.calibration_for(level) for level in LEVELS if pack.calibration_for(level)}
            for pack in library.enabled
        },
    }
    if args.json:
        emit(payload)
        return 0
    for level in LEVELS:
        marker = "  <- you" if profile and profile.level == level else ""
        print(report.style(f"{LEVEL_TITLES[level]}{marker}", "bold"))
        for pack in library.enabled:
            brief = pack.calibration_for(level)
            if not brief:
                continue
            print(f"  {pack.name}")
            if brief.get("bar"):
                print(f"    bar       {brief['bar']}")
            if brief.get("push_on"):
                print(f"    push on   {', '.join(brief['push_on'])}")
            if brief.get("assume"):
                print(f"    assume    {brief['assume']}")
        print()
    return 0


# --------------------------------------------------------------------------- #
# writing commands
# --------------------------------------------------------------------------- #


def cmd_record(args) -> int:
    profile = load_profile_or_default(args)
    library = library_for(profile)
    payload = read_payload(args)
    as_of = args.date or today()

    if isinstance(payload, list):
        payload = {"rows": payload}
    if not isinstance(payload, dict) or "rows" not in payload:
        raise StudykitError(
            'Expected {"session": ..., "pack": ..., "rows": [...]} or a bare list of rows.'
        )

    defaults = {
        "date": payload.get("date", as_of),
        "pack": payload.get("pack") or (profile.packs[0] if profile.packs else None),
        "session": payload.get("session"),
        "level": payload.get("level", profile.level),
    }
    if defaults["session"] is None:
        raise StudykitError(f"`session` is required; one of {', '.join(SESSIONS)}")

    before = {(i.pack, i.topic, i.subtopic): i for i in compute_items(read())}
    rows = []
    for entry in payload["rows"]:
        merged = {k: v for k, v in defaults.items() if v is not None}
        merged.update(entry)
        rows.append(validate(merged, library, default_level=profile.level))

    if args.dry_run:
        emit({"ok": True, "dry_run": True, "rows": [r.as_dict() for r in rows]})
        return 0

    append(rows)
    state, metrics = rebuild(profile, library, as_of)
    after = {(i.pack, i.topic, i.subtopic): i for i in compute_items(read())}

    changes = []
    for row in rows:
        item = after[row.key]
        previous = before.get(row.key)
        changes.append(
            {
                "item": item.label,
                "strength": item.strength,
                "was": previous.strength if previous else None,
                "reps": item.reps,
                "interval": item.interval,
                "due": item.due,
            }
        )
    seen: set[str] = set()
    changes = [c for c in changes if not (c["item"] in seen or seen.add(c["item"]))]

    result = {
        "ok": True,
        "recorded": len(rows),
        "date": defaults["date"],
        "changes": changes,
        "next_due": state["items"][0]["label"] if state["items"] else None,
        "coverage_pct": metrics["summary"]["coverage_pct"],
        "calibration_error": metrics["summary"]["calibration_error"],
    }
    if args.json:
        emit(result)
    else:
        print(f"Recorded {len(rows)} measurement(s) on {defaults['date']}.")
        for change in changes:
            was = f"{change['was']} -> " if change["was"] is not None else ""
            print(
                f"  {change['item']:<44} {was}{change['strength']}   "
                f"reps {change['reps']}  next {change['due']} (+{change['interval']}d)"
            )
    return 0


def _next_ids(pack, prefix: str, count: int) -> list[str]:
    used = set()
    for question in pack.questions:
        if question.id.startswith(prefix + "-"):
            tail = question.id.split("-")[-1]
            if tail.isdigit():
                used.add(int(tail))
    out = []
    candidate = 1
    while len(out) < count:
        if candidate not in used:
            used.add(candidate)
            out.append(f"{prefix}-{candidate:03d}")
        candidate += 1
    return out


def cmd_bank_add(args) -> int:
    profile = load_profile_or_default(args)
    library = library_for(profile)
    payload = read_payload(args)
    if isinstance(payload, list):
        payload = {"questions": payload}
    questions = payload.get("questions")
    if not questions:
        raise StudykitError('Expected {"pack": ..., "topic": ..., "questions": [...]}.')

    default_pack = payload.get("pack") or (profile.packs[0] if profile.packs else None)
    default_topic = payload.get("topic")
    default_levels = payload.get("levels") or list(LEVELS[LEVELS.index(profile.level) :])

    grouped: dict[tuple[str, str], list[dict]] = {}
    for entry in questions:
        pack_name = entry.get("pack", default_pack)
        topic_id = entry.get("topic", default_topic)
        if not pack_name or not topic_id:
            raise StudykitError("Each question needs a pack and a topic (or set them at the top level).")
        pack = library.pack(pack_name)
        topic = pack.topic(topic_id)
        subtopic = entry.get("subtopic")
        if subtopic not in topic.subtopics:
            raise StudykitError(
                f"{topic_id}: unknown subtopic {subtopic!r}. Known: {', '.join(topic.subtopics)}"
            )
        if entry.get("qtype") not in QTYPES:
            raise StudykitError(f"qtype must be one of {', '.join(QTYPES)}")
        for field in ("q", "a"):
            if not entry.get(field):
                raise StudykitError(f"Question missing {field!r}")
        grouped.setdefault((pack_name, topic_id), []).append(entry)

    written = []
    for (pack_name, topic_id), entries in grouped.items():
        pack = library.pack(pack_name)
        target = (
            pack.root / "questions" / f"{topic_id}.toml"
            if args.into_pack
            else bank_dir() / pack_name / f"{topic_id}.toml"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        fresh = not target.exists()
        ids = _next_ids(pack, pack.topic(topic_id).prefix, len(entries))
        blocks = []
        for entry, question_id in zip(entries, ids):
            blocks.append(
                tomlwrite.question_block(
                    {
                        "id": question_id,
                        "qtype": entry["qtype"],
                        "subtopic": entry["subtopic"],
                        "levels": entry.get("levels", default_levels),
                        "source": entry.get("source", "session"),
                        "q": entry["q"],
                        "a": entry["a"],
                    }
                )
            )
            written.append({"id": question_id, "pack": pack_name, "topic": topic_id, "path": str(target)})
        with target.open("a", encoding="utf-8") as handle:
            if fresh:
                handle.write(tomlwrite.bank_header(topic_id))
            handle.write("\n".join(blocks) + "\n")

    # Re-load so a malformed append is caught here rather than next session.
    load_library(profile.packs or None)
    emit({"ok": True, "banked": len(written), "questions": written})
    return 0


def cmd_rebuild(args) -> int:
    profile = load_profile_or_default(args)
    library = library_for(profile)
    state, metrics = rebuild(profile, library, args.date or today())
    emit(
        {
            "ok": True,
            "state": str(state_path()),
            "metrics": str(metrics_path()),
            "items": len(state["items"]),
            "unmeasured_facets": sum(len(g["missing"]) for g in state["gaps"]),
        }
    )
    return 0


def cmd_dashboard(args) -> int:
    profile = load_profile_or_default(args)
    library = library_for(profile)
    as_of = args.date or today()
    state, metrics = ensure_state(profile, library, as_of)
    target = Path(args.out).expanduser() if args.out else dashboard_path()
    html = dashboard_mod.render(state, metrics, select.recommend(library, read(), profile.level, as_of))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")
    if args.open:
        webbrowser.open(target.resolve().as_uri())
    if args.json:
        emit({"ok": True, "path": str(target)})
    else:
        print(f"Dashboard written to {target}")
    return 0


def cmd_config(args) -> int:
    if args.action == "get":
        profile = Profile.load()
        payload = {
            "level": profile.level,
            "packs": profile.packs,
            "budget": profile.budget,
            "mode": profile.mode,
            "confidence_prompt": profile.confidence_prompt,
            "data_dir": str(data_dir()),
            "packs_dir": str(packs_dir()),
        }
        if args.key:
            if args.key not in payload:
                raise StudykitError(f"Unknown key {args.key!r}. One of: {', '.join(payload)}")
            print(payload[args.key] if not isinstance(payload[args.key], list) else ",".join(payload[args.key]))
        else:
            emit(payload)
        return 0

    profile = Profile.load()
    key, value = args.key, args.value
    if key == "level":
        profile.level = check_level(value)
    elif key == "packs":
        available = sorted(load_library().all)
        chosen = [p.strip() for p in value.split(",") if p.strip()]
        unknown = [p for p in chosen if p not in available]
        if unknown:
            raise StudykitError(f"Unknown pack(s): {', '.join(unknown)}")
        profile.packs = chosen
    elif key == "budget":
        select.parse_budget(value)
        profile.budget = value
    elif key == "mode":
        if value not in MODES:
            raise StudykitError(f"Unknown mode {value!r}; one of {', '.join(MODES)}")
        profile.mode = value
    elif key == "confidence_prompt":
        profile.confidence_prompt = value.lower() in ("1", "true", "yes", "on")
    else:
        raise StudykitError(f"Cannot set {key!r}.")
    profile.save()
    library = library_for(profile)
    rebuild(profile, library, today())
    print(f"{key} = {value}")
    return 0


def cmd_doctor(args) -> int:
    problems: list[str] = []
    notes: list[str] = []
    library = load_library()

    for pack in library.all.values():
        for topic in pack.topics.values():
            if topic.card is None:
                notes.append(f"{pack.name}/{topic.id}: no knowledge card")
            if not topic.subtopics:
                problems.append(f"{pack.name}/{topic.id}: declares no subtopics")
            if topic.area and pack.areas and topic.area not in pack.areas:
                problems.append(f"{pack.name}/{topic.id}: area {topic.area!r} not in pack.areas")
        for problem in pack.problems.values():
            if not problem.prompt_path.exists():
                problems.append(f"{pack.name}/{problem.slug}: missing prompt.md")
            if not problem.notes_path.exists():
                problems.append(f"{pack.name}/{problem.slug}: missing notes.md")
        for question in pack.questions:
            if question.topic not in pack.topics:
                problems.append(f"{pack.name}: question {question.id} names unknown topic {question.topic}")
                continue
            if question.subtopic not in pack.topics[question.topic].subtopics:
                problems.append(
                    f"{pack.name}: question {question.id} names unknown subtopic {question.subtopic!r}"
                )
        for level in LEVELS:
            if level in pack.levels and not pack.calibration_for(level):
                notes.append(f"{pack.name}: no calibration brief for level {level!r}")
        for topic in pack.topics.values():
            for level in topic.levels:
                if not any(q.topic == topic.id and level in q.levels for q in pack.questions):
                    notes.append(f"{pack.name}/{topic.id}: no questions at level {level!r}")

    try:
        profile = Profile.load()
        rows = read()
        for row in rows:
            try:
                validate(row.as_dict(), library)
            except StudykitError as exc:
                problems.append(f"ledger: {exc}")
        notes.append(f"profile: level {profile.level}, packs {', '.join(profile.packs) or 'all'}")
        notes.append(f"ledger: {len(rows)} rows")
    except ProfileMissing:
        notes.append("no profile yet - run `./study setup`")

    if args.json:
        emit({"ok": not problems, "problems": problems, "notes": notes})
    else:
        if problems:
            print(report.style(f"{len(problems)} problem(s)", "bold", "red"))
            for line in problems:
                print(f"  {line}")
        else:
            print(report.style("packs and data look consistent", "green"))
        if args.verbose and notes:
            print()
            print(report.style("notes", "dim"))
            for line in notes:
                print(f"  {line}")
        elif notes and not args.verbose:
            print(report.style(f"  ({len(notes)} note(s); --verbose to see them)", "dim"))
    return 1 if problems else 0


def cmd_test(args) -> int:
    """Run the repository test suite with the interpreter selected by ./study."""
    import unittest

    tests_dir = Path(__file__).resolve().parent.parent / "tests"
    suite = unittest.defaultTestLoader.discover(str(tests_dir))
    result = unittest.TextTestRunner(verbosity=2 if args.verbose else 1).run(suite)
    return 0 if result.wasSuccessful() else 1


def cmd_export(args) -> int:
    mapping = {"state": state_path(), "metrics": metrics_path(), "profile": data_dir() / "profile.json"}
    if args.what == "ledger":
        emit([r.as_dict() for r in read()])
        return 0
    payload = read_json(mapping[args.what])
    if payload is None:
        raise StudykitError(f"No {args.what} yet. Run a session, or `./study rebuild`.")
    emit(payload)
    return 0


# --------------------------------------------------------------------------- #
# parser
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="study",
        description="A spaced-repetition study kit for engineering knowledge, driven by a coding agent.",
    )
    parser.add_argument("--version", action="version", version=f"studykit {VERSION}")
    parser.add_argument("--date", help="Treat this ISO date as today.")
    parser.add_argument("--json", action="store_true", help="Machine-readable output where a human view exists.")

    # The same two flags on every subcommand, so they work on either side of it.
    # SUPPRESS keeps an omitted flag from overwriting the value given before the
    # subcommand name.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--date", help=argparse.SUPPRESS, default=argparse.SUPPRESS)
    common.add_argument(
        "--json", action="store_true", help=argparse.SUPPRESS, default=argparse.SUPPRESS
    )
    subparsers = parser.add_subparsers(dest="command", required=True, parser_class=lambda **kw: argparse.ArgumentParser(parents=[common], **kw))

    setup = subparsers.add_parser("setup", help="Set your level and packs. Run this first.")
    setup.add_argument("--level", choices=LEVELS)
    setup.add_argument("--packs", help="Comma-separated pack names.")
    setup.add_argument("--budget", help="Default session length, e.g. 25m.")
    setup.add_argument("--mode", choices=MODES)
    setup.add_argument("--no-confidence", action="store_true", help="Never ask for a pre-answer confidence.")
    setup.add_argument("--non-interactive", action="store_true")
    setup.add_argument("--force", action="store_true", help="Overwrite an existing profile.")
    setup.set_defaults(func=cmd_setup)

    status = subparsers.add_parser("status", help="One screen: what is due and what to do next.")
    status.set_defaults(func=cmd_status)

    progress = subparsers.add_parser("progress", help="Full report: queue, weak facets, calibration, coverage.")
    progress.set_defaults(func=cmd_progress)

    queue = subparsers.add_parser("queue", help="The ordered work list.")
    queue.add_argument("--limit", type=int, default=20)
    queue.set_defaults(func=cmd_queue)

    plan = subparsers.add_parser("plan", help="Compose a session to fit a budget. Agent-facing JSON.")
    plan.add_argument("budget", nargs="?", help="e.g. 15m, 1h, half day")
    plan.add_argument("--level", choices=LEVELS)
    plan.add_argument("--mode", choices=MODES)
    plan.add_argument("--seed", type=int, help="Reproducible selection.")
    plan.add_argument("--no-problem", action="store_true", help="Never include a full problem.")
    plan.set_defaults(func=cmd_plan)

    questions = subparsers.add_parser("questions", help="Draw questions from the bank. Agent-facing JSON.")
    questions.add_argument("--count", type=int, default=8)
    questions.add_argument("--topic")
    questions.add_argument("--subtopic")
    questions.add_argument("--qtype", choices=QTYPES)
    questions.add_argument("--pack")
    questions.add_argument("--level", choices=LEVELS)
    questions.add_argument("--seed", type=int)
    questions.set_defaults(func=cmd_questions)

    card = subparsers.add_parser("card", help="Print a knowledge card.")
    card.add_argument("topic")
    card.add_argument("--pack")
    card.set_defaults(func=cmd_card)

    problem = subparsers.add_parser("problem", help="Print a problem's candidate prompt, or its notes.")
    problem.add_argument("slug", nargs="?")
    problem.add_argument("--notes", action="store_true", help="Interviewer notes. Never before the attempt.")
    problem.add_argument("--list", action="store_true")
    problem.add_argument("--pack")
    problem.set_defaults(func=cmd_problem)

    packs_cmd = subparsers.add_parser("packs", help="What content is installed and how covered it is.")
    packs_cmd.add_argument("--all", action="store_true", help="Include packs not enabled in your profile.")
    packs_cmd.set_defaults(func=cmd_packs)

    levels_cmd = subparsers.add_parser("levels", help="The level ladder and each pack's calibration brief.")
    levels_cmd.set_defaults(func=cmd_levels)

    record = subparsers.add_parser("record", help="Append measurements, then recompute state and metrics.")
    record.add_argument("--json-text", "--data", dest="json_text", help="JSON payload as a string.")
    record.add_argument("--file", help="Read the JSON payload from a file.")
    record.add_argument("--dry-run", action="store_true", help="Validate without writing.")
    record.set_defaults(func=cmd_record)

    bank = subparsers.add_parser("bank", help="Manage question banks.")
    bank_sub = bank.add_subparsers(dest="bank_command", required=True)
    bank_add = bank_sub.add_parser("add", help="Bank questions generated during a session. Assigns ids.")
    bank_add.add_argument("--json-text", "--data", dest="json_text")
    bank_add.add_argument("--file")
    bank_add.add_argument(
        "--into-pack",
        action="store_true",
        help="Write into the pack itself rather than your private overlay. For pack authors.",
    )
    bank_add.set_defaults(func=cmd_bank_add)

    rebuild_cmd = subparsers.add_parser("rebuild", help="Recompute state.json and metrics.json from the ledger.")
    rebuild_cmd.set_defaults(func=cmd_rebuild)

    dash = subparsers.add_parser("dashboard", help="Write a self-contained HTML dashboard.")
    dash.add_argument("--out", help="Where to write it.")
    dash.add_argument("--open", action="store_true", help="Open it in a browser.")
    dash.set_defaults(func=cmd_dashboard)

    config = subparsers.add_parser("config", help="Read or change your profile.")
    config_sub = config.add_subparsers(dest="action", required=True)
    config_get = config_sub.add_parser("get")
    config_get.add_argument("key", nargs="?")
    config_get.set_defaults(func=cmd_config, action="get")
    config_set = config_sub.add_parser("set")
    config_set.add_argument("key")
    config_set.add_argument("value")
    config_set.set_defaults(func=cmd_config, action="set")

    doctor = subparsers.add_parser("doctor", help="Validate packs and data.")
    doctor.add_argument("--verbose", "-v", action="store_true")
    doctor.set_defaults(func=cmd_doctor)

    test = subparsers.add_parser("test", help="Run the repository test suite.")
    test.add_argument("--verbose", "-v", action="store_true")
    test.set_defaults(func=cmd_test)

    export = subparsers.add_parser("export", help="Print state, metrics, ledger or profile as JSON.")
    export.add_argument("what", choices=["state", "metrics", "ledger", "profile"])
    export.set_defaults(func=cmd_export)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.date:
        args.date = valid_date(args.date)
    if not hasattr(args, "level"):
        args.level = None
    if not hasattr(args, "pack"):
        args.pack = None
    try:
        return args.func(args)
    except StudykitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except BrokenPipeError:
        os._exit(0)
    except KeyboardInterrupt:
        print()
        return 130
