"""kanban-tool: the command line the skills call."""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import cache, cards, collect
from .store import Data
from .transcript import cut

STATUS_ORDER = ["doing", "todo", "idea", "done", "dropped", "archived"]
INLINE_MAX = 20000   # characters of digest that `collect` prints itself
NEED_SETUP = "This board is not set up yet. Run /kanban:setup first.\n"


def _now():
    return datetime.now(timezone.utc)


def _days(ts, now):
    try:
        then = datetime.strptime(str(ts)[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return max(0, (now - then).days)


_SESSION_ID = re.compile(r'"session_id": *"([^"]+)"')


def _pending(data):
    """How many sessions the hook log names. Counted by session id, from start and
    end lines alike: in the desktop app a session is seldom closed, so its end line
    may never come."""
    ids = set()
    for p in [data.path / "pending.jsonl"] + data.processing_files():
        try:
            with open(str(p), "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    ids.update(_SESSION_ID.findall(line)[:1])
        except OSError:
            pass
    return len(ids)


def _last_sync(data):
    t = data.last_sync_time()
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if t else "never"


def _require(data, out):
    cfg = data.config()
    if not cfg.get("url"):
        out.write(NEED_SETUP)
        return None
    return cfg


def card_index(cards_by_id, now, full=True):
    """The cards as compact text, most active first."""
    def rank(item):
        c = item[1]
        st = c.get("status")
        return (STATUS_ORDER.index(st) if st in STATUS_ORDER else 9, )
    items = sorted(cards_by_id.items(), key=lambda i: str(i[1].get("last_touched") or ""), reverse=True)
    items.sort(key=rank)
    lines = []
    for cid, c in items:
        d = _days(c.get("last_touched"), now)
        age = "" if d is None else (" · touched today" if d == 0 else " · touched %d d ago" % d)
        stale = ""
        if c.get("status") in ("todo", "doing") and d is not None and d >= 14:
            stale = " · COLD" if d >= 30 else " · STALE"
        repos = ", ".join(str(r) for r in (c.get("repos") or [])[:4])
        lines.append("%s · %s [%s]%s%s%s" % (cid, c.get("title") or "Untitled", c.get("status") or "?",
                                           " · " + repos if repos else "", age, stale))
        if c.get("summary"):
            lines.append("  stands: " + cut(c["summary"], 220 if full else 160))
        if c.get("next_step") and c.get("status") not in ("done", "dropped", "archived"):
            lines.append("  next: " + cut(c["next_step"], 140))
        if isinstance(c.get("notes"), str) and c["notes"].strip():
            # The owner's own words: often progress made outside Claude.
            lines.append("  owner's notes: " + cut(c["notes"], 300 if full else 160))
        if full:
            titles = [cut(str(s.get("title") or ""), 50) for s in (c.get("sessions") or [])[:3] if isinstance(s, dict)]
            if titles:
                lines.append("  recent sessions: " + "; ".join(t for t in titles if t))
    return "\n".join(lines) + ("\n" if lines else "")


# --- commands -----------------------------------------------------------
def cmd_init(a, data, out):
    cfg = data.config()
    cfg["url"] = a.url
    cfg.setdefault("machine", os.urandom(4).hex())
    cfg.setdefault("exclude", [])
    cfg.setdefault("scan_days", collect.DEFAULT_SCAN_DAYS)
    cfg.setdefault("created", cards.iso(_now()))
    if a.scan_days:
        cfg["scan_days"] = a.scan_days
    data.save_config(cfg)
    out.write("Saved. Board: %s\nData folder: %s\n" % (cfg["url"], data.path))
    return 0


def cmd_status(a, data, out):
    cfg = data.config()
    if not cfg.get("url"):
        out.write("Not set up. Data folder: %s\n" % data.path)
        return 0
    cached = data.read_json("cards.json", {}) or {}
    out.write("Board: %s\nData folder: %s\nSessions waiting: %d\nLast sync: %s\nCards in the local cache: %d\n"
              "Excluded folders: %s\n" % (cfg["url"], data.path, _pending(data), _last_sync(data),
                                          len(cached.get("cards") or {}), ", ".join(cfg.get("exclude") or []) or "none"))
    return 0


def cmd_begin(a, data, out):
    cfg = _require(data, out)
    if not cfg:
        return 2
    data.clear(data.db)
    data.clear(data.work)
    out.write("Board: %s\nSessions waiting: %d. Last sync: %s.\n\n"
              "Next: save the board with ArtifactData, action \"list\", once for collection \"meta\" and once for "
              "\"cards\", both with out_dir:\n%s\nKeep the version numbers the two results show.\n"
              % (cfg["url"], _pending(data), _last_sync(data), data.db))
    return 0


def cmd_collect(a, data, out):
    if not _require(data, out):
        return 2
    if not (data.db / "meta" / "board.json").exists():
        out.write("REFUSED: the board is not saved yet. Run `kanban-tool begin`, then ArtifactData \"list\" for "
                  "\"meta\" and \"cards\" with out_dir %s, then collect.\n" % data.db)
        return 2
    existing, _, synced = cards.load_db(data)
    projects = Path(os.path.expanduser(a.projects)) if a.projects else Path(os.path.expanduser("~/.claude/projects"))
    now = _now()
    again = a.again or []
    short = [x for x in again if len(x) < 6]
    if short:
        out.write("REFUSED: --again needs at least the first 6 characters of a session id: %s\n" % ", ".join(short))
        return 2
    digest = collect.run(data, synced or {}, projects, a.scan_days, now, cards=existing, again=again)
    if digest.get("again_missing"):
        out.write("No transcript found for --again %s. It may be older than 30 days and deleted.\n"
                  % ", ".join(digest["again_missing"]))
    n = len(digest["sessions"])
    left = ", ".join("%s %d" % (k.replace("_", " "), v) for k, v in sorted(digest["skipped"].items()) if v)
    if n == 0:
        cache.finish_nothing_new(data, now)
        out.write("Nothing new. No session needs a card%s. The local copy now matches the board (%d cards). "
                  "The sync is closed; do not run apply or commit.\n"
                  "One last step, so the board shows that the sync ran: ArtifactData, action \"update\", collection "
                  "\"meta\", doc_id \"board\", data {\"last_sync\": \"%s\"}, with if_version from your list result.\n"
                  % (" (left out: %s)" % left if left else "", len(existing), cards.iso(now)))
        return 0
    (data.work / "cards.md").write_text(card_index(existing, now), encoding="utf-8")
    unparsed = [s for s in digest["sessions"] if s["unparsed"]]
    out.write("%d sessions to place%s.\n" % (n, " (left out: %s)" % left if left else ""))
    if unparsed:
        out.write("%d of them are UNPARSED: the transcript format was not recognised. They are listed at the top "
                  "of the digest. Tell the user.\n" % len(unparsed))
    by_folder = {}
    for s in digest["sessions"]:
        name = s["repo_root"] or "(no repo)"
        by_folder[name] = by_folder.get(name, 0) + 1
    out.write("By repo:\n")
    for name, count in sorted(by_folder.items(), key=lambda kv: -kv[1]):
        out.write("  %3d  %s\n" % (count, name))
    out.write("\n")
    digest_md = (data.work / "digest.md").read_text(encoding="utf-8")
    cards_md = (data.work / "cards.md").read_text(encoding="utf-8")
    if len(digest_md) + len(cards_md) <= INLINE_MAX:
        # Small enough to print: no file read is needed.
        out.write("==== CARDS ON THE BOARD (%d) ====\n%s\n==== SESSIONS ====\n%s"
                  % (len(existing), cards_md or "none\n", digest_md))
    else:
        out.write("Too long to print. Read both files in full:\n  sessions: %s\n  cards on the board (%d): %s\n"
                  % (data.work / "digest.md", len(existing), data.work / "cards.md"))
    return 0


def cmd_index(a, data, out):
    existing, _, _ = cards.load_db(data)
    out.write(card_index(existing, _now()) or "No cards in the saved board (db/cards is empty).\n")
    return 0


def cmd_apply(a, data, out):
    if not _require(data, out):
        return 2
    try:
        if a.file:
            with open(os.path.expanduser(a.file), "r", encoding="utf-8") as f:
                raw = f.read()
        else:
            raw = sys.stdin.read()
        decision = json.loads(raw)
    except (OSError, ValueError) as e:
        out.write("REFUSED: the decision is not valid JSON (%s).\nNothing was written.\n" % e)
        return 2
    return cards.apply(data, decision, _now(), out)


def cmd_commit(a, data, out):
    return cache.commit(data, _now(), out)


def cmd_refresh(a, data, out):
    if not _require(data, out):
        return 2
    if not (data.db / "meta" / "board.json").exists():
        out.write("REFUSED: the board is not saved. Run `kanban-tool begin`, then ArtifactData \"list\" for \"meta\" "
                  "and \"cards\" with out_dir %s, then refresh.\nNothing was changed.\n" % data.db)
        return 2
    return cache.refresh(data, _now(), out)


def cmd_show(a, data, out):
    cfg = _require(data, out)
    if not cfg:
        return 2
    cached = data.read_json("cards.json", None)
    if not isinstance(cached, dict) or not isinstance(cached.get("cards"), dict):
        out.write("There is no local copy of the board yet. Run /kanban:sync.\nBoard: %s\n" % cfg["url"])
        return 0
    all_cards = cached["cards"]
    now = _now()
    if not a.all:
        all_cards = {k: c for k, c in all_cards.items() if c.get("status") in ("doing", "todo")}
    out.write("Board: %s\nLocal copy from %s. Sessions waiting for a sync: %d.\n\n"
              % (cfg["url"], str(cached.get("written") or "?")[:16].replace("T", " "), _pending(data)))
    out.write(card_index(all_cards, now, full=False) or "No open cards.\n")
    return 0


def cmd_exclude(a, data, out):
    cfg = _require(data, out)
    if not cfg:
        return 2
    ex = [e for e in (cfg.get("exclude") or []) if isinstance(e, str)]

    def norm(p):
        # A name (no "/") stays a name. A path is stored in full.
        p = p.strip()
        return p if "/" not in p else (os.path.expanduser(p).rstrip("/") or "/")

    if a.add:
        path = norm(a.add)
        if "/" in path and not path.startswith("/"):
            out.write("REFUSED: %r is a relative path, and that can never match a session's folder. Give the full "
                      "path (for example ~/git/client-x) or only the folder's name (client-x).\n" % a.add)
            return 2
        if path and path not in ex:
            ex.append(path)
    if a.remove:
        ex = [e for e in ex if e != norm(a.remove)]
    cfg["exclude"] = ex
    if a.add or a.remove:
        data.save_config(cfg)
    out.write("Excluded folders:\n" + ("".join("  %s\n" % e for e in ex) or "  none\n"))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="kanban-tool", description="The file work of the kanban plugin.")
    sub = p.add_subparsers(dest="cmd")
    sub.required = True

    def add(name, fn, help_):
        sp = sub.add_parser(name, help=help_)
        sp.add_argument("--data", required=True, help="the plugin's data folder")
        sp.set_defaults(fn=fn)
        return sp

    sp = add("init", cmd_init, "save the board URL")
    sp.add_argument("--url", required=True)
    sp.add_argument("--scan-days", type=int)
    add("status", cmd_status, "show the config and what waits")
    add("begin", cmd_begin, "start a sync: clear the work folders")
    sp = add("collect", cmd_collect, "digest the sessions that are not on the board")
    sp.add_argument("--scan-days", type=int, help="look this many days back instead of since the last sync")
    sp.add_argument("--projects", help="the transcript folder (default ~/.claude/projects)")
    sp.add_argument("--again", action="append", metavar="SESSION",
                    help="read this session again from its start, also when it is synced (a card sync wrote wrong); "
                         "the session id or its first 6 or more characters; can be given more than once")
    add("index", cmd_index, "print the cards of the saved board")
    sp = add("apply", cmd_apply, "merge the decision JSON (stdin, or --file) into the cards")
    sp.add_argument("--file", help="read the decision from this file instead of stdin")
    add("commit", cmd_commit, "close the sync after the batch was written")
    add("refresh", cmd_refresh, "rebuild the local cache from the saved board")
    sp = add("show", cmd_show, "print the open cards from the local cache")
    sp.add_argument("--all", action="store_true")
    sp = add("exclude", cmd_exclude, "folders that never go on the board")
    sp.add_argument("--add")
    sp.add_argument("--remove")
    sp.add_argument("--list", action="store_true")

    a = p.parse_args(argv)
    try:
        return a.fn(a, Data(a.data), sys.stdout)
    except OSError as e:
        sys.stdout.write("kanban-tool failed: %s\n" % e)
        return 1
