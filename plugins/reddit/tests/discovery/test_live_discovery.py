"""Live smoke test for Session 4. Runs only with REDDIT_MCP_LIVE=1. About 4 requests."""

from __future__ import annotations

import pytest
from fastmcp import Client

from reddit_mcp.arctic import ArcticShiftClient, NullCache, Settings
from reddit_mcp.server import build_server

pytestmark = [pytest.mark.live, pytest.mark.anyio]


async def test_live_share_link_resolves_to_the_eval_post():
    client = ArcticShiftClient(Settings.from_env(), cache=NullCache())
    try:
        async with Client(build_server(client)) as c:
            r = await c.call_tool("resolve_share_link", {"url": "https://www.reddit.com/r/running/s/0MH2aME2Z9"})
        link = r.data["links"][0]
        assert link["resolved"] is True
        assert link["post_id"] == "16puhb3" and link["comment_id"] == "k1unwm1"
        assert link["post"]["title"].startswith("Achievements for Saturday, September 23, 2023")
        assert client.request_count <= 4
    finally:
        await client.aclose()
