"""What a bank can supply, measured per level.

The case that matters is a pack that holds plenty of a type overall while almost
none of its facets have one, because a draw asks a facet at a time.
"""

import unittest

from studykit.balance import TARGETS, check, facet_coverage
from studykit.packs import Pack, Question, Topic

SUBTOPICS = ("assembly", "wiring", "testing", "packing")


def question(qtype, levels, subtopic="assembly", qid=None):
    return Question(
        id=qid or f"{qtype[:2]}-{subtopic[:2]}",
        pack="test",
        topic="widgets",
        subtopic=subtopic,
        qtype=qtype,
        levels=tuple(levels),
        q="Q?",
        a="A.",
    )


def pack(questions, levels=("graduate", "senior"), subtopics=SUBTOPICS):
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


def covering(qtype, level, subtopics):
    return [question(qtype, (level,), st, qid=f"{qtype}-{st}") for st in subtopics]


def every_type(level, subtopics=SUBTOPICS):
    out = []
    for qtype in TARGETS[level]:
        out += covering(qtype, level, subtopics)
    return out


class TestFacetCoverage(unittest.TestCase):
    def test_coverage_is_facets_not_questions(self):
        """Ten judgment questions on one facet still leave the other three bare."""
        crowded = [
            question("judgment", ("senior",), "assembly", qid=f"j-{i}") for i in range(10)
        ]
        coverage = facet_coverage(pack(crowded, levels=("senior",)), "senior")
        self.assertEqual(round(coverage["judgment"]), 25)

    def test_a_level_with_no_facets_has_no_coverage(self):
        self.assertEqual(facet_coverage(pack([], levels=("senior",), subtopics=()), "senior"), {})


class TestCheck(unittest.TestCase):
    def test_full_coverage_is_silent(self):
        self.assertEqual(check(pack(every_type("senior"), levels=("senior",))), [])

    def test_a_type_crowded_onto_one_facet_cannot_supply_the_mix(self):
        """The failure pool share hides: the count is fine, the spread is not."""
        base = every_type("senior")
        base = [q for q in base if q.qtype != "judgment"]
        base += [question("judgment", ("senior",), "assembly", qid=f"j-{i}") for i in range(20)]
        notes = check(pack(base, levels=("senior",)))
        self.assertTrue(any("judgment in 25% of facets" in n for n in notes))

    def test_a_surplus_is_not_reported(self):
        """`select.qtype_weights` caps a type's share, so extra is not a defect."""
        base = every_type("senior")
        base += [question("recall", ("senior",), "assembly", qid=f"r-{i}") for i in range(50)]
        self.assertEqual(check(pack(base, levels=("senior",))), [])

    def test_a_level_the_pack_does_not_declare_is_not_judged(self):
        notes = check(pack(every_type("senior"), levels=("senior",)))
        self.assertFalse(any("'graduate'" in n for n in notes))

    def test_a_level_with_no_questions_is_reported_against_its_facets(self):
        notes = check(pack(every_type("senior"), levels=("graduate", "senior")))
        self.assertTrue(any("'graduate'" in n and "no questions" in n for n in notes))

    def test_a_pool_too_thin_to_space_is_reported(self):
        notes = check(
            pack(
                covering("recall", "senior", SUBTOPICS),
                levels=("senior",),
            )
        )
        self.assertTrue(any("below 2 each" in n for n in notes))

    def test_marginal_coverage_is_not_reported(self):
        """A facet or two short of a target is not an authoring instruction."""
        wide = tuple(f"st{i}" for i in range(10))
        base = every_type("senior", wide)
        # judgment target is 35%; drop to 30% coverage, inside the slack.
        base = [q for q in base if not (q.qtype == "judgment" and q.subtopic in wide[3:])]
        notes = check(pack(base, levels=("senior",), subtopics=wide))
        self.assertFalse(any("judgment" in n for n in notes))

    def test_lead_and_staff_share_one_target(self):
        self.assertEqual(TARGETS["lead"], TARGETS["staff"])
        self.assertEqual(TARGETS["senior"], TARGETS["staff"])


if __name__ == "__main__":
    unittest.main()
