"""Fixes from the Session 5 code review (docs/review.md, "Code review")."""

from __future__ import annotations

import pytest
from fastmcp import Client

from reddit_mcp.arctic import RateLimited, estimate_tokens, make_result, resolve_window, to_epoch
from reddit_mcp.server import build_server
from support import PROBE_TIME, load_fixture

pytestmark = pytest.mark.anyio

PHRASE = load_fixture("posts/buildapc-title-phrase.json")


def page(n: int, start: int = 1700000000) -> dict:
    return {"data": [{"id": f"p{i}", "subreddit": "s", "created_utc": start - i} for i in range(n)]}


async def call(client, tool, args):
    async with Client(build_server(client)) as c:
        return await c.call_tool(tool, args, raise_on_error=False)


async def test_a_narrowed_answer_never_stands_in_for_the_full_one(client, fake_archive):
    """A 422 retry with limit 50 must not be served later as the answer to limit=100."""
    fake_archive.add("posts/search", (422, {"error": "Timeout"}), page(50), page(100))
    params = {"subreddit": "s", "limit": 100, "before": 1700000001}
    first = await client.get("posts/search", params, fields=["id"])
    assert first.narrowed and len(first.data) == 50
    second = await client.get("posts/search", params, fields=["id"])
    assert not second.from_cache and len(second.data) == 100


async def test_partial_ids_answer_is_not_cached_forever(client, fake_archive):
    old = {"id": "a", "created_utc": 1600000000}
    fake_archive.add("posts/ids", {"data": [old]})
    await client.get("posts/ids", {"ids": "a,b"}, fields=["id"])
    key = client.cache.key(f"{client.settings.base_url}/posts/ids", fake_archive.params())
    assert client.cache.is_immutable(key) is False  # b may be backfilled later
    await client.get("posts/ids", {"ids": "a"}, fields=["id"])
    key = client.cache.key(f"{client.settings.base_url}/posts/ids", fake_archive.params())
    assert client.cache.is_immutable(key) is True


async def test_second_429_blocks_the_next_request_too(client, fake_archive, fake_time):
    fake_archive.add("posts/search", (429, {}, {"x-ratelimit-reset": "30"}), (429, {}, {"x-ratelimit-reset": "30"}), PHRASE)
    with pytest.raises(RateLimited):
        await client.get("posts/search", {"subreddit": "a"}, fields=["id"])
    fake_time.sleeps.clear()
    await client.get("posts/search", {"subreddit": "b"}, fields=["id"])
    assert fake_time.sleeps and fake_time.sleeps[0] >= 29


def test_integer_years_are_years():
    assert to_epoch(2022) == to_epoch("2022") == 1640995200
    w = resolve_window(None, 2022, 2023, now=PROBE_TIME)
    assert (w.after, w.before) == (1640995200, 1704067200)  # 2022-01-01 to the end of 2023
    assert to_epoch(1659849574) == 1659849574  # real epoch seconds unchanged


async def test_trending_counts_429_retries_against_the_budget(client, fake_archive):
    fake_archive.add_status()
    replies = []
    for _ in range(20):
        replies += [(429, {}, {"x-ratelimit-reset": "1"}), {"data": [
            {"id": f"c{len(replies)}", "link_id": "t3_x", "subreddit": "s", "author": "u",
             "created_utc": int(PROBE_TIME) - 60 * len(replies)} for _ in range(1)]}]
    fake_archive.add("comments/search", *replies)
    fake_archive.add("posts/ids", {"data": []})
    r = await call(client, "trending_posts", {"subreddits": ["s"], "max_requests": 5})
    assert not r.is_error, r.content[0].text
    archive = [p for p in fake_archive.paths() if p != "STATUS"]
    assert len(archive) <= 5 + 1  # the budget, plus one 429 retry at the very end at most


async def test_budget_below_one_page_per_stream_is_refused(client, fake_archive):
    subs = [f"s{i}" for i in range(10)]
    r = await call(client, "count_mentions", {"subreddits": subs, "terms": ["x"], "in": "both", "max_requests": 2})
    assert r.is_error and "max_requests must be at least 21" in r.content[0].text
    r = await call(client, "trending_posts", {"subreddits": subs, "max_requests": 1})
    assert r.is_error and "max_requests must be at least 11" in r.content[0].text
    assert fake_archive.requests == []


async def test_last_budget_request_gets_no_422_retry(client, fake_archive):
    fake_archive.add_status()
    fake_archive.add("comments/search", (422, {"error": "Timeout"}))
    fake_archive.add("posts/ids", {"data": []})
    r = await call(client, "trending_posts", {"subreddits": ["a", "b"], "max_requests": 4})
    assert not r.is_error
    assert len([p for p in fake_archive.paths() if p == "comments/search"]) <= 3


async def test_other_long_lists_are_trimmed_to_the_budget(client, fake_archive):
    fake_archive.add_status()
    threads = [{"id": f"t{i}", "title": "x" * 200} for i in range(200)]
    r = await make_result(client, items=[{"id": "a", "body": "y" * 100}], threads=threads)
    assert estimate_tokens(r) <= 8000 - 150
    assert r["omitted_threads"] > 0 and r["truncated"] is True
    assert r["items"]  # the items themselves survive
