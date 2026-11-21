"""trending_posts, count_mentions and the bounded window scan they share (T4, T14)."""

from __future__ import annotations

import random

import pytest

from reddit_mcp.tools.discovery import Term, scan_window
from support import PROBE_TIME, load_fixture

pytestmark = pytest.mark.anyio

NOW = int(PROBE_TIME)
DAY = 86400


def comments(n: int, *, sub: str, start: int, end: int, threads: dict[str, float], seed: int = 1,
             bodies: list[str] | None = None) -> list[dict]:
    """`n` comments spread evenly over [start, end), on threads picked by weight."""
    rnd = random.Random(seed)
    names, weights = list(threads), list(threads.values())
    out = []
    for i in range(n):
        ts = end - 1 - int(i * (end - start) / n)
        link = rnd.choices(names, weights)[0]
        out.append({
            "id": f"c{sub[:3]}{i}", "subreddit": sub, "author": f"user{rnd.randrange(400)}",
            "created_utc": ts, "link_id": f"t3_{link}",
            "body": bodies[i % len(bodies)] if bodies else "hello",
        })
    return out


def posts_for(ids: list[str], sub: str) -> list[dict]:
    return [{"id": i, "subreddit": sub, "title": f"Thread {i}", "author": "op", "created_utc": NOW - DAY,
             "num_comments": 1, "score": 1, "retrieved_on": NOW - DAY + 5} for i in ids]


def archive_requests(fake_archive) -> list[str]:
    return [p for p in fake_archive.paths() if p != "STATUS"]


# ---------------------------------------------------------------- term matching


def test_term_matching_variants():
    t = Term.parse("Wooting 60HE")
    for text in ["I love my wooting 60he", "Wooting-60 HE!", "the wooting60he rocks", "two Wooting 60HEs"]:
        assert t.find(text), text
    assert not t.find("wooting 60hex")
    k = Term.parse("Keychron")
    assert k.find("Keychron's switches") and k.find("keychrons are fine") and k.find("(KEYCHRON)")
    assert not k.find("keychronic") and not k.find("mykeychron")
    alias = Term.parse("HHKB|Happy Hacking")
    assert alias.label == "HHKB"
    assert alias.find("the happy hacking keyboard") and alias.find("HHKB type-s")


# ---------------------------------------------------------------- scan_window


async def test_scan_complete_small_window(client, fake_archive, sim):
    items = comments(60, sub="tiny", start=NOW - DAY, end=NOW, threads={"a": 1})
    fake_archive.add("comments/search", sim.listing(items))
    s = await scan_window(client, "comments/search", {"subreddit": "tiny"}, ("id", "created_utc"),
                          NOW - DAY, NOW, 10, label="r/tiny comments")
    assert s.mode == "complete" and s.complete and s.requests == 1 and s.scanned == 60
    assert s.describe()["share_scanned"] == "100%"


async def test_scan_pages_back_when_it_fits(client, fake_archive, sim):
    items = comments(350, sub="mid", start=NOW - DAY, end=NOW, threads={"a": 1})
    fake_archive.add("comments/search", sim.listing(items))
    s = await scan_window(client, "comments/search", {"subreddit": "mid"}, ("id", "created_utc"),
                          NOW - DAY, NOW, 10, label="r/mid comments")
    assert s.mode == "complete" and s.scanned == 350 and s.requests == 4
    befores = [int(fake_archive.params(i)["before"]) for i in range(4)]
    assert befores == sorted(befores, reverse=True)


async def test_scan_samples_when_too_big(client, fake_archive, sim):
    items = comments(5000, sub="big", start=NOW - 10 * DAY, end=NOW, threads={"a": 1})
    fake_archive.add("comments/search", sim.listing(items))
    s = await scan_window(client, "comments/search", {"subreddit": "big"}, ("id", "created_utc"),
                          NOW - 10 * DAY, NOW, 6, label="r/big comments")
    assert s.mode == "sampled" and not s.complete
    assert s.requests == 6 and s.scanned == 600
    assert s.est_total == pytest.approx(5000, rel=0.1)
    # the slices spread over the whole window, oldest slice starts at the window start
    afters = sorted(int(fake_archive.params(i)["after"]) for i in range(6))
    assert afters[0] == NOW - 10 * DAY
    assert s.scale == pytest.approx(5000 / 600, rel=0.1)


async def test_scan_records_a_failed_slice(client, fake_archive, sim):
    items = comments(5000, sub="big", start=NOW - 10 * DAY, end=NOW, threads={"a": 1})
    fake_archive.add("comments/search", sim.listing(items))
    oldest_slice = lambda q: q.url.params.get("after") == str(NOW - 10 * DAY) and int(q.url.params["before"]) < NOW - DAY  # noqa: E731
    fake_archive.add("comments/search", (422, {"data": None, "error": "Timeout. Maybe slow down a bit"}), match=oldest_slice)
    s = await scan_window(client, "comments/search", {"subreddit": "big"}, ("id", "created_utc"),
                          NOW - 10 * DAY, NOW, 4, label="r/big comments")
    assert len(s.failed) == 1 and "busy (fast 422)" in s.failed[0]
    assert s.est_total == pytest.approx(5000, rel=0.15)  # the failed slice is filled in by density
    assert "failed_slices" in s.describe()


# ---------------------------------------------------------------- trending_posts


async def test_trending_complete(call, fake_archive, sim):
    items = comments(100, sub="MechanicalKeyboards", start=NOW - DAY, end=NOW, threads={"aaa": 6, "bbb": 3, "ccc": 1})
    items += [{"id": f"bot{i}", "subreddit": "MechanicalKeyboards", "author": "AutoModerator",
               "created_utc": NOW - 100 - i, "link_id": "t3_ddd"} for i in range(80)]
    fake_archive.add_status()
    fake_archive.add("comments/search", sim.listing(items))
    fake_archive.add("posts/ids", sim.ids(posts_for(["aaa", "bbb", "ccc", "ddd"], "MechanicalKeyboards")))
    r = await call("trending_posts", {"subreddits": ["r/MechanicalKeyboards"], "hours": 24})
    assert [p["id"] for p in r["posts"]] == ["aaa", "bbb", "ccc"]  # AutoModerator's thread is not trending
    top = r["posts"][0]
    assert top["new_comments_seen"] > 40 and "new_comments_estimated" not in top
    assert top["permalink"] == "https://www.reddit.com/r/MechanicalKeyboards/comments/aaa/"
    assert top["score_status"] in ("initial", "snapshot") and "created_utc" in top
    assert r["method"] == "recent comment activity, not Reddit's hot"
    assert any("not Reddit's hot" in n for n in r["notes"])
    assert r["coverage"][0]["mode"] == "complete"
    sent = fake_archive.params(0)
    assert sent["sort"] == "desc" and int(sent["after"]) == NOW - DAY
    assert archive_requests(fake_archive) == ["comments/search", "comments/search", "posts/ids"]
    assert r["requests_used"] == 4  # 2 pages, the post lookup, the status check


async def test_trending_samples_big_subreddits_and_compares_by_estimate(call, fake_archive, sim):
    big = comments(6000, sub="AskReddit", start=NOW - DAY, end=NOW, threads={"big1": 5, "big2": 3, "big3": 2}, seed=2)
    small = comments(90, sub="HHKB", start=NOW - DAY, end=NOW, threads={"small1": 1}, seed=3)
    fake_archive.add_status()
    fake_archive.add("comments/search", sim.listing(big + small))
    fake_archive.add("posts/ids", sim.ids(posts_for(["big1", "big2", "big3"], "AskReddit") + posts_for(["small1"], "HHKB")))
    r = await call("trending_posts", {"subreddits": ["AskReddit", "HHKB"], "max_requests": 9})
    ids = [p["id"] for p in r["posts"]]
    assert ids[:3] == ["big1", "big2", "big3"] and ids[3] == "small1"
    big1 = r["posts"][0]
    assert big1["new_comments_estimated"] == pytest.approx(3000, rel=0.2)
    assert big1["new_comments_seen"] < big1["new_comments_estimated"]
    modes = {c["stream"]: c["mode"] for c in r["coverage"]}
    assert modes == {"r/AskReddit comments": "sampled", "r/HHKB comments": "complete"}
    assert len(archive_requests(fake_archive)) <= 9
    assert r["requests_used"] == len(fake_archive.requests)
    assert any("sampled" in n for n in r["notes"])
    assert r["counts"].startswith("SAMPLE")  # a sampled count is called a sample (Session 5 review)


async def test_trending_without_subreddits_is_refused(call, fake_archive):
    text = await call("trending_posts", {"subreddits": []}, error=True)
    assert "not available from an archive: r/all" in text
    assert fake_archive.requests == []


async def test_trending_on_saved_comments(call, fake_archive, fake_time, sim):
    saved = load_fixture("discovery/comments-mk-24h.json")["data"]
    fake_time.wall_start = max(c["created_utc"] for c in saved) + 60
    fake_archive.add_status()
    fake_archive.add("comments/search", sim.listing(saved))
    fake_archive.add("posts/ids", {"data": []})
    r = await call("trending_posts", {"subreddits": ["MechanicalKeyboards"], "hours": 24, "limit": 3})
    assert r["posts"][0]["id"] == "1y0utr3" and r["posts"][0]["new_comments_seen"] == 16
    assert r["posts"][0]["note"] == "post not in the archive"


# ---------------------------------------------------------------- count_mentions


KEYBOARD_BODIES = [
    "Get a Keychron Q1, it is great",
    "Wooting 60HE for gaming, nothing else",
    "keychron again, and maybe an HHKB",
    "I went with a Happy Hacking board",
    "no brand here",
]


async def test_count_mentions_complete(call, fake_archive, sim):
    start = NOW - 30 * DAY
    cs = comments(150, sub="MechanicalKeyboards", start=start, end=NOW, threads={"t1": 2, "t2": 1, "t3": 1},
                  bodies=KEYBOARD_BODIES)
    ps = [{"id": "p1", "subreddit": "MechanicalKeyboards", "author": "a", "created_utc": NOW - 2 * DAY,
           "title": "Keychron or Wooting?", "selftext": "Help me pick", "num_comments": 40},
          {"id": "p2", "subreddit": "MechanicalKeyboards", "author": "AutoModerator", "created_utc": NOW - DAY,
           "title": "Weekly Keychron thread", "selftext": "", "num_comments": 3}]
    fake_archive.add_status()
    fake_archive.add("posts/search", sim.listing(ps))
    fake_archive.add("comments/search", sim.listing(cs))
    fake_archive.add("posts/ids", sim.ids(posts_for(["t1", "t2", "t3"], "MechanicalKeyboards")))
    r = await call("count_mentions", {
        "subreddits": ["MechanicalKeyboards"], "terms": ["Keychron", "Wooting", "HHKB|Happy Hacking", "Ducky"],
        "time": "month",
    })
    rows = {t["term"]: t for t in r["terms"]}
    assert rows["Keychron"]["mentions"] == 60 + 1  # 2 of 5 bodies, plus post p1 (AutoModerator's p2 ignored)
    assert rows["Keychron"]["in_posts"] == 1 and rows["Keychron"]["in_comments"] == 60
    assert rows["Wooting"]["mentions"] == 31
    assert rows["HHKB"]["mentions"] == 60
    assert rows["Ducky"]["mentions"] == 0 and rows["Ducky"]["examples"] == []
    assert rows["Keychron"]["threads"] == 4  # t1, t2, t3 and p1
    assert [t["term"] for t in r["terms"]][-1] == "Ducky"
    ex = rows["Keychron"]["examples"][0]
    assert ex["thread"] == "https://www.reddit.com/r/MechanicalKeyboards/comments/t1/"
    assert ex["title"] == "Thread t1"  # fetched by ID for comment-only threads
    assert "/comments/t1/_/" in ex["example"] and "Keychron" in ex["snippet"]
    assert r["scan_truncated"] is False
    assert "estimated_mentions_in_window" not in rows["Keychron"]
    assert all(c["mode"] == "complete" for c in r["coverage"])
    assert r["window"].endswith("UTC") and r["window_epoch"]["before"] == NOW
    assert r["requests_used"] == len(fake_archive.requests)


async def test_count_mentions_defaults_to_three_months(call, fake_archive, sim):
    fake_archive.add_status().add("posts/search", {"data": []}).add("comments/search", {"data": []})
    r = await call("count_mentions", {"subreddits": ["a", "b"], "terms": ["x"]})
    after = r["window_epoch"]["after"]
    assert 89 * DAY <= NOW - after <= 92 * DAY
    # The tool reads the wall clock here, so derive the expected date from `after`, not a fixed string.
    from datetime import datetime, timezone

    assert datetime.fromtimestamp(after, timezone.utc).strftime("%Y-%m-%d") in r["window"]
    assert sorted(set(archive_requests(fake_archive))) == ["comments/search", "posts/search"]
    assert {fake_archive.params(i)["subreddit"] for i in range(4) if fake_archive.paths()[i] != "STATUS"} == {"a", "b"}


async def test_count_mentions_in_posts_only(call, fake_archive, sim):
    fake_archive.add_status().add("posts/search", {"data": []})
    r = await call("count_mentions", {"subreddits": ["a"], "terms": ["x"], "in": "posts", "time": "week"})
    assert archive_requests(fake_archive) == ["posts/search"]
    assert r["searched"] == "posts"


async def test_count_mentions_all_time_needs_opt_in(call, fake_archive):
    text = await call("count_mentions", {"subreddits": ["a"], "terms": ["x"], "time": "all"}, error=True)
    assert "all_time=true" in text
    assert fake_archive.requests == []


async def test_count_mentions_needs_a_subreddit(call, fake_archive):
    text = await call("count_mentions", {"subreddits": [], "terms": ["x"]}, error=True)
    assert text.startswith("input error:") and "subreddit" in text


async def test_count_mentions_sampled_is_bounded_and_labelled(call, fake_archive, sim):
    start = NOW - 90 * DAY
    a = comments(20000, sub="MechanicalKeyboards", start=start, end=NOW, threads={f"m{i}": 1 for i in range(300)},
                 bodies=KEYBOARD_BODIES, seed=5)
    b = comments(9000, sub="keyboards", start=start, end=NOW, threads={f"k{i}": 1 for i in range(200)},
                 bodies=KEYBOARD_BODIES[::-1], seed=6)
    ps = [{"id": f"p{i}", "subreddit": "MechanicalKeyboards", "author": "x", "created_utc": NOW - i * 3000,
           "title": "Which Keychron?" if i % 4 == 0 else "Help", "selftext": "", "num_comments": i} for i in range(2500)]
    fake_archive.add_status()
    fake_archive.add("posts/search", sim.listing(ps))
    fake_archive.add("comments/search", sim.listing(a + b))
    fake_archive.add("posts/ids", sim.ids([]))
    r = await call("count_mentions", {
        "subreddits": ["MechanicalKeyboards", "keyboards"], "terms": ["Keychron", "Wooting", "HHKB|Happy Hacking"],
        "time": "3 months", "max_requests": 20,
    })
    sent = archive_requests(fake_archive)
    assert len(sent) <= 20 and r["requests_used"] == len(fake_archive.requests)
    assert r["scan_truncated"] is True
    assert any("TRUNCATED SCAN" in n for n in r["notes"])
    assert r["counts"].startswith("SAMPLE")
    assert all("created_utc" in ex for t in r["terms"] for ex in t["examples"] if ex.get("title"))
    modes = {c["stream"]: c["mode"] for c in r["coverage"]}
    assert modes["r/MechanicalKeyboards comments"] == "sampled"
    for c in r["coverage"]:
        assert {"items_scanned", "estimated_items_in_window", "share_scanned", "requests"} <= set(c)
    rows = {t["term"]: t for t in r["terms"]}
    assert rows["Keychron"]["estimated_mentions_in_window"] > rows["Keychron"]["mentions"]
    # 2 of 5 bodies mention Keychron in both subreddits: about 40% of 29,000 comments, plus 625 posts
    assert rows["Keychron"]["estimated_mentions_in_window"] == pytest.approx(0.4 * 29000 + 625, rel=0.2)
    assert fake_archive.max_in_flight == 1  # R1: one request at a time
    assert r["items_scanned"]["comments"] <= 100 * len([p for p in sent if p == "comments/search"])


async def test_count_mentions_stays_under_the_token_budget(call, fake_archive, sim):
    long_body = " ".join(f"brand{i}" for i in range(25)) + " " + "lorem ipsum " * 60
    cs = comments(300, sub="s", start=NOW - 30 * DAY, end=NOW, threads={f"t{i}": 1 for i in range(50)}, bodies=[long_body])
    fake_archive.add_status().add("posts/search", {"data": []}).add("comments/search", sim.listing(cs))
    fake_archive.add("posts/ids", sim.ids(posts_for([f"t{i}" for i in range(50)], "s")))
    r = await call("count_mentions", {"subreddits": ["s"], "terms": [f"brand{i}" for i in range(25)], "time": "month"})
    assert sim.size(r) < 8000
    assert all(t["mentions"] == 300 for t in r["terms"]) or r.get("truncated")


async def test_count_mentions_on_saved_comments(call, fake_archive, fake_time, sim):
    saved = load_fixture("discovery/comments-mk-body-keychron.json")["data"]
    fake_time.wall_start = max(c["created_utc"] for c in saved) + 60
    fake_archive.add_status()
    fake_archive.add("comments/search", sim.listing(saved))
    fake_archive.add("posts/ids", {"data": []})
    r = await call("count_mentions", {"subreddits": ["MechanicalKeyboards"], "terms": ["Keychron", "Logitech"],
                                      "in": "comments", "time": "2 weeks"})
    rows = {t["term"]: t for t in r["terms"]}
    assert rows["Keychron"]["mentions"] >= 90  # the archive matched 'keychron' in every one
    assert rows["Keychron"]["threads"] > 10
    assert r["coverage"][0]["mode"] == "complete"


async def test_422_retries_count_against_the_budget(call, fake_archive, sim):
    start = NOW - 90 * DAY
    cs = comments(20000, sub="big", start=start, end=NOW, threads={"t": 1}, bodies=KEYBOARD_BODIES)
    fake_archive.add_status()
    fake_archive.add("comments/search", sim.listing(cs))
    busy = lambda q: int(q.url.params["before"]) < NOW - 30 * DAY  # noqa: E731  the older slices fail
    fake_archive.add("comments/search", (422, {"data": None, "error": "Timeout. Maybe slow down a bit"}), match=busy)
    fake_archive.add("posts/ids", sim.ids(posts_for(["t"], "big")))
    r = await call("count_mentions", {"subreddits": ["big"], "terms": ["Keychron"], "in": "comments",
                                      "time": "3 months", "max_requests": 12})
    sent = archive_requests(fake_archive)
    assert len(sent) <= 12
    cov = r["coverage"][0]
    assert cov["requests"] <= 11 and cov["failed_slices"]
    assert cov["estimated_items_in_window"] == pytest.approx(20000, rel=0.25)
    assert r["scan_truncated"] is True
