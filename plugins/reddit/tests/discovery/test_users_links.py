"""get_user (T13) and resolve_share_link (T15), on responses saved on 2026-11-20."""

from __future__ import annotations

import pytest

from support import load_fixture

pytestmark = pytest.mark.anyio

USER = load_fixture("discovery/user-willswill.json")
USER_SUBS = load_fixture("discovery/user-subs-willswill.json")
SHORT = load_fixture("discovery/shortlink-running-2.json")
POST_16 = {"data": [{"id": "16puhb3", "subreddit": "running", "author": "AutoModerator",
                     "title": "Achievements for Saturday, September 23, 2023", "created_utc": 1695470471,
                     "num_comments": 120, "score": 30, "retrieved_on": 1695470480}]}
COMMENT_K1 = {"data": [{"id": "k1unwm1", "subreddit": "running", "author": "zacattack1996",
                        "link_id": "t3_16puhb3", "parent_id": "t3_16puhb3", "created_utc": 1695500000,
                        "body": "Ran my first 5k time trial.", "score": 5}]}


async def test_get_user(call, fake_archive):
    fake_archive.add_status()
    fake_archive.add("users/search", USER)
    fake_archive.add("users/interactions/subreddits", USER_SUBS)
    fake_archive.add("posts/search", {"data": []})
    fake_archive.add("comments/search", {"data": []})
    r = await call("get_user", {"username": "u/willswill"})
    assert fake_archive.paths()[:4] == ["users/search", "users/interactions/subreddits", "posts/search", "comments/search"]
    assert fake_archive.params(0) == {"author": "willswill"}
    # T14: the interactions and listings are bounded to the last year by default
    assert "after" in fake_archive.params(1) and "after" in fake_archive.params(2)
    u = r["user"]
    assert u["archived_comments"] == 1047 and u["archived_posts"] == 37
    assert u["archive_karma"]["total"] == 4094
    assert "stale archive karma" in u["archive_karma"]["label"]
    assert "not Reddit karma" in u["archive_karma"]["label"]
    assert u["account_age"] == "not available from the archive"
    assert "created" not in u and "account_created" not in u
    assert any("No account age" in n for n in r["notes"])
    assert r["active_subreddits"][0] == {"subreddit": "buildapc", "posts_and_comments": 743,
                                        "link": "https://www.reddit.com/r/buildapc/"}


async def test_get_user_survives_a_timeout_on_one_part(call, fake_archive):
    fake_archive.add_status()
    fake_archive.add("users/search", USER)
    fake_archive.add("users/interactions/subreddits", (422, {"data": None, "error": "Timeout"}))
    fake_archive.add("posts/search", {"data": []})
    fake_archive.add("comments/search", {"data": []})
    r = await call("get_user", {"username": "willswill", "time": "all"})
    assert "timed out" in r["active_subreddits"]
    assert "after" not in fake_archive.params(-2)


async def test_get_user_unknown(call, fake_archive):
    fake_archive.add_status().add("users/search", {"data": []})
    r = await call("get_user", {"username": "nobody_here_123"})
    assert r["found"] is False
    assert fake_archive.paths() == ["users/search", "STATUS"]


async def test_resolve_share_link(call, fake_archive):
    fake_archive.add_status()
    fake_archive.add("short_links", SHORT)
    fake_archive.add("posts/ids", POST_16)
    fake_archive.add("comments/ids", COMMENT_K1)
    r = await call("resolve_share_link", {"url": "https://www.reddit.com/r/running/s/0MH2aME2Z9?utm_source=share"})
    assert fake_archive.paths()[:3] == ["short_links", "posts/ids", "comments/ids"]
    assert fake_archive.params(0) == {"paths": "/r/running/s/0MH2aME2Z9"}  # case kept, query dropped
    link = r["links"][0]
    assert link["resolved"] is True
    assert link["url"] == "https://www.reddit.com/r/running/comments/16puhb3/achievements_for_saturday_september_23_2023/k1unwm1/"
    assert link["post_id"] == "16puhb3" and link["comment_id"] == "k1unwm1"
    assert link["post"]["title"] == "Achievements for Saturday, September 23, 2023"
    assert link["post"]["permalink"] == "https://www.reddit.com/r/running/comments/16puhb3/"
    assert link["comment"]["permalink"] == "https://www.reddit.com/r/running/comments/16puhb3/_/k1unwm1/"
    assert link["seen_in"] == "t1_k8so54m"


async def test_resolve_share_link_unknown_and_mixed(call, fake_archive):
    fake_archive.add_status()
    fake_archive.add("short_links", {"data": []})
    fake_archive.add("posts/ids", POST_16)
    r = await call("resolve_share_link", {"url": [
        "/r/buildapc/s/BU8o238QND",
        "https://www.reddit.com/r/running/comments/16puhb3/x/",
        "https://example.com/r/x/s/abc",
    ]})
    first, second, third = r["links"]
    assert first["resolved"] is False and "does not contact reddit.com" in first["note"]
    assert second["resolved"] is True and second["post"]["id"] == "16puhb3"
    assert third["resolved"] is False
    assert fake_archive.params(0) == {"paths": "/r/buildapc/s/BU8o238QND"}


async def test_resolve_share_link_only_talks_to_the_archive(call, fake_archive):
    fake_archive.add_status().add("short_links", load_fixture("discovery/shortlink-running.json"))
    fake_archive.add("posts/ids", {"data": []}).add("comments/ids", {"data": []})
    r = await call("resolve_share_link", {"url": "reddit.com/r/running/s/3TzXiyxaMD"})
    # FakeArchive asserts every request goes to the archive hosts; none went to reddit.com
    assert set(fake_archive.paths()) <= {"short_links", "posts/ids", "comments/ids", "STATUS"}
    assert r["links"][0]["post_id"] == "17snc7d"
    assert r["links"][0]["post_note"] == "the post is not in the archive"
