"""list_posts, search_posts and get_posts through the MCP server (T1-T8, O1, O2, criterion 7)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastmcp import Client

from posts.postdb import DAY, post
from reddit_mcp.arctic import Window, estimate_tokens
from reddit_mcp.server import build_server
from reddit_mcp.tools.posts import _walk
from support import PROBE_TIME

pytestmark = pytest.mark.anyio


async def call(client, tool, args):
    async with Client(build_server(client)) as c:
        return await c.call_tool(tool, args, raise_on_error=False)


def search_params(fake_archive):
    return [dict(r.url.params) for r in fake_archive.requests if r.url.path.endswith("posts/search")]


def ts(y, m=1, d=1):
    return int(datetime(y, m, d, tzinfo=UTC).timestamp())


def check_items(items):
    for p in items:
        assert p["permalink"] == f"https://www.reddit.com/r/{p['subreddit']}/comments/{p['id']}/"
        assert isinstance(p["created_utc"], int)
        assert p["score_status"] in ("initial", "snapshot")


# ------------------------------------------------------------------ list_posts


async def test_new_merges_subreddits_and_sends_epoch_window(client, db, fake_archive):
    db.add(post("a1", "buildapc", age_days=1), post("a2", "buildapc", age_days=5),
           post("b1", "intel", age_days=2), post("old", "intel", age_days=200))
    r = await call(client, "list_posts", {"subreddits": ["r/buildapc", "intel"], "time": "last 3 months"})
    d = r.data
    assert [p["id"] for p in d["items"]] == ["a1", "b1", "a2"]
    assert "not live Reddit" in d["source"]
    check_items(d["items"])
    sent = search_params(fake_archive)
    assert {p["subreddit"] for p in sent} == {"buildapc", "intel"}
    for p in sent:
        assert p["sort"] == "desc" and p["after"].isdigit() and p["before"].isdigit()
        assert "fields" in p
    # 'last 3 months' is calendar months back from now
    assert int(sent[0]["after"]) == ts(2026, 8, 20) + 22 * 3600 + 32 * 60


async def test_old_is_native_ascending(client, db, fake_archive):
    db.add(post("a1", age_days=1), post("a2", age_days=5))
    r = await call(client, "list_posts", {"subreddits": ["buildapc"], "sort": "old"})
    assert [p["id"] for p in r.data["items"]] == ["a2", "a1"]
    assert search_params(fake_archive)[0]["sort"] == "asc"


async def test_paging_dedupes_shared_timestamps(client, db, fake_archive):
    posts = [post(f"p{i:03d}", age_days=3 + i / 1000) for i in range(150)]
    same = posts[90]["created_utc"]
    for p in posts[90:130]:  # 40 posts in one second, across the page boundary
        p["created_utc"] = same
    db.add(*posts)
    w = await _walk(client, {"subreddit": "buildapc"}, Window(None, None, ""), order="desc",
                    fields=("id", "created_utc"), max_pages=5)
    ids = [p["id"] for p in w.items]
    assert len(ids) == len(set(ids)) == 150 and w.exhausted
    # page 2 starts at the shared second again (before = same + 1) and drops the repeats
    assert [p.get("before") for p in search_params(fake_archive)] == [None, str(same + 1)]


@pytest.mark.parametrize("sort", ["hot", "rising", "best", "relevance"])
async def test_live_rankings_are_refused(client, db, fake_archive, sort):
    r = await call(client, "list_posts", {"subreddits": ["buildapc"], "sort": sort})
    assert r.is_error and "not available from an archive" in r.content[0].text
    assert fake_archive.requests == []


async def test_r_all_is_refused(client, db, fake_archive):
    r = await call(client, "list_posts", {"subreddits": ["all"]})
    assert r.is_error and "r/all" in r.content[0].text


@pytest.mark.parametrize("time", ["hour", "day"])
async def test_top_of_today_is_refused(client, db, fake_archive, time):
    r = await call(client, "list_posts", {"subreddits": ["buildapc"], "sort": "top", "time": time})
    assert r.is_error
    text = r.content[0].text
    assert text.startswith("input error") or "scores not final" in text
    assert "36 hours" in text and "1 or 0" in text
    assert fake_archive.requests == []


async def test_top_ranks_on_client_and_leaves_out_unfinal(client, db, fake_archive):
    db.add(post("young", age_days=0.5, score=1), post("big", age_days=10, score=900),
           post("mid", age_days=12, score=40), post("small", age_days=20, score=2))
    r = await call(client, "list_posts", {"subreddits": ["buildapc"], "sort": "top", "time": "month", "limit": 2})
    d = r.data
    assert [p["id"] for p in d["items"]] == ["big", "mid"]
    scan = d["scan"]
    assert scan["complete"] is True and scan["posts_scanned"] == 4 and scan["left_out_unfinal"] == 1
    assert scan["window"] == d["window"]
    assert any("younger than about 36 h" in n for n in d["notes"])
    # the scan asks for no selftext; the winners' text comes from one posts/ids call
    assert "selftext" not in search_params(fake_archive)[0]["fields"]
    assert fake_archive.paths().count("posts/ids") == 1
    check_items(d["items"])


async def test_comments_sort_samples_a_big_window_within_the_budget(client, db, fake_archive):
    # 3,000 posts in 30 days: far more than 5 pages
    db.add(*[post(f"q{i}", age_days=0.01 + i * 30 / 3000, num_comments=i % 97) for i in range(3000)])
    r = await call(client, "list_posts", {"subreddits": ["buildapc"], "sort": "comments", "time": "month",
                                          "max_pages": 5, "limit": 5, "text_chars": 0})
    d = r.data
    scan = d["scan"]
    assert scan["pages"] == 5 and scan["posts_scanned"] == 500
    assert scan["truncated"] is True and 2000 < scan["estimated_posts_in_window"] < 4000
    assert "sample" in scan["per_subreddit"][0]["coverage"]
    sent = search_params(fake_archive)
    assert len(sent) == 5
    # the slices reach back across the whole window, not only the newest days
    assert min(int(p["after"]) for p in sent) < PROBE_TIME - 25 * DAY
    assert [p["num_comments"] for p in d["items"]] == sorted((p["num_comments"] for p in d["items"]), reverse=True)
    assert any("bounded" in n for n in d["notes"])


async def test_controversial_uses_full_objects(client, db, fake_archive):
    db.add(post("split", age_days=5, score=10, upvote_ratio=0.52), post("loved", age_days=6, score=500, upvote_ratio=0.98))
    r = await call(client, "list_posts", {"subreddits": ["buildapc"], "sort": "controversial", "time": "month"})
    assert r.data["items"][0]["id"] == "split"
    assert "fields" not in search_params(fake_archive)[0]


async def test_unknown_subreddit_says_so(client, db, fake_archive):
    r = await call(client, "list_posts", {"subreddits": ["thisdoesnotexist12345"]})
    d = r.data
    assert d["items"] == []
    assert any("no posts at all" in n and "private, quarantined or banned" in n for n in d["notes"])


async def test_empty_window_names_the_newest_post(client, db, fake_archive):
    db.add(post("x", age_days=400))
    r = await call(client, "list_posts", {"subreddits": ["buildapc"], "time": "week"})
    assert any("no posts in" in n and "newest archived post" in n for n in r.data["notes"])


async def test_result_stays_under_the_token_budget(client, db, fake_archive):
    db.add(*[post(f"t{i}", age_days=1 + i / 100, selftext="word " * 600) for i in range(100)])
    r = await call(client, "list_posts", {"subreddits": ["buildapc"], "limit": 100, "text_chars": 1500})
    assert estimate_tokens(r.data) <= 8000
    assert r.data["truncated"] is True


# ------------------------------------------------------------------ search_posts


async def test_global_search_is_refused_before_any_request(client, db, fake_archive):
    r = await call(client, "search_posts", {"query": "Framework laptop hinge"})
    assert r.is_error and "no Reddit-wide keyword search" in r.content[0].text
    assert fake_archive.requests == []


async def test_search_sends_one_keyword_and_filters_locally(client, db, fake_archive):
    db.add(post("hit", title="9900K power limit for undervolt", age_days=30),
           post("laptop", title="9900K power limit on a laptop, undervolt", age_days=31),
           post("noor", title="9900K power limit temps", age_days=32))
    r = await call(client, "search_posts", {"subreddits": ["buildapc"],
                                            "query": '9900k "power limit" undervolt OR underclock -laptop'})
    d = r.data
    assert [p["id"] for p in d["items"]] == ["hit"]
    sent = search_params(fake_archive)[0]
    assert sent["query"] == "9900k"
    assert not {"title", "selftext"} & set(sent)
    assert d["method"][0]["method"].startswith("archive keyword search")
    assert any("applied locally" in n for n in d["notes"])


async def test_search_422_falls_back_to_a_labelled_local_scan(client, db, fake_archive):
    db.add(post("hit", "MechanicalKeyboards", title="Keyboard chatter on my board", age_days=30), post("other", "MechanicalKeyboards", title="new keycaps", age_days=31))
    db.fail = lambda p: (422, {"error": "Timeout. Maybe slow down a bit"}) if "title" in p else None
    r = await call(client, "search_posts", {"subreddits": ["MechanicalKeyboards"], "query": "title:chatter"})
    d = r.data
    assert [p["id"] for p in d["items"]] == ["hit"]
    m = d["method"][0]
    assert m["method"].startswith("local scan (T6)") and "HTTP 422" in m["method"]
    assert m["posts_scanned"] == 2
    sent = search_params(fake_archive)
    assert "title" in sent[0] and "title" not in sent[-1]


async def test_search_fallback_samples_a_long_window_evenly(client, db, fake_archive):
    # 2,000 posts over the year, 3 of them match: spread across the year
    db.add(*[post(f"y{i}", "MechanicalKeyboards", age_days=5 + i * 0.18, flair="Help",
                  title="key chatter again" if i in (10, 900, 1900) else "keycap question") for i in range(2000)])
    db.fail = lambda p: (422, {"error": "Timeout. Maybe slow down a bit"}) if "query" in p else None
    r = await call(client, "search_posts", {"subreddits": ["MechanicalKeyboards"], "query": "flair:Help chatter",
                                            "time": "year", "max_pages": 6})
    m = r.data["method"][0]
    assert m["partial"] is True and m["pages"] == 6 and "sample" in m["coverage"]
    windows = [p for p in search_params(fake_archive) if "query" not in p]
    assert all(p["link_flair_text"] == "Help" for p in windows)
    assert min(int(p["after"]) for p in windows) < PROBE_TIME - 300 * DAY


async def test_search_flair_and_year_window(client, db, fake_archive):
    in_2025 = PROBE_TIME - 330 * DAY  # 2025-12-25
    db.add(post("h", "MechanicalKeyboards", title="key chatter help", flair="Help"),
           post("old", "MechanicalKeyboards", title="key chatter", flair="Help", age_days=800))
    db.posts[0]["created_utc"] = int(in_2025)
    r = await call(client, "search_posts", {"subreddits": ["MechanicalKeyboards"], "query": "flair:Help chatter",
                                            "after": "2025", "before": "2025"})
    d = r.data
    assert [p["id"] for p in d["items"]] == ["h"]
    sent = search_params(fake_archive)[0]
    assert sent["link_flair_text"] == "Help"
    assert sent["after"] == str(ts(2025)) and sent["before"] == str(ts(2026))
    assert d["archive_filters"] == {"link_flair_text": "Help"}


async def test_search_by_author_needs_no_subreddit(client, db, fake_archive):
    db.add(post("w", title="Intel 9900K Underclocking", author="willswill"))
    r = await call(client, "search_posts", {"query": "author:willswill 9900k"})
    assert [p["id"] for p in r.data["items"]] == ["w"]
    assert search_params(fake_archive)[0]["author"] == "willswill"


async def test_search_top_ranks_matches(client, db, fake_archive):
    db.add(post("a", "framework", title="hinge creak", score=3, age_days=10), post("b", "framework", title="hinge fix", score=80, age_days=20))
    r = await call(client, "search_posts", {"subreddits": ["framework"], "query": "hinge", "sort": "top", "time": "year"})
    assert [p["id"] for p in r.data["items"]] == ["b", "a"]


async def test_search_relevance_refused(client, db, fake_archive):
    r = await call(client, "search_posts", {"subreddits": ["framework"], "query": "hinge", "sort": "relevance"})
    assert r.is_error and "relevance" in r.content[0].text


# ------------------------------------------------------------------ get_posts


async def test_get_posts_by_url_and_id(client, db, fake_archive):
    db.add(post("wi7uhk", title="Intel 9900K Underclocking/Power Limit Experiments", selftext="x " * 2000,
                upvote_ratio=0.9, _meta={"retrieved_2nd_on": 1}))
    r = await call(client, "get_posts", {"ids_or_urls": [
        "https://www.reddit.com/r/buildapc/comments/wi7uhk/intel_9900k_underclockingpower_limit_experiments/",
        "t3_wi7uhk", "zzzzzz", "https://www.reddit.com/r/buildapc/s/AbCdEf"]})
    d = r.data
    assert [p["id"] for p in d["items"]] == ["wi7uhk"]
    p = d["items"][0]
    assert p["score_status"] == "snapshot" and p["truncated"] is True and len(p["selftext"]) <= 1502
    assert d["not_found"] == ["zzzzzz"]
    assert any("share link" in n for n in d["notes"])
    ids_req = [r for r in fake_archive.requests if r.url.path.endswith("posts/ids")]
    assert len(ids_req) == 1 and "fields" not in dict(ids_req[0].url.params)  # full objects


async def test_get_posts_splits_above_500(client, db, fake_archive):
    ids = [f"id{i:04d}" for i in range(1200)]
    r = await call(client, "get_posts", {"ids_or_urls": ids, "text_chars": 0})
    assert fake_archive.paths().count("posts/ids") == 3
    assert len(r.data["not_found"]) == 1200
