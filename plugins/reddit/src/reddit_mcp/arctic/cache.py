"""SQLite response cache (R7).

A response is stored either as immutable (it can never change in the archive) or with a TTL.
Errors are never stored.
"""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlencode


class ResponseCache:
    def __init__(self, path: Path | str | None, *, ttl: float = 600.0, clock: Callable[[], float] = time.time):
        """`path=None` keeps the cache in memory (tests, or REDDIT_MCP_CACHE=off -> use NullCache)."""
        self.ttl = ttl
        self.clock = clock
        target = ":memory:" if path is None else str(path)
        if path is not None:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(target, check_same_thread=False)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS responses ("
            " key TEXT PRIMARY KEY, body TEXT NOT NULL, stored_at REAL NOT NULL, expires_at REAL)"
        )
        self._db.commit()
        self.purge_expired()

    @staticmethod
    def key(url: str, params: Mapping[str, Any]) -> str:
        return url + "?" + urlencode(sorted((k, str(v)) for k, v in params.items()))

    def get(self, key: str) -> str | None:
        row = self._db.execute("SELECT body, expires_at FROM responses WHERE key = ?", (key,)).fetchone()
        if row is None:
            return None
        body, expires_at = row
        if expires_at is not None and expires_at <= self.clock():
            return None
        return body

    def put(self, key: str, body: str, *, immutable: bool, ttl: float | None = None) -> None:
        now = self.clock()
        expires = None if immutable else now + (self.ttl if ttl is None else ttl)
        self._db.execute(
            "INSERT OR REPLACE INTO responses (key, body, stored_at, expires_at) VALUES (?, ?, ?, ?)",
            (key, body, now, expires),
        )
        self._db.commit()

    def purge_expired(self) -> int:
        cur = self._db.execute(
            "DELETE FROM responses WHERE expires_at IS NOT NULL AND expires_at <= ?", (self.clock(),)
        )
        self._db.commit()
        return cur.rowcount

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
