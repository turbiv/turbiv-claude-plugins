"""deep_search: the anchor walk, the 422 rules (probes Q7), the local step and the coverage report."""

from __future__ import annotations

import pytest
from fastmcp import Client

from posts.postdb import DAY, post
from reddit_mcp.server import build_server
from support import PROBE_TIME

pytestmark = pytest.mark.anyio

CONCEPTS = [["9900k", "i9-9900k", "9900kf"], ["power limit", "PL1", "PL2", "undervolt", "underclock", "TDP"]]
WI7UHK = dict(
    title="Intel 9900K Underclocking/Power Limit Experiments", author="willswill", score=9, num_comments=2,
    selftext="I have been running my 9900K at lower PL1 and PL2 values to see the temps...",
)


async def deep(client, **args):
    async with Client(build_server(client)) as c:
        return await c.call_tool("deep_search", {"concepts": CONCEPTS, "subreddits": ["buildapc"], **args},
                                 raise_on_error=False)


def sent(fake_archive, path="posts/search"):
    return [dict(r.url.params) for r in fake_archive.requests if r.url.path.endswith(path)]


def filler(n, *, start_age=1, per_day=1.0, sub="buildapc", title="9900k temps"):
    return [post(f"f{sub}{i}", sub, age_days=start_age + i / per_day, title=title) for i in range(n)]


async def test_finds_an_old_post_by_walking_back(client, db, fake_archive):
    old = post("wi7uhk", age_days=(PROBE_TIME - 1659849574) / DAY, **WI7UHK)
    db.add(*filler(250, per_day=4), old, post("noise", title="9900k vs 5800x gaming", age_days=900))
    r = await deep(client)
    d = r.data
    assert not r.is_error
    top = d["candidates"][0]
    assert top["id"] == "wi7uhk" and top["concepts_matched"] == "2/2"
    assert "9900k (title)" in top["matched"] and "power limit (title)" in top["matched"]
    assert top["permalink"].endswith("/r/buildapc/comments/wi7uhk/")
    cov = d["coverage"]
    assert cov["truncated"] is False and cov["full_matches"] == 1
    assert cov["requests_used"] <= 30
    title_step = cov["steps"][0]
    assert title_step["step"] == "title=9900k" and title_step["status"] == "done" and title_step["pages"] == 3
    assert [s["step"] for s in cov["steps"]] == ["title=9900k", "title=9900kf", "query=9900k", "query=9900kf"]
    first = sent(fake_archive)[0]
    assert first["title"] == "9900k" and first["limit"] == "100" and first["sort"] == "desc"
    # then the same term as query (title + selftext)
    assert any(p.get("query") == "9900k" for p in sent(fake_archive))


async def test_selftext_only_match_comes_from_the_query_step(client, db, fake_archive):
    db.add(post("body", title="CPU settings question", selftext="My i9 9900k with a 95W power limit", age_days=500))
    d = (await deep(client)).data
    assert d["candidates"][0]["id"] == "body"
    assert "(selftext)" in d["candidates"][0]["matched"]


async def test_rank_by_coverage_then_comments(client, db, fake_archive):
    db.add(post("a", title="9900k undervolt guide", num_comments=5, age_days=30),
           post("b", title="9900k temps", num_comments=500, age_days=31),
           post("c", title="9900k TDP question", num_comments=50, age_days=32))
    d = (await deep(client)).data
    assert [c["id"] for c in d["candidates"]] == ["c", "a", "b"]


async def test_title_coverage_breaks_ties_before_comment_count(client, db, fake_archive):
    db.add(post("wi7uhk", age_days=1500, **WI7UHK),
           post("busy", title="9900k build check", selftext="I set a power limit of 95W", num_comments=300, age_days=40))
    d = (await deep(client)).data
    assert [c["id"] for c in d["candidates"]] == ["wi7uhk", "busy"]


async def test_fast_422_waits_10s_and_retries_the_same_window(client, db, fake_archive, fake_time):
    db.add(post("hit", title="9900k power limit", age_days=10))
    calls = {"n": 0}

    def fail(p):
        if p.get("title") and calls["n"] == 0:
            calls["n"] += 1
            return (422, {"error": "Timeout. Maybe slow down a bit"})
        return None

    db.fail = fail
    d = (await deep(client)).data
    assert d["candidates"][0]["id"] == "hit"
    assert 10.0 in fake_time.sleeps
    titles = [p for p in sent(fake_archive) if "title" in p]
    assert titles[0] == titles[1]  # same window, retried once
    assert d["coverage"]["windows_failed"] == []


async def test_second_fast_422_halves_the_window(client, db, fake_archive):
    db.add(post("hit", title="9900k power limit", age_days=10))
    calls = {"n": 0}

    def fail(p):
        if p.get("title") and calls["n"] < 2:
            calls["n"] += 1
            return (422, {"error": "Timeout. Maybe slow down a bit"})
        return None

    db.fail = fail
    await deep(client, after="2020-01-01")
    titles = [p for p in sent(fake_archive) if "title" in p]
    full = int(titles[0]["before"]) - int(titles[0]["after"])
    assert int(titles[2]["before"]) - int(titles[2]["after"]) == full // 2


async def test_fast_422_waits_grow_and_reset(client, db, fake_archive, fake_time):
    db.add(post("hit", title="9900k power limit", age_days=10))
    calls = {"n": 0}

    def fail(p):
        if p.get("title") and calls["n"] < 3:
            calls["n"] += 1
            return (422, {"error": "Timeout. Maybe slow down a bit"})
        return None

    db.fail = fail
    d = (await deep(client, after="2020-01-01")).data
    assert [w for w in fake_time.sleeps if w >= 10] == [10.0, 20.0, 40.0]
    assert d["coverage"]["seconds_waited_after_422"] == 70


async def test_slow_422_halves_at_once(client, db, fake_archive, fake_time):
    db.add(post("hit", title="9900k power limit", age_days=10))
    calls = {"n": 0}

    def fail(p):
        if p.get("title") and calls["n"] == 0:
            calls["n"] += 1
            fake_time.advance(5.0)  # a real timeout takes seconds
            return (422, {"error": "Timeout. Maybe slow down a bit"})
        return None

    db.fail = fail
    await deep(client, after="2020-01-01")
    titles = [p for p in sent(fake_archive) if "title" in p]
    assert 10.0 not in fake_time.sleeps
    full = int(titles[0]["before"]) - int(titles[0]["after"])
    assert int(titles[1]["before"]) - int(titles[1]["after"]) == full // 2


async def test_always_failing_archive_stays_in_budget_and_reports(client, db, fake_archive):
    db.fail = lambda p: (422, {"error": "Timeout. Maybe slow down a bit"})
    r = await deep(client, max_requests=12)
    d = r.data
    cov = d["coverage"]
    assert cov["requests_used"] <= 12
    assert d["candidates"] == []
    assert any("web search" in n for n in d["notes"])
    assert cov["seconds_waited_after_422"] <= 240 + 60
    assert any(n.startswith("stopped early") for n in d["notes"])


async def test_budget_truncates_and_says_where_to_continue(client, db, fake_archive):
    db.add(*filler(1000, per_day=2))
    d = (await deep(client, max_requests=4)).data
    cov = d["coverage"]
    assert cov["truncated"] is True and cov["requests_used"] <= 4
    assert cov["continue_with"]["before"] < PROBE_TIME
    assert any(n.startswith("truncated") and "before=" in n for n in d["notes"])
    assert cov["steps"][0]["resume_before"] == cov["continue_with"]["before"]


async def test_several_subreddits_share_the_budget_and_dedupe(client, db, fake_archive):
    db.add(post("x1", "buildapc", title="9900k power limit", age_days=3),
           post("y1", "intel", title="9900k PL1 PL2 values", age_days=4))
    async with Client(build_server(client)) as c:
        r = await c.call_tool("deep_search", {"concepts": CONCEPTS, "subreddits": ["buildapc", "intel", "buildapc"]})
    d = r.data
    assert d["subreddits"] == ["buildapc", "intel"]
    assert {c["id"] for c in d["candidates"]} == {"x1", "y1"}
    assert len(d["candidates"]) == 2


async def test_comment_step_groups_by_post_and_fetches_posts(client, db, fake_archive):
    db.add(post("thr", title="Which CPU settings?", selftext="", age_days=300, num_comments=40))
    db.comments = [
        {"id": f"c{i}", "link_id": "t3_thr", "subreddit": "buildapc", "body": "set your 9900k PL1 to 95W",
         "created_utc": int(PROBE_TIME - (300 - i) * DAY), "score": i} for i in range(3)
    ]
    async with Client(build_server(client)) as c:
        r = await c.call_tool("deep_search", {"concepts": CONCEPTS, "subreddits": ["buildapc"], "in": "comments"})
    d = r.data
    top = d["candidates"][0]
    assert top["id"] == "thr" and top["concepts_matched"] == "2/2"
    assert "(comment)" in top["matched"] and top["matching_comments"] == 3
    assert top["comment_links"][0].endswith("/comments/thr/_/c2/")
    body = sent(fake_archive, "comments/search")[0]["body"]
    assert body.startswith("9900k OR ")
    assert fake_archive.paths().count("posts/ids") == 1


async def test_comment_or_syntax_falls_back_to_one_term(client, db, fake_archive):
    db.comments = [{"id": "c1", "link_id": "t3_p", "subreddit": "buildapc", "body": "9900k undervolt",
                    "created_utc": int(PROBE_TIME - 9 * DAY), "score": 1}]
    db.add(post("p", title="help", age_days=9))
    db.fail = lambda p: (422, {"error": "Timeout"}) if " OR " in p.get("body", "") else None
    async with Client(build_server(client)) as c:
        r = await c.call_tool("deep_search", {"concepts": CONCEPTS, "subreddits": ["buildapc"], "in": "comments"})
    assert r.data["candidates"][0]["id"] == "p"
    assert sent(fake_archive, "comments/search")[-1]["body"] == "9900k"
    assert "fell back" in r.data["coverage"]["steps"][0]["note"]


async def test_input_checks(client, db, fake_archive):
    async with Client(build_server(client)) as c:
        r = await c.call_tool("deep_search", {"concepts": [], "subreddits": ["buildapc"]}, raise_on_error=False)
        assert r.is_error
        r = await c.call_tool("deep_search", {"concepts": CONCEPTS, "subreddits": []}, raise_on_error=False)
        assert r.is_error and "no Reddit-wide keyword search" in r.content[0].text
    assert fake_archive.requests == []
