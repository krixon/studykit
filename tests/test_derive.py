"""Figures in a question are derived, not asserted.

The cases here are the real ones: every failure this catches is a mistake that
was made in a live session and reached the ledger before anyone noticed.
"""

import unittest

from studykit.config import StudykitError
from studykit.derive import ambiguous_scales, check, evaluate, figures
from studykit.packs import Question


def question(q="Q?", a="A.", derivation=()):
    return Question(
        id="tq-001",
        pack="test",
        topic="widgets",
        subtopic="assembly",
        qtype="numeric",
        levels=("staff",),
        q=q,
        a=a,
        derivation=tuple(derivation),
    )


class TestEvaluate(unittest.TestCase):
    def test_names_carry_forward(self):
        env = evaluate(["req = 2_000_000 * 40", "setup_ms = 2 * 140", "days = req * setup_ms / 1000 / 86400"])
        self.assertEqual(env["req"], 80_000_000)
        self.assertAlmostEqual(env["days"], 259.259, places=2)

    def test_the_whitelisted_functions_work(self):
        env = evaluate(["bits = 89.48", "k = round(bits * log(2))"])
        self.assertEqual(env["k"], 62)

    def test_a_trailing_comment_is_ignored(self):
        self.assertEqual(evaluate(["n = 5000 * 600  # per window"])["n"], 3_000_000)

    def test_an_undefined_name_is_refused(self):
        with self.assertRaisesRegex(StudykitError, "not defined above it"):
            evaluate(["total = missing * 2"])

    def test_arbitrary_code_is_refused(self):
        for line in (
            "n = __import__('os').getcwd()",
            "n = open('/etc/passwd').read()",
            "n = [1, 2, 3]",
            "n = 'text'",
            "n = (lambda: 1)()",
        ):
            with self.subTest(line=line), self.assertRaises(StudykitError):
                evaluate([line])

    def test_a_huge_exponent_cannot_hang_the_process(self):
        with self.assertRaisesRegex(StudykitError, "exponent above"):
            evaluate(["n = 2 ** 10000000"])

    def test_division_by_zero_is_a_clean_error(self):
        with self.assertRaisesRegex(StudykitError, "division by zero"):
            evaluate(["n = 1 / 0"])


class TestFigures(unittest.TestCase):
    def found(self, text):
        return sorted(f.raw for f in figures(text))

    def test_units_scales_and_separators_are_magnitudes(self):
        self.assertEqual(
            self.found("280 ms of setup, 32 MB, 80M requests, 268,435,456 bits, 52%, 25x, 1e-19"),
            ["1e-19", "25x", "268,435,456 bits", "280 ms", "32 MB", "52%", "80M"],
        )

    def test_bare_counts_are_left_alone(self):
        self.assertEqual(self.found("TLS 1.3 needs 1 round trip; take the next 3 distinct nodes at RF=3"), [])

    def test_a_comma_separated_list_is_not_a_thousands_separator(self):
        """The ring positions A#2, A#0, B#1 are punctuation, not numbers."""
        self.assertEqual(self.found("the ring reads A#2, A#0, B#1 and you take 3"), [])

    def test_a_unit_written_against_its_number_is_still_a_magnitude(self):
        """No space is the common way to write these, and it used to match nothing."""
        self.assertEqual(
            self.found("40ms of queries, 200KB per key, 5s of stall, 5days of replay"),
            ["200KB", "40ms", "5days", "5s"],
        )

    def test_an_adjacent_unit_keeps_its_own_value(self):
        found = {f.raw: f.value for f in figures("40ms and 3MB")}
        self.assertEqual(found, {"40ms": 40.0, "3MB": 3.0})

    def test_a_lowercase_m_with_no_unit_is_ambiguous(self):
        self.assertEqual(ambiguous_scales(figures("retries at 1m, 5m and 30m")), ["1m", "30m", "5m"])

    def test_an_uppercase_M_is_million_by_convention(self):
        self.assertEqual(ambiguous_scales(figures("80M requests and 5 million users")), [])

    def test_a_scaled_figure_carrying_a_unit_is_not_ambiguous(self):
        self.assertEqual(ambiguous_scales(figures("2m rps sustained")), [])

    def test_odds_are_read_as_the_proportion_they_mean(self):
        odds = [f for f in figures("about 1 in 5 per step") if "in" in f.raw]
        self.assertEqual(len(odds), 1)
        self.assertAlmostEqual(odds[0].value, 0.2)


class TestCheck(unittest.TestCase):
    def test_a_derived_figure_passes(self):
        problems, _ = check(
            question(
                a="Setup is 280 ms per call, so 11.2 seconds per user per day.",
                derivation=["setup_ms = 2 * 140", "per_user_s = 40 * setup_ms / 1000"],
            )
        )
        self.assertEqual(problems, [])

    def test_the_stem_figure_that_contradicted_its_own_answer(self):
        """TLS 1.2 at 150 ms RTT is 3 round trips, so the stem's 350 ms was wrong."""
        problems, _ = check(
            question(
                q="Origin is 150 ms RTT away, TLS 1.2, and the first request carries 350 ms of setup.",
                a="TLS 1.2 is 1 RTT of TCP plus 2 of TLS.",
                derivation=["rtt_ms = 150", "setup_ms = 3 * rtt_ms"],
            )
        )
        self.assertEqual(len(problems), 1)
        self.assertIn("350 ms", problems[0])

    def test_the_invented_figure(self):
        """12% was asserted; the bug it describes produces 52%."""
        problems, _ = check(
            question(
                q="A check reports 12% of keys are stored on only two machines.",
                derivation=["distinct = 4 / 5 * 3 / 5", "under = 1 - distinct"],
            )
        )
        self.assertEqual(len(problems), 1)
        self.assertIn("12%", problems[0])

    def test_the_figure_that_survived_a_rewritten_scenario(self):
        """1 in 3 was right for 3 nodes and stayed after the stem moved to 5."""
        problems, _ = check(
            question(
                q="Five machines, 256 virtual nodes each.",
                a="The chance a next position is already held is about 1 in 3 per step.",
                derivation=["collide = (256 - 1) / (5 * 256 - 1)"],
            )
        )
        self.assertEqual(len(problems), 1)
        self.assertIn("1 in 3", problems[0])

    def test_rounding_in_the_prose_is_accepted(self):
        problems, _ = check(
            question(a="About 260 human-days of waiting per day.", derivation=["days = 80_000_000 * 0.28 / 86400"])
        )
        self.assertEqual(problems, [])

    def test_scientific_notation_claims_only_an_order_of_magnitude(self):
        problems, _ = check(
            question(a="A false positive rate around 1e-19.", derivation=["fp = 0.5 ** 62"])
        )
        self.assertEqual(problems, [])

    def test_a_figure_written_to_the_ten_may_round_to_the_ten(self):
        """30x for 29.33 is fine; 350 ms for 450 is not, and both are one digit apart."""
        loose, _ = check(question(a="About 30x the memory.", derivation=["ratio = 1980 / 67.5"]))
        self.assertEqual(loose, [])
        tight, _ = check(question(a="About 350 ms.", derivation=["ms = 3 * 150"]))
        self.assertEqual(len(tight), 1)

    def test_a_broken_derivation_is_the_problem_reported(self):
        problems, _ = check(question(a="200 ms.", derivation=["ms = nonsense * 2"]))
        self.assertEqual(len(problems), 1)
        self.assertIn("not defined above it", problems[0])

    def test_figures_without_a_derivation_are_only_a_note(self):
        """Adding this check must not retroactively fail the shipped packs."""
        problems, notes = check(question(a="Origin sees 200 ms of latency."))
        self.assertEqual(problems, [])
        self.assertEqual(len(notes), 1)

    def test_a_question_with_no_figures_needs_nothing(self):
        self.assertEqual(check(question(q="Why is queue depth a poor alert?", a="Because.")), ([], []))


if __name__ == "__main__":
    unittest.main()
