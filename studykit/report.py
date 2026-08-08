"""Terminal rendering. Reads state and metrics; never computes or writes them."""

from __future__ import annotations

import os
import shutil
import sys

from .config import LEVEL_TITLES, LEVELS, days_between

_STYLES = {"bold": "1", "dim": "2", "red": "31", "green": "32", "yellow": "33", "blue": "34"}


def card(text: str, area: str, levels: tuple[str, ...]) -> str:
    """A card as printed: its own markdown, with area and levels from the manifest."""
    titles = [LEVEL_TITLES[name] for name in LEVELS if name in levels]
    span = f"{titles[0]} → {titles[-1]}" if titles else ""
    heading, _, body = text.partition("\n")
    return f"{heading}\n\n**Area:** {area} · **Levels:** {span}\n\n{body.strip()}\n"


def _colour_enabled() -> bool:
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("STUDYKIT_COLOR") == "always":
        return True
    return sys.stdout.isatty()


def style(text: str, *names: str) -> str:
    if not names or not _colour_enabled():
        return text
    codes = ";".join(_STYLES[n] for n in names if n in _STYLES)
    return f"\033[{codes}m{text}\033[0m" if codes else text


def width(default: int = 88) -> int:
    return min(shutil.get_terminal_size((default, 24)).columns, 100)


def rule(title: str = "") -> str:
    if not title:
        return style("-" * width(), "dim")
    pad = max(width() - len(title) - 3, 0)
    return style(f"-- {title} " + "-" * pad, "dim")


def bar(value: float | None, maximum: float = 5.0, size: int = 20) -> str:
    if value is None:
        return style("no data", "dim")
    filled = int(round(size * min(value / maximum, 1.0)))
    return "#" * filled + style("." * (size - filled), "dim")


def _strength_colour(strength: int | None) -> tuple[str, ...]:
    if strength is None:
        return ("dim",)
    if strength <= 2:
        return ("red",)
    if strength == 3:
        return ("yellow",)
    return ("green",)


def render_status(state: dict, metrics: dict, recommendation: dict) -> str:
    items = state.get("items", [])
    as_of = state.get("generated", "")
    overdue = [i for i in items if i["kind"] == "facet" and i["overdue_days"] > 0]
    due = [i for i in items if i["kind"] == "facet" and i["overdue_days"] == 0]
    unmeasured = sum(len(g["missing"]) for g in state.get("gaps", []))
    summary = metrics.get("summary", {})

    lines = [
        style(f"studykit  {LEVEL_TITLES.get(state.get('level',''), state.get('level',''))}  {as_of}", "bold"),
        "",
        f"  overdue      {style(str(len(overdue)), *(('red',) if overdue else ('dim',)))}",
        f"  due today    {len(due)}",
        f"  never tested {style(str(unmeasured), *(('yellow',) if unmeasured else ('dim',)))}",
        f"  coverage     {summary.get('coverage_pct') or 0}%  "
        f"({summary.get('facets_measured', 0)}/{summary.get('facets_in_scope', 0)} facets)",
        f"  mean strength {summary.get('mean_strength') or '-'}",
        "",
        style("  next: ", "bold") + recommendation["headline"],
        style(f"        {recommendation['command']}", "dim"),
    ]
    return "\n".join(lines)


def render_progress(state: dict, metrics: dict, recommendation: dict) -> str:
    as_of = state.get("generated", "")
    out: list[str] = []
    summary = metrics.get("summary", {})

    out.append(style(f"Progress  {LEVEL_TITLES.get(state.get('level',''))}  as of {as_of}", "bold"))
    if not summary.get("measurements"):
        out.append("")
        out.append("Nothing measured yet. Everything below fills in after your first session.")
        out.append("")
        out.append(style("  next: ", "bold") + recommendation["headline"])
        out.append(style(f"        {recommendation['command']}", "dim"))
        return "\n".join(out)

    items = state.get("items", [])
    facets = [i for i in items if i["kind"] == "facet"]
    overdue = [i for i in facets if i["overdue_days"] > 0]

    out += ["", rule("due now")]
    if overdue:
        for item in sorted(overdue, key=lambda i: (-i["overdue_days"], i["strength"]))[:12]:
            out.append(
                f"  {style(str(item['strength']), *_strength_colour(item['strength']))}  "
                f"{item['label']:<44} {item['overdue_days']}d late   reps {item['reps']}"
            )
    else:
        due_today = [i for i in facets if i["overdue_days"] == 0]
        out.append(
            f"  nothing overdue"
            + (f", {len(due_today)} due today" if due_today else "")
        )

    gaps = state.get("gaps", [])
    out += ["", rule("never measured  (unknown, not merely stale)")]
    if gaps:
        for gap in gaps[:10]:
            out.append(
                f"  {gap['topic']:<30} {len(gap['missing'])}/{gap['total']} facets   "
                + style(" ".join(gap["missing"][:5]), "dim")
            )
    else:
        out.append("  every facet in scope has been measured at least once")

    weakest = metrics.get("weakest", [])
    out += ["", rule("weakest facets")]
    if weakest:
        for entry in weakest[:8]:
            if entry["strength"] > 3:
                break
            label = f"{entry['topic']}/{entry['subtopic']}"
            out.append(
                f"  {style(str(entry['strength']), *_strength_colour(entry['strength']))}  "
                f"{label:<44} last {entry['last']}  due {entry['due']}"
            )
    else:
        out.append("  no measurements yet")

    out += ["", rule("by question type")]
    by_qtype = metrics.get("by_qtype", [])
    if by_qtype:
        for entry in by_qtype:
            out.append(f"  {entry['qtype']:<16} {entry['mean']:<5} {bar(entry['mean'])}  n={entry['n']}")
        recall = next((e["mean"] for e in by_qtype if e["qtype"] == "recall"), None)
        judgment = next((e["mean"] for e in by_qtype if e["qtype"] == "judgment"), None)
        if recall is not None and judgment is not None and recall - judgment >= 1:
            out.append("")
            out.append(
                style(
                    "  Recall is running well above judgment. The knowledge is there and inert; "
                    "that needs applied work, not more flashcards.",
                    "yellow",
                )
            )
    else:
        out.append("  no typed questions recorded yet")

    out += ["", rule("calibration")]
    error = summary.get("calibration_error")
    if error is None:
        out.append("  no confidence ratings captured")
    else:
        verdict = "overconfident" if error > 0.25 else "underconfident" if error < -0.25 else "well calibrated"
        out.append(f"  mean predicted - measured  {error:+.2f}   {style(verdict, 'bold')}")

    thin = metrics.get("thin_evidence", [])
    out += ["", rule("thin evidence  (one rep, carrying a 4 or 5)")]
    if thin:
        for entry in thin[:8]:
            label = f"{entry['topic']}/{entry['subtopic']}"
            out.append(f"  {entry['strength']}  {label:<44} due {entry['due']}")
    else:
        out.append("  none")

    uncovered = metrics.get("uncovered_areas", [])
    if uncovered:
        out += ["", rule("areas with no measurement at all"), "  " + ", ".join(uncovered)]

    problems = metrics.get("problems", [])
    if problems:
        out += ["", rule("problems")]
        for entry in sorted(problems, key=lambda p: p["due"]):
            late = days_between(entry["due"], as_of)
            when = f"{late}d late" if late > 0 else f"due {entry['due']}"
            out.append(
                f"  {style(str(entry['score']), *_strength_colour(entry['score']))}  "
                f"{entry['slug']:<32} {entry['attempts']} attempt(s)  {when}"
            )

    out += ["", rule(), style("  next: ", "bold") + recommendation["headline"],
            style(f"        {recommendation['command']}", "dim")]
    return "\n".join(out)


def render_queue(entries: list[dict], limit: int = 20) -> str:
    if not entries:
        return "Queue empty. Nothing due and nothing unmeasured at this level."
    out = [style(f"{'reason':<12}{'strength':<10}{'facet':<44}due", "bold")]
    for entry in entries[:limit]:
        strength = entry["strength"]
        out.append(
            f"{entry['reason']:<12}"
            + style(f"{strength if strength is not None else '-':<10}", *_strength_colour(strength))
            + f"{entry['topic'] + '/' + entry['subtopic']:<44}"
            + (entry["due"] or "-")
        )
    if len(entries) > limit:
        out.append(style(f"... {len(entries) - limit} more", "dim"))
    return "\n".join(out)


def render_packs(library, level: str, state: dict, enabled: list[str]) -> str:
    """`enabled` comes from the profile, not from the library.

    A Library always holds every pack on disk, so its own `enabled_names`
    would mark all of them on. Only the profile knows what is in rotation.
    """
    measured = {(i["pack"], i["topic"], i["subtopic"]) for i in state.get("items", [])}
    out = []
    for pack in library.all.values():
        flag = style("on ", "green") if pack.name in enabled else style("off", "dim")
        out.append(style(f"{flag}  {pack.name}  -  {pack.title}", "bold"))
        if pack.description:
            out.append(style(f"      {pack.description}", "dim"))
        in_level = [t for t in pack.topics.values() if level in t.levels]
        questions = [q for q in pack.questions if level in q.levels]
        out.append(
            f"      {len(in_level)}/{len(pack.topics)} topics at this level, "
            f"{len(questions)} questions, {len([p for p in pack.problems.values() if level in p.levels])} problems"
        )
        for topic in sorted(in_level, key=lambda t: t.id):
            done = sum(1 for s in topic.subtopics if (pack.name, topic.id, s) in measured)
            card = "" if topic.card else style("  (no card)", "yellow")
            out.append(
                f"        {topic.id:<32} {done}/{len(topic.subtopics)} measured   "
                f"{len([q for q in questions if q.topic == topic.id])} q{card}"
            )
        out.append("")
    return "\n".join(out).rstrip()
