"""Ledger validation.

These are the rules the scoring model previously stated in prose and that got
violated anyway. Each test here corresponds to a rule in docs/scoring.md.
"""

import unittest

from studykit.config import StudykitError
from studykit.ledger import Row, question_exposure, validate
from studykit.packs import load_library


class LedgerTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library = load_library(["system-design"])

    def valid(self, **overrides):
        entry = {
            "date": "2026-01-01",
            "pack": "system-design",
            "session": "quiz",
            "topic": "caching",
            "subtopic": "hot-key",
            "measured": 3,
        }
        entry.update(overrides)
        return entry

    def assertRejected(self, fragment, **overrides):
        with self.assertRaises(StudykitError) as caught:
            validate(self.valid(**overrides), self.library)
        self.assertIn(fragment, str(caught.exception))


class TestAcceptance(LedgerTestCase):
    def test_a_valid_row_passes_and_fills_the_area_in(self):
        row = validate(self.valid(), self.library)
        self.assertEqual(row.topic, "caching")
        self.assertEqual(row.area, "caching")

    def test_optional_fields_survive_the_round_trip(self):
        row = validate(
            self.valid(qtype="judgment", qid="ca-005", predicted=4, post=5, taught=True, note="x"),
            self.library,
        )
        payload = row.as_dict()
        self.assertEqual(payload["predicted"], 4)
        self.assertEqual(payload["post"], 5)
        self.assertTrue(payload["taught"])

    def test_absent_predicted_stays_absent(self):
        # The engine must never invent a self-report the user did not give.
        row = validate(self.valid(), self.library)
        self.assertIsNone(row.predicted)
        self.assertNotIn("predicted", row.as_dict())

    def test_level_falls_back_to_the_profile_level(self):
        row = validate(self.valid(), self.library, default_level="senior")
        self.assertEqual(row.level, "senior")


class TestRejection(LedgerTestCase):
    def test_unknown_topic(self):
        self.assertRejected("no topic", topic="not-a-topic")

    def test_unknown_subtopic(self):
        self.assertRejected("no subtopic", subtopic="not-a-facet")

    def test_unknown_pack(self):
        self.assertRejected("No pack", pack="nope")

    def test_unknown_session(self):
        self.assertRejected("unknown session", session="pondering")

    def test_unknown_qtype(self):
        self.assertRejected("unknown qtype", qtype="vibes")

    def test_score_out_of_range(self):
        self.assertRejected("must be 1-5", measured=6)
        self.assertRejected("must be 1-5", measured=0)

    def test_score_must_be_a_whole_number(self):
        self.assertRejected("whole number", measured=3.5)
        self.assertRejected("whole number", measured=True)

    def test_missing_required_field(self):
        entry = self.valid()
        del entry["measured"]
        with self.assertRaises(StudykitError) as caught:
            validate(entry, self.library)
        self.assertIn("measured", str(caught.exception))

    def test_derived_fields_cannot_be_written(self):
        for field in ("strength", "interval", "due", "reps"):
            with self.assertRaises(StudykitError) as caught:
                validate(self.valid(**{field: 5}), self.library)
            self.assertIn("derived", str(caught.exception))

    def test_unknown_field_is_a_typo_not_a_feature(self):
        self.assertRejected("unknown field", mesured=3)

    def test_unbanked_question_id(self):
        self.assertRejected("not in the", qid="zz-999")


class TestProblemRows(LedgerTestCase):
    def test_a_problem_row_is_accepted(self):
        row = validate(
            self.valid(topic="problem:url-shortener", subtopic="overall", session="practice"),
            self.library,
        )
        self.assertTrue(row.is_problem)

    def test_a_problem_row_must_use_overall(self):
        self.assertRejected(
            "must use subtopic", topic="problem:url-shortener", subtopic="hot-key", session="practice"
        )

    def test_unknown_problem_slug(self):
        self.assertRejected("no problem", topic="problem:invented", subtopic="overall")


class TestExposure(unittest.TestCase):
    def test_exposure_is_derived_from_the_ledger(self):
        rows = [
            Row(date="2026-01-01", pack="p", session="quiz", topic="t", subtopic="s", measured=3, qid="a-1"),
            Row(date="2026-01-05", pack="p", session="quiz", topic="t", subtopic="s", measured=4, qid="a-1"),
            Row(date="2026-01-05", pack="p", session="quiz", topic="t", subtopic="s", measured=2, qid="a-2"),
        ]
        exposure = question_exposure(rows)
        self.assertEqual(exposure["a-1"]["reps"], 2)
        self.assertEqual(exposure["a-1"]["last"], "2026-01-05")
        self.assertEqual(exposure["a-2"]["reps"], 1)


if __name__ == "__main__":
    unittest.main()
