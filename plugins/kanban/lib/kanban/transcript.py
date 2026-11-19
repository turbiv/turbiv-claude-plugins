"""Turn one Claude Code transcript (.jsonl) into a short digest.

The transcript format is internal to Claude Code and can change in any
release. So this module reads defensively: it never raises on bad input,
and it sets `unparsed` when a file has content but no messages it can
recognise. The caller must report such files, never write cards from them.
"""
import json
import re
from pathlib import Path

PROMPT_MAX = 300
REPLY_MAX = 1200
TITLE_MAX = 60
MAX_PROMPTS = 3
MAX_FOLDERS = 5
MAX_FILES = 15
EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
# A file this small with no messages is an empty session, not a format change.
UNPARSED_MIN_BYTES = 2000
SYNC_MARKS = ("/kanban:sync", "/kanban:setup", "[kanban-sync]")

_COMMAND = re.compile(r"<command-name>\s*(/[^<\s]+)\s*</command-name>")
_ARGS = re.compile(r"<command-args>(.*?)</command-args>", re.S)
# Blocks the app adds around what the user typed. They are not the user's words.
_WRAPPERS = re.compile(
    r"<(system-reminder|local-command-caveat|local-command-stdout|local-command-stderr)>.*?</\1>", re.S)
# Commands that only change the session's settings. They say nothing about the work.
BUILTIN_COMMANDS = frozenset(
    "/model /clear /compact /config /cost /help /resume /rename /login /logout /plugin /permissions "
    "/fast /context /memory /mcp /status /doctor /exit /quit /usage /effort /agents /hooks /ide /vim "
    "/theme /export /add-dir /bug /terminal-setup /statusline /output-style /release-notes /tasks".split())


def cut(text, limit):
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def norm_ts(value):
    """'2026-11-10T10:00:05.123Z' -> '2026-11-10T10:00:05Z'. '' when not a time."""
    if not isinstance(value, str) or len(value) < 19 or value[10] != "T":
        return ""
    return value[:19] + "Z"


def _text_of(content):
    """The plain text of a message's content, or '' (tool results give '')."""
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str):
                parts.append(block["text"])
        text = "\n".join(parts)
    else:
        return ""
    return _WRAPPERS.sub("", text).strip() if "<" in text else text.strip()


def _readable(text):
    """A slash command arrives wrapped in tags. Make it '/name args'."""
    m = _COMMAND.search(text)
    if not m:
        return text
    args = _ARGS.search(text)
    return (m.group(1) + " " + (args.group(1).strip() if args else "")).strip()


def _prompt_kind(entry, text):
    """Is this user entry something a person asked?

    'human': typed by the user (or the origin is unknown, as in older versions).
    'other': plain text from somewhere else, such as the task another session gave.
    None: not a prompt (tool results, reminders, notifications, settings commands).
    """
    if not text or entry.get("isMeta"):
        return None
    command = _COMMAND.search(text)
    if command:
        return None if command.group(1) in BUILTIN_COMMANDS else "human"
    if text.startswith("<") or text.startswith("[Request interrupted"):
        return None
    origin = entry.get("origin")
    kind = origin.get("kind") if isinstance(origin, dict) else None
    return "human" if kind in (None, "human") else "other"


def digest(path, since=None):
    """Digest the transcript at `path`.

    With `since` (an ISO time), the text fields (prompts, last_prompt,
    last_reply, files, turns) only cover entries after that time. `start`
    and `end` always cover the whole session.
    """
    path = Path(path)
    out = {
        "id": path.stem, "title": "", "start": "", "end": "", "folders": [], "branch": "",
        "prompts": [], "last_prompt": "", "last_reply": "", "turns": 0,
        "files": [], "files_total": 0, "unparsed": False, "sync_session": False,
    }
    since = norm_ts(since) if since else ""
    custom_title = ai_title = summary = ""
    human, other, files = [], [], []
    messages = replies = 0
    first_text = None
    size = 0
    try:
        f = open(str(path), "r", encoding="utf-8", errors="replace")
    except OSError:
        return out
    with f:
        for line in f:
            size += len(line)
            # These lines carry whole API requests. They are large and never needed.
            if line.startswith('{"type":"api-request'):
                continue
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if not isinstance(e, dict):
                continue
            kind = e.get("type")
            if kind == "custom-title":
                custom_title = str(e.get("customTitle") or custom_title)
                continue
            if kind == "ai-title":
                ai_title = str(e.get("aiTitle") or ai_title)
                continue
            if kind == "summary":
                summary = str(e.get("summary") or summary)
                continue
            if kind not in ("user", "assistant") or e.get("isSidechain"):
                continue
            msg = e.get("message")
            if not isinstance(msg, dict):
                continue
            messages += 1
            ts = norm_ts(e.get("timestamp"))
            if ts:
                out["start"] = min(out["start"], ts) if out["start"] else ts
                out["end"] = max(out["end"], ts)
            cwd = e.get("cwd")
            if isinstance(cwd, str) and cwd and cwd not in out["folders"] and len(out["folders"]) < MAX_FOLDERS:
                out["folders"].append(cwd)
            if isinstance(e.get("gitBranch"), str) and e["gitBranch"]:
                out["branch"] = e["gitBranch"]
            late = not since or (ts and ts > since)
            content = msg.get("content")
            if kind == "user":
                text = _text_of(content)
                pk = _prompt_kind(e, text)
                if pk and first_text is None:
                    first_text = text
                if pk and late:
                    (human if pk == "human" else other).append(_readable(text))
            else:
                text = _text_of(content)
                if text.strip():
                    replies += 1
                    if late:
                        out["last_reply"] = cut(text, REPLY_MAX)
                if late and isinstance(content, list):
                    for block in content:
                        if (isinstance(block, dict) and block.get("type") == "tool_use"
                                and block.get("name") in EDIT_TOOLS and isinstance(block.get("input"), dict)):
                            fp = block["input"].get("file_path") or block["input"].get("notebook_path")
                            if isinstance(fp, str) and fp and fp not in files:
                                files.append(fp)

    # A session started by another session has no human prompt: use its task text.
    prompts = human if human else other[:1]
    out["prompts"] = [cut(p, PROMPT_MAX) for p in prompts[:MAX_PROMPTS]]
    out["last_prompt"] = cut(prompts[-1], PROMPT_MAX) if prompts else ""
    out["turns"] = len(prompts)
    out["files_total"] = len(files)
    out["files"] = files[:MAX_FILES]
    out["title"] = cut(custom_title or ai_title or summary or (prompts[0] if prompts else ""), TITLE_MAX)
    if first_text is not None:
        out["sync_session"] = any(mark in first_text for mark in SYNC_MARKS)
    if messages == 0:
        out["unparsed"] = size >= UNPARSED_MIN_BYTES
    elif not since and not prompts and replies:
        out["unparsed"] = True
    return out
