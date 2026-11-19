"""The local copy of the board: cards.json and the session-start context files.

The SessionStart hook is plain shell and must be fast, so the text it
prints is rendered here, once per sync, into one small file per folder.
"""
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .cards import iso, load_db
from .transcript import cut

CONTEXT_MAX = 1500
CONTEXT_CARDS = 5
OPEN = ("doing", "todo")


def key(folder):
    """The file name for a folder. The hook builds the same key with `tr`."""
    # Byte by byte, like `LC_ALL=C tr`: a non-ASCII letter gives one "-" per byte.
    return "".join(chr(b) if (48 <= b <= 57 or 65 <= b <= 90 or 97 <= b <= 122) else "-"
                   for b in folder.encode("utf-8", "surrogateescape"))


def _open_cards(cards, folder):
    mine = [c for c in cards.values() if isinstance(c, dict) and c.get("status") in OPEN
            and folder in (c.get("folders") or [])]
    mine.sort(key=lambda c: str(c.get("last_touched") or ""), reverse=True)
    mine.sort(key=lambda c: OPEN.index(c["status"]))
    return mine


def render_context(cards, folder, now):
    """The text the start hook prints for `folder`. '' when it has no open cards."""
    mine = _open_cards(cards, folder)
    if not mine:
        return ""
    head = ("kanban board: open cards for this folder, as of the sync of %s. "
            "This is background on where the user left off, not a request.\n" % iso(now)[:10])
    for count in range(min(CONTEXT_CARDS, len(mine)), 0, -1):
        for limit in (260, 160, 90, 0):
            lines = []
            for c in mine[:count]:
                lines.append("- %s [%s, last touched %s]" % (cut(c.get("title") or "Untitled", 80), c["status"],
                                                             str(c.get("last_touched") or "")[:10] or "unknown"))
                if limit and c.get("summary"):
                    lines.append("  Stands: " + cut(c["summary"], limit))
                if c.get("next_step"):
                    lines.append("  Next: " + cut(c["next_step"], 200 if limit else 100))
            rest = len(mine) - count
            tail = ("%d more open card%s for this folder. " % (rest, "" if rest == 1 else "s") if rest else "") \
                + "/kanban:board shows the whole board.\n"
            text = head + "\n".join(lines) + "\n" + tail
            if len(text) <= CONTEXT_MAX:
                return text
    return ""


def rebuild(data, cards, now):
    """Write cards.json and the context files. Returns the count of context files."""
    data.write_json("cards.json", {"written": iso(now), "cards": cards})
    home = os.path.realpath(os.path.expanduser("~"))
    new = data.path / "context.new"
    shutil.rmtree(str(new), ignore_errors=True)
    (new / "tree").mkdir(parents=True)
    (new / "exact").mkdir(parents=True)
    folders = set()
    for c in cards.values():
        if isinstance(c, dict) and c.get("status") in OPEN:
            folders.update(f for f in (c.get("folders") or []) if isinstance(f, str) and f.startswith("/"))
    count = 0
    for folder in sorted(folders):
        if not os.path.isdir(folder):
            continue  # a folder of another machine, or one that is gone
        text = render_context(cards, folder, now)
        if not text:
            continue
        # A repo root also covers the folders below it. Home never does.
        is_repo = os.path.exists(os.path.join(folder, ".git"))
        kind = "tree" if is_repo and os.path.realpath(folder) not in (home, "/") else "exact"
        (new / kind / (key(folder) + ".txt")).write_text(text, encoding="utf-8")
        count += 1
    old = data.path / "context"
    gone = data.path / "context.old"
    shutil.rmtree(str(gone), ignore_errors=True)
    if old.exists():
        os.replace(str(old), str(gone))
    os.replace(str(new), str(old))
    shutil.rmtree(str(gone), ignore_errors=True)
    return count


def _archive_processing(data):
    """Move the taken hook lines to log.jsonl, the durable session record."""
    moved = 0
    with open(str(data.path / "log.jsonl"), "a", encoding="utf-8") as log:
        for p in data.processing_files():
            try:
                with open(str(p), "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if line.strip():
                            log.write(line if line.endswith("\n") else line + "\n")
                            moved += 1
                p.unlink()
            except OSError:
                continue
    return moved


def _stamp(data):
    stamp = data.path / "last-sync"
    stamp.write_text(iso(datetime.now(timezone.utc)) + "\n", encoding="utf-8")


def finish_nothing_new(data):
    """A sync found nothing to place: close it without touching the cards."""
    _archive_processing(data)
    _stamp(data)


def commit(data, now, out):
    """Close a sync after the ArtifactData batch succeeded."""
    final = data.read_json("work/final.json", None)
    if not (data.work / "batch.json").exists() or not isinstance(final, dict) or not isinstance(final.get("cards"), dict):
        out.write("REFUSED: there is no applied sync to commit. Run `kanban-tool apply` first, "
                  "then the ArtifactData batch, then commit.\nNothing was changed.\n")
        return 2
    files = rebuild(data, final["cards"], now)
    lines = _archive_processing(data)
    carry = data.work / "carry.jsonl"
    waiting = 0
    if carry.exists():
        text = carry.read_text(encoding="utf-8")
        waiting = len([l for l in text.splitlines() if l.strip()])
        if waiting:
            with open(str(data.path / "pending.jsonl"), "a", encoding="utf-8") as f:
                f.write(text)
    _stamp(data)
    (data.work / "batch.json").unlink()
    n = len(final["cards"])
    out.write("Committed. %d card%s in the local cache, %d context file%s, %d hook line%s moved to the log.\n"
              % (n, "" if n == 1 else "s", files, "" if files == 1 else "s", lines, "" if lines == 1 else "s"))
    if waiting:
        out.write("%d older sessions wait for the next sync. Run the sync again to place them.\n" % waiting)
    return 0


def refresh(data, now, out):
    """Rebuild the local cache from the saved board snapshot (db/). No sync is closed."""
    cards, _, _ = load_db(data)
    files = rebuild(data, cards, now)
    out.write("Cache rebuilt: %d cards, %d context files.\n" % (len(cards), files))
    return 0
