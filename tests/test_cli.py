"""End to end through the CLI, against a temporary data directory.

The point of these is the whole path: setup writes a profile, record appends and
rebuilds, and the artefacts other things depend on are actually produced.
"""

import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from studykit import cli


class CliTestCase(unittest.TestCase):
    def setUp(self):
        self.data = Path(tempfile.mkdtemp(prefix="studykit-test-"))
        self._previous = os.environ.get("STUDYKIT_DATA")
        os.environ["STUDYKIT_DATA"] = str(self.data)
        os.environ["NO_COLOR"] = "1"
        self.run_cli("setup", "--level", "senior", "--packs", "system-design", "--non-interactive")

    def tearDown(self):
        if self._previous is None:
            os.environ.pop("STUDYKIT_DATA", None)
        else:
            os.environ["STUDYKIT_DATA"] = self._previous
        shutil.rmtree(self.data, ignore_errors=True)

    def run_cli(self, *args):
        """Run a command, returning (exit code, stdout)."""
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(list(args))
        self.stderr = err.getvalue()
        return code, out.getvalue()

    def run_json(self, *args):
        code, out = self.run_cli(*args)
        self.assertEqual(code, 0, self.stderr)
        return json.loads(out)


class TestSetup(CliTestCase):
    def test_setup_writes_a_profile_and_a_ledger(self):
        self.assertTrue((self.data / "profile.json").exists())
        self.assertTrue((self.data / "ledger.jsonl").exists())
        profile = json.loads((self.data / "profile.json").read_text())
        self.assertEqual(profile["level"], "senior")

    def test_config_set_level_takes_effect(self):
        self.run_cli("config", "set", "level", "graduate")
        self.assertEqual(self.run_json("config", "get")["level"], "graduate")


class TestPlanAndQuestions(CliTestCase):
    def test_plan_returns_blocks_and_questions(self):
        plan = self.run_json("plan", "25m", "--seed", "1", "--date", "2026-06-01")
        self.assertTrue(plan["blocks"])
        quiz = plan["blocks"][0]
        self.assertEqual(quiz["type"], "quiz-set")
        self.assertTrue(quiz["questions"])
        self.assertIn("a", quiz["questions"][0])

    def test_global_flags_work_after_the_subcommand_too(self):
        before = self.run_json("--date", "2026-06-01", "plan", "10m", "--seed", "1")
        after = self.run_json("plan", "10m", "--seed", "1", "--date", "2026-06-01")
        self.assertEqual(before["date"], after["date"])

    def test_questions_honours_a_topic_filter(self):
        result = self.run_json("questions", "--topic", "caching", "--count", "3")
        self.assertTrue(result["questions"])
        self.assertTrue(all(q["topic"] == "caching" for q in result["questions"]))


class TestRecord(CliTestCase):
    payload = json.dumps(
        {
            "session": "quiz",
            "pack": "system-design",
            "rows": [
                {"topic": "caching", "subtopic": "hot-key", "qtype": "recall", "measured": 2, "predicted": 4},
                {"topic": "sharding", "subtopic": "shard-key", "qtype": "judgment", "measured": 5},
            ],
        }
    )

    def test_record_appends_and_rebuilds(self):
        code, _ = self.run_cli("record", "--date", "2026-06-01", "--json-text", self.payload)
        self.assertEqual(code, 0, self.stderr)

        lines = (self.data / "ledger.jsonl").read_text().strip().splitlines()
        self.assertEqual(len(lines), 2)

        state = json.loads((self.data / "state.json").read_text())
        strengths = {i["label"]: i["strength"] for i in state["items"]}
        self.assertEqual(strengths["caching/hot-key"], 2)
        self.assertEqual(strengths["sharding/shard-key"], 5)

        metrics = json.loads((self.data / "metrics.json").read_text())
        self.assertEqual(metrics["summary"]["measurements"], 2)
        # Only the first row carried a predicted, so the mean is over that row alone.
        self.assertEqual(metrics["summary"]["calibration_error"], 2.0)

    def test_dry_run_writes_nothing(self):
        self.run_cli("record", "--date", "2026-06-01", "--dry-run", "--json-text", self.payload)
        self.assertEqual((self.data / "ledger.jsonl").read_text().strip(), "")

    def test_an_invalid_row_exits_two_and_writes_nothing(self):
        bad = json.dumps({"session": "quiz", "pack": "system-design", "rows": [
            {"topic": "caching", "subtopic": "not-a-facet", "measured": 3}]})
        code, _ = self.run_cli("record", "--json-text", bad)
        self.assertEqual(code, 2)
        self.assertIn("no subtopic", self.stderr)
        self.assertEqual((self.data / "ledger.jsonl").read_text().strip(), "")

    def test_rebuild_reproduces_state_exactly(self):
        self.run_cli("record", "--date", "2026-06-01", "--json-text", self.payload)
        before = (self.data / "state.json").read_text()
        (self.data / "state.json").unlink()
        self.run_cli("rebuild", "--date", "2026-06-01")
        self.assertEqual((self.data / "state.json").read_text(), before)


class TestBank(CliTestCase):
    def test_banking_assigns_an_id_and_makes_it_recordable(self):
        result = self.run_json(
            "bank",
            "add",
            "--json-text",
            json.dumps(
                {
                    "pack": "system-design",
                    "topic": "caching",
                    "questions": [
                        {"subtopic": "hot-key", "qtype": "judgment", "q": "Is it hot?", "a": "Yes, -2."}
                    ],
                }
            ),
        )
        question_id = result["questions"][0]["id"]
        self.assertTrue(question_id.startswith("ca-"))
        self.assertTrue((self.data / "bank" / "system-design" / "caching.toml").exists())

        code, _ = self.run_cli(
            "record",
            "--json-text",
            json.dumps(
                {
                    "session": "quiz",
                    "pack": "system-design",
                    "rows": [
                        {
                            "topic": "caching",
                            "subtopic": "hot-key",
                            "qtype": "judgment",
                            "qid": question_id,
                            "measured": 3,
                        }
                    ],
                }
            ),
        )
        self.assertEqual(code, 0, self.stderr)

    def test_banked_ids_do_not_collide_with_the_shipped_pack(self):
        result = self.run_json(
            "bank",
            "add",
            "--json-text",
            json.dumps(
                {
                    "pack": "system-design",
                    "topic": "caching",
                    "questions": [
                        {"subtopic": "eviction", "qtype": "recall", "q": "q1", "a": "a1"},
                        {"subtopic": "eviction", "qtype": "recall", "q": "q2", "a": "a2"},
                    ],
                }
            ),
        )
        ids = [q["id"] for q in result["questions"]]
        self.assertEqual(len(set(ids)), 2)
        # Loading again must not raise on duplicate ids.
        self.run_json("packs", "--json")


class TestReportsAndArtefacts(CliTestCase):
    def test_test_command_is_available(self):
        args = cli.build_parser().parse_args(["test"])
        self.assertIs(args.func, cli.cmd_test)

    def test_status_and_progress_run_on_an_empty_ledger(self):
        for command in ("status", "progress", "queue", "packs", "levels"):
            code, out = self.run_cli(command)
            self.assertEqual(code, 0, f"{command}: {self.stderr}")
            self.assertTrue(out.strip(), command)

    def test_dashboard_is_self_contained(self):
        self.run_cli("record", "--date", "2026-06-01", "--json-text", TestRecord.payload)
        code, _ = self.run_cli("dashboard", "--date", "2026-06-01")
        self.assertEqual(code, 0, self.stderr)
        html = (self.data / "dashboard.html").read_text()
        self.assertIn("<svg", html)
        for forbidden in ("http://", "https://", "<script src", "<link rel=\"stylesheet\""):
            self.assertNotIn(forbidden, html)

    def test_problem_prompt_does_not_leak_the_notes(self):
        code, prompt = self.run_cli("problem", "url-shortener")
        self.assertEqual(code, 0, self.stderr)
        self.assertNotIn("Interviewer notes", prompt)
        self.assertNotIn("Common traps", prompt)

        code, notes = self.run_cli("problem", "url-shortener", "--notes")
        self.assertEqual(code, 0, self.stderr)
        self.assertIn("Common traps", notes)

    def test_doctor_passes_on_the_shipped_packs(self):
        result = self.run_json("doctor", "--json")
        self.assertTrue(result["ok"], result["problems"])


if __name__ == "__main__":
    unittest.main()
