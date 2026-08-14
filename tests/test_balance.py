"""A bank is balanced per level or not at all.

The case that matters is a pack that looks balanced in aggregate while its
graduate pool is almost entirely recall, which is what the shipped packs did.
"""

import unittest

from studykit.balance import TARGETS, check, mix
from studykit.packs import Pack, Question, Topic


def question(qtype, levels, qid="tq-001"):
    return Question(
        id=qid,
        pack="test",
        topic="widgets",
        subtopic="assembly",
        qtype=qtype,
        levels=tuple(levels),
        q="Q?",
        a="A.",
    )


def pack(questions, levels=("graduate", "mid", "senior"), subtopics=("assembly",)):
    return Pack(
        name="test",
        title="Test pack",
        description="A pack that exists only to be measured.",
        levels=tuple(levels),
        areas=("testing",),
        root=None,
        topics={
            "widgets": Topic(
                id="widgets",
                pack="test",
                title="Widgets",
                area="testing",
                prefix="wd",
                levels=tuple(levels),
                subtopics=tuple(subtopics),
                card=None,
            )
        },
        questions=list(questions),
    )


def spread(counts, levels):
    """One question per type per count, all tagged `levels`."""
    out = []
    for qtype, n in counts.items():
        out += [question(qtype, levels, qid=f"{qtype[:2]}-{i:03d}") for i in range(n)]
    return out


class TestMix(unittest.TestCase):
    def test_an_empty_pool_has_no_mix(self):
        self.assertEqual(mix([]), {})

    def test_shares_are_percentages_of_the_pool(self):
        got = mix(spread({"recall": 3, "judgment": 1}, ("senior",)))
        self.assertEqual(got["recall"], 75)
        self.assertEqual(got["judgment"], 25)
        self.assertEqual(got["numeric"], 0)


class TestCheck(unittest.TestCase):
    def test_a_pool_on_target_is_silent(self):
        counts = {t: TARGETS["senior"][t] for t in TARGETS["senior"]}
        got = check(pack(spread(counts, ("senior",)), levels=("senior",), subtopics=("assembly",)))
        self.assertEqual(got, [])

    def test_aggregate_balance_does_not_hide_a_recall_heavy_graduate_pool(self):
        """The shipped-pack failure: senior is fine, graduate is 90% recall."""
        senior = spread({t: TARGETS["senior"][t] for t in TARGETS["senior"]}, ("senior",))
        graduate = spread({"recall": 90, "discrimination": 10}, ("graduate",))
        notes = check(pack(senior + graduate, levels=("graduate", "senior")))
        self.assertTrue(any("'graduate'" in n and "recall 90%" in n for n in notes))
        self.assertFalse(any("'senior'" in n and "mix" in n for n in notes))

    def test_a_level_the_pack_does_not_declare_is_not_judged(self):
        notes = check(pack(spread({"recall": 50}, ("senior",)), levels=("senior",)))
        self.assertFalse(any("'graduate'" in n for n in notes))

    def test_a_level_with_no_questions_is_reported_against_its_subtopics(self):
        notes = check(pack(spread({"recall": 50}, ("senior",)), levels=("graduate", "senior")))
        self.assertTrue(any("'graduate'" in n and "no questions" in n for n in notes))

    def test_a_pool_too_thin_to_space_is_reported(self):
        notes = check(
            pack(
                spread({"recall": 4, "discrimination": 3, "judgment": 2}, ("senior",)),
                levels=("senior",),
                subtopics=("assembly", "wiring", "testing", "packing", "shipping"),
            )
        )
        self.assertTrue(any("below 2 each" in n for n in notes))

    def test_a_share_inside_tolerance_is_not_reported(self):
        counts = dict(TARGETS["senior"])
        counts["recall"] += 5
        counts["judgment"] -= 5
        notes = check(pack(spread(counts, ("senior",)), levels=("senior",)))
        self.assertFalse(any("mix" in n for n in notes))

    def test_lead_and_staff_share_one_target(self):
        self.assertEqual(TARGETS["lead"], TARGETS["staff"])
        self.assertEqual(TARGETS["senior"], TARGETS["staff"])


if __name__ == "__main__":
    unittest.main()
