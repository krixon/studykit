"""House style, enforced rather than requested.

`AGENTS.md` said "No em-dashes" and then contained five of them, as did every
card in every pack. A rule nothing checks is a rule that decays, so it is a
test: CI runs it, and so does the pre-push hook.

The banned characters are built with `chr` so this file does not itself contain
the thing it is looking for.
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: Em-dash, and the long dashes that would otherwise be used to evade the rule.
#: The en-dash is included because ranges here are written `1-5` and `45-60m`.
BANNED = {
    chr(0x2014): "em-dash",
    chr(0x2013): "en-dash",
    chr(0x2015): "horizontal bar",
    chr(0x2012): "figure dash",
}

SUFFIXES = (".md", ".py", ".toml", ".yml", ".yaml")

#: `data/` is the user's own, and never ours to lint.
SKIP = {".git", "data", "__pycache__", ".venv", "node_modules"}


def sources():
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix not in SUFFIXES:
            continue
        if SKIP & set(path.relative_to(ROOT).parts):
            continue
        yield path


class TestHouseStyle(unittest.TestCase):
    def test_no_long_dashes(self):
        offences = []
        for path in sources():
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                for character, name in BANNED.items():
                    if character in line:
                        offences.append(f"{path.relative_to(ROOT)}:{number}: {name}")
        self.assertEqual(
            offences,
            [],
            "House style forbids long dashes. Use a colon where the clause expands what "
            "precedes it, a comma where it qualifies, a full stop where it is really a "
            "second sentence:\n  " + "\n  ".join(offences),
        )

    def test_the_check_actually_looks_at_the_content(self):
        """A test that silently walks nothing would pass forever."""
        scanned = list(sources())
        self.assertGreater(len(scanned), 50, "expected to scan the packs and the docs")
        self.assertIn(ROOT / "AGENTS.md", scanned)


if __name__ == "__main__":
    unittest.main()
