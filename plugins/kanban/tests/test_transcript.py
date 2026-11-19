import tempfile
import unittest
from pathlib import Path

import fixtures as fx
from kanban import transcript


class DigestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_normal_transcript(self):
        p = fx.normal(self.tmp / "abc-1.jsonl")
        d = transcript.digest(p)
        self.assertEqual(d["id"], "abc-1")
        self.assertEqual(d["title"], "Sauna dashboard UI")  # the last custom-title wins
        self.assertEqual(d["prompts"], ["Build the sauna card for the dashboard", "Make the temperature bigger"])
        self.assertEqual(d["last_prompt"], "Make the temperature bigger")
        self.assertEqual(d["last_reply"], "Done. The card shows the temperature in large type.")
        self.assertEqual(d["turns"], 2)
        self.assertEqual(d["files"], ["/work/proj/a.yaml", "/work/proj/b.yaml"])
        self.assertEqual(d["start"], "2026-11-10T10:00:00Z")
        self.assertEqual(d["end"], "2026-11-10T10:06:00Z")
        self.assertEqual(d["folders"], ["/work/proj"])
        self.assertEqual(d["branch"], "main")
        self.assertFalse(d["unparsed"])
        self.assertFalse(d["sync_session"])

    def test_limits(self):
        long = "x" * 5000
        entries = [fx.user("p%d %s" % (i, long), "2026-11-10T10:0%d:00Z" % i) for i in range(5)]
        entries.append(fx.assistant(long, "2026-11-10T10:09:00Z"))
        d = transcript.digest(fx.write(self.tmp / "s.jsonl", entries))
        self.assertEqual(len(d["prompts"]), 3)
        self.assertTrue(all(len(p) <= 300 for p in d["prompts"]))
        self.assertTrue(d["last_prompt"].startswith("p4 "))
        self.assertLessEqual(len(d["last_prompt"]), 300)
        self.assertLessEqual(len(d["last_reply"]), 1200)
        self.assertEqual(d["turns"], 5)

    def test_what_is_not_a_prompt(self):
        p = fx.write(self.tmp / "s.jsonl", [
            fx.user("<system-reminder>ignore</system-reminder>", "2026-11-10T10:00:00Z", origin=None),
            fx.user("Skill text", "2026-11-10T10:00:01Z", isMeta=True, origin=None),
            fx.tool_result("2026-11-10T10:00:02Z"),
            fx.user("<task-notification>x</task-notification>", "2026-11-10T10:00:03Z",
                    origin={"kind": "task-notification"}),
            fx.user("[Request interrupted by user]", "2026-11-10T10:00:04Z", origin=None),
            fx.user("The real question", "2026-11-10T10:00:05Z"),
            fx.assistant("An answer", "2026-11-10T10:00:06Z"),
        ])
        d = transcript.digest(p)
        self.assertEqual(d["prompts"], ["The real question"])
        self.assertEqual(d["turns"], 1)

    def test_wrapper_blocks_are_stripped(self):
        # The app puts reminder blocks in front of what the user typed.
        e = fx.user("x", "2026-11-10T10:00:00Z")
        e["message"]["content"] = [
            {"type": "text", "text": "<system-reminder>\nLinked sessions now: a, b\n</system-reminder>"},
            {"type": "text", "text": "Please fix the ledger"},
        ]
        only = fx.user("<system-reminder>\nThe session you started was stopped.\n</system-reminder>",
                       "2026-11-10T10:00:02Z")
        joined = fx.user("<system-reminder>a</system-reminder>\n<system-reminder>b</system-reminder>\nSecond ask",
                         "2026-11-10T10:00:03Z")
        p = fx.write(self.tmp / "s.jsonl", [e, fx.assistant("ok", "2026-11-10T10:00:01Z"), only, joined])
        d = transcript.digest(p)
        self.assertEqual(d["prompts"], ["Please fix the ledger", "Second ask"])

    def test_builtin_commands_are_not_prompts(self):
        p = fx.write(self.tmp / "s.jsonl", [
            fx.user("<command-name>/model</command-name>\n<command-message>model</command-message>\n<command-args>claude-x</command-args>",
                    "2026-11-10T10:00:00Z", origin=None),
            fx.user("<local-command-stdout>Set model to x</local-command-stdout>", "2026-11-10T10:00:01Z", origin=None),
            fx.user("<local-command-caveat>Caveat text</local-command-caveat>", "2026-11-10T10:00:01Z", origin=None),
            fx.user("Real work", "2026-11-10T10:00:02Z"),
            fx.assistant("ok", "2026-11-10T10:00:03Z"),
        ])
        d = transcript.digest(p)
        self.assertEqual(d["prompts"], ["Real work"])
        self.assertFalse(d["sync_session"])

    def test_prompt_without_origin_field(self):
        # Older or other versions have no origin field: plain text still counts.
        e = fx.user("Plain old prompt", "2026-11-10T10:00:00Z")
        del e["origin"]
        d = transcript.digest(fx.write(self.tmp / "s.jsonl", [e, fx.assistant("ok", "2026-11-10T10:00:01Z")]))
        self.assertEqual(d["prompts"], ["Plain old prompt"])

    def test_session_started_by_another_session(self):
        # No human prompt at all: the first plain text entry is the task.
        p = fx.write(self.tmp / "s.jsonl", [
            fx.user("Build the plugin as briefed", "2026-11-10T10:00:00Z", origin={"kind": "session"}),
            fx.assistant("On it", "2026-11-10T10:00:01Z"),
        ])
        d = transcript.digest(p)
        self.assertEqual(d["prompts"], ["Build the plugin as briefed"])
        self.assertFalse(d["unparsed"])

    def test_text_blocks_as_prompt(self):
        e = fx.user("x", "2026-11-10T10:00:00Z")
        e["message"]["content"] = [{"type": "text", "text": "Prompt in a block"}]
        d = transcript.digest(fx.write(self.tmp / "s.jsonl", [e, fx.assistant("ok", "2026-11-10T10:00:01Z")]))
        self.assertEqual(d["prompts"], ["Prompt in a block"])

    def test_title_fallbacks(self):
        p = fx.write(self.tmp / "a.jsonl", [fx.title("Generated", "ai-title"),
                                            fx.user("Hello there", "2026-11-10T10:00:00Z"),
                                            fx.assistant("hi", "2026-11-10T10:00:01Z")])
        self.assertEqual(transcript.digest(p)["title"], "Generated")
        p = fx.write(self.tmp / "b.jsonl", [fx.user("A" * 100, "2026-11-10T10:00:00Z"),
                                            fx.assistant("hi", "2026-11-10T10:00:01Z")])
        self.assertEqual(len(transcript.digest(p)["title"]), 60)

    def test_sidechain_ignored(self):
        p = fx.write(self.tmp / "s.jsonl", [
            fx.user("Main prompt", "2026-11-10T10:00:00Z"),
            fx.user("Subagent prompt", "2026-11-10T10:00:01Z", isSidechain=True),
            fx.assistant("Subagent reply", "2026-11-10T10:00:02Z", isSidechain=True),
            fx.assistant("Main reply", "2026-11-10T10:00:03Z"),
        ])
        d = transcript.digest(p)
        self.assertEqual(d["prompts"], ["Main prompt"])
        self.assertEqual(d["last_reply"], "Main reply")

    def test_bad_and_huge_lines(self):
        p = fx.write(self.tmp / "s.jsonl", [fx.user("Hi", "2026-11-10T10:00:00Z"),
                                            fx.assistant("yo", "2026-11-10T10:00:01Z")],
                     raw=["not json at all", '{"type":"api-request-blob","x":"' + "a" * 3000000 + '"}',
                          '{"broken": ', "[1,2,3]", '"just a string"', ""])
        d = transcript.digest(p)
        self.assertEqual(d["prompts"], ["Hi"])
        self.assertFalse(d["unparsed"])

    def test_unknown_format_is_unparsed(self):
        p = fx.write(self.tmp / "s.jsonl", [{"kind": "msg", "body": "x" * 300, "n": i} for i in range(20)])
        d = transcript.digest(p)
        self.assertTrue(d["unparsed"])
        self.assertEqual(d["prompts"], [])

    def test_replies_but_no_prompt_is_unparsed(self):
        e = fx.user("x", "2026-11-10T10:00:00Z")
        e["message"] = {"role": "user", "parts": "new shape"}
        p = fx.write(self.tmp / "s.jsonl", [e, fx.assistant("reply " * 400, "2026-11-10T10:00:01Z")])
        self.assertTrue(transcript.digest(p)["unparsed"])

    def test_empty_and_tiny_files(self):
        p = self.tmp / "e.jsonl"
        p.write_text("")
        d = transcript.digest(p)
        self.assertFalse(d["unparsed"])
        self.assertEqual(d["turns"], 0)
        p = fx.write(self.tmp / "t.jsonl", [fx.title("Only a title")])
        self.assertFalse(transcript.digest(p)["unparsed"])

    def test_missing_file(self):
        d = transcript.digest(self.tmp / "nope.jsonl")
        self.assertEqual(d["turns"], 0)
        self.assertFalse(d["unparsed"])

    def test_sync_session(self):
        for text in ["/kanban:sync", "<command-name>/kanban:sync</command-name>", "[kanban-sync] daily run",
                     "<command-message>kanban:setup</command-message><command-name>/kanban:setup</command-name>"]:
            p = fx.write(self.tmp / "s.jsonl", [fx.user(text, "2026-11-10T10:00:00Z"),
                                                fx.assistant("ok", "2026-11-10T10:00:01Z")])
            self.assertTrue(transcript.digest(p)["sync_session"], text)
        p = fx.write(self.tmp / "s.jsonl", [fx.user("Fix the bug", "2026-11-10T10:00:00Z"),
                                            fx.assistant("ok", "2026-11-10T10:00:01Z"),
                                            fx.user("/kanban:sync", "2026-11-10T10:01:00Z")])
        self.assertFalse(transcript.digest(p)["sync_session"])

    def test_slash_command_prompt_is_readable(self):
        text = "<command-message>flow:start</command-message>\n<command-name>/flow:start</command-name>\n<command-args>add a deploy line</command-args>"
        p = fx.write(self.tmp / "s.jsonl", [fx.user(text, "2026-11-10T10:00:00Z"),
                                            fx.assistant("ok", "2026-11-10T10:00:01Z")])
        self.assertEqual(transcript.digest(p)["prompts"], ["/flow:start add a deploy line"])

    def test_since(self):
        p = fx.normal(self.tmp / "s.jsonl")
        d = transcript.digest(p, since="2026-11-10T10:01:00Z")
        self.assertEqual(d["prompts"], ["Make the temperature bigger"])
        self.assertEqual(d["turns"], 1)
        self.assertEqual(d["files"], ["/work/proj/b.yaml", "/work/proj/a.yaml"])
        self.assertEqual(d["start"], "2026-11-10T10:00:00Z")
        self.assertEqual(d["end"], "2026-11-10T10:06:00Z")
        d = transcript.digest(p, since="2026-11-10T10:06:00Z")
        self.assertEqual(d["turns"], 0)

    def test_many_folders_and_files_are_capped(self):
        entries = [fx.user("go", "2026-11-10T10:00:00Z")]
        for i in range(30):
            entries.append(fx.assistant("step", "2026-11-10T10:%02d:00Z" % (i + 1), cwd="/w/p%d" % i,
                                        tools=[("Edit", "/w/f%d" % i)]))
        d = transcript.digest(fx.write(self.tmp / "s.jsonl", entries))
        self.assertEqual(len(d["folders"]), 5)
        self.assertEqual(len(d["files"]), 15)
        self.assertEqual(d["files_total"], 30)


if __name__ == "__main__":
    unittest.main()
