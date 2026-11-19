import io
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import fixtures  # noqa: F401  (sets sys.path)
from kanban import cards
from kanban.store import Data

NOW = datetime(2026, 11, 19, 12, 0, 0, tzinfo=timezone.utc)


def session(sid, end="2026-11-18T10:00:00Z", **kw):
    s = {"id": sid, "title": "Title of " + sid, "start": "2026-11-18T09:00:00Z", "end": end,
         "folders": ["/work/proj"], "folder": "/work/proj", "repo": "proj", "repo_root": "/work/proj",
         "known_cards": [], "unparsed": False}
    s.update(kw)
    return s


def card(**kw):
    c = {"title": "Sauna dashboard", "status": "doing", "summary": "Old summary", "next_step": "Old next",
         "log": [{"date": "2026-11-01T10:00:00Z", "text": "Old work", "session": "old-1"}],
         "repos": ["proj"], "folders": ["/work/proj"], "links": [], "sessions": [
             {"id": "old-1", "title": "Old", "date": "2026-11-01T10:00:00Z"}],
         "last_touched": "2026-11-01T10:00:00Z", "created": "2026-10-01T10:00:00Z",
         "status_changed_at": "2026-11-01T10:00:00Z", "is_new": False, "notes": "my notes", "order": 5}
    c.update(kw)
    return c


class ApplyBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(os.path.realpath(tempfile.mkdtemp()))
        self.data = Data(self.tmp / "data")
        self.data.save_config({"url": "u", "machine": "m1"})
        self.sessions = [session("aaaa1111-x"), session("bbbb2222-x", end="2026-11-17T10:00:00Z")]
        self.existing = {}
        self.board = {"title": "Kanban", "last_sync": "2026-11-01T00:00:00Z"}
        self.synced = {}

    def write_inputs(self):
        self.data.write_json("work/digest.json", {
            "sessions": self.sessions, "machine": "m1",
            "repos": [{"name": "proj", "root": "/work/proj", "github": "https://github.com/o/proj",
                       "commits": [], "dirty": []}]})
        for cid, c in self.existing.items():
            self.data.write_json("db/cards/%s.json" % cid, c)
        self.data.write_json("db/meta/board.json", self.board)
        if self.synced:
            self.data.write_json("db/meta/synced.json", {"sessions": self.synced})

    def apply(self, decision, expect=0):
        self.write_inputs()
        decision.setdefault("versions", {})
        decision["versions"].setdefault("meta/board", 1)
        if self.synced:
            decision["versions"].setdefault("meta/synced", 1)
        for cid in self.existing:
            decision["versions"].setdefault("cards/" + cid, 3)
        out = io.StringIO()
        code = cards.apply(self.data, decision, NOW, out)
        self.assertEqual(code, expect, out.getvalue())
        self.output = out.getvalue()
        batch = self.data.read_json("work/batch.json", None)
        self.writes = {w["collection"] + "/" + w["doc_id"]: w for w in batch["writes"]} if batch else {}
        return self.writes

    def doc(self, key):
        return json.loads(Path(self.writes[key]["file_path"]).read_text())

    def all_skipped(self, *ids):
        return [{"id": i, "reason": "test"} for i in ids]


class NewCardTest(ApplyBase):
    def test_new_card(self):
        w = self.apply({"cards": [{"id": None, "title": "Sauna dashboard", "summary": "It works.",
                                   "next_step": "Polish it.",
                                   "sessions": [{"id": "aaaa1111", "log": "Built the card."},
                                                {"id": "bbbb2222-x", "log": "Planned it."}]}], "skip": []})
        key = [k for k in w if k.startswith("cards/")][0]
        self.assertRegex(key, r"^cards/sauna-dashboard-[a-z0-9]{4}$")
        self.assertEqual(w[key]["op"], "set")
        self.assertNotIn("if_version", w[key])
        c = self.doc(key)
        self.assertEqual(c["title"], "Sauna dashboard")
        self.assertEqual(c["status"], "doing")
        self.assertTrue(c["is_new"])
        self.assertEqual(c["last_touched"], "2026-11-18T10:00:00Z")
        self.assertEqual(c["status_changed_at"], "2026-11-18T10:00:00Z")
        self.assertEqual(c["created"], "2026-11-18T09:00:00Z")
        self.assertEqual(c["repos"], ["proj"])
        self.assertEqual(c["folders"], ["/work/proj"])
        self.assertEqual(c["links"], [{"label": "GitHub: proj", "url": "https://github.com/o/proj"}])
        self.assertEqual([e["text"] for e in c["log"]], ["Built the card.", "Planned it."])
        self.assertEqual([s["id"] for s in c["sessions"]], ["aaaa1111-x", "bbbb2222-x"])
        self.assertEqual(c["sessions"][0]["title"], "Title of aaaa1111-x")
        self.assertNotIn("order", c)

    def test_new_card_status(self):
        for given, want in [("idea", "idea"), ("done", "done"), ("archived", "doing"), ("nonsense", "doing")]:
            w = self.apply({"cards": [{"id": None, "title": "T", "status": given,
                                       "sessions": [{"id": "aaaa1111-x", "log": "x"}]}],
                            "skip": self.all_skipped("bbbb2222-x")})
            key = [k for k in w if k.startswith("cards/")][0]
            self.assertEqual(self.doc(key)["status"], want, given)

    def test_scratch_session_has_no_repo(self):
        self.sessions = [session("aaaa1111-x", repo=None, repo_root=None, folder="/scratch/a", folders=["/scratch/a"])]
        w = self.apply({"cards": [{"id": None, "title": "T", "sessions": [{"id": "aaaa1111-x", "log": "x"}]}], "skip": []})
        c = self.doc([k for k in w if k.startswith("cards/")][0])
        self.assertEqual(c["repos"], [])
        self.assertEqual(c["folders"], ["/scratch/a"])

    def test_limits(self):
        w = self.apply({"cards": [{"id": None, "title": "T" * 200, "summary": "S" * 2000, "next_step": "N" * 900,
                                   "sessions": [{"id": "aaaa1111-x", "log": "L" * 900}]}],
                        "skip": self.all_skipped("bbbb2222-x")})
        c = self.doc([k for k in w if k.startswith("cards/")][0])
        self.assertEqual((len(c["title"]), len(c["summary"]), len(c["next_step"]), len(c["log"][0]["text"])),
                         (80, 600, 200, 240))

    def test_two_new_cards_with_one_title_get_two_ids(self):
        w = self.apply({"cards": [
            {"id": None, "title": "Same", "sessions": [{"id": "aaaa1111-x", "log": "x"}]},
            {"id": None, "title": "Same", "sessions": [{"id": "bbbb2222-x", "log": "y"}]}], "skip": []})
        self.assertEqual(len([k for k in w if k.startswith("cards/")]), 2)


class ExistingCardTest(ApplyBase):
    def setUp(self):
        super().setUp()
        self.existing = {"sauna-ab12": card()}

    def one(self, **kw):
        d = {"id": "sauna-ab12", "summary": "New summary", "next_step": "New next",
             "sessions": [{"id": "aaaa1111-x", "log": "Did more."}]}
        d.update(kw)
        return {"cards": [d], "skip": self.all_skipped("bbbb2222-x")}

    def test_update_only_changed_fields(self):
        w = self.apply(self.one())
        u = w["cards/sauna-ab12"]
        self.assertEqual(u["op"], "update")
        self.assertEqual(u["if_version"], 3)
        c = self.doc("cards/sauna-ab12")
        self.assertEqual(c["summary"], "New summary")
        self.assertEqual(c["next_step"], "New next")
        self.assertEqual(c["last_touched"], "2026-11-18T10:00:00Z")
        self.assertEqual([e["text"] for e in c["log"]], ["Did more.", "Old work"])
        self.assertEqual([s["id"] for s in c["sessions"]], ["aaaa1111-x", "old-1"])
        for never in ("notes", "order", "title", "created", "status", "status_changed_at", "repos", "folders"):
            self.assertNotIn(never, c)

    def test_title_and_done_are_never_set_on_an_existing_card(self):
        self.apply(self.one(title="Renamed by sync", status="done"))
        c = self.doc("cards/sauna-ab12")
        self.assertNotIn("title", c)
        self.assertNotIn("status", c)

    def test_todo_becomes_doing_after_newer_work(self):
        self.existing = {"sauna-ab12": card(status="todo", status_changed_at="2026-11-10T00:00:00Z")}
        self.apply(self.one())
        c = self.doc("cards/sauna-ab12")
        self.assertEqual(c["status"], "doing")
        self.assertEqual(c["status_changed_at"], "2026-11-19T12:00:00Z")

    def test_hand_set_status_is_kept_when_the_session_is_older(self):
        self.existing = {"sauna-ab12": card(status="todo", status_changed_at="2026-11-18T23:00:00Z")}
        self.apply(self.one())
        self.assertNotIn("status", self.doc("cards/sauna-ab12"))

    def test_done_is_reopened(self):
        for st in ("done", "archived"):
            self.existing = {"sauna-ab12": card(status=st, status_changed_at="2026-11-10T00:00:00Z")}
            self.apply(self.one())
            c = self.doc("cards/sauna-ab12")
            self.assertEqual(c["status"], "doing")
            self.assertTrue(c["log"][0]["text"].startswith("Reopened: "))

    def test_wont_do_card_is_never_reopened(self):
        # The owner dropped it. Newer work is logged, but the status is the owner's.
        self.existing = {"sauna-ab12": card(status="dropped", status_changed_at="2026-11-10T00:00:00Z")}
        self.apply(self.one())
        c = self.doc("cards/sauna-ab12")
        self.assertNotIn("status", c)
        self.assertNotIn("status_changed_at", c)
        self.assertEqual(c["log"][0]["text"], "Did more.")
        self.assertEqual(c["last_touched"], "2026-11-18T10:00:00Z")

    def test_new_card_cannot_start_as_wont_do(self):
        self.existing = {}
        w = self.apply({"cards": [{"id": None, "title": "T", "status": "dropped",
                                   "sessions": [{"id": "aaaa1111-x", "log": "x"}]}],
                        "skip": self.all_skipped("bbbb2222-x")})
        self.assertEqual(self.doc([k for k in w if k.startswith("cards/")][0])["status"], "doing")

    def test_owner_edit_of_next_step_wins_until_newer_work(self):
        self.existing = {"sauna-ab12": card(next_step="Mine", next_step_edited_at="2026-11-18T12:00:00Z")}
        self.apply(self.one())
        self.assertNotIn("next_step", self.doc("cards/sauna-ab12"))
        self.existing = {"sauna-ab12": card(next_step="Mine", next_step_edited_at="2026-11-18T09:30:00Z")}
        self.apply(self.one())
        self.assertEqual(self.doc("cards/sauna-ab12")["next_step"], "New next")

    def test_log_and_sessions_are_capped_and_deduped(self):
        log = [{"date": "2026-10-%02dT10:00:00Z" % (i + 1), "text": "w%d" % i, "session": "o%d" % i} for i in range(25)]
        log.sort(key=lambda e: e["date"], reverse=True)
        sessions = [{"id": "o%d" % i, "title": "t", "date": "2026-10-%02dT10:00:00Z" % (i + 1)} for i in range(25)]
        sessions.sort(key=lambda e: e["date"], reverse=True)
        sessions[3] = {"id": "aaaa1111-x", "title": "earlier part", "date": "2026-10-22T10:00:00Z"}
        self.existing = {"sauna-ab12": card(log=log, sessions=sessions)}
        self.apply(self.one())
        c = self.doc("cards/sauna-ab12")
        self.assertEqual(len(c["log"]), 20)
        self.assertEqual(c["log"][0]["text"], "Did more.")
        self.assertEqual(len(c["sessions"]), 20)
        self.assertEqual([s["id"] for s in c["sessions"]].count("aaaa1111-x"), 1)
        self.assertEqual(c["sessions"][0], {"id": "aaaa1111-x", "title": "Title of aaaa1111-x", "date": "2026-11-18T10:00:00Z"})

    def test_new_repo_and_folder_are_added(self):
        self.sessions[0].update(repo="other", repo_root="/work/other", folder="/work/other")
        self.apply(self.one())
        c = self.doc("cards/sauna-ab12")
        self.assertEqual(c["repos"], ["proj", "other"])
        self.assertEqual(c["folders"], ["/work/proj", "/work/other"])

    def test_one_session_on_two_cards(self):
        self.existing["other-cd34"] = card(title="Other")
        w = self.apply({"cards": [
            {"id": "sauna-ab12", "sessions": [{"id": "aaaa1111-x", "log": "Part one."}]},
            {"id": "other-cd34", "sessions": [{"id": "aaaa1111-x", "log": "Part two."}]}],
            "skip": self.all_skipped("bbbb2222-x")})
        self.assertEqual(self.doc("cards/sauna-ab12")["log"][0]["text"], "Part one.")
        self.assertEqual(self.doc("cards/other-cd34")["log"][0]["text"], "Part two.")
        synced = self.doc("meta/synced")["sessions"]
        self.assertEqual(sorted(synced["aaaa1111-x"]["cards"]), ["other-cd34", "sauna-ab12"])

    def test_done_card_is_archived_after_30_days(self):
        self.existing["old-done"] = card(title="Old", status="done", status_changed_at="2026-10-19T11:00:00Z")
        self.existing["new-done"] = card(title="New", status="done", status_changed_at="2026-10-25T11:00:00Z")
        w = self.apply({"cards": [], "skip": self.all_skipped("aaaa1111-x", "bbbb2222-x")})
        self.assertEqual(self.doc("cards/old-done"), {"status": "archived", "status_changed_at": "2026-11-19T12:00:00Z"})
        self.assertNotIn("cards/new-done", w)
        self.assertNotIn("cards/sauna-ab12", w)


class MetaTest(ApplyBase):
    def test_board_and_synced(self):
        self.synced = {"ancient": {"cards": ["x"], "end": "2026-08-01T00:00:00Z", "machine": "m0"},
                       "recent": {"cards": ["y"], "end": "2026-11-01T00:00:00Z", "machine": "m0"}}
        w = self.apply({"cards": [{"id": None, "title": "T", "sessions": [{"id": "aaaa1111-x", "log": "x"}]}],
                        "skip": [{"id": "bbbb2222-x", "reason": "small talk"}]})
        self.assertEqual(self.doc("meta/board"), {"last_sync": "2026-11-19T12:00:00Z"})
        self.assertEqual(w["meta/board"]["op"], "update")
        self.assertEqual(w["meta/board"]["if_version"], 1)
        s = self.doc("meta/synced")["sessions"]
        self.assertNotIn("ancient", s)  # older than 90 days
        self.assertIn("recent", s)
        self.assertEqual(s["bbbb2222-x"], {"cards": [], "end": "2026-11-17T10:00:00Z", "machine": "m1"})
        self.assertEqual(len(s["aaaa1111-x"]["cards"]), 1)
        self.assertEqual(w["meta/synced"]["op"], "set")
        self.assertEqual(w["meta/synced"]["if_version"], 1)

    def test_first_synced_document_has_no_version(self):
        w = self.apply({"cards": [], "skip": self.all_skipped("aaaa1111-x", "bbbb2222-x")})
        self.assertNotIn("if_version", w["meta/synced"])

    def test_grown_session_keeps_its_earlier_cards(self):
        self.synced = {"aaaa1111-x": {"cards": ["earlier"], "end": "2026-11-10T00:00:00Z", "machine": "m1"}}
        self.apply({"cards": [{"id": None, "title": "T", "sessions": [{"id": "aaaa1111-x", "log": "x"}]}],
                    "skip": self.all_skipped("bbbb2222-x")})
        got = self.doc("meta/synced")["sessions"]["aaaa1111-x"]
        self.assertIn("earlier", got["cards"])
        self.assertEqual(len(got["cards"]), 2)
        self.assertEqual(got["end"], "2026-11-18T10:00:00Z")


class RefusalTest(ApplyBase):
    def refuse(self, decision, needle):
        self.apply(decision, expect=2)
        self.assertIn(needle, self.output)
        self.assertFalse((self.data.work / "out").exists())
        self.assertFalse((self.data.work / "batch.json").exists())

    def good(self, **kw):
        c = {"id": None, "title": "T", "sessions": [{"id": "aaaa1111-x", "log": "x"}]}
        c.update(kw)
        return {"cards": [c], "skip": self.all_skipped("bbbb2222-x")}

    def test_unknown_session(self):
        d = self.good()
        d["cards"][0]["sessions"].append({"id": "zzzz9999", "log": "x"})
        self.refuse(d, "zzzz9999")

    def test_ambiguous_session_prefix(self):
        self.sessions = [session("aaaa1111-x"), session("aaaa1111-y")]
        self.refuse({"cards": [{"id": None, "title": "T", "sessions": [{"id": "aaaa1111", "log": "x"}]}], "skip": []},
                    "aaaa1111")

    def test_unknown_card(self):
        self.refuse(self.good(id="no-such-card"), "no-such-card")

    def test_session_left_out(self):
        d = self.good()
        d["skip"] = []
        self.refuse(d, "bbbb2222-x")

    def test_session_on_four_cards(self):
        cards_ = [{"id": None, "title": "T%d" % i, "sessions": [{"id": "aaaa1111-x", "log": "x"}]} for i in range(4)]
        self.refuse({"cards": cards_, "skip": self.all_skipped("bbbb2222-x")}, "aaaa1111-x")

    def test_new_card_without_title_or_sessions(self):
        self.refuse(self.good(title=" "), "title")
        d = self.good()
        d["cards"][0]["sessions"] = []
        d["skip"] = self.all_skipped("aaaa1111-x", "bbbb2222-x")
        self.refuse(d, "session")

    def test_secrets(self):
        for secret in ["ghp_" + "a1B2" * 9, "sk-ant-" + "x9" * 20, "AKIA" + "ABCDEFGH12345678",
                       "-----BEGIN RSA PRIVATE KEY-----", "xoxb-1234567890-abcdefghij"]:
            self.refuse(self.good(summary="The token is " + secret), "summary")
        d = self.good()
        d["cards"][0]["sessions"][0]["log"] = "password ghp_" + "a1B2" * 9
        self.refuse(d, "log")

    def test_missing_version(self):
        self.existing = {"sauna-ab12": card()}
        self.write_inputs()
        out = io.StringIO()
        code = cards.apply(self.data, {"versions": {"meta/board": 1}, "cards": [
            {"id": "sauna-ab12", "summary": "s", "sessions": [{"id": "aaaa1111-x", "log": "x"}]}],
            "skip": self.all_skipped("bbbb2222-x")}, NOW, out)
        self.assertEqual(code, 2)
        self.assertIn("cards/sauna-ab12", out.getvalue())

    def test_not_json_object(self):
        self.write_inputs()
        out = io.StringIO()
        self.assertEqual(cards.apply(self.data, ["nope"], NOW, out), 2)

    def test_no_digest(self):
        out = io.StringIO()
        self.assertEqual(cards.apply(self.data, {"cards": [], "skip": []}, NOW, out), 2)
        self.assertIn("collect", out.getvalue())


class BatchSplitTest(ApplyBase):
    def test_more_than_50_writes_are_split(self):
        self.sessions = [session("s%03d-xxxx" % i) for i in range(60)]
        d = {"cards": [{"id": None, "title": "Card %d" % i, "sessions": [{"id": "s%03d-xxxx" % i, "log": "x"}]}
                       for i in range(60)], "skip": []}
        self.write_inputs()
        out = io.StringIO()
        self.assertEqual(cards.apply(self.data, dict(d, versions={"meta/board": 1}), NOW, out), 0)
        batch = self.data.read_json("work/batch.json")
        self.assertEqual(len(batch["writes"]), 62)
        self.assertEqual([len(b) for b in batch["batches"]], [50, 12])
        # The meta documents go last: they record the sync as done.
        self.assertEqual({w["collection"] for w in batch["batches"][-1][-2:]}, {"meta"})


if __name__ == "__main__":
    unittest.main()
