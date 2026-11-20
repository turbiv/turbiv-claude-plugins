"""The Arctic Shift client: R1-R7, E1-E4, T5, T8, D1."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from reddit_mcp.arctic import (
    ArchiveUnavailable,
    DEFAULT_POST_FIELDS,
    InputError,
    QueryRejected,
    QueryTooHeavy,
    RateLimited,
)
from support import PROBE_TIME, load_fixture, make_client

pytestmark = pytest.mark.anyio

ERR_422 = load_fixture("client/error-422.json")
PHRASE = load_fixture("posts/buildapc-title-phrase.json")


# ---------------------------------------------------------------- R1 pacing, one in flight


async def test_requests_are_spaced_and_serial(client, fake_archive, fake_time):
    fake_archive.add("posts/search", PHRASE)
    for i in range(3):
        await client.get("posts/search", {"subreddit": "buildapc", "limit": 5 + i}, fields=["id"])
    assert len(fake_archive.requests) == 3
    # each later request waited out the rest of the 1 s spacing (answers take 0.1 s)
    assert fake_time.sleeps == pytest.approx([1.0, 1.0])


async def test_parallel_calls_still_go_one_at_a_time(client, fake_archive):
    fake_archive.add("posts/search", PHRASE)
    await asyncio.gather(
        *(client.get("posts/search", {"subreddit": f"s{i}"}, fields=["id"]) for i in range(4))
    )
    assert len(fake_archive.requests) == 4
    assert fake_archive.max_in_flight == 1


async def test_spacing_has_a_floor(fake_archive, fake_time):
    c = make_client(fake_archive, fake_time, min_interval=0.1)
    assert c.settings.min_interval == 0.5


# ---------------------------------------------------------------- R3 fields whitelist


async def test_search_needs_fields(client, fake_archive):
    with pytest.raises(InputError, match="needs fields"):
        await client.get("posts/search", {"subreddit": "buildapc"})
    assert fake_archive.requests == []


async def test_bad_field_is_rejected_before_the_network(client, fake_archive):
    with pytest.raises(InputError, match="permalink.*full=True"):
        await client.get("posts/search", {"subreddit": "buildapc"}, fields=["id", "permalink"])
    with pytest.raises(InputError, match="body"):
        await client.get("posts/search", {"subreddit": "buildapc"}, fields=["body"])
    assert fake_archive.requests == []


async def test_fields_are_sent_as_a_list(client, fake_archive):
    fake_archive.add("posts/search", PHRASE)
    await client.get("posts/search", {"subreddit": "buildapc"}, fields=DEFAULT_POST_FIELDS)
    assert fake_archive.params()["fields"] == ",".join(DEFAULT_POST_FIELDS)


async def test_full_objects_on_purpose(client, fake_archive):
    fake_archive.add("comments/search", load_fixture("comments/askreddit-4d-full.json"))
    r = await client.get("comments/search", {"subreddit": "AskReddit"}, full=True)
    assert "fields" not in fake_archive.params()
    assert len(r.data) == 2


# ---------------------------------------------------------------- R4, T5, T8 input rules


async def test_limit_rules(client, fake_archive):
    with pytest.raises(InputError, match="1-100"):
        await client.get("posts/search", {"subreddit": "x", "limit": 500}, fields=["id"])
    with pytest.raises(InputError, match="auto"):
        await client.get("posts/search", {"subreddit": "x", "limit": "auto"}, fields=["id"])
    assert fake_archive.requests == []


async def test_global_keyword_search_is_refused(client, fake_archive):
    for kw in ("query", "title", "selftext"):
        with pytest.raises(InputError, match="no Reddit-wide search"):
            await client.get("posts/search", {kw: "keyboard"}, fields=["id"])
    with pytest.raises(InputError, match="no Reddit-wide search"):
        await client.get("comments/search", {"body": "keyboard"}, fields=["id"])
    assert fake_archive.requests == []


async def test_global_listing_without_keyword_is_allowed(client, fake_archive):
    fake_archive.add("posts/search", load_fixture("posts/global-newest.json"))
    r = await client.get("posts/search", {"limit": 5, "sort": "desc"}, fields=["id", "subreddit", "created_utc"])
    assert len(r.data) == 5


async def test_relative_offsets_are_never_sent(client, fake_archive):
    with pytest.raises(InputError, match="epoch seconds"):
        await client.get("posts/search", {"subreddit": "x", "before": "3m"}, fields=["id"])
    with pytest.raises(InputError, match="epoch seconds"):
        await client.get("posts/search", {"subreddit": "x", "after": "2025-01-01"}, fields=["id"])
    assert fake_archive.requests == []


# ---------------------------------------------------------------- R6, D1


async def test_user_agent_names_the_project(client, fake_archive):
    fake_archive.add("posts/search", PHRASE)
    await client.get("posts/search", {"subreddit": "buildapc"}, fields=["id"])
    ua = fake_archive.requests[0].headers["user-agent"]
    assert ua.startswith("reddit-research-mcp/")
    assert "github.com/turbiv/turbiv-claude-plugins" in ua


async def test_never_contacts_reddit(client):
    for url in ("https://www.reddit.com/r/x/new.json", "https://old.reddit.com/", "https://redd.it/abc"):
        with pytest.raises(InputError, match="refusing to contact"):
            await client._send(url, {})


async def test_only_configured_hosts(client):
    with pytest.raises(InputError, match="refusing to contact"):
        await client._send("https://example.com/api/posts/search", {})


# ---------------------------------------------------------------- R5 batching


async def test_ids_are_split_into_batches_of_500(client, fake_archive):
    fake_archive.add("posts/ids", lambda req: {"data": [{"id": i} for i in req.url.params["ids"].split(",")]})
    ids = [f"t3_a{i}" for i in range(1200)] + ["a0"]  # one duplicate
    out = await client.get_ids("posts", ids, fields=["id"])
    sizes = [len(r.url.params["ids"].split(",")) for r in fake_archive.requests]
    assert sizes == [500, 500, 200]
    assert len(out) == 1200
    assert not any(i.startswith("t3_") for r in fake_archive.requests for i in r.url.params["ids"].split(","))


async def test_generic_batches(client, fake_archive):
    fake_archive.add("short_links", {"data": []})
    await client.get_batched("short_links", "paths", [f"/r/x/s/{i}" for i in range(2500)], 1000)
    assert len(fake_archive.requests) == 3


# ---------------------------------------------------------------- E1 429


async def test_429_waits_for_reset_at_then_retries_once(client, fake_archive, fake_time):
    reset_at = int((PROBE_TIME + 20) * 1000)
    fake_archive.add("posts/search", (429, {"error": "slow"}, {"x-ratelimit-reset-at": str(reset_at)}), PHRASE)
    r = await client.get("posts/search", {"subreddit": "buildapc"}, fields=["id"])
    assert len(r.data) == 5
    assert len(fake_archive.requests) == 2
    assert 19 <= fake_time.sleeps[0] <= 20


async def test_429_wait_is_capped(client, fake_archive, fake_time):
    fake_archive.add("posts/search", (429, {}, {"x-ratelimit-reset": "500"}), PHRASE)
    await client.get("posts/search", {"subreddit": "buildapc"}, fields=["id"])
    assert fake_time.sleeps[0] == pytest.approx(65)


async def test_second_429_gives_up(client, fake_archive):
    fake_archive.add("posts/search", (429, {}, {"x-ratelimit-reset": "30"}))
    with pytest.raises(RateLimited, match="rate limiting"):
        await client.get("posts/search", {"subreddit": "buildapc"}, fields=["id"])
    assert len(fake_archive.requests) == 2


# ---------------------------------------------------------------- E2 422


async def test_422_retries_twice_halving_limit_then_explains(client, fake_archive, fake_time):
    fake_archive.add("posts/search", (422, ERR_422))
    with pytest.raises(QueryTooHeavy) as e:
        await client.get("posts/search", {"subreddit": "buildapc", "title": "power limit", "limit": 100}, fields=["id"])
    assert [p["limit"] for p in (r.url.params for r in fake_archive.requests)] == ["100", "50", "25"]
    err = e.value
    assert err.error == "Timeout. Maybe slow down a bit"
    assert len(err.attempts) == 3
    assert err.fast  # each answer took 0.1 s
    assert "busy" in err.suggestions[0]  # fast 422 = load shedding (probes Q7)
    assert any("window" in s for s in err.suggestions)
    assert "too heavy" in str(err)
    retry_sleeps = [s for s in fake_time.sleeps if s >= 1.0]
    assert all(1.0 <= s <= 3.0 for s in retry_sleeps) and len(retry_sleeps) >= 2


async def test_422_then_success_reports_narrowing(client, fake_archive):
    fake_archive.add("posts/search", (422, ERR_422), PHRASE)
    r = await client.get("posts/search", {"subreddit": "buildapc", "title": '"power limit"', "limit": 100}, fields=["id"])
    assert r.narrowed and r.params["limit"] == "50"
    assert "limit 100 -> 50" in r.notes[0]


async def test_422_without_retries(client, fake_archive):
    fake_archive.add("posts/search", (422, ERR_422))
    with pytest.raises(QueryTooHeavy):
        await client.get("posts/search", {"subreddit": "buildapc", "title": "x"}, fields=["id"], retry_422=0)
    assert len(fake_archive.requests) == 1


# ---------------------------------------------------------------- E4 400


async def test_400_error_is_verbatim(client, fake_archive):
    fake_archive.add("subreddits/search", (400, {"data": None, "error": "'foo' is not a valid field"}))
    with pytest.raises(QueryRejected) as e:
        await client.get("subreddits/search", {"subreddit": "x"})
    assert e.value.error == "'foo' is not a valid field"
    assert "'foo' is not a valid field" in str(e.value)


# ---------------------------------------------------------------- E3 outage vs query error


async def test_5xx_with_status_up_is_not_called_an_outage(client, fake_archive):
    fake_archive.add("posts/search", (500, "Internal Server Error")).add_status()
    with pytest.raises(ArchiveUnavailable) as e:
        await client.get("posts/search", {"author": "someone"}, fields=["id"])
    assert not e.value.outage
    assert "status page says the API is up" in str(e.value)
    assert fake_archive.paths() == ["posts/search", "STATUS"]


async def test_cloudflare_530_with_status_down_is_an_outage(client, fake_archive):
    status = load_fixture("status/status-2026-11-20.json")
    status["api"] = {**status["api"], "isAvailable": False, "failedAt": 1795213000000}
    fake_archive.add("posts/search", (530, "error code: 1033")).add_status(status)
    with pytest.raises(ArchiveUnavailable) as e:
        await client.get("posts/search", {"subreddit": "x"}, fields=["id"])
    assert e.value.outage
    msg = str(e.value)
    assert msg.startswith("archive unavailable: HTTP 530")
    assert "API is down" in msg and "never falls back to reddit.com" in msg


async def test_connection_failure_and_status_unreachable(client, fake_archive):
    fake_archive.add("posts/search", httpx.ConnectError("nodename nor servname provided"))
    fake_archive.add("STATUS", httpx.ConnectError("nodename nor servname provided"))
    with pytest.raises(ArchiveUnavailable) as e:
        await client.get("posts/search", {"subreddit": "x"}, fields=["id"])
    assert e.value.outage and e.value.status_error
    assert "could not connect" in str(e.value) and "status page could not be read" in str(e.value)


async def test_timeout_is_unavailable(client, fake_archive):
    fake_archive.add("posts/search", httpx.ReadTimeout("slow")).add_status()
    with pytest.raises(ArchiveUnavailable, match="no answer within"):
        await client.get("posts/search", {"subreddit": "x"}, fields=["id"])


async def test_html_body_on_200_is_unavailable(client, fake_archive):
    fake_archive.add("posts/search", (200, "<html>cloudflare</html>"))
    with pytest.raises(ArchiveUnavailable, match="not JSON"):
        await client.get("posts/search", {"subreddit": "x"}, fields=["id"])


async def test_error_member_on_200(client, fake_archive):
    fake_archive.add("posts/search", {"data": None, "error": "something odd"})
    with pytest.raises(QueryRejected, match="something odd"):
        await client.get("posts/search", {"subreddit": "x"}, fields=["id"])


# ---------------------------------------------------------------- R7 cache


async def test_cache_hit_makes_no_request(client, fake_archive):
    fake_archive.add("posts/search", PHRASE)
    a = await client.get("posts/search", {"subreddit": "buildapc"}, fields=["id"])
    b = await client.get("posts/search", {"subreddit": "buildapc"}, fields=["id"])
    assert len(fake_archive.requests) == 1
    assert b.from_cache and b.data == a.data


async def test_recent_results_expire(client, fake_archive, fake_time):
    fake_archive.add("posts/search", PHRASE)
    await client.get("posts/search", {"subreddit": "buildapc"}, fields=["id"])
    fake_time.advance(client.settings.cache_ttl + 1)
    await client.get("posts/search", {"subreddit": "buildapc"}, fields=["id"])
    assert len(fake_archive.requests) == 2


async def test_old_closed_window_is_immutable(client, fake_archive):
    old = [{"id": "wi7uhk", "created_utc": 1659849574}]
    fake_archive.add("posts/search", {"data": old})
    params = {"subreddit": "buildapc", "before": 1660089600}
    await client.get("posts/search", params, fields=["id", "created_utc"])
    key = client.cache.key(f"{client.settings.base_url}/posts/search", fake_archive.params())
    assert client.cache.is_immutable(key) is True


async def test_open_window_is_not_immutable(client, fake_archive):
    fake_archive.add("posts/search", {"data": [{"id": "a", "created_utc": 1659849574}]})
    await client.get("posts/search", {"subreddit": "buildapc"}, fields=["id", "created_utc"])
    key = client.cache.key(f"{client.settings.base_url}/posts/search", fake_archive.params())
    assert client.cache.is_immutable(key) is False


async def test_ids_of_final_items_are_immutable(client, fake_archive):
    data = load_fixture("comments/askreddit-45d-full.json")
    fake_archive.add("comments/ids", data)
    await client.get("comments/ids", {"ids": "pebdp7r,pebdp4b"}, full=True)
    key = client.cache.key(f"{client.settings.base_url}/comments/ids", fake_archive.params())
    assert client.cache.is_immutable(key) is True


async def test_errors_are_not_cached(client, fake_archive):
    fake_archive.add("posts/search", (422, ERR_422), (422, ERR_422), (422, ERR_422), PHRASE)
    with pytest.raises(QueryTooHeavy):
        await client.get("posts/search", {"subreddit": "buildapc", "title": "x"}, fields=["id"])
    r = await client.get("posts/search", {"subreddit": "buildapc", "title": "x"}, fields=["id"])
    assert not r.from_cache and len(r.data) == 5


async def test_sqlite_cache_on_disk(tmp_path, fake_archive, fake_time):
    from reddit_mcp.arctic import ResponseCache

    path = tmp_path / "c" / "cache.sqlite3"
    c1 = make_client(fake_archive, fake_time)
    c1.cache = ResponseCache(path, clock=fake_time.wall)
    fake_archive.add("posts/search", PHRASE)
    await c1.get("posts/search", {"subreddit": "buildapc"}, fields=["id"])
    c1.cache.close()
    c2 = make_client(fake_archive, fake_time)
    c2.cache = ResponseCache(path, clock=fake_time.wall)
    r = await c2.get("posts/search", {"subreddit": "buildapc"}, fields=["id"])
    assert r.from_cache and len(fake_archive.requests) == 1


async def test_status_is_cached_briefly(client, fake_archive):
    fake_archive.add_status()
    await client.status()
    await client.status()
    assert fake_archive.paths() == ["STATUS"]


async def test_slow_422_is_called_too_heavy_not_busy(client, fake_archive):
    fake_archive.elapsed = 5.5  # the archive ran the query and timed out
    fake_archive.add("posts/search", (422, ERR_422))
    with pytest.raises(QueryTooHeavy) as e:
        await client.get("posts/search", {"subreddit": "buildapc", "title": "power limit"}, fields=["id"])
    assert not e.value.fast
    assert not any("busy" in s for s in e.value.suggestions)


async def test_429_holds_back_other_calls_too(client, fake_archive, fake_time):
    fake_archive.add("posts/search", (429, {}, {"x-ratelimit-reset": "30"}), PHRASE, match=lambda r: r.url.params.get("subreddit") == "a")
    fake_archive.add("posts/search", PHRASE, match=lambda r: r.url.params.get("subreddit") == "b")
    start = fake_time.monotonic()
    await asyncio.gather(
        client.get("posts/search", {"subreddit": "a"}, fields=["id"]),
        client.get("posts/search", {"subreddit": "b"}, fields=["id"]),
    )
    # request 1 got 429 at ~0.1 s; neither later request went out before the 30 s reset
    assert len(fake_archive.requests) == 3
    assert fake_time.monotonic() - start >= 30
    assert fake_archive.max_in_flight == 1
