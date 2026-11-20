"""Find the sessions that are not on the board yet and digest them."""
import fnmatch
import json
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import transcript

DEFAULT_SCAN_DAYS = 30
MAX_SESSIONS = 200
COMPACT_ABOVE = 40          # with more sessions than this, the text is cut shorter
WORKTREE_MARK = "/.claude/worktrees/"
_SID = re.compile(r'"session_id"\s*:\s*"([^"]+)"')
_TPATH = re.compile(r'"transcript_path"\s*:\s*"((?:[^"\\]|\\.)*)"')


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git(root, *args):
    try:
        r = subprocess.run(["git", "-C", root] + list(args), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           timeout=10, env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
        return r.stdout.decode("utf-8", "replace").strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def repo_root(folder, cache=None):
    """The main repo of a folder, or None. A worktree maps to its main repo."""
    if cache is not None and folder in cache:
        return cache[folder]
    root = None
    if WORKTREE_MARK in folder:
        # Works also when the worktree was removed.
        root = folder.split(WORKTREE_MARK)[0]
    elif os.path.isdir(folder):
        common = _git(folder, "rev-parse", "--git-common-dir")
        if common:
            common = os.path.normpath(os.path.join(folder, common))
            if os.path.basename(common) == ".git":
                # Also right in a linked worktree: its common dir is the main repo's .git.
                root = os.path.dirname(common)
            else:
                root = _git(folder, "rev-parse", "--show-toplevel") or None
    if cache is not None:
        cache[folder] = root
    return root


def github_url(remote):
    remote = remote.strip()
    m = re.match(r"^(?:git@|ssh://git@)github\.com[:/]([^/]+)/(.+?)(?:\.git)?/?$", remote)
    if m:
        return "https://github.com/%s/%s" % (m.group(1), m.group(2))
    m = re.match(r"^https?://(?:[^@/]+@)?github\.com/([^/]+)/(.+?)(?:\.git)?/?$", remote)
    if m:
        return "https://github.com/%s/%s" % (m.group(1), m.group(2))
    return None


def repo_state(root, since):
    commits = _git(root, "log", "--since=" + since, "-n", "20", "--date=short", "--pretty=format:%h %s (%ad)")
    dirty = _git(root, "status", "--short")
    return {
        "name": os.path.basename(root), "root": root,
        "github": github_url(_git(root, "remote", "get-url", "origin")),
        "commits": [c for c in commits.splitlines() if c][:20],
        "dirty": [d for d in dirty.splitlines() if d][:20],
    }


def excluded(folders, patterns):
    """Is one of the folders shut out by a pattern?

    A pattern with a "/" is a full path (or a glob of one): it shuts out that
    folder and everything below it. A pattern without a "/" is a folder name:
    it shuts out every folder that has a path part with that name, so the
    name of a repo covers its subfolders and its worktrees too.
    """
    for pat in patterns:
        if not isinstance(pat, str) or not pat.strip():
            continue
        pat = pat.strip()
        by_name = "/" not in pat
        if not by_name:
            pat = os.path.expanduser(pat).rstrip("/") or "/"
        for f in folders:
            if not f:
                continue
            if by_name:
                if any(fnmatch.fnmatch(part, pat) for part in f.split("/") if part):
                    return True
            elif f == pat or f.startswith(pat + "/") or fnmatch.fnmatch(f, pat) or fnmatch.fnmatch(f, pat + "/*"):
                return True
    return False


def _candidates(events, projects_dir, cutoff, again=()):
    """session id -> {path, source}. Hook lines first, then the folder scan.
    `again`: session ids (or their first 6 or more characters) to take whatever
    their age."""
    found = {}
    for e in events:
        sid = tpath = None
        if "bad" in e:
            m = _SID.search(e["bad"])
            sid = m.group(1) if m else None
            m = _TPATH.search(e["bad"])
            if m:
                try:
                    tpath = json.loads('"' + m.group(1) + '"')
                except ValueError:
                    tpath = None
        else:
            inp = e.get("in")
            if isinstance(inp, dict):
                sid, tpath = inp.get("session_id"), inp.get("transcript_path")
        if not isinstance(sid, str) or not sid or "/" in sid:
            continue
        path = Path(tpath) if isinstance(tpath, str) and tpath and os.path.isfile(tpath) else None
        if sid not in found or (found[sid]["path"] is None and path is not None):
            found[sid] = {"path": path, "source": "hook"}
    try:
        files = list(projects_dir.glob("*/*.jsonl"))
    except OSError:
        files = []
    by_id = {}
    for f in files:
        by_id.setdefault(f.stem, f)
        try:
            recent = f.stat().st_mtime >= cutoff
        except OSError:
            continue
        if (recent or any(f.stem.startswith(a) for a in again)) and f.stem not in found:
            found[f.stem] = {"path": f, "source": "scan"}
    for sid, c in found.items():
        if c["path"] is None:
            c["path"] = by_id.get(sid)
    return found


def _on_cards(cards):
    """session id -> {cards, end}, read from the cards' own session lists."""
    out = {}
    for cid, c in (cards or {}).items():
        for s in (c.get("sessions") or []) if isinstance(c, dict) else []:
            if isinstance(s, dict) and isinstance(s.get("id"), str):
                e = out.setdefault(s["id"], {"cards": [], "end": ""})
                e["cards"].append(cid)
                e["end"] = max(e["end"], str(s.get("date") or ""))
    return out


def run(data, synced, projects_dir, scan_days, now, max_sessions=MAX_SESSIONS, cards=None, again=()):
    """Build the digest of everything that is new. Writes work/digest.json and
    work/digest.md and returns the digest object.

    `cards` is the saved board. A session that a card already names is treated
    as synced even when `meta/synced` does not have it (a sync can die after
    the cards were written and before the record was).

    `again`: sessions to read again from their start, also when they are synced
    and have nothing new. For a card that sync wrote wrong."""
    cfg = data.config()
    patterns = cfg.get("exclude") if isinstance(cfg.get("exclude"), list) else []
    synced = synced if isinstance(synced, dict) else {}
    on_cards = _on_cards(cards)
    last = data.last_sync_time()
    first_sync = last is None
    if scan_days is not None:
        cutoff = now.timestamp() - scan_days * 86400
    elif last is not None:
        cutoff = last - 3600  # one hour of overlap; synced sessions are dropped below
    else:
        cutoff = now.timestamp() - int(cfg.get("scan_days") or DEFAULT_SCAN_DAYS) * 86400
    since = iso(datetime.fromtimestamp(cutoff, timezone.utc))

    events = data.take_pending()
    skipped = {"synced": 0, "excluded": 0, "no_prompt": 0, "sync_session": 0, "scheduled": 0, "missing": 0,
               "over_cap": 0}
    sessions, roots = [], {}
    again = tuple(a for a in again if isinstance(a, str) and len(a) >= 6)
    found_again = set()
    for sid, c in _candidates(events, Path(projects_dir), cutoff, again).items():
        if c["path"] is None:
            skipped["missing"] += 1
            continue
        prev = synced.get(sid) if isinstance(synced.get(sid), dict) else on_cards.get(sid)
        is_again = any(sid.startswith(a) for a in again)
        if is_again:
            found_again.add(sid)
        d = transcript.digest(c["path"], since=prev.get("end") if prev and not is_again else None)
        d["again"] = is_again
        if d["sync_session"]:
            skipped["sync_session"] += 1
            continue
        if d["scheduled"]:
            # A run of some other scheduled task. Nobody "left off" there.
            skipped["scheduled"] += 1
            continue
        if prev and not is_again and d["end"] <= str(prev.get("end") or ""):
            skipped["synced"] += 1
            continue
        root = None
        for folder in d["folders"]:
            root = repo_root(folder, roots)
            if root:
                break
        if excluded(d["folders"] + [root], patterns):
            skipped["excluded"] += 1
            continue
        # No prompt: nothing was asked. But a session that was synced in the middle
        # of a turn has later replies and edits with no new prompt: keep those.
        went_on = bool(prev) and bool(d["last_reply"] or d["files"])
        if d["turns"] == 0 and not d["unparsed"] and not went_on:
            skipped["no_prompt"] += 1
            continue
        d.update({
            "source": c["source"], "transcript": str(c["path"]),
            "repo_root": root, "repo": os.path.basename(root) if root else None,
            "folder": root or (d["folders"][0] if d["folders"] else None),
            "known_cards": list(prev.get("cards") or []) if prev else [],
        })
        if not d["end"]:
            # An unparsed file has no times: use the file's own.
            try:
                d["end"] = d["start"] = iso(datetime.fromtimestamp(c["path"].stat().st_mtime, timezone.utc))
            except OSError:
                d["end"] = d["start"] = iso(now)
        sessions.append(d)

    # Sessions read again go first, so the cap never pushes them to the next sync.
    sessions.sort(key=lambda s: (bool(s.get("again")), s["end"]), reverse=True)
    carry = sessions[max_sessions:]
    sessions = sessions[:max_sessions]
    skipped["over_cap"] = len(carry)

    repos = []
    for root in sorted({s["repo_root"] for s in sessions if s["repo_root"]}):
        if os.path.isdir(root):
            repos.append(repo_state(root, since))

    digest = {
        "generated": iso(now), "machine": cfg.get("machine") or "", "first_sync": first_sync,
        "since": since, "sessions": sessions, "repos": repos, "skipped": skipped,
        "again_missing": [a for a in again if not any(sid.startswith(a) for sid in found_again)],
    }
    work = data.clear(data.work)
    data.write_json("work/digest.json", digest)
    (work / "digest.md").write_text(render(digest), encoding="utf-8")
    # Sessions over the cap wait for the next sync: commit puts these lines back.
    with open(str(work / "carry.jsonl"), "w", encoding="utf-8") as f:
        for s in carry:
            f.write(json.dumps({"ev": "end", "ts": iso(now), "dir": s["folder"] or "",
                                "in": {"session_id": s["id"], "transcript_path": s["transcript"]}}) + "\n")
    return digest


STEPS_HEAD_SHOWN = transcript.STEPS_HEAD


def render(digest):
    """The digest as compact text. This is what Claude reads."""
    sessions = digest["sessions"]
    compact = len(sessions) > COMPACT_ABOVE
    p_max, r_max = (200, 500) if compact else (transcript.PROMPT_MAX, transcript.REPLY_MAX)
    o_max = 160 if compact else transcript.OUTCOME_MAX
    cut = transcript.cut
    out = ["# Sessions that are not on the board yet: %d" % len(sessions), ""]
    sk = ", ".join("%s %d" % (k.replace("_", " "), v) for k, v in sorted(digest["skipped"].items()) if v)
    if sk:
        out += ["Left out: " + sk + ".", ""]
    unparsed = [s for s in sessions if s["unparsed"]]
    if unparsed:
        out += ["UNPARSED (the transcript format was not recognised; read the end of each file yourself):"]
        out += ["- %s  %s" % (s["id"], s["transcript"]) for s in unparsed] + [""]
    if digest["repos"]:
        out.append("## Repos")
        for r in digest["repos"]:
            out.append("### %s  (%s)%s" % (r["name"], r["root"], "  " + r["github"] if r["github"] else ""))
            if r["commits"]:
                out.append("commits since %s:" % digest["since"][:10])
                out += ["  " + c for c in r["commits"]]
            if r["dirty"]:
                out.append("uncommitted: " + ", ".join(d.strip() for d in r["dirty"][:8])
                           + (" (+%d)" % (len(r["dirty"]) - 8) if len(r["dirty"]) > 8 else ""))
        out.append("")
    out.append("## Sessions, newest first")
    for s in sessions:
        out.append("")
        out.append("### %s · %s" % (s["id"], s["title"] or "(no title)"))
        where = s["repo"] or (s["folder"] or "no folder")
        if s["repo"] and s["branch"]:
            where += " (%s)" % s["branch"]
        out.append("%s → %s · %d prompts · %s%s" % (
            s["start"][:16].replace("T", " "), s["end"][:16].replace("T", " "), s["turns"], where,
            " · already on: " + ", ".join(s["known_cards"]) if s["known_cards"] else ""))
        if s["unparsed"]:
            out.append("UNPARSED: " + s["transcript"])
            continue
        if s["turns"] == 0 and s["known_cards"]:
            out.append("(no new prompt: the turn that was running at the last sync went on)")
        if s.get("again"):
            out.append("(read again from the start: rewrite the card's summary, status and next step from all of it)")
        steps = s.get("steps") or []
        if steps:
            # Each request with how its reply began: "→" says whether it was done.
            for j, st in enumerate(steps):
                if j == STEPS_HEAD_SHOWN and s.get("steps_left_out"):
                    out.append("(%d more requests)" % s["steps_left_out"])
                out.append("asked %d: %s" % (st["n"], cut(st["ask"], p_max)))
                last = j == len(steps) - 1
                if st["outcome"] and not (last and s["last_reply"]):
                    out.append("  → " + cut(st["outcome"], o_max))
        else:
            for i, p in enumerate(s["prompts"]):
                out.append("asked %d: %s" % (i + 1, cut(p, p_max)))
            if s["turns"] > len(s["prompts"]) and s["last_prompt"]:
                out.append("asked last: " + cut(s["last_prompt"], p_max))
        if s["last_reply"]:
            out.append("ended with: " + cut(s["last_reply"], r_max))
        if s["files"]:
            names = [os.path.basename(f) for f in s["files"][:8]]
            more = s["files_total"] - len(names)
            out.append("edited: " + ", ".join(names) + (" (+%d)" % more if more > 0 else ""))
    return "\n".join(out) + "\n"
