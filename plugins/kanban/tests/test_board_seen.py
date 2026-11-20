"""The board page's "what changed since you last looked" comparison.

The functions live in a marked block of board/index.html (the page is one
file). This test cuts the block out and runs it in Node.
"""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

PAGE = Path(__file__).resolve().parent.parent / "board" / "index.html"
BLOCK = re.compile(r"// ---- seen:begin\n(.*?)// ---- seen:end", re.S)

DRIVER = r"""
var input = JSON.parse(require("fs").readFileSync(0, "utf8"));
var out = input.map(function (c) {
  if (c.op === "fnv") return fnv(c.s);
  if (c.op === "entry") return entryOf(c.card);
  if (c.op === "snapshot") return snapshotOf(c.cards);
  if (c.op === "diff") return diffBoard(c.base, c.cards);
  if (c.op === "patch-diff") { patchBase(c.base, c.id, c.patch, c.card); return { base: c.base, diff: diffBoard(c.base, c.cards) }; }
  throw new Error("unknown op " + c.op);
});
process.stdout.write(JSON.stringify(out));
"""


def run(cases):
    m = BLOCK.search(PAGE.read_text(encoding="utf-8"))
    if not m:
        raise AssertionError("board/index.html has no `// ---- seen:begin` ... `// ---- seen:end` block")
    p = subprocess.run(["node", "-e", m.group(1) + DRIVER], input=json.dumps(cases),
                       capture_output=True, text=True, timeout=30)
    if p.returncode:
        raise AssertionError(p.stderr)
    return json.loads(p.stdout)


def card(cid, status="doing", title=None, summary="Works.", next_step="Ship it.", session="s1"):
    return {"id": cid, "title": title or cid.title(), "status": status, "summary": summary,
            "next_step": next_step, "sessions": [{"id": session}] if session else []}


def base_of(*cards):
    return run([{"op": "snapshot", "cards": list(cards)}])[0]


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class SeenTest(unittest.TestCase):
    def test_fnv_is_fnv1a_32(self):
        self.assertEqual(run([{"op": "fnv", "s": ""}, {"op": "fnv", "s": "a"}]), ["811c9dc5", "e40c292c"])

    def test_entry_fields(self):
        e = run([{"op": "entry", "card": card("a", "todo", "A title", "S", "N", "sess-9")}])[0]
        self.assertEqual(e["t"], "A title")
        self.assertEqual(e["s"], "todo")
        self.assertEqual(e["x"], "sess-9")
        self.assertEqual(len(e["h"]), 8)
        self.assertNotEqual(e["h"], e["n"])

    def test_entry_without_sessions_or_text(self):
        e = run([{"op": "entry", "card": {"id": "a", "status": "idea"}}])[0]
        self.assertEqual(e["x"], "")
        self.assertEqual(e["t"], "")
        self.assertEqual(e["h"], "811c9dc5")

    def test_no_baseline_shows_nothing(self):
        d = run([{"op": "diff", "base": None, "cards": [card("a")]}])[0]
        self.assertEqual(d["total"], 0)
        self.assertEqual(d["byId"], {})
        self.assertEqual(d["removed"], [])

    def test_new_card(self):
        d = run([{"op": "diff", "base": {}, "cards": [card("a")]}])[0]
        self.assertEqual(d["counts"]["new"], 1)
        self.assertEqual(d["byId"]["a"]["kinds"], ["new"])
        self.assertEqual(d["total"], 1)

    def test_moved_card_keeps_the_old_column(self):
        base = base_of(card("a", "todo"))
        d = run([{"op": "diff", "base": base, "cards": [card("a", "doing")]}])[0]
        self.assertEqual(d["byId"]["a"]["kinds"], ["moved"])
        self.assertEqual(d["byId"]["a"]["from"], "todo")
        self.assertEqual(d["counts"]["moved"], 1)

    def test_renamed_card(self):
        base = base_of(card("a", title="Old name"))
        d = run([{"op": "diff", "base": base, "cards": [card("a", title="New name")]}])[0]
        self.assertEqual(d["byId"]["a"]["kinds"], ["renamed"])

    def test_updated_by_summary_next_step_or_session(self):
        base = base_of(card("a"), card("b"), card("c"))
        d = run([{"op": "diff", "base": base, "cards": [
            card("a", summary="Rewritten."), card("b", next_step="Other step."), card("c", session="s2")]}])[0]
        for cid in "abc":
            self.assertEqual(d["byId"][cid]["kinds"], ["updated"], cid)
        self.assertEqual(d["counts"]["updated"], 3)

    def test_moved_and_updated(self):
        base = base_of(card("a", "todo"))
        d = run([{"op": "diff", "base": base, "cards": [card("a", "done", summary="Looks finished.")]}])[0]
        self.assertEqual(d["byId"]["a"]["kinds"], ["moved", "updated"])

    def test_unchanged_card_is_left_out(self):
        base = base_of(card("a"))
        d = run([{"op": "diff", "base": base, "cards": [card("a")]}])[0]
        self.assertEqual(d["byId"], {})
        self.assertEqual(d["total"], 0)

    def test_removed_card_by_old_title(self):
        base = base_of(card("gone", title="Old"))
        d = run([{"op": "diff", "base": base, "cards": []}])[0]
        self.assertEqual(d["removed"], [{"id": "gone", "title": "Old"}])
        self.assertEqual(d["counts"]["removed"], 1)
        self.assertEqual(d["total"], 1)

    def test_null_entry_is_not_removed_and_a_card_with_its_id_is_new(self):
        d = run([{"op": "diff", "base": {"x": None}, "cards": []},
                 {"op": "diff", "base": {"x": None}, "cards": [card("x")]}])
        self.assertEqual(d[0]["removed"], [])
        self.assertEqual(d[0]["total"], 0)
        self.assertEqual(d[1]["byId"]["x"]["kinds"], ["new"])

    def test_odd_entries_do_not_throw(self):
        d = run([{"op": "diff", "base": {"a": "junk", "b": {"s": 3}}, "cards": [card("a"), card("b")]}])[0]
        self.assertEqual(d["byId"]["a"]["kinds"], ["new"])
        self.assertIn("b", d["byId"])

    def test_patch_keeps_other_fields(self):
        base = base_of(card("a", "todo"))
        r = run([{"op": "patch-diff", "base": base, "id": "a", "patch": {"s": "done"}, "cards": [card("a", "done")]}])[0]
        self.assertEqual(r["base"]["a"]["t"], "A")
        self.assertEqual(r["base"]["a"]["s"], "done")
        self.assertEqual(r["diff"]["byId"], {})

    def test_patch_null_and_new_entry(self):
        base = base_of(card("a"))
        r = run([{"op": "patch-diff", "base": base, "id": "a", "patch": None, "cards": []},
                 {"op": "patch-diff", "base": {}, "id": "b", "patch": {"t": "B", "s": "idea", "h": "1", "n": "2", "x": ""},
                  "cards": []}])
        self.assertIsNone(r[0]["base"]["a"])
        self.assertEqual(r[0]["diff"]["removed"], [])
        self.assertEqual(r[1]["base"]["b"]["t"], "B")

    def test_own_move_of_a_new_card_is_not_renamed_or_updated(self):
        moved = card("n1", "todo")
        r = run([{"op": "patch-diff", "base": {}, "id": "n1", "patch": {"s": "todo"}, "card": moved, "cards": [moved]},
                 {"op": "patch-diff", "base": {"n1": None}, "id": "n1", "patch": {"s": "todo"}, "card": moved, "cards": [moved]}])
        for x in r:
            self.assertEqual(x["diff"]["byId"], {})
            self.assertEqual(x["base"]["n1"]["t"], "N1")


if __name__ == "__main__":
    unittest.main()
