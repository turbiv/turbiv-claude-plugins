"""Session 4 test helpers: a simulated archive listing and a tool caller."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from typing import Any

import httpx
import pytest
from fastmcp import Client

from reddit_mcp.server import build_server


def listing(items: Sequence[dict[str, Any]], key: str = "subreddit") -> Callable[[httpx.Request], Any]:
    """A reply for posts/search or comments/search that behaves like the archive: it filters by
    `subreddit`/`author`, `after` and `before` (epoch seconds, after inclusive, before exclusive),
    sorts by created_utc and returns at most `limit` items with only the requested fields."""

    def reply(request: httpx.Request) -> Any:
        p = dict(request.url.params)
        out = list(items)
        for k in ("subreddit", "author", "link_id"):
            if k in p:
                out = [x for x in out if str(x.get(k, "")).lower() == p[k].lower()]
        if "after" in p:
            out = [x for x in out if x["created_utc"] >= int(p["after"])]
        if "before" in p:
            out = [x for x in out if x["created_utc"] < int(p["before"])]
        out.sort(key=lambda x: x["created_utc"], reverse=p.get("sort", "desc") == "desc")
        out = out[: int(p.get("limit", 25))]
        if "fields" in p:
            names = p["fields"].split(",")
            out = [{n: x[n] for n in names if n in x} for x in out]
        return {"data": out}

    return reply


def ids_reply(items: Sequence[dict[str, Any]]) -> Callable[[httpx.Request], Any]:
    by_id = {x["id"]: x for x in items}

    def reply(request: httpx.Request) -> Any:
        ids = request.url.params["ids"].split(",")
        return {"data": [by_id[i] for i in ids if i in by_id]}

    return reply


@pytest.fixture
def call(client):
    """`await call("tool", {...})` -> the structured result (or the error text if it failed)."""

    async def run(tool: str, args: dict[str, Any], *, error: bool = False) -> Any:
        async with Client(build_server(client)) as c:
            r = await c.call_tool(tool, args, raise_on_error=False)
        if error:
            assert r.is_error, f"{tool} should have failed: {r.data}"
            return r.content[0].text
        assert not r.is_error, r.content[0].text if r.content else r
        return r.structured_content if r.data is None else r.data

    return run


def size_tokens(obj: Any) -> int:
    return len(json.dumps(obj, ensure_ascii=False, default=str)) // 3 + 1


@pytest.fixture
def sim():
    """`sim.listing(items)`, `sim.ids(items)`, `sim.size(obj)` (conftest functions are not importable)."""
    from types import SimpleNamespace

    return SimpleNamespace(listing=listing, ids=ids_reply, size=size_tokens)
