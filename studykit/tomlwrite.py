"""Just enough TOML writing to append a question to a bank.

Banking appends rendered `[[q]]` blocks rather than re-serialising a whole file,
so hand-authored formatting and comments in the shipped packs survive untouched.
"""

from __future__ import annotations

_ESCAPES = {
    "\\": "\\\\",
    '"': '\\"',
    "\b": "\\b",
    "\t": "\\t",
    "\n": "\\n",
    "\f": "\\f",
    "\r": "\\r",
}


def escape(text: str) -> str:
    out = []
    for char in text:
        if char in _ESCAPES:
            out.append(_ESCAPES[char])
        elif ord(char) < 0x20 or ord(char) == 0x7F:
            out.append(f"\\u{ord(char):04X}")
        else:
            out.append(char)
    return "".join(out)


def string(value: str) -> str:
    return f'"{escape(value)}"'


def string_array(values) -> str:
    return "[" + ", ".join(string(str(v)) for v in values) + "]"


def question_block(question: dict) -> str:
    """Render one question as a `[[q]]` table. Key order is fixed for diff sanity."""
    lines = ["[[q]]"]
    lines.append(f"id = {string(question['id'])}")
    lines.append(f"qtype = {string(question['qtype'])}")
    lines.append(f"subtopic = {string(question['subtopic'])}")
    lines.append(f"levels = {string_array(question['levels'])}")
    if question.get("source"):
        lines.append(f"source = {string(question['source'])}")
    lines.append(f"q = {string(question['q'].strip())}")
    lines.append(f"a = {string(question['a'].strip())}")
    return "\n".join(lines) + "\n"


def bank_header(topic: str) -> str:
    return (
        f'# Questions banked during sessions. Format: docs/authoring-packs.md\n'
        f'topic = {string(topic)}\n\n'
    )
