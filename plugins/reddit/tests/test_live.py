"""The one live smoke test. Runs only with REDDIT_MCP_LIVE=1. Sends 2 requests, 1 s apart."""

from __future__ import annotations

import time

import pytest

from reddit_mcp.arctic import ArcticShiftClient, NullCache, Settings, get_freshness

pytestmark = [pytest.mark.live, pytest.mark.anyio]


async def test_live_status_and_listing():
    client = ArcticShiftClient(Settings.from_env(), cache=NullCache())
    try:
        f = await get_freshness(client, max_age=0)
        assert f.api_available is not None
        r = await client.get(
            "posts/search",
            {"subreddit": "buildapc", "limit": 2, "sort": "desc"},
            fields=["id", "created_utc", "retrieved_on", "score"],
        )
        assert isinstance(r.data, list) and r.data
        assert all(time.time() - p["created_utc"] < 30 * 86400 for p in r.data)
        assert client.request_count == 2
    finally:
        await client.aclose()
