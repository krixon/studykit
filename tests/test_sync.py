"""Sync, against a real git remote in a temporary directory.

A bare repo on disk stands in for GitHub. That keeps the test hermetic while
still exercising the thing that actually matters: commit, push, and the fact
that derived files never make it into history.
"""

import contextlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from studykit import cli, sync

HAVE_GIT = shutil.which("git") is not None


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True)


@unittest.skipUnless(HAVE_GIT, "git is not installed")
class SyncTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="studykit-sync-"))
        self.data = self.root / "data"
        self.remote = self.root / "remote.git"
        git("init", "--bare", "-b", "main", str(self.remote), cwd=self.root)

        self._previous = os.environ.get("STUDYKIT_DATA")
        os.environ["STUDYKIT_DATA"] = str(self.data)
        os.environ["NO_COLOR"] = "1"
        # A committer identity, in case the machine running the tests has none.
        os.environ.setdefault("GIT_AUTHOR_NAME", "studykit tests")
        os.environ.setdefault("GIT_AUTHOR_EMAIL", "tests@example.invalid")
        os.environ.setdefault("GIT_COMMITTER_NAME", "studykit tests")
        os.environ.setdefault("GIT_COMMITTER_EMAIL", "tests@example.invalid")

        self.run_cli("setup", "--level", "senior", "--packs", "system-design", "--non-interactive")

    def tearDown(self):
        if self._previous is None:
            os.environ.pop("STUDYKIT_DATA", None)
        else:
            os.environ["STUDYKIT_DATA"] = self._previous
        shutil.rmtree(self.root, ignore_errors=True)

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(list(args))
        self.stderr = err.getvalue()
        return code, out.getvalue()

    def run_json(self, *args):
        code, out = self.run_cli(*args)
        self.assertEqual(code, 0, self.stderr)
        return json.loads(out)

    def tracked(self):
        """Paths present on the remote's main branch."""
        listing = git("ls-tree", "-r", "--name-only", "main", cwd=self.remote)
        return set(listing.stdout.split())

    def record_one(self, measured=3):
        return self.run_cli(
            "record",
            "--json-text",
            json.dumps(
                {
                    "session": "quiz",
                    "pack": "system-design",
                    "rows": [
                        {
                            "topic": "caching",
                            "subtopic": "eviction",
                            "measured": measured,
                        }
                    ],
                }
            ),
        )


class TestInit(SyncTestCase):
    def test_init_pushes_the_ledger_and_profile(self):
        self.run_cli("sync", "init", str(self.remote))
        tracked = self.tracked()
        self.assertIn("ledger.jsonl", tracked)
        self.assertIn("profile.json", tracked)

    def test_derived_files_are_never_committed(self):
        self.run_cli("sync", "init", str(self.remote))
        self.record_one()
        self.run_cli("sync")
        tracked = self.tracked()
        self.assertNotIn("state.json", tracked)
        self.assertNotIn("metrics.json", tracked)

    def test_init_records_the_remote_in_the_profile(self):
        self.run_cli("sync", "init", str(self.remote))
        config = self.run_json("config", "get")
        self.assertEqual(config["sync_remote"], str(self.remote))
        self.assertEqual(config["sync_branch"], "main")
        self.assertFalse(config["sync_auto"])

    def test_init_with_auto_turns_auto_on(self):
        self.run_cli("sync", "init", str(self.remote), "--auto")
        self.assertTrue(self.run_json("config", "get")["sync_auto"])

    def test_init_leaves_nothing_uncommitted(self):
        """--auto edits the profile, so it has to land before the first commit."""
        self.run_cli("sync", "init", str(self.remote), "--auto")
        payload = self.run_json("--json", "sync", "status")
        self.assertEqual(payload["uncommitted"], [])
        self.assertEqual(payload["unpushed"], 0)

    def test_init_refuses_to_graft_onto_a_remote_with_history(self):
        # Someone else's machine got there first.
        other = self.root / "other"
        git("clone", str(self.remote), str(other), cwd=self.root)
        (other / "ledger.jsonl").write_text("{}\n", encoding="utf-8")
        git("add", "-A", cwd=other)
        git("commit", "-m", "first", cwd=other)
        git("push", "origin", "main", cwd=other)

        code, _ = self.run_cli("sync", "init", str(self.remote))
        self.assertEqual(code, 2)
        self.assertIn("already has a main branch", self.stderr)
        self.assertIn("git clone", self.stderr)


class TestPush(SyncTestCase):
    def test_sync_without_a_remote_explains_itself(self):
        code, _ = self.run_cli("sync")
        self.assertEqual(code, 2)
        self.assertIn("sync init", self.stderr)

    def test_a_recorded_row_reaches_the_remote(self):
        self.run_cli("sync", "init", str(self.remote))
        self.record_one(measured=4)
        self.run_cli("sync")
        blob = git("show", "main:ledger.jsonl", cwd=self.remote).stdout
        self.assertIn('"subtopic": "eviction"', blob)

    def test_a_second_sync_with_nothing_new_is_a_no_op(self):
        self.run_cli("sync", "init", str(self.remote))
        result = self.run_json("--json", "sync")
        self.assertFalse(result["committed"])
        self.assertEqual(result.get("note"), "already in sync")

    def test_auto_sync_pushes_on_record(self):
        self.run_cli("sync", "init", str(self.remote), "--auto")
        self.record_one()
        self.assertIn('"subtopic": "eviction"', git("show", "main:ledger.jsonl", cwd=self.remote).stdout)

    def test_auto_sync_failure_does_not_fail_the_record(self):
        self.run_cli("sync", "init", str(self.remote), "--auto")
        shutil.rmtree(self.remote)
        code, _ = self.record_one()
        self.assertEqual(code, 0)
        self.assertIn("warning: sync failed", self.stderr)
        # The measurement is still on disk, which is the whole point.
        self.assertEqual(len(self.run_json("export", "ledger")), 1)


class TestConfig(SyncTestCase):
    def test_auto_cannot_be_turned_on_without_a_remote(self):
        code, _ = self.run_cli("config", "set", "sync_auto", "true")
        self.assertEqual(code, 2)
        self.assertIn("Set a remote before", self.stderr)

    def test_setup_force_keeps_the_sync_settings(self):
        self.run_cli("sync", "init", str(self.remote), "--auto")
        self.run_cli("setup", "--level", "staff", "--packs", "system-design", "--non-interactive", "--force")
        config = self.run_json("config", "get")
        self.assertEqual(config["level"], "staff")
        self.assertEqual(config["sync_remote"], str(self.remote))
        self.assertTrue(config["sync_auto"])

    def test_status_reports_off_when_unconfigured(self):
        payload = self.run_json("--json", "sync", "status")
        self.assertFalse(payload["configured"])

    def test_status_reports_unpushed_work(self):
        self.run_cli("sync", "init", str(self.remote))
        self.record_one()
        payload = self.run_json("--json", "sync", "status")
        self.assertTrue(payload["configured"])
        self.assertEqual(payload["unpushed"], 0)
        self.assertIn("ledger.jsonl", payload["uncommitted"])


class TestDoctor(SyncTestCase):
    def test_doctor_notes_that_sync_is_off(self):
        payload = self.run_json("--json", "doctor")
        self.assertTrue(payload["ok"])
        self.assertTrue(any("sync: off" in n for n in payload["notes"]))

    def test_doctor_flags_a_configured_remote_with_no_repository(self):
        self.run_cli("sync", "init", str(self.remote))
        shutil.rmtree(self.data / ".git")
        code, out = self.run_cli("--json", "doctor")
        self.assertEqual(code, 1, "doctor exits 1 when it finds a problem")
        payload = json.loads(out)
        self.assertFalse(payload["ok"])
        self.assertTrue(any("not a git repository" in p for p in payload["problems"]))

    def test_the_enclosing_tool_repo_is_never_mistaken_for_the_data_repo(self):
        """The default data directory sits inside the studykit checkout."""
        inner = self.root / "checkout"
        (inner / "data").mkdir(parents=True)
        git("init", "-b", "main", str(inner), cwd=self.root)
        os.environ["STUDYKIT_DATA"] = str(inner / "data")
        try:
            self.assertFalse(sync.is_repo())
        finally:
            os.environ["STUDYKIT_DATA"] = str(self.data)


if __name__ == "__main__":
    unittest.main()
