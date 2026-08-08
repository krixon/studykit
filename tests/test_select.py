"""Queue order, level filtering, question drawing and session composition."""

import unittest

from studykit.config import StudykitError
from studykit.ledger import Row
from studykit.packs import load_library
from studykit.select import (
    build_queue,
    compose,
    draw_questions,
    parse_budget,
    recommend,
)


def row(date, topic, subtopic, measured, pack="system-design", post=None):
    return Row(
        at=f"{date}T12:00:00",
        pack=pack,
        session="quiz",
        topic=topic,
        subtopic=subtopic,
        measured=measured,
        post=post,
    )


class TestParseBudget(unittest.TestCase):
    def test_minutes_and_hours(self):
        self.assertEqual(parse_budget("15m"), 15)
        self.assertEqual(parse_budget("90"), 90)
        self.assertEqual(parse_budget("1h"), 60)
        self.assertEqual(parse_budget("1.5h"), 90)

    def test_words(self):
        self.assertEqual(parse_budget("half day"), 180)
        self.assertEqual(parse_budget("full day"), 360)

    def test_default_is_used_when_nothing_is_given(self):
        self.assertEqual(parse_budget(None, "25m"), 25)

    def test_rejects_nonsense_and_the_unmeasurably_short(self):
        with self.assertRaises(StudykitError):
            parse_budget("soon")
        with self.assertRaises(StudykitError):
            parse_budget("2m")


class SelectionTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library = load_library(["system-design"])


class TestQueue(SelectionTestCase):
    def test_an_empty_ledger_gives_a_queue_of_unmeasured_facets(self):
        queue = build_queue(self.library, [], "senior", "2026-06-01")
        self.assertTrue(queue)
        self.assertTrue(all(e.reason == "unmeasured" for e in queue))

    def test_overdue_beats_unmeasured(self):
        rows = [row("2026-01-01", "caching", "hot-key", 2)]
        queue = build_queue(self.library, rows, "senior", "2026-06-01")
        self.assertEqual(queue[0].reason, "overdue")
        self.assertEqual(queue[0].subtopic, "hot-key")

    def test_weakest_first_among_the_overdue(self):
        rows = [
            row("2026-01-01", "caching", "hot-key", 5),
            row("2026-01-01", "caching", "eviction", 2),
        ]
        overdue = [e for e in build_queue(self.library, rows, "senior", "2026-06-01") if e.reason == "overdue"]
        self.assertEqual(overdue[0].subtopic, "eviction")

    def test_the_queue_rotates_through_topics(self):
        # Interleaving is worthless if the head of the queue is one topic.
        queue = build_queue(self.library, [], "senior", "2026-06-01")
        head = [e.topic for e in queue[:8]]
        self.assertEqual(len(set(head)), 8)

    def test_level_filters_topics_out_of_scope(self):
        graduate = {e.topic for e in build_queue(self.library, [], "graduate", "2026-06-01")}
        staff = {e.topic for e in build_queue(self.library, [], "staff", "2026-06-01")}
        self.assertNotIn("consistency-models", graduate)  # senior+
        self.assertIn("consistency-models", staff)
        self.assertTrue(graduate < staff)


class TestDrawQuestions(SelectionTestCase):
    def test_draws_the_requested_count_without_repeats(self):
        targets = build_queue(self.library, [], "senior", "2026-06-01")[:20]
        questions, _ = draw_questions(self.library, [], "senior", targets, 8, as_of="2026-06-01", seed=1)
        self.assertEqual(len(questions), 8)
        self.assertEqual(len({q.id for q in questions}), 8)

    def test_only_draws_questions_tagged_for_the_level(self):
        targets = build_queue(self.library, [], "graduate", "2026-06-01")[:40]
        questions, _ = draw_questions(self.library, [], "graduate", targets, 10, as_of="2026-06-01", seed=1)
        self.assertTrue(questions)
        for question in questions:
            self.assertIn("graduate", question.levels)

    def test_consecutive_questions_come_from_different_topics(self):
        targets = build_queue(self.library, [], "senior", "2026-06-01")[:24]
        questions, _ = draw_questions(self.library, [], "senior", targets, 10, as_of="2026-06-01", seed=3)
        topics = [q.topic for q in questions]
        self.assertFalse(any(a == b for a, b in zip(topics, topics[1:])))

    def test_a_question_shown_today_is_not_drawn_again(self):
        targets = build_queue(self.library, [], "senior", "2026-06-01")[:20]
        first, _ = draw_questions(self.library, [], "senior", targets, 4, as_of="2026-06-01", seed=1)
        history = [
            Row(
                at="2026-06-01T12:00:00",
                pack="system-design",
                session="quiz",
                topic=q.topic,
                subtopic=q.subtopic,
                measured=3,
                qid=q.id,
            )
            for q in first
        ]
        second, _ = draw_questions(
            self.library, history, "senior", targets, 4, as_of="2026-06-01", seed=1
        )
        self.assertFalse({q.id for q in first} & {q.id for q in second})

    def test_the_same_seed_gives_the_same_draw(self):
        targets = build_queue(self.library, [], "senior", "2026-06-01")[:20]
        a, _ = draw_questions(self.library, [], "senior", targets, 6, as_of="2026-06-01", seed=42)
        b, _ = draw_questions(self.library, [], "senior", targets, 6, as_of="2026-06-01", seed=42)
        self.assertEqual([q.id for q in a], [q.id for q in b])


class TestCompose(SelectionTestCase):
    def test_a_short_budget_is_a_quiz_set_only(self):
        plan = compose(self.library, [], "senior", 10, as_of="2026-06-01", seed=1)
        self.assertEqual([b["type"] for b in plan["blocks"]], ["quiz-set"])
        self.assertLessEqual(plan["planned_minutes"], 10 + plan["overrun_allowance"])

    def test_the_overrun_allowance_is_bounded_and_reported(self):
        for budget, expected in ((10, 2), (25, 3), (45, 5), (120, 12)):
            plan = compose(self.library, [], "senior", budget, as_of="2026-06-01", seed=1)
            self.assertEqual(plan["overrun_allowance"], expected)
            self.assertLessEqual(plan["planned_minutes"], budget + expected)

    def test_a_long_budget_includes_a_full_problem(self):
        plan = compose(self.library, [], "senior", 60, as_of="2026-06-01", seed=1)
        self.assertIn("full-problem", [b["type"] for b in plan["blocks"]])

    def test_no_problem_flag_is_honoured(self):
        plan = compose(self.library, [], "senior", 60, as_of="2026-06-01", seed=1, allow_problem=False)
        self.assertNotIn("full-problem", [b["type"] for b in plan["blocks"]])

    def test_a_weak_facet_with_reps_behind_it_triggers_a_worked_example(self):
        rows = [
            row("2026-03-01", "caching", "hot-key", 3),
            row("2026-04-01", "caching", "hot-key", 2),
            row("2026-05-01", "caching", "hot-key", 1),
        ]
        plan = compose(self.library, rows, "senior", 45, as_of="2026-06-01", seed=1, allow_problem=False)
        self.assertIn("faded-worked-example", [b["type"] for b in plan["blocks"]])

    def test_a_facet_with_nothing_to_retrieve_gets_taught_not_quizzed(self):
        rows = [row("2026-05-01", "caching", "hot-key", 1)]
        plan = compose(self.library, rows, "senior", 45, as_of="2026-06-01", seed=1, allow_problem=False)
        block = next(b for b in plan["blocks"] if b["type"] == "learn")
        self.assertEqual(block["focus"]["subtopic"], "hot-key")
        self.assertNotIn("faded-worked-example", [b["type"] for b in plan["blocks"]])

    def test_teaching_that_failed_once_is_taught_again_not_faded(self):
        rows = [
            row("2026-03-01", "caching", "hot-key", 2),
            row("2026-04-01", "caching", "hot-key", 2),
            row("2026-05-01", "caching", "hot-key", 2, post=2),
        ]
        plan = compose(self.library, rows, "senior", 45, as_of="2026-06-01", seed=1, allow_problem=False)
        self.assertIn("learn", [b["type"] for b in plan["blocks"]])

    def test_teaching_that_landed_leaves_the_facet_to_the_faded_example(self):
        rows = [
            row("2026-03-01", "caching", "hot-key", 2),
            row("2026-04-01", "caching", "hot-key", 2),
            row("2026-05-01", "caching", "hot-key", 2, post=4),
        ]
        plan = compose(self.library, rows, "senior", 45, as_of="2026-06-01", seed=1, allow_problem=False)
        self.assertNotIn("learn", [b["type"] for b in plan["blocks"]])

    def test_two_blocks_never_target_the_same_facet(self):
        rows = [row("2026-05-01", "caching", "hot-key", 2)]
        plan = compose(self.library, rows, "senior", 90, as_of="2026-06-01", seed=1, allow_problem=False)
        focused = [b["focus"] for b in plan["blocks"] if "focus" in b and b["type"] != "card-writing"]
        keys = [(f["pack"], f["topic"], f["subtopic"]) for f in focused]
        self.assertEqual(len(keys), len(set(keys)))

    def test_teaching_a_weak_facet_outranks_a_problem_for_the_budget(self):
        rows = [row("2026-05-01", "caching", "hot-key", 1)]
        plan = compose(self.library, rows, "senior", 60, as_of="2026-06-01", seed=1)
        types = [b["type"] for b in plan["blocks"]]
        self.assertIn("learn", types)
        self.assertNotIn("full-problem", types)

    def test_a_budget_too_small_for_learn_falls_back_to_the_same_facet(self):
        rows = [row("2026-05-01", "caching", "hot-key", 1)]
        plan = compose(self.library, rows, "senior", 28, as_of="2026-06-01", seed=1, allow_problem=False)
        faded = next(b for b in plan["blocks"] if b["type"] == "faded-worked-example")
        self.assertEqual(faded["focus"]["subtopic"], "hot-key")
        self.assertNotIn("learn", [b["type"] for b in plan["blocks"]])

    def test_learn_and_its_fallback_are_never_both_taken(self):
        rows = [row("2026-05-01", "caching", "hot-key", 1)]
        plan = compose(self.library, rows, "senior", 120, as_of="2026-06-01", seed=1)
        types = [b["type"] for b in plan["blocks"]]
        self.assertIn("learn", types)
        self.assertNotIn("faded-worked-example", types)

    def test_a_drained_queue_reserves_nothing_for_a_quiz(self):
        library = load_library(["system-design"])
        facets = [(t.id, s) for t in library.topics("senior") for s in t.subtopics]
        rows = [row("2026-06-01", topic, subtopic, 5) for topic, subtopic in facets]
        plan = compose(library, rows, "senior", 25, as_of="2026-06-01", seed=1)
        self.assertNotIn("quiz-set", [b["type"] for b in plan["blocks"]])

    def test_a_learn_block_that_does_not_fit_is_reported(self):
        rows = [row("2026-05-01", "caching", "hot-key", 1)]
        plan = compose(self.library, rows, "senior", 15, as_of="2026-06-01", seed=1)
        self.assertNotIn("learn", [b["type"] for b in plan["blocks"]])
        self.assertTrue(any("hot-key" in n for n in plan["notes"]))

    def test_no_note_when_the_fallback_taught_the_facet_anyway(self):
        rows = [row("2026-05-01", "caching", "hot-key", 1)]
        plan = compose(self.library, rows, "senior", 30, as_of="2026-06-01", seed=1, allow_problem=False)
        self.assertIn("faded-worked-example", [b["type"] for b in plan["blocks"]])
        self.assertEqual(plan["notes"], [])

    def test_the_plan_carries_the_level_calibration_brief(self):
        plan = compose(self.library, [], "senior", 25, as_of="2026-06-01", seed=1)
        brief = plan["calibration"]["system-design"]
        self.assertIn("bar", brief)
        self.assertIn("avoid", brief)

    def test_recording_time_is_always_reserved(self):
        plan = compose(self.library, [], "senior", 25, as_of="2026-06-01", seed=1)
        self.assertEqual(plan["recording_reserve"], 2)
        self.assertLessEqual(plan["planned_minutes"], 25 + plan["overrun_allowance"])
        self.assertEqual(sum(b["minutes"] for b in plan["blocks"]) + 2, plan["planned_minutes"])


class TestRecommend(SelectionTestCase):
    def test_an_empty_ledger_recommends_a_first_session(self):
        self.assertIn("first session", recommend(self.library, [], "senior", "2026-06-01")["headline"])

    def test_a_weak_facet_dominates_the_recommendation(self):
        rows = [row("2026-05-01", "caching", "hot-key", 1)]
        headline = recommend(self.library, rows, "senior", "2026-06-01")["headline"]
        self.assertIn("caching/hot-key", headline)


if __name__ == "__main__":
    unittest.main()
