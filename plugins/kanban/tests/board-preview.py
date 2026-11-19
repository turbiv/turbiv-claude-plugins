#!/usr/bin/env python3
"""Build a stand-alone preview of the board page, with a fake in-memory db.

Usage: board-preview.py OUT.html [CARDS.json]

The real page needs claude.ai for its data. This wraps board/index.html with
a small mock of window.claude so the layout can be checked in any browser.
CARDS.json is a list of card objects (each with an "id"), or a folder of
card files as `ArtifactData list ... out_dir` saves them. Without it, a few
sample cards are used. Add ?view=1 to the URL for the read-only view and
?empty=1 for the empty board.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE = HERE.parent / "board" / "index.html"


def iso(days_ago):
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def samples():
    def card(i, title, status, age, **kw):
        c = {
            "id": "sample-%d" % i, "title": title, "status": status,
            "summary": kw.get("summary", "The first version works end to end. Two details are still rough."),
            "next_step": kw.get("next_step", "Fix the rough details, then use it for a week."),
            "log": [{"date": iso(age), "text": "Built the first working version.", "session": "s1"},
                    {"date": iso(age + 2), "text": "Compared three ways to build it and picked one.", "session": "s0"}],
            "repos": kw.get("repos", ["sample-repo"]), "folders": ["/Users/you/git/sample-repo"],
            "links": [{"label": "GitHub", "url": "https://github.com/you/sample-repo"}],
            "sessions": [{"id": "0000-1111", "title": "Sample session", "date": iso(age)}],
            "last_touched": iso(age), "created": iso(age + 9), "status_changed_at": iso(age),
            "is_new": kw.get("is_new", False), "notes": kw.get("notes", ""),
        }
        return c
    return [
        card(1, "Sample: sauna dashboard", "doing", 0, is_new=True, repos=["homelab"]),
        card(2, "Sample: vinyl record holder", "doing", 21, repos=["3d-modeling"]),
        card(3, "Sample: a card nobody touched for a long time, with a long title", "todo", 44, repos=["homelab", "ops", "docs", "more"]),
        card(4, "Sample: <img src=x onerror=alert(1)> shows as text", "todo", 3, summary="<b>bold?</b> shows as text", next_step="<script>alert(1)</script>"),
        card(5, "Sample: idea with no repo", "idea", 60, repos=[], summary="", next_step=""),
        card(6, "Sample: finished thing", "done", 5),
        card(7, "Sample: archived thing", "archived", 90),
        card(8, "Sample: dropped thing", "dropped", 50),
    ]


def load(path):
    p = Path(path)
    if p.is_dir():
        out = []
        for f in sorted(p.glob("*.json")):
            c = json.loads(f.read_text())
            c["id"] = f.stem
            out.append(c)
        return out
    return json.loads(p.read_text())


MOCK = r"""
<script>
(function () {
  var qs = new URLSearchParams(location.search);
  var cards = qs.get("empty") ? {} : Object.fromEntries(__CARDS__.map(function (c) { var d = Object.assign({}, c); delete d.id; return [c.id, d]; }));
  var meta = { board: { title: "Kanban (preview)", last_sync: new Date(Date.now() - 2 * 3600e3).toISOString(), stale_days: 14, cold_days: 30 } };
  var stores = { cards: cards, meta: meta }, subs = [];
  function snapDoc(id, data) { return { id: id, exists: !!data, data: function () { return data; }, metadata: { fromCache: false } }; }
  function emit() { subs.forEach(function (f) { f(); }); }
  function merge(a, b) { Object.keys(b).forEach(function (k) { a[k] = b[k]; }); return a; }
  function docRef(col, id) {
    var s = stores[col] = stores[col] || {};
    return {
      id: id, path: col + "/" + id,
      get: async function () { return snapDoc(id, s[id]); },
      set: async function (d) { s[id] = JSON.parse(JSON.stringify(d)); emit(); },
      update: async function (d) {
        if (window.__failWrites) throw { code: "unavailable" };
        if (!s[id]) throw { code: "invalid_argument" };
        s[id] = merge(Object.assign({}, s[id]), d); emit();
      },
      delete: async function () { delete s[id]; emit(); },
      onSnapshot: function (next) { var f = function () { next(snapDoc(id, s[id])); }; subs.push(f); setTimeout(f, 50); return function () {}; }
    };
  }
  function colRef(col) {
    var q = {
      limit: function () { return q; }, where: function () { return q; }, orderBy: function () { return q; },
      doc: function (id) { return docRef(col, id); },
      onSnapshot: function (next) {
        var f = function () { var s = stores[col] || {}; next({ docs: Object.keys(s).sort().map(function (id) { return snapDoc(id, s[id]); }), metadata: { fromCache: false } }); };
        subs.push(f); setTimeout(f, 50); return function () {};
      }
    };
    return q;
  }
  var db = { doc: function (p) { var a = p.split("/"); return docRef(a[0], a[1]); }, collection: colRef };
  var user = { canEdit: async function () { return !qs.get("view"); }, isOwner: async function () { return !qs.get("view"); } };
  window.claude = { use: async function (n) { return n === "db" ? db : n === "user" ? user : null; } };
  window.__stores = stores;
})();
</script>
"""

RESET = "<style>body{margin:0;font:14px system-ui}img{max-width:100%}[hidden]{display:none!important}</style>"


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cards = load(sys.argv[2]) if len(sys.argv) > 2 else samples()
    mock = MOCK.replace("__CARDS__", json.dumps(cards).replace("</", "<\\/"))
    html = ('<!doctype html><html><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            + RESET + "</head><body>" + mock + PAGE.read_text() + "</body></html>")
    Path(sys.argv[1]).write_text(html)
    print("wrote", sys.argv[1], "with", len(cards), "cards")


if __name__ == "__main__":
    main()
