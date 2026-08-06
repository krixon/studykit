"""The interval algorithm and the state it produces.

Concentrated here because none of it is obvious by inspection, and because a
scheduling bug is silent: you find out weeks later that something never came back.
"""

import unittest

from studykit.ledger import Row
from studykit.schedule import (
    CEILING_DAYS,
    compute_items,
    live_items,
    next_interval,
    round_half_up,
)


def row(date, subtopic="a", measured=3, topic="caching", pack="p"):
    return Row(date=date, pack=pack, session="quiz", topic=topic, subtopic=subtopic, measured=measured)


class TestRounding(unittest.TestCase):
    def test_half_rounds_up_not_to_even(self):
        # Python's round() is banker's rounding, which would give 2 here.
        self.assertEqual(round_half_up(2.5), 3)
        self.assertEqual(round_half_up(3.5), 4)
        self.assertEqual(round_half_up(2.4), 2)


class TestNextInterval(unittest.TestCase):
    def test_failure_resets_to_one_day(self):
        for strength in (1, 2):
            self.assertEqual(next_interval(60, strength, 5, is_problem=False), 1)

    def test_multipliers(self):
        self.assertEqual(next_interval(10, 3, 3, is_problem=False), 16)
        self.assertEqual(next_interval(10, 4, 3, is_problem=False), 22)
        self.assertEqual(next_interval(10, 5, 3, is_problem=False), 30)

    def test_three_has_a_two_day_floor(self):
        # 1 * 1.6 rounds to 2 anyway; the floor matters when previous is 1.
        self.assertEqual(next_interval(1, 3, 3, is_problem=False), 2)

    def test_reps_cap_bites_before_the_multiplier(self):
        self.assertEqual(next_interval(60, 5, 1, is_problem=False), 3)
        self.assertEqual(next_interval(60, 5, 2, is_problem=False), 10)
        self.assertEqual(next_interval(20, 5, 3, is_problem=False), 60)

    def test_problems_are_exempt_from_the_reps_cap(self):
        self.assertEqual(next_interval(20, 5, 1, is_problem=True), 60)

    def test_ceiling_applies_to_everything(self):
        self.assertEqual(next_interval(100, 5, 9, is_problem=False), CEILING_DAYS)
        self.assertEqual(next_interval(100, 5, 1, is_problem=True), CEILING_DAYS)


class TestComputeItems(unittest.TestCase):
    def test_first_measurement_uses_the_base_interval_then_the_cap(self):
        [item] = compute_items([row("2026-01-01", measured=5)])
        self.assertEqual(item.strength, 5)
        self.assertEqual(item.reps, 1)
        self.assertEqual(item.interval, 3)  # 2 * 3.0 = 6, capped at 3 by reps=1
        self.assertEqual(item.due, "2026-01-04")

    def test_strength_is_the_latest_not_an_average(self):
        [item] = compute_items([row("2026-01-01", measured=5), row("2026-01-10", measured=2)])
        self.assertEqual(item.strength, 2)
        self.assertEqual(item.interval, 1)

    def test_same_day_measurements_collapse_to_a_mean_and_one_rep(self):
        items = compute_items(
            [
                row("2026-01-01", measured=2),
                row("2026-01-01", measured=4),
                row("2026-01-01", measured=3),
            ]
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].strength, 3)
        self.assertEqual(items[0].reps, 1)

    def test_same_day_mean_rounds_half_up(self):
        [item] = compute_items([row("2026-01-01", measured=2), row("2026-01-01", measured=3)])
        self.assertEqual(item.strength, 3)

    def test_reps_count_dates_not_rows(self):
        rows = [row("2026-01-01"), row("2026-01-01"), row("2026-01-05")]
        [item] = compute_items(rows)
        self.assertEqual(item.reps, 2)

    def test_interval_compounds_across_sessions(self):
        rows = [
            row("2026-01-01", measured=4),  # 2*2.2=4.4->4, capped to 3 (reps 1)
            row("2026-01-04", measured=4),  # 3*2.2=6.6->7, capped to 10 -> 7
            row("2026-01-11", measured=4),  # 7*2.2=15.4->15, uncapped
        ]
        [item] = compute_items(rows)
        self.assertEqual(item.reps, 3)
        self.assertEqual(item.interval, 15)
        self.assertEqual(item.due, "2026-01-26")

    def test_facets_are_tracked_separately(self):
        items = compute_items([row("2026-01-01", subtopic="a"), row("2026-01-01", subtopic="b")])
        self.assertEqual(len(items), 2)

    def test_problem_rows_are_a_separate_kind(self):
        [item] = compute_items(
            [row("2026-01-01", topic="problem:url-shortener", subtopic="overall", measured=4)]
        )
        self.assertEqual(item.kind, "problem")
        self.assertEqual(item.label, "url-shortener")


class TestOverallSupersession(unittest.TestCase):
    def test_overall_survives_while_no_facet_is_measured(self):
        items = live_items(compute_items([row("2026-01-01", subtopic="overall")]))
        self.assertEqual([i.subtopic for i in items], ["overall"])

    def test_overall_is_dropped_once_a_facet_exists(self):
        items = live_items(
            compute_items([row("2026-01-01", subtopic="overall"), row("2026-01-02", subtopic="hot-key")])
        )
        self.assertEqual([i.subtopic for i in items], ["hot-key"])

    def test_supersession_is_per_topic(self):
        rows = [
            row("2026-01-01", topic="caching", subtopic="overall"),
            row("2026-01-02", topic="sharding", subtopic="overall"),
            row("2026-01-03", topic="sharding", subtopic="shard-key"),
        ]
        items = live_items(compute_items(rows))
        labels = sorted(f"{i.topic}/{i.subtopic}" for i in items)
        self.assertEqual(labels, ["caching/overall", "sharding/shard-key"])


if __name__ == "__main__":
    unittest.main()
