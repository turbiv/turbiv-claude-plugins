"""The plugin's data folder: config, the hook log, and the work files of a sync."""
import json
import os
import shutil
import time
from pathlib import Path


class Data:
    def __init__(self, path):
        self.path = Path(os.path.expanduser(str(path)))

    # --- small JSON files -------------------------------------------------
    def read_json(self, name, default=None):
        try:
            with open(str(self.path / name), "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return default

    def write_json(self, name, obj):
        """Write through a temp file and a rename, so a reader never sees half a file."""
        target = self.path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".tmp%d" % os.getpid())
        with open(str(tmp), "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=1, ensure_ascii=False, sort_keys=True)
            f.write("\n")
        os.replace(str(tmp), str(target))
        return target

    def config(self):
        cfg = self.read_json("config.json", None)
        return cfg if isinstance(cfg, dict) else {}

    def save_config(self, cfg):
        return self.write_json("config.json", cfg)

    # --- the hook log -----------------------------------------------------
    def processing_files(self):
        return sorted(self.path.glob("processing-*.jsonl"))

    def take_pending(self):
        """Take the hook lines that wait for a sync.

        pending.jsonl is renamed first, so a hook that fires during the sync
        writes to a fresh file. The taken lines stay in processing-*.jsonl
        until `commit`; a sync that dies leaves them for the next one.
        Returns a list of dicts. A line that is not valid JSON (the hook caps
        long lines) comes back as {"bad": "<the text>"}.
        """
        pending = self.path / "pending.jsonl"
        if pending.exists():
            target = self.path / ("processing-%d-%d.jsonl" % (int(time.time() * 1000), os.getpid()))
            try:
                os.replace(str(pending), str(target))
            except OSError:
                pass
        events = []
        for p in self.processing_files():
            try:
                with open(str(p), "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            e = json.loads(line)
                        except ValueError:
                            e = None
                        events.append(e if isinstance(e, dict) else {"bad": line})
            except OSError:
                continue
        return events

    # --- folders of one sync ----------------------------------------------
    @property
    def work(self):
        return self.path / "work"

    @property
    def db(self):
        return self.path / "db"

    def clear(self, folder):
        shutil.rmtree(str(folder), ignore_errors=True)
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def last_sync_time(self):
        try:
            return (self.path / "last-sync").stat().st_mtime
        except OSError:
            return None
