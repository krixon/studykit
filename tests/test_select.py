"""Queue order, level filtering, question drawing and session composition."""

import unittest

from studykit.balance import TARGETS
from studykit.config import StudykitError
from studykit.ledger import Row
from studykit.packs import Question, load_library
from studykit.select import (
    _question_rank,
    build_queue,
    compose,
    draw_questions,
    parse_budget,
    qtype_weights,
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

    def test_a_question_tagged_above_the_level_is_reachable(self):
        """Level gates the topic, not the question. A graduate whose own pool is
        thin gets asked from the rest of an in-scope topic rather than nothing."""
        targets = build_queue(self.library, [], "graduate", "2026-06-01")[:40]
        questions, _ = draw_questions(self.library, [], "graduate", targets, 10, as_of="2026-06-01", seed=1)
        self.assertEqual(len(questions), 10)
        self.assertTrue(any("graduate" not in q.levels for q in questions))

    def test_an_out_of_scope_topic_is_still_never_drawn(self):
        in_scope = {t.id for t in self.library.topics("graduate")}
        questions, _ = draw_questions(
            self.library,
            [],
            "graduate",
            build_queue(self.library, [], "graduate", "2026-06-01")[:40],
            12,
            as_of="2026-06-01",
            seed=1,
        )
        self.assertTrue(questions)
        for question in questions:
            self.assertIn(question.topic, in_scope)

    def test_the_drawn_mix_moves_with_the_level(self):
        targets_g = build_queue(self.library, [], "graduate", "2026-06-01")[:40]
        targets_s = build_queue(self.library, [], "staff", "2026-06-01")[:40]
        grad, _ = draw_questions(self.library, [], "graduate", targets_g, 20, as_of="2026-06-01", seed=1)
        staff, _ = draw_questions(self.library, [], "staff", targets_s, 20, as_of="2026-06-01", seed=1)
        recall_g = sum(1 for q in grad if q.qtype == "recall")
        recall_s = sum(1 for q in staff if q.qtype == "recall")
        judgment_g = sum(1 for q in grad if q.qtype == "judgment")
        judgment_s = sum(1 for q in staff if q.qtype == "judgment")
        self.assertGreater(recall_g, recall_s)
        self.assertGreater(judgment_s, judgment_g)

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


def qrow(qtype, measured, n=1):
    return [
        Row(
            at=f"2026-05-{i + 1:02d}T12:00:00",
            pack="system-design",
            session="quiz",
            topic="caching",
            subtopic="read-strategies",
            measured=measured,
            qtype=qtype,
            qid=f"{qtype}-{i}",
        )
        for i in range(n)
    ]


class TestQuestionRank(unittest.TestCase):
    """Level is a preference inside the chosen type, applied after exposure."""

    @staticmethod
    def question(qid, levels):
        return Question(
            id=qid,
            pack="test",
            topic="widgets",
            subtopic="assembly",
            qtype="recall",
            levels=tuple(levels),
            q="Q?",
            a="A.",
        )

    def test_an_in_level_question_wins_a_tie(self):
        at_level = self.question("a", ("graduate",))
        above = self.question("b", ("staff",))
        ranked = sorted(
            [above, at_level], key=lambda q: _question_rank(q, {}, "2026-06-01", "graduate")
        )
        self.assertEqual(ranked[0].id, "a")

    def test_exposure_still_outranks_the_level(self):
        """Spacing is the primary mechanism; the level only breaks its ties."""
        seen_at_level = self.question("a", ("graduate",))
        unseen_above = self.question("b", ("staff",))
        exposure = {"a": {"reps": 3, "last": "2026-05-01", "scores": [5, 5, 5]}}
        ranked = sorted(
            [seen_at_level, unseen_above],
            key=lambda q: _question_rank(q, exposure, "2026-06-01", "graduate"),
        )
        self.assertEqual(ranked[0].id, "b")

    def test_with_no_level_given_nothing_is_off_level(self):
        one = self.question("a", ("staff",))
        two = self.question("b", ("graduate",))
        self.assertEqual(
            _question_rank(one, {}, "2026-06-01")[2], _question_rank(two, {}, "2026-06-01")[2]
        )


class TestQtypeWeights(unittest.TestCase):
    def test_an_empty_ledger_is_the_level_prior(self):
        self.assertEqual(qtype_weights("senior", []), {k: v / 100 for k, v in TARGETS["senior"].items()})

    def test_the_weights_are_shares(self):
        weights = qtype_weights("mid", qrow("recall", 5, 30) + qrow("judgment", 2, 30))
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=6)

    def test_a_type_answered_well_loses_share(self):
        """The whole point: strong vocabulary backs off without being excluded."""
        weights = qtype_weights("graduate", qrow("recall", 5, 60))
        self.assertLess(weights["recall"], TARGETS["graduate"]["recall"] / 100)
        self.assertGreater(weights["recall"], 0)

    def test_a_type_answered_badly_gains_share(self):
        weights = qtype_weights("senior", qrow("judgment", 2, 60))
        self.assertGreater(weights["judgment"], TARGETS["senior"]["judgment"] / 100)

    def test_a_thin_ledger_barely_moves_the_prior(self):
        prior = TARGETS["senior"]["recall"] / 100
        thin = qtype_weights("senior", qrow("recall", 5, 2))["recall"]
        thick = qtype_weights("senior", qrow("recall", 5, 200))["recall"]
        self.assertLess(abs(thin - prior), abs(thick - prior))
        self.assertAlmostEqual(thin, prior, places=2)

    def test_a_low_target_type_does_not_take_over_on_one_bad_answer(self):
        weights = qtype_weights("graduate", qrow("numeric", 1, 1))
        self.assertLess(weights["numeric"], weights["recall"])

    def test_uniform_mastery_falls_back_to_the_prior(self):
        rows = []
        for qtype in TARGETS["senior"]:
            rows += qrow(qtype, 5, 20)
        self.assertEqual(qtype_weights("senior", rows), {k: v / 100 for k, v in TARGETS["senior"].items()})


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
