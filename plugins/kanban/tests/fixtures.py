"""Helpers that build small synthetic transcripts for the tests."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))


def user(text, ts, cwd="/work/proj", **kw):
    d = {"type": "user", "message": {"role": "user", "content": text}, "timestamp": ts,
         "cwd": cwd, "gitBranch": kw.pop("branch", "main"), "isSidechain": False,
         "origin": {"kind": "human"}, "sessionId": "s"}
    d.update(kw)
    return d


def tool_result(ts, cwd="/work/proj"):
    return {"type": "user", "timestamp": ts, "cwd": cwd, "isSidechain": False,
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1",
                                                     "content": [{"type": "text", "text": "ok"}]}]}}


def assistant(text, ts, cwd="/work/proj", tools=(), **kw):
    content = [{"type": "text", "text": text}] if text else []
    for name, path in tools:
        content.append({"type": "tool_use", "id": "t", "name": name, "input": {"file_path": path}})
    d = {"type": "assistant", "message": {"role": "assistant", "content": content},
         "timestamp": ts, "cwd": cwd, "gitBranch": "main", "isSidechain": False}
    d.update(kw)
    return d


def title(text, kind="custom-title"):
    key = {"custom-title": "customTitle", "ai-title": "aiTitle"}[kind]
    return {"type": kind, key: text, "sessionId": "s"}


def write(path, entries, raw=()):
    """Write entries (dicts) as JSON lines. `raw` strings are added as they are."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for e in entries:
            f.write((e if isinstance(e, str) else json.dumps(e)) + "\n")
        for r in raw:
            f.write(r + "\n")
    return path


def normal(path, cwd="/work/proj", day="2026-11-10", title_text="Sauna dashboard UI"):
    return write(path, [
        title("Old title"),
        user("Build the sauna card for the dashboard", day + "T10:00:00.000Z", cwd),
        assistant("Looking at it.", day + "T10:00:05.000Z", cwd, tools=[("Edit", cwd + "/a.yaml")]),
        tool_result(day + "T10:00:06.000Z", cwd),
        user("Make the temperature bigger", day + "T10:05:00.000Z", cwd),
        assistant("Done. The card shows the temperature in large type.", day + "T10:06:00.000Z", cwd,
                  tools=[("Write", cwd + "/b.yaml"), ("Edit", cwd + "/a.yaml")]),
        title(title_text),
    ])


def set_mtime(path, when):
    ts = when.timestamp()
    os.utime(str(path), (ts, ts))
