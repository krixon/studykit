"""Where packs and data live, and how a pack gets installed."""

import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from studykit import cli
from studykit.config import StudykitError, data_dir, pack_roots, packs_dir, user_packs_dir
from studykit.packs import load_library

MINIMAL_PACK = """\
[pack]
name = "{name}"
title = "Test pack"
description = "A pack that exists only to be found."
levels = ["senior"]
areas = ["testing"]

[calibration.senior]
bar = "Correct and quantified."
assume = "Vocabulary is shared."
push_on = ["numbers"]
avoid = "Do not accept an unquantified claim."

[[topic]]
id = "widgets"
title = "Widgets"
area = "testing"
levels = ["senior"]
subtopics = ["assembly"]
prefix = "wg"
"""

QUESTION = """\
[[q]]
id = "wg-001"
qtype = "recall"
subtopic = "assembly"
levels = ["senior"]
q = "What holds a widget together?"
a = "A grommet."
"""


class EnvTestCase(unittest.TestCase):
    """Environment variables are process-global, so save and restore all of them."""

    KEYS = ("STUDYKIT_DATA", "STUDYKIT_PACKS", "XDG_DATA_HOME")

    def setUp(self):
        self._previous = {k: os.environ.get(k) for k in self.KEYS}

    def tearDown(self):
        for key, value in self._previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class TestDataLocation(EnvTestCase):
    def test_the_default_is_outside_the_checkout(self):
        for key in self.KEYS:
            os.environ.pop(key, None)
        self.assertEqual(data_dir(), Path.home() / ".studykit")
        self.assertFalse(
            data_dir().is_relative_to(packs_dir().parent),
            "the ledger must not sit inside the directory you might re-clone",
        )

    def test_xdg_data_home_is_honoured(self):
        os.environ.pop("STUDYKIT_DATA", None)
        with tempfile.TemporaryDirectory() as xdg:
            os.environ["XDG_DATA_HOME"] = xdg
            self.assertEqual(data_dir(), Path(xdg).resolve() / "studykit")

    def test_an_explicit_data_dir_beats_xdg(self):
        with tempfile.TemporaryDirectory() as xdg, tempfile.TemporaryDirectory() as explicit:
            os.environ["XDG_DATA_HOME"] = xdg
            os.environ["STUDYKIT_DATA"] = explicit
            self.assertEqual(data_dir(), Path(explicit).resolve())

    def test_the_user_pack_root_sits_beside_the_data(self):
        with tempfile.TemporaryDirectory() as explicit:
            os.environ["STUDYKIT_DATA"] = explicit
            self.assertEqual(user_packs_dir(), Path(explicit).resolve() / "packs")
            self.assertIn(user_packs_dir(), pack_roots())


class TestInstalledPacks(EnvTestCase):
    def setUp(self):
        super().setUp()
        self.data = Path(tempfile.mkdtemp(prefix="studykit-packs-"))
        os.environ["STUDYKIT_DATA"] = str(self.data)
        os.environ["NO_COLOR"] = "1"

    def tearDown(self):
        shutil.rmtree(self.data, ignore_errors=True)
        super().tearDown()

    def install(self, name):
        """Drop a pack into the user root, the way a user would."""
        root = self.data / "packs" / name
        (root / "questions").mkdir(parents=True)
        (root / "pack.toml").write_text(MINIMAL_PACK.format(name=name), encoding="utf-8")
        (root / "questions" / "widgets.toml").write_text(QUESTION, encoding="utf-8")
        return root

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(list(args))
        self.assertEqual(code, 0, err.getvalue())
        return out.getvalue()

    def run_json(self, *args):
        return json.loads(self.run_cli(*args))

    def setup_with(self, pack):
        self.run_cli("setup", "--level", "senior", "--packs", pack, "--non-interactive")

    def test_an_installed_pack_is_found(self):
        self.install("widgets-pack")
        library = load_library()
        self.assertIn("widgets-pack", library.all)

    def test_installing_does_not_displace_the_shipped_packs(self):
        """Installing adds to the set, it does not swap the root out."""
        self.install("widgets-pack")
        library = load_library()
        self.assertIn("system-design", library.all)
        self.assertIn("widgets-pack", library.all)

    def test_a_name_collision_is_loud_and_names_both_directories(self):
        self.install("system-design")
        with self.assertRaises(StudykitError) as caught:
            load_library()
        message = str(caught.exception)
        self.assertIn("system-design", message)
        self.assertIn(str(packs_dir()), message)
        self.assertIn(str(self.data / "packs"), message)

    def test_nothing_is_written_into_the_checkout(self):
        """A session must leave `git status` on the tool repo clean."""
        self.install("widgets-pack")
        self.setup_with("widgets-pack")
        self.run_cli(
            "bank",
            "add",
            "--json-text",
            json.dumps(
                {
                    "pack": "widgets-pack",
                    "topic": "widgets",
                    "questions": [{"subtopic": "assembly", "qtype": "recall", "q": "How many?", "a": "Two."}],
                }
            ),
        )
        written = [p for p in packs_dir().rglob("*") if p.is_file()]
        self.assertTrue(written, "sanity: the shipped packs exist")
        for path in written:
            self.assertNotIn("How many?", path.read_text(encoding="utf-8", errors="ignore"))

    def test_packs_reports_where_each_one_came_from(self):
        self.install("widgets-pack")
        self.setup_with("widgets-pack")
        payload = self.run_json("--json", "packs", "--all")
        by_name = {p["name"]: p for p in payload["packs"]}
        self.assertTrue(by_name["widgets-pack"]["installed"])
        self.assertFalse(by_name["system-design"]["installed"])


if __name__ == "__main__":
    unittest.main()
