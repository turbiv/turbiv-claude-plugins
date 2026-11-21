"""The SQLite cache (R7): location, size cap, eviction, and failures that never break a tool."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from reddit_mcp.arctic import ResponseCache, Settings
from reddit_mcp.arctic.cache import PURGE_EVERY


class Clock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


def test_default_location_is_the_user_cache_dir(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert Settings.from_env({}).cache_path == tmp_path / ".cache" / "reddit-mcp" / "cache.sqlite3"
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    assert Settings().cache_path == tmp_path / "xdg" / "reddit-mcp" / "cache.sqlite3"
    assert Settings.from_env({"REDDIT_MCP_CACHE": "off"}).cache_path is None
    assert Settings.from_env({"REDDIT_MCP_CACHE_MAX_MB": "50"}).cache_max_mb == 50.0
    assert Settings().cache_max_mb == 200.0


def test_expired_rows_are_deleted_on_later_writes(tmp_path: Path):
    clock = Clock()
    c = ResponseCache(tmp_path / "c.sqlite3", ttl=10, clock=clock)
    c.put("old", "x", immutable=False)
    c.put("keep", "y", immutable=True)
    clock.t += 11
    assert c.get("old") is None  # expired: a miss at once
    for i in range(PURGE_EVERY):
        c.put(f"k{i}", "z", immutable=False)
    rows = {r[0] for r in c._db.execute("SELECT key FROM responses")}
    assert "old" not in rows and "keep" in rows


def test_size_cap_evicts_the_oldest_rows(tmp_path: Path):
    clock = Clock()
    c = ResponseCache(tmp_path / "c.sqlite3", clock=clock, max_bytes=10_000)
    for i in range(PURGE_EVERY):
        clock.t += 1
        c.put(f"k{i}", "b" * 200, immutable=True)  # 40,000 bytes in all
    assert c.size_bytes() <= 10_000
    assert c.get(f"k{PURGE_EVERY - 1}") is not None  # the newest stay
    assert c.get("k0") is None  # the oldest went, immutable or not


def test_size_is_enforced_at_start(tmp_path: Path):
    path = tmp_path / "c.sqlite3"
    big = ResponseCache(path, max_bytes=10**9)
    for i in range(50):
        big.put(f"k{i}", "b" * 1000, immutable=True)
    big.close()
    small = ResponseCache(path, max_bytes=20_000)
    assert small.size_bytes() <= 20_000


def test_one_huge_answer_is_not_stored(tmp_path: Path):
    c = ResponseCache(tmp_path / "c.sqlite3", max_bytes=4000)
    c.put("huge", "x" * 2000, immutable=True)
    assert c.get("huge") is None


def test_a_broken_cache_never_fails_a_call(tmp_path: Path):
    c = ResponseCache(tmp_path / "c.sqlite3")
    c._db.close()  # every later statement raises sqlite3.ProgrammingError
    assert c.get("k") is None
    c.put("k", "v", immutable=True)  # no exception
    assert c.purge_expired() == 0 and c.size_bytes() == 0


def test_locked_file_is_a_miss_not_an_error(tmp_path: Path):
    path = tmp_path / "c.sqlite3"
    c = ResponseCache(path)
    c._db.execute("PRAGMA busy_timeout = 0")
    other = sqlite3.connect(path)
    other.execute("BEGIN EXCLUSIVE")
    try:
        c.put("k", "v", immutable=True)  # database is locked: skipped
        assert c.get("k") is None
    finally:
        other.rollback()
        other.close()


def test_an_unusable_cache_falls_back_to_no_cache(tmp_path: Path, capsys):
    from reddit_mcp.arctic import ArcticShiftClient, NullCache
    from reddit_mcp.arctic.cache import open_cache

    bad = tmp_path / "corrupt.sqlite3"
    bad.write_bytes(b"this is not a sqlite file" * 100)
    assert isinstance(open_cache(bad, ttl=60), NullCache)
    blocker = tmp_path / "a-file"
    blocker.write_text("x")
    assert isinstance(open_cache(blocker / "sub" / "c.sqlite3", ttl=60), NullCache)  # parent is a file
    err = capsys.readouterr().err
    assert err.count("running without a cache") == 2
    client = ArcticShiftClient(Settings(cache_path=bad))  # the server starts anyway
    assert isinstance(client.cache, NullCache) and client.cache.is_immutable("k") is None


def test_is_immutable_survives_a_broken_file(tmp_path: Path):
    c = ResponseCache(tmp_path / "c.sqlite3")
    c._db.close()
    assert c.is_immutable("k") is None
