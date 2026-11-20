import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import fixtures as fx
from kanban import collect
from kanban.store import Data

NOW = datetime(2026, 11, 19, 12, 0, 0, tzinfo=timezone.utc)


def hook_line(ev, sid, transcript, cwd="/work/proj"):
    return json.dumps({"ev": ev, "ts": "2026-11-19T11:00:00Z", "dir": cwd,
                       "in": {"session_id": sid, "transcript_path": str(transcript), "cwd": cwd}})


class CollectTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(os.path.realpath(tempfile.mkdtemp()))
        self.data = Data(self.tmp / "data")
        self.data.save_config({"url": "https://claude.ai/artifact/x", "machine": "m1", "exclude": []})
        self.projects = self.tmp / "projects"
        self.projects.mkdir()

    def pending(self, *lines):
        with open(str(self.data.path / "pending.jsonl"), "a") as f:
            for line in lines:
                f.write(line + "\n")

    def transcript(self, sid, cwd="/work/proj", project="-work-proj", days_ago=1, **kw):
        p = fx.normal(self.projects / project / (sid + ".jsonl"), cwd=cwd, **kw)
        fx.set_mtime(p, NOW - timedelta(days=days_ago))
        return p

    def run_collect(self, synced=None, scan_days=None):
        return collect.run(self.data, synced or {}, self.projects, scan_days, NOW)

    def ids(self, digest):
        return sorted(s["id"] for s in digest["sessions"])

    def test_hook_session(self):
        t = self.transcript("s-hook", days_ago=400)  # old file: only the hook line finds it
        self.pending(hook_line("end", "s-hook", t))
        d = self.run_collect()
        self.assertEqual(self.ids(d), ["s-hook"])
        self.assertEqual(d["sessions"][0]["source"], "hook")
        self.assertEqual(d["sessions"][0]["title"], "Sauna dashboard UI")

    def test_scan_finds_session_without_hook(self):
        self.transcript("s-scan", days_ago=2)
        self.transcript("s-old", days_ago=45)
        d = self.run_collect()
        self.assertEqual(self.ids(d), ["s-scan"])
        self.assertEqual(d["sessions"][0]["source"], "scan")

    def test_scan_window_after_a_sync(self):
        self.transcript("s-before", days_ago=5)
        self.transcript("s-after", days_ago=1)
        stamp = self.data.path / "last-sync"
        stamp.write_text("")
        fx.set_mtime(stamp, NOW - timedelta(days=3))
        self.assertEqual(self.ids(self.run_collect()), ["s-after"])
        # An explicit window overrides the stamp.
        self.assertEqual(self.ids(self.run_collect(scan_days=30)), ["s-after", "s-before"])

    def test_same_session_logged_three_times(self):
        t = self.transcript("s-dup")
        self.pending(hook_line("start", "s-dup", t), hook_line("end", "s-dup", t), hook_line("end", "s-dup", t))
        d = self.run_collect()
        self.assertEqual(self.ids(d), ["s-dup"])

    def test_hook_line_without_transcript_path_is_found_by_id(self):
        self.transcript("s-find", days_ago=400)
        self.pending(json.dumps({"ev": "end", "ts": "x", "dir": "/work/proj", "in": {"session_id": "s-find"}}))
        self.assertEqual(self.ids(self.run_collect()), ["s-find"])

    def test_bad_hook_lines(self):
        t = self.transcript("s-cut", days_ago=400)
        cut = hook_line("end", "s-cut", t)[:-9]  # a line capped by the hook: not valid JSON
        self.pending("garbage", cut, '{"ev":"end","in":null}', "")
        d = self.run_collect()
        self.assertEqual(self.ids(d), ["s-cut"])

    def test_synced_sessions(self):
        self.transcript("s-same")
        self.transcript("s-grown")
        synced = {"s-same": {"cards": ["c1"], "end": "2026-11-10T10:06:00Z"},
                  "s-grown": {"cards": ["c2"], "end": "2026-11-10T10:01:00Z"}}
        d = self.run_collect(synced=synced)
        self.assertEqual(self.ids(d), ["s-grown"])
        self.assertEqual(d["skipped"]["synced"], 1)
        s = d["sessions"][0]
        self.assertEqual(s["prompts"], ["Make the temperature bigger"])  # only what is new
        self.assertEqual(s["known_cards"], ["c2"])

    def test_again_reads_a_synced_session_from_its_start(self):
        # A card that sync wrote wrong: read its session again, also when nothing is new
        # and the file is older than the scan window.
        self.transcript("86a44c20-full-id", days_ago=40)
        self.transcript("s-other", days_ago=40)
        synced = {"86a44c20-full-id": {"cards": ["sauna-ab12"], "end": "2026-11-10T10:06:00Z"}}
        d = collect.run(self.data, synced, self.projects, None, NOW, again=["86a44c20"])
        self.assertEqual(self.ids(d), ["86a44c20-full-id"])
        s = d["sessions"][0]
        self.assertTrue(s["again"])
        self.assertEqual(s["prompts"], ["Build the sauna card for the dashboard", "Make the temperature bigger"])
        self.assertEqual(s["known_cards"], ["sauna-ab12"])
        self.assertEqual(d["again_missing"], [])
        md = (self.data.work / "digest.md").read_text()
        self.assertIn("read again from the start", md)
        self.assertIn("asked 1: Build the sauna card for the dashboard\n  → Looking at it.", md)

    def test_again_names_an_id_it_cannot_find(self):
        d = collect.run(self.data, {}, self.projects, None, NOW, again=["nothere1", "abc"])
        self.assertEqual(d["again_missing"], ["nothere1"])  # under 6 characters: ignored

    def test_work_after_a_mid_turn_sync_is_not_lost(self):
        # A sync ran while a turn was going. The rest of that turn has no new prompt.
        self.transcript("s-mid")
        d = self.run_collect(synced={"s-mid": {"cards": ["c1"], "end": "2026-11-10T10:05:30Z"}})
        self.assertEqual(self.ids(d), ["s-mid"])
        s = d["sessions"][0]
        self.assertEqual(s["turns"], 0)
        self.assertIn("large type", s["last_reply"])
        self.assertEqual(s["known_cards"], ["c1"])
        self.assertIn("no new prompt", (self.data.work / "digest.md").read_text())

    def test_scheduled_runs_are_left_out(self):
        text = '<scheduled-task name="morning-brief" file="/x">\nThis is an automated run.\nMake my brief.\n</scheduled-task>'
        p = fx.write(self.projects / "-w" / "s-sched.jsonl", [
            fx.user(text, "2026-11-18T10:00:00Z", origin={"kind": "task-notification"}),
            fx.assistant("ok", "2026-11-18T10:00:01Z")])
        fx.set_mtime(p, NOW - timedelta(days=1))
        d = self.run_collect()
        self.assertEqual(d["sessions"], [])
        self.assertEqual(d["skipped"]["scheduled"], 1)

    def test_session_already_on_a_card_is_not_taken_twice(self):
        # The record in meta/synced was lost (a sync died between two batches),
        # but the card on the board names the session.
        self.transcript("s-oncard")
        self.transcript("s-grew")
        cards = {"c9": {"sessions": [{"id": "s-oncard", "date": "2026-11-10T10:06:00Z"},
                                     {"id": "s-grew", "date": "2026-11-10T10:01:00Z"}]}}
        d = collect.run(self.data, {}, self.projects, None, NOW, cards=cards)
        self.assertEqual(self.ids(d), ["s-grew"])
        self.assertEqual(d["sessions"][0]["known_cards"], ["c9"])
        self.assertEqual(d["skipped"]["synced"], 1)

    def test_exclude_by_repo_name(self):
        self.transcript("s-keep", cwd="/work/proj")
        self.transcript("s-named", cwd="/elsewhere/client-x/sub", project="-e-client-x-sub")
        self.transcript("s-wt", cwd="/gone/secret-repo/.claude/worktrees/w1", project="-gone-secret")
        cfg = self.data.config()
        cfg["exclude"] = ["client-x", "secret-repo"]
        self.data.save_config(cfg)
        d = self.run_collect()
        self.assertEqual(self.ids(d), ["s-keep"])
        self.assertEqual(d["skipped"]["excluded"], 2)

    def test_exclude_by_path_and_glob(self):
        self.transcript("s-keep", cwd="/work/proj")
        self.transcript("s-secret", cwd="/work/client-x", project="-work-client-x")
        self.transcript("s-sub", cwd="/work/client-x/sub", project="-work-client-x-sub")
        self.transcript("s-glob", cwd="/jobs/acme-site", project="-jobs-acme-site")
        cfg = self.data.config()
        cfg["exclude"] = ["/work/client-x", "/jobs/acme-*"]
        self.data.save_config(cfg)
        d = self.run_collect()
        self.assertEqual(self.ids(d), ["s-keep"])
        self.assertEqual(d["skipped"]["excluded"], 3)

    def test_skips_sync_sessions_and_empty_sessions(self):
        p = fx.write(self.projects / "-w" / "s-sync.jsonl", [
            fx.user("[kanban-sync] daily", "2026-11-18T10:00:00Z"), fx.assistant("ok", "2026-11-18T10:00:01Z")])
        fx.set_mtime(p, NOW - timedelta(days=1))
        p = fx.write(self.projects / "-w" / "s-empty.jsonl", [fx.title("Nothing here")])
        fx.set_mtime(p, NOW - timedelta(days=1))
        d = self.run_collect()
        self.assertEqual(d["sessions"], [])
        self.assertEqual(d["skipped"]["sync_session"], 1)
        self.assertEqual(d["skipped"]["no_prompt"], 1)

    def test_unparsed_session_is_kept_and_marked(self):
        p = fx.write(self.projects / "-w" / "s-odd.jsonl", [{"kind": "m", "body": "x" * 300} for _ in range(20)])
        fx.set_mtime(p, NOW - timedelta(days=1))
        d = self.run_collect()
        self.assertEqual(self.ids(d), ["s-odd"])
        self.assertTrue(d["sessions"][0]["unparsed"])

    def test_removed_worktree_maps_to_main_repo(self):
        self.transcript("s-wt", cwd="/gone/repo/.claude/worktrees/w1", project="-gone-repo-wt")
        s = self.run_collect()["sessions"][0]
        self.assertEqual(s["repo_root"], "/gone/repo")
        self.assertEqual(s["repo"], "repo")

    def test_scratch_workspace_has_no_repo(self):
        cwd = "/Users/x/Library/Application Support/Claude/scratch-workspaces/a/b/scratch-2026-11-12-4fe9fe"
        self.transcript("s-scratch", cwd=cwd, project="-scratch")
        s = self.run_collect()["sessions"][0]
        self.assertIsNone(s["repo"])
        self.assertIsNone(s["repo_root"])

    def test_real_git_repo(self):
        repo = self.tmp / "myrepo"
        (repo / "sub").mkdir(parents=True)
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                   GIT_COMMITTER_EMAIL="t@t")
        def git(*a):
            subprocess.run(["git", "-C", str(repo)] + list(a), check=True, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        git("init", "-q")
        (repo / "f.txt").write_text("x")
        git("add", "."); git("commit", "-qm", "First commit here")
        git("remote", "add", "origin", "git@github.com:owner/myrepo.git")
        (repo / "dirty.txt").write_text("y")
        self.transcript("s-git", cwd=str(repo / "sub"), project="-myrepo")
        d = self.run_collect()
        s = d["sessions"][0]
        self.assertEqual(s["repo_root"], str(repo))
        self.assertEqual(s["repo"], "myrepo")
        r = d["repos"][0]
        self.assertEqual(r["github"], "https://github.com/owner/myrepo")
        self.assertTrue(any("First commit here" in c for c in r["commits"]))
        self.assertTrue(any("dirty.txt" in x for x in r["dirty"]))

    def test_pending_is_taken_and_kept_until_commit(self):
        t = self.transcript("s-a")
        self.pending(hook_line("end", "s-a", t))
        self.run_collect()
        self.assertFalse((self.data.path / "pending.jsonl").exists())
        self.assertEqual(len(list(self.data.path.glob("processing-*.jsonl"))), 1)
        # A second collect (the first sync died) still sees the session.
        self.assertEqual(self.ids(self.run_collect()), ["s-a"])

    def test_writes_digest_files(self):
        self.transcript("s-a")
        self.run_collect()
        work = self.data.path / "work"
        self.assertEqual(json.loads((work / "digest.json").read_text())["sessions"][0]["id"], "s-a")
        md = (work / "digest.md").read_text()
        self.assertIn("Sauna dashboard UI", md)
        self.assertIn("s-a", md)

    def test_sync_files_stay_out_of_dot_claude(self):
        from kanban.store import exchange_dir
        home = Path("/home/u")
        self.assertEqual(exchange_dir(home / ".claude/plugins/data/kanban-x", {}, home),
                         home / ".cache/kanban-board/kanban-x")
        self.assertEqual(exchange_dir(home / ".claude/plugins/data/kanban-x", {"XDG_CACHE_HOME": "/c"}, home),
                         Path("/c/kanban-board/kanban-x"))
        self.assertEqual(exchange_dir(home / "elsewhere/data", {}, home), home / "elsewhere/data")
        self.assertEqual(exchange_dir(home / ".claude/x", {"KANBAN_WORK_DIR": "/w"}, home), Path("/w"))

    def test_newest_sessions_first_and_cap(self):
        for i in range(5):
            self.transcript("s-%d" % i, days_ago=i + 1, day="2026-11-1%d" % (5 - i))
        d = collect.run(self.data, {}, self.projects, None, NOW, max_sessions=3)
        self.assertEqual([s["id"] for s in d["sessions"]], ["s-0", "s-1", "s-2"])
        self.assertEqual(d["skipped"]["over_cap"], 2)


if __name__ == "__main__":
    unittest.main()
