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


class TestBankIds(TestInstalledPacks):
    def bank(self, question, answer="An answer.", pack="widgets-pack"):
        return self.run_json(
            "bank",
            "add",
            "--json-text",
            json.dumps(
                {
                    "pack": pack,
                    "topic": "widgets",
                    "questions": [
                        {"subtopic": "assembly", "qtype": "recall", "q": question, "a": answer}
                    ],
                }
            ),
        )["questions"][0]["id"]

    def test_a_bank_id_cannot_collide_with_a_pack_id(self):
        self.install("widgets-pack")
        self.setup_with("widgets-pack")
        banked = self.bank("What is a grommet?")
        self.assertTrue(banked.startswith("wg-u"), banked)
        self.assertNotIn(banked, {"wg-001", "wg-002", "wg-003"})

    def test_the_same_question_gets_the_same_id_anywhere(self):
        """Two machines banking the same question must not mint two ids."""
        self.install("widgets-pack")
        self.setup_with("widgets-pack")
        first = self.bank("What is a grommet?")

        second_machine = Path(tempfile.mkdtemp(prefix="studykit-other-"))
        try:
            os.environ["STUDYKIT_DATA"] = str(second_machine)
            (second_machine / "packs").mkdir(parents=True)
            shutil.copytree(self.data / "packs" / "widgets-pack", second_machine / "packs" / "widgets-pack")
            self.setup_with("widgets-pack")
            self.assertEqual(self.bank("What is a grommet?"), first)
        finally:
            os.environ["STUDYKIT_DATA"] = str(self.data)
            shutil.rmtree(second_machine, ignore_errors=True)

    def test_different_questions_get_different_ids(self):
        self.install("widgets-pack")
        self.setup_with("widgets-pack")
        self.assertNotEqual(self.bank("What is a grommet?"), self.bank("What is a flange?"))

    def test_the_same_block_arriving_twice_is_not_a_duplicate(self):
        """What a union merge of two machines' bank files produces."""
        self.install("widgets-pack")
        self.setup_with("widgets-pack")
        self.bank("What is a grommet?")
        banked = self.data / "bank" / "widgets-pack" / "widgets.toml"
        body = banked.read_text(encoding="utf-8")
        block = body[body.index("[[q]]") :]
        banked.write_text(body + block, encoding="utf-8")

        library = load_library()
        ids = [q.id for q in library.pack("widgets-pack").questions]
        self.assertEqual(len(ids), len(set(ids)), "the repeated block should collapse")

    def test_one_id_carrying_two_different_questions_is_still_an_error(self):
        self.install("widgets-pack")
        self.setup_with("widgets-pack")
        banked = self.data / "bank" / "widgets-pack" / "widgets.toml"
        body = banked.read_text(encoding="utf-8") if banked.exists() else ""
        banked.parent.mkdir(parents=True, exist_ok=True)
        clash = QUESTION.replace("wg-001", "wg-uaaaaaaaa")
        banked.write_text(body + clash + clash.replace("A grommet.", "A flange."), encoding="utf-8")
        with self.assertRaises(StudykitError) as caught:
            load_library()
        self.assertIn("wg-uaaaaaaaa", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
