"""Arithmetic in a question, evaluated rather than trusted.

A figure in a stem or an answer is something the candidate is scored against, so
a wrong one produces an unfair score in an append-only ledger. `derivation`
carries the arithmetic as named assignments; this module runs it and checks every
figure in the prose against the results.

The figure scanner is deliberately conservative: it looks only at numbers
carrying a unit, a scale word, a thousands separator, an exponent, or a
magnitude of 1000 or more. Bare counts like "TLS 1.3" or "the next 3 nodes" are
not magnitudes and are left alone. This is a net, not a proof.
"""

from __future__ import annotations

import ast
import math
import operator
import re
from dataclasses import dataclass

from .config import StudykitError

_FUNCS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "exp": math.exp,
    "sqrt": math.sqrt,
    "ceil": math.ceil,
    "floor": math.floor,
}

_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}

#: `2 ** 10 ** 9` would hang the process before any check ran.
_MAX_EXPONENT = 1024


def evaluate(lines) -> dict[str, float]:
    """Run a derivation, returning each assigned name in order."""
    env: dict[str, float] = {}
    for line in lines:
        text = line.split("#", 1)[0].strip()
        if not text:
            continue
        try:
            tree = ast.parse(text, mode="exec")
        except SyntaxError as exc:
            raise StudykitError(f"derivation {text!r}: {exc.msg}") from None
        if len(tree.body) != 1 or not isinstance(tree.body[0], ast.Assign):
            raise StudykitError(f"derivation {text!r}: expected one `name = expression`")
        targets = tree.body[0].targets
        if len(targets) != 1 or not isinstance(targets[0], ast.Name):
            raise StudykitError(f"derivation {text!r}: assign to a single plain name")
        env[targets[0].id] = _eval(tree.body[0].value, env, text)
    if not env:
        raise StudykitError("derivation has no assignments")
    return env


def _eval(node, env: dict[str, float], where: str) -> float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise StudykitError(f"derivation {where!r}: only numbers are allowed")
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in env:
            raise StudykitError(f"derivation {where!r}: {node.id} is not defined above it")
        return env[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = _eval(node.operand, env, where)
        return -value if isinstance(node.op, ast.USub) else value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        left = _eval(node.left, env, where)
        right = _eval(node.right, env, where)
        if isinstance(node.op, ast.Pow) and abs(right) > _MAX_EXPONENT:
            raise StudykitError(f"derivation {where!r}: exponent above {_MAX_EXPONENT}")
        try:
            return _BINOPS[type(node.op)](left, right)
        except ZeroDivisionError:
            raise StudykitError(f"derivation {where!r}: division by zero") from None
        except OverflowError:
            raise StudykitError(f"derivation {where!r}: result too large") from None
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCS:
            raise StudykitError(
                f"derivation {where!r}: allowed calls are {', '.join(sorted(_FUNCS))}"
            )
        if node.keywords:
            raise StudykitError(f"derivation {where!r}: keyword arguments are not allowed")
        args = [_eval(arg, env, where) for arg in node.args]
        try:
            return float(_FUNCS[node.func.id](*args))
        except (TypeError, ValueError) as exc:
            raise StudykitError(f"derivation {where!r}: {node.func.id}: {exc}") from None
    raise StudykitError(f"derivation {where!r}: {type(node).__name__} is not allowed here")


_SCALES = {
    "k": 1e3,
    "thousand": 1e3,
    "m": 1e6,
    "million": 1e6,
    "bn": 1e9,
    "billion": 1e9,
}

_UNIT = r"""
    %|ms\b|s\b|secs?\b|seconds?\b|mins?\b|minutes?\b|hrs?\b|hours?\b|days?\b
    |bits?\b|bytes?\b|[KMGT]i?B\b|/s\b|/sec\b|per\s+second\b|rps\b|qps\b
"""

# Concatenated rather than interpolated: an f-string reads a regex quantifier
# like \d{1,3} as a replacement field and silently rewrites the pattern.
_FIGURE = re.compile(
    r"""
    (?<![\w.])
    # A separator only counts when it groups three digits, so the commas in
    # "A#2, A#0, B#1" stay punctuation.
    (?P<num>\d{1,3}(?:[,_]\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?(?:e-?\d+)?)
    (?P<mult>x)?
    \s*
    (?P<scale>k|m|bn|thousand|million|billion)?\b
    \s*
    (?P<unit>"""
    + _UNIT
    + r""")?
    """,
    re.VERBOSE | re.IGNORECASE,
)


#: "1 in 5 per step" is a magnitude carrying no unit, and it is the shape a
#: rewritten scenario breaks most quietly. Compared as the proportion it means.
_ODDS = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s+in\s+(\d[\d,_]*)(?![\w.])")


#: A written figure is allowed to round, but no looser than this, or the check
#: stops distinguishing 350 from 450.
_FLOOR = 0.05
_CEILING = 0.2


@dataclass(frozen=True)
class Figure:
    raw: str
    value: float
    #: Half the place value of the last digit actually written: "350 ms" is
    #: precise to the ten, "0.1%" to the hundredth.
    slack: float
    #: 1e-19 is a claim about the order of magnitude and nothing finer.
    magnitude_only: bool = False
    #: "1 in 5" is a precise claim, and its own last digit says nothing useful
    #: about how much rounding to permit.
    odds: bool = False

    def matches(self, value: float) -> bool:
        if self.value == 0:
            return abs(value) < 1e-12
        if self.magnitude_only:
            return 1 / 3 <= abs(value / self.value) <= 3
        error = abs(value - self.value) / abs(self.value)
        if self.odds:
            return error <= 0.08
        return error <= min(_CEILING, max(_FLOOR, self.slack / abs(self.value)))


def _half_place(numeral: str) -> float:
    """Half the place value of the last written digit."""
    plain = numeral.replace(",", "").replace("_", "").lower()
    if "e" in plain:
        mantissa, exponent = plain.split("e")
        return _half_place(mantissa) * 10 ** int(exponent)
    if "." in plain:
        return 0.5 * 10 ** -len(plain.split(".")[1])
    # Trailing zeros are not significant: 350 is written to the nearest ten.
    stripped = plain.rstrip("0")
    return 0.5 * 10 ** (len(plain) - len(stripped))


def _significant(numeral: str) -> int:
    digits = numeral.split("e")[0].replace(",", "").replace("_", "").replace(".", "")
    return len(digits.lstrip("0")) or 1


def figures(text: str) -> list[Figure]:
    """Every magnitude in the text, with the bare counts left out."""
    out: list[Figure] = []
    for match in _FIGURE.finditer(text):
        numeral = match.group("num")
        scale = (match.group("scale") or "").lower()
        unit = match.group("unit")
        plain = numeral.replace(",", "").replace("_", "")
        try:
            value = float(plain)
        except ValueError:
            continue
        if scale:
            value *= _SCALES[scale]
        interesting = bool(unit or scale or match.group("mult") or "," in numeral)
        if "e" in plain.lower() or abs(value) >= 1000:
            interesting = True
        if not interesting:
            continue
        scaling = _SCALES[scale] if scale else 1
        out.append(
            Figure(
                raw=match.group(0).strip(),
                value=value,
                slack=_half_place(numeral) * scaling,
                magnitude_only="e" in plain.lower() and _significant(numeral) == 1,
            )
        )
    for match in _ODDS.finditer(text):
        denominator = float(match.group(2).replace(",", "").replace("_", ""))
        if not denominator:
            continue
        out.append(
            Figure(
                raw=match.group(0).strip(),
                value=float(match.group(1)) / denominator,
                slack=0.0,
                odds=True,
            )
        )
    return out


def check(question) -> tuple[list[str], list[str]]:
    """Cross-check one question's prose against its derivation.

    Returns (problems, notes). A question with no derivation is only ever a note,
    so adding this check cannot retroactively fail a pack that predates it.
    """
    found = figures(question.q) + figures(question.a)
    if not question.derivation:
        if found:
            listed = ", ".join(sorted({f.raw for f in found})[:6])
            return [], [f"{question.id}: figures with no derivation ({listed})"]
        return [], []

    try:
        env = evaluate(question.derivation)
    except StudykitError as exc:
        return [f"{question.id}: {exc}"], []

    values = list(env.values())
    problems = [
        f"{question.id}: {figure.raw!r} matches no derivation result"
        for figure in found
        if not any(figure.matches(value) for value in values)
    ]
    quoted = {
        name
        for name, value in env.items()
        if any(figure.matches(value) for figure in found)
    }
    notes = []
    if unused := [n for n in env if n not in quoted]:
        notes.append(f"{question.id}: derivation results never quoted ({', '.join(unused)})")
    return problems, notes
