"""archive_status and the status feed (L1, L2, E3)."""

from __future__ import annotations

import httpx
import pytest
from fastmcp import Client

from reddit_mcp.arctic import parse_freshness
from reddit_mcp.server import build_server
from support import PROBE_TIME, load_fixture

STATUS = load_fixture("status/status-2026-11-20.json")


def test_freshness_from_the_probe_snapshot():
    f = parse_freshness(STATUS, PROBE_TIME)
    assert f.api_available is True
    assert f.newest_post_age == pytest.approx(25, abs=1)
    assert f.newest_comment_age == pytest.approx(90, abs=1)
    assert f.post_second_pass_age / 3600 == pytest.approx(36.0, abs=0.1)
    assert f.warnings == []
    s = f.summary()
    assert "The archive API is up." in s
    assert "Newest post is 25 s old." in s
    assert "comments lag 2 min" in s
    assert "36.0 h" in s


def test_stalled_ingest_and_comment_lag_warn():
    body = {**STATUS, "api": {**STATUS["api"], "mostRecentPostAt": int((PROBE_TIME - 86400) * 1000),
                              "mostRecentCommentAt": int((PROBE_TIME - 3 * 3600) * 1000)}}
    f = parse_freshness(body, PROBE_TIME)
    assert any("stopped ingesting" in w and "24.0 h" in w for w in f.warnings)
    assert any("comment ingest lags 3.0 h" in w for w in f.warnings)


def test_component_down_warns():
    body = {**STATUS, "archiver": {**STATUS["archiver"], "isAvailable": False, "failedAt": 1795213000000}}
    f = parse_freshness(body, PROBE_TIME)
    assert any("live archiver is down since 2026-11-20" in w for w in f.warnings)


@pytest.mark.anyio
async def test_archive_status_tool(client, fake_archive):
    fake_archive.add_status()
    async with Client(build_server(client)) as c:
        r = await c.call_tool("archive_status", {})
    data = r.data
    assert data["available"] is True
    assert "not live Reddit" in data["source"]
    assert data["summary"].startswith("The archive API is up. Newest post is 25 s old.")
    assert {c["name"] for c in data["components"]} >= {"api", "archiver", "archiverTrailing"}
    assert fake_archive.paths() == ["STATUS"]


@pytest.mark.anyio
async def test_archive_status_when_unreachable(client, fake_archive):
    fake_archive.add("STATUS", httpx.ConnectError("nodename nor servname provided"))
    async with Client(build_server(client)) as c:
        r = await c.call_tool("archive_status", {}, raise_on_error=False)
    assert r.is_error
    text = r.content[0].text
    assert text.startswith("archive unavailable:")
    assert "reddit.com" in text  # says it never falls back to reddit.com
