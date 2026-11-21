"""SQLite response cache (R7).

A response is stored either as immutable (it can never change in the archive) or with a TTL.
Errors are never stored.

- Where: `REDDIT_MCP_CACHE` (default `$XDG_CACHE_HOME/reddit-mcp/cache.sqlite3`, else
  `~/.cache/reddit-mcp/cache.sqlite3`), or `off`.
- Size: at most `max_bytes` of response bodies (`REDDIT_MCP_CACHE_MAX_MB`, default 200 MB).
- Eviction: expired rows are deleted at start and every `PURGE_EVERY` writes. When the bodies pass
  `max_bytes`, the oldest rows (immutable ones too) are deleted until they are under 80 % of it.
- A cache error (a locked or broken file) never fails a tool: the read is a miss, the write is
  skipped.
"""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

DEFAULT_MAX_BYTES = 200 * 1024 * 1024
PURGE_EVERY = 200


class ResponseCache:
    def __init__(
        self,
        path: Path | str | None,
        *,
        ttl: float = 600.0,
        clock: Callable[[], float] = time.time,
        max_bytes: int = DEFAULT_MAX_BYTES,
    ):
        """`path=None` keeps the cache in memory (tests, or REDDIT_MCP_CACHE=off -> use NullCache)."""
        self.ttl = ttl
        self.clock = clock
        self.max_bytes = max(1, int(max_bytes))
        self._writes = 0
        target = ":memory:" if path is None else str(path)
        if path is not None:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        # Several Claude Code sessions may share the file: wait up to 5 s for another writer.
        self._db = sqlite3.connect(target, check_same_thread=False, timeout=5.0)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS responses ("
            " key TEXT PRIMARY KEY, body TEXT NOT NULL, stored_at REAL NOT NULL, expires_at REAL)"
        )
        self._db.execute("CREATE INDEX IF NOT EXISTS responses_stored_at ON responses (stored_at)")
        self._db.commit()
        self.purge_expired()
        self.enforce_size()

    @staticmethod
    def key(url: str, params: Mapping[str, Any]) -> str:
        return url + "?" + urlencode(sorted((k, str(v)) for k, v in params.items()))

    def get(self, key: str) -> str | None:
        try:
            row = self._db.execute("SELECT body, expires_at FROM responses WHERE key = ?", (key,)).fetchone()
        except sqlite3.Error:
            return None
        if row is None:
            return None
        body, expires_at = row
        if expires_at is not None and expires_at <= self.clock():
            return None
        return body

    def put(self, key: str, body: str, *, immutable: bool, ttl: float | None = None) -> None:
        if len(body) > self.max_bytes // 4:
            return  # one answer must not push everything else out
        now = self.clock()
        expires = None if immutable else now + (self.ttl if ttl is None else ttl)
        try:
            self._db.execute(
                "INSERT OR REPLACE INTO responses (key, body, stored_at, expires_at) VALUES (?, ?, ?, ?)",
                (key, body, now, expires),
            )
            self._db.commit()
        except sqlite3.Error:
            return
        self._writes += 1
        if self._writes % PURGE_EVERY == 0:
            self.purge_expired()
            self.enforce_size()

    def purge_expired(self) -> int:
        try:
            cur = self._db.execute(
                "DELETE FROM responses WHERE expires_at IS NOT NULL AND expires_at <= ?", (self.clock(),)
            )
            self._db.commit()
        except sqlite3.Error:
            return 0
        return cur.rowcount

    def size_bytes(self) -> int:
        try:
            return int(self._db.execute("SELECT COALESCE(SUM(LENGTH(body)), 0) FROM responses").fetchone()[0])
        except sqlite3.Error:
            return 0

    def enforce_size(self) -> int:
        """Delete the oldest rows until the bodies take under 80 % of `max_bytes`. Returns rows deleted."""
        total = self.size_bytes()
        if total <= self.max_bytes:
            return 0
        target = int(self.max_bytes * 0.8)
        deleted = 0
        try:
            rows = self._db.execute("SELECT key, LENGTH(body) FROM responses ORDER BY stored_at").fetchall()
            doomed = []
            for key, size in rows:
                if total <= target:
                    break
                doomed.append((key,))
                total -= size
            self._db.executemany("DELETE FROM responses WHERE key = ?", doomed)
            self._db.commit()
            deleted = len(doomed)
            if deleted > 1000:
                self._db.execute("VACUUM")  # give the space back to the file system
        except sqlite3.Error:
            return deleted
        return deleted

    def is_immutable(self, key: str) -> bool | None:
        row = self._db.execute("SELECT expires_at FROM responses WHERE key = ?", (key,)).fetchone()
        return None if row is None else row[0] is None

    def close(self) -> None:
        self._db.close()


class NullCache:
    """Stores nothing. Used when REDDIT_MCP_CACHE=off."""

    ttl = 0.0

    key = staticmethod(ResponseCache.key)

    def get(self, key: str) -> str | None:
        return None

    def put(self, key: str, body: str, *, immutable: bool, ttl: float | None = None) -> None:
        return None

    def purge_expired(self) -> int:
        return 0

    def close(self) -> None:
        return None
