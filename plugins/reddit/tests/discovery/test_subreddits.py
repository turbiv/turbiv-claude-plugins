"""find_subreddits, subreddit_info, read_wiki (T12), on responses saved on 2026-11-20."""

from __future__ import annotations

import pytest

from support import load_fixture

pytestmark = pytest.mark.anyio

PREFIX = load_fixture("discovery/prefix-espresso.json")
COFFEE = load_fixture("discovery/subreddit-coffee.json")
TS_POSTS = load_fixture("discovery/ts-espresso-posts-day.json")
TS_COMMENTS = load_fixture("discovery/ts-espresso-comments-day.json")
RULES = load_fixture("discovery/rules-espresso.json")
WIKI_LIST = load_fixture("discovery/wikilist-espresso.json")
WIKI_FAQ = load_fixture("discovery/wiki-espresso-faq.json")


async def test_find_subreddits_by_prefix(call, fake_archive):
    fake_archive.add_status().add("subreddits/search", PREFIX).add("time_series", TS_POSTS)
    r = await call("find_subreddits", {"name_or_prefix": "r/espresso", "nsfw": False, "limit": 5})
    assert fake_archive.paths() == ["subreddits/search", "time_series", "time_series", "time_series", "STATUS"]
    assert [fake_archive.params(i)["key"] for i in (1, 2, 3)] == [
        "r/espresso/posts/count", "r/espressocirclejerk/posts/count", "r/espressomachines/posts/count"]
    sent = fake_archive.params(0)
    assert sent["subreddit_prefix"] == "espresso"
    assert sent["over18"] == "false"
    assert sent["sort_type"] == "subscribers"
    subs = r["subreddits"]
    assert [s["name"] for s in subs][:3] == ["r/espresso", "r/espressocirclejerk", "r/espressomachines"]
    top = subs[0]
    assert top["subscribers"] == 650051
    assert top["link"] == "https://www.reddit.com/r/espresso/"
    assert top["archived_posts"] == 263175
    assert top["subscribers_as_of"] == "2025-02-14"
    values = [p["value"] for p in TS_POSTS["data"]][-28:]
    assert top["posts_per_day"] == round(sum(values) / 28, 1)
    assert "posts_per_day" not in subs[3]
    assert len(subs) == 5
    assert "not live Reddit" in r["source"]
    assert any("cannot search subreddits by topic" in n for n in r["notes"])


async def test_find_subreddits_keyword_is_a_local_filter(call, fake_archive):
    fake_archive.add_status().add("subreddits/search", PREFIX)
    r = await call("find_subreddits", {"name_or_prefix": "espresso", "keyword": "machine", "activity_for_top": 0})
    assert fake_archive.params(0)["limit"] == "100"
    names = [s["name"] for s in r["subreddits"]]
    assert "r/espressomachines" in names
    assert "r/espresso_decaf" not in names
    assert any("local filter" in n for n in r["notes"])


async def test_find_subreddits_no_match_says_so(call, fake_archive):
    fake_archive.add_status().add("subreddits/search", {"data": []})
    r = await call("find_subreddits", {"name_or_prefix": "thisdoesnotexist12345"})
    assert r["subreddits"] == []
    assert any("No archived subreddit name starts with" in n for n in r["notes"])


async def test_find_subreddits_rejects_bad_names(call, fake_archive):
    text = await call("find_subreddits", {"name_or_prefix": "home espresso"}, error=True)
    assert text.startswith("input error:")
    assert fake_archive.requests == []


async def test_subreddit_info_full(call, fake_archive):
    fake_archive.add_status()
    fake_archive.add("subreddits/search", COFFEE)
    fake_archive.add("time_series", TS_POSTS, match=lambda q: q.url.params["key"].endswith("/posts/count"))
    fake_archive.add("time_series", TS_COMMENTS, match=lambda q: q.url.params["key"].endswith("/comments/count"))
    fake_archive.add("subreddits/rules", RULES)
    fake_archive.add("subreddits/wikis/list", WIKI_LIST)
    r = await call("subreddit_info", {"subreddit": "coffee"})
    paths = fake_archive.paths()
    assert paths[:5] == ["subreddits/search", "time_series", "time_series", "subreddits/rules", "subreddits/wikis/list"]
    assert fake_archive.params(1)["key"] == "r/Coffee/posts/count"  # canonical case from the search
    assert fake_archive.params(1)["precision"] == "day"
    assert r["found"] is True
    sub = r["subreddit"]
    assert sub["name"] == "r/Coffee" and sub["subscribers"] == 2316917
    assert "sidebar" in sub
    values = [p["value"] for p in TS_POSTS["data"]][-28:]
    assert r["activity"]["posts"]["posts_per_day"] == round(sum(values) / 28, 1)
    assert r["activity"]["posts"]["through"] == "2026-11-19"
    assert r["activity"]["comments"]["comments_per_day"] > 500
    assert r["rules"][0]["rule"] == "Be civil"
    assert "faq" in r["wiki_pages"] and "guides/brewing-basics" in r["wiki_pages"]


async def test_subreddit_info_not_in_archive(call, fake_archive):
    fake_archive.add_status().add("subreddits/search", {"data": []})
    r = await call("subreddit_info", {"subreddit": "thisdoesnotexist12345"})
    assert r["found"] is False
    assert "private, quarantined" in r["notes"][0]
    assert fake_archive.paths() == ["subreddits/search", "STATUS"]


async def test_subreddit_info_falls_back_when_time_series_fails(call, fake_archive):
    fake_archive.add_status()
    fake_archive.add("subreddits/search", COFFEE)
    fake_archive.add("time_series", (422, {"data": None, "error": "Timeout. Maybe slow down a bit"}))
    now = 1795213920
    posts = [{"id": f"p{i}", "created_utc": now - i * 1800} for i in range(100)]
    fake_archive.add("posts/search", {"data": posts})
    fake_archive.add("subreddits/rules", RULES)
    fake_archive.add("subreddits/wikis/list", WIKI_LIST)
    r = await call("subreddit_info", {"subreddit": "Coffee"})
    posts_activity = r["activity"]["posts"]
    assert "estimate from the newest 100" in posts_activity["method"]
    assert posts_activity["posts_per_day"] == pytest.approx(48.5, abs=1)
    assert "comments" not in r["activity"]


async def test_read_wiki_page(call, fake_archive):
    fake_archive.add_status().add("subreddits/wikis", WIKI_FAQ)
    r = await call("read_wiki", {"subreddit": "espresso", "page": "/r/espresso/wiki/faq", "max_chars": 1000})
    assert fake_archive.params(0)["paths"] == "/r/espresso/wiki/faq"
    assert r["found"] is True
    assert r["content"].startswith("# Brewing FAQ")
    assert "&gt;" not in r["content"]
    assert r["truncated"] is True and r["next_offset"] == 1000
    assert r["url"] == "https://www.reddit.com/r/espresso/wiki/faq/"
    assert r["revision_date"].startswith("2025-01-05")
    r2 = await call("read_wiki", {"subreddit": "espresso", "page": "faq", "offset": 1000, "max_chars": 20000})
    assert "truncated" not in r2 and "next_offset" not in r2
    assert r2["offset"] == 1000


async def test_read_wiki_missing_page_lists_pages(call, fake_archive):
    fake_archive.add_status().add("subreddits/wikis", {"data": []}).add("subreddits/wikis/list", WIKI_LIST)
    r = await call("read_wiki", {"subreddit": "Espresso", "page": "nope"})
    assert r["found"] is False
    assert fake_archive.paths()[:3] == ["subreddits/wikis", "subreddits/wikis", "subreddits/wikis/list"]
    assert {fake_archive.params(0)["paths"], fake_archive.params(1)["paths"]} == {
        "/r/espresso/wiki/nope", "/r/Espresso/wiki/nope"}
    assert "faq" in r["notes"][1]


async def test_read_wiki_rejects_path_tricks(call, fake_archive):
    text = await call("read_wiki", {"subreddit": "espresso", "page": "../../x"}, error=True)
    assert text.startswith("input error:")


async def test_find_subreddits_activity_survives_a_busy_archive(call, fake_archive):
    fake_archive.add_status().add("subreddits/search", PREFIX)
    fake_archive.add("time_series", (422, {"data": None, "error": "Timeout. Maybe slow down a bit"}))
    r = await call("find_subreddits", {"name_or_prefix": "espresso", "activity_for_top": 1})
    assert r["subreddits"][0]["name"] == "r/espresso" and "posts_per_day" not in r["subreddits"][0]
