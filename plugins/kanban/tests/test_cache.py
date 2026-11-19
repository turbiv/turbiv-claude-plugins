import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import fixtures as fx
from kanban import cache, cli
from kanban.store import Data

NOW = datetime(2026, 11, 19, 12, 0, 0, tzinfo=timezone.utc)
TOOL = Path(__file__).resolve().parent.parent / "bin" / "kanban-tool"


def key(folder):
    return "".join(ch if ch.isalnum() and ch.isascii() else "-" for ch in folder)


def card(title, status="doing", touched="2026-11-18T10:00:00Z", folders=("/work/proj",), **kw):
    c = {"title": title, "status": status, "summary": "Summary of " + title, "next_step": "Next of " + title,
         "last_touched": touched, "folders": list(folders), "repos": ["proj"]}
    c.update(kw)
    return c


class ContextTest(unittest.TestCase):
    def test_order_limit_and_rest(self):
        cards = {
            "a": card("Todo new", "todo", "2026-11-19T10:00:00Z"),
            "b": card("Doing old", "doing", "2026-11-01T10:00:00Z"),
            "c": card("Doing new", "doing", "2026-11-18T10:00:00Z"),
            "d": card("Done thing", "done"), "e": card("Archived thing", "archived"), "f": card("Idea thing", "idea"),
            "g": card("Elsewhere", folders=["/other"]),
        }
        for i in range(5):
            cards["t%d" % i] = card("Todo %d" % i, "todo", "2026-11-0%dT10:00:00Z" % (i + 1))
        text = cache.render_context(cards, "/work/proj", NOW)
        self.assertLess(text.index("Doing new"), text.index("Doing old"))
        self.assertLess(text.index("Doing old"), text.index("Todo new"))
        for absent in ("Done thing", "Archived thing", "Idea thing", "Elsewhere"):
            self.assertNotIn(absent, text)
        self.assertEqual(text.count("\n- "), 5)
        self.assertIn("3 more open cards", text)
        self.assertIn("/kanban:board", text)
        self.assertIn("Next of Doing new", text)
        self.assertLessEqual(len(text), 1500)

    def test_length_cap_with_long_text(self):
        cards = {str(i): card("T%d " % i + "x" * 70, summary="s" * 600, next_step="n" * 200) for i in range(5)}
        text = cache.render_context(cards, "/work/proj", NOW)
        self.assertLessEqual(len(text), 1500)
        self.assertGreaterEqual(text.count("\n- "), 3)

    def test_no_open_cards_gives_empty_text(self):
        self.assertEqual(cache.render_context({"a": card("Done", "done")}, "/work/proj", NOW), "")

    def test_text_is_marked_as_data(self):
        text = cache.render_context({"a": card("X")}, "/work/proj", NOW)
        self.assertIn("not a request", text)


class CommitTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(os.path.realpath(tempfile.mkdtemp()))
        self.data = Data(self.tmp / "data")
        self.data.save_config({"url": "u", "machine": "m1"})
        self.repo = self.tmp / "repo"
        (self.repo / ".git").mkdir(parents=True)
        self.plain = self.tmp / "plain"
        self.plain.mkdir()

    def prepare(self, cards):
        self.data.write_json("work/final.json", {"cards": cards, "used": {}, "skipped": []})
        self.data.write_json("work/batch.json", {"writes": [], "batches": []})
        (self.data.path / "processing-1-1.jsonl").write_text('{"ev":"end","in":{"session_id":"s1"}}\n')
        (self.data.work / "carry.jsonl").write_text('{"ev":"end","in":{"session_id":"later"}}\n')

    def test_commit(self):
        self.prepare({"a": card("In repo", folders=[str(self.repo)]),
                      "b": card("In plain", folders=[str(self.plain)]),
                      "c": card("Folder gone", folders=["/does/not/exist"])})
        stale = self.data.path / "context" / "tree" / "old.txt"
        stale.parent.mkdir(parents=True)
        stale.write_text("old")
        out = io.StringIO()
        self.assertEqual(cache.commit(self.data, NOW, out), 0)
        d = self.data.path
        self.assertIn("In repo", (d / "context" / "tree" / (key(str(self.repo)) + ".txt")).read_text())
        self.assertIn("In plain", (d / "context" / "exact" / (key(str(self.plain)) + ".txt")).read_text())
        self.assertFalse(stale.exists())
        self.assertEqual(len(list((d / "context").rglob("*.txt"))), 2)
        self.assertEqual(sorted(json.loads((d / "cards.json").read_text())["cards"]), ["a", "b", "c"])
        self.assertIn("s1", (d / "log.jsonl").read_text())
        self.assertEqual(list(d.glob("processing-*.jsonl")), [])
        self.assertIn("later", (d / "pending.jsonl").read_text())
        self.assertTrue((d / "last-sync").exists())
        self.assertFalse((d / "work" / "batch.json").exists())

    def test_commit_twice_is_refused(self):
        self.prepare({})
        self.assertEqual(cache.commit(self.data, NOW, io.StringIO()), 0)
        out = io.StringIO()
        self.assertEqual(cache.commit(self.data, NOW, out), 2)

    def test_commit_without_apply_is_refused_and_changes_nothing(self):
        (self.data.path / "processing-1-1.jsonl").write_text("{}\n")
        out = io.StringIO()
        self.assertEqual(cache.commit(self.data, NOW, out), 2)
        self.assertTrue((self.data.path / "processing-1-1.jsonl").exists())
        self.assertFalse((self.data.path / "last-sync").exists())

    def test_home_folder_gets_only_an_exact_file(self):
        home = Path(os.path.expanduser("~"))
        self.prepare({"a": card("Home card", folders=[str(home)])})
        cache.commit(self.data, NOW, io.StringIO())
        self.assertEqual(list((self.data.path / "context" / "tree").glob("*.txt")), [])
        self.assertEqual(len(list((self.data.path / "context" / "exact").glob("*.txt"))), 1)

    def test_refresh_from_db_snapshot(self):
        self.data.write_json("db/cards/a.json", card("From db", folders=[str(self.repo)]))
        self.assertEqual(cache.refresh(self.data, NOW, io.StringIO()), 0)
        self.assertIn("From db", (self.data.path / "context" / "tree" / (key(str(self.repo)) + ".txt")).read_text())
        self.assertFalse((self.data.path / "last-sync").exists())


class CliTest(unittest.TestCase):
    """The whole flow through the real command, as the skills run it."""

    def setUp(self):
        self.tmp = Path(os.path.realpath(tempfile.mkdtemp()))
        self.d = self.tmp / "data dir"   # a space, on purpose
        self.projects = self.tmp / "projects"

    def tool(self, *args, stdin=None, expect=0):
        r = subprocess.run([sys.executable, str(TOOL)] + list(args), input=stdin, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True)
        self.assertEqual(r.returncode, expect, r.stdout)
        return r.stdout

    def test_needs_setup(self):
        out = self.tool("begin", "--data", str(self.d), expect=2)
        self.assertIn("/kanban:setup", out)

    def test_full_flow(self):
        d = str(self.d)
        out = self.tool("init", "--data", d, "--url", "https://claude.ai/artifact/abc")
        self.assertIn("https://claude.ai/artifact/abc", out)
        cfg = json.loads((self.d / "config.json").read_text())
        self.assertEqual(len(cfg["machine"]), 8)
        # init again keeps the machine id and the exclude list
        self.tool("exclude", "--data", d, "--add", "/work/secret")
        self.tool("init", "--data", d, "--url", "https://claude.ai/artifact/abc")
        cfg2 = json.loads((self.d / "config.json").read_text())
        self.assertEqual((cfg2["machine"], cfg2["exclude"]), (cfg["machine"], ["/work/secret"]))
        self.assertIn("/work/secret", self.tool("exclude", "--data", d, "--list"))
        self.tool("exclude", "--data", d, "--remove", "/work/secret")

        fx.normal(self.projects / "-work-proj" / "s-one.jsonl")
        out = self.tool("begin", "--data", d)
        self.assertIn(str(self.d / "db"), out)
        # collect before the board was listed is refused
        self.assertIn("ArtifactData", self.tool("collect", "--data", d, "--projects", str(self.projects), expect=2))
        (self.d / "db" / "meta").mkdir(parents=True)
        (self.d / "db" / "meta" / "board.json").write_text('{"title": "Kanban"}')
        out = self.tool("collect", "--data", d, "--projects", str(self.projects), "--scan-days", "100000")
        self.assertIn("s-one", out)
        self.assertIn("By repo:", out)
        self.assertIn("==== SESSIONS ====", out)        # a small digest is printed
        self.assertIn("Make the temperature bigger", out)
        decision = {"versions": {"meta/board": 1}, "skip": [],
                    "cards": [{"id": None, "title": "Sauna", "summary": "s", "next_step": "n",
                               "sessions": [{"id": "s-one", "log": "Did it."}]}]}
        out = self.tool("apply", "--data", d, stdin=json.dumps(decision))
        self.assertIn('"op": "set"', out)
        out = self.tool("commit", "--data", d)
        self.assertIn("1 card", out)
        self.assertIn("Sauna", self.tool("show", "--data", d))
        # A second sync: the session is on the board, so nothing is new.
        synced = (self.d / "work" / "out" / "meta" / "synced.json").read_text()
        self.tool("begin", "--data", d)
        (self.d / "db" / "meta").mkdir(parents=True)
        (self.d / "db" / "meta" / "board.json").write_text('{"title": "Kanban"}')
        (self.d / "db" / "meta" / "synced.json").write_text(synced)
        out = self.tool("collect", "--data", d, "--projects", str(self.projects), "--scan-days", "100000")
        self.assertIn("Nothing new", out)
        self.assertIn("apply", self.tool("commit", "--data", d, expect=2))

    def test_apply_bad_json(self):
        d = str(self.d)
        self.tool("init", "--data", d, "--url", "https://claude.ai/artifact/abc")
        self.assertIn("JSON", self.tool("apply", "--data", d, stdin="{not json", expect=2))

    def test_index_prints_cards(self):
        d = str(self.d)
        self.tool("init", "--data", d, "--url", "https://claude.ai/artifact/abc")
        Data(self.d).write_json("db/cards/sauna-ab12.json", card("Sauna dashboard"))
        out = self.tool("index", "--data", d)
        self.assertIn("sauna-ab12", out)
        self.assertIn("Sauna dashboard", out)


if __name__ == "__main__":
    unittest.main()
