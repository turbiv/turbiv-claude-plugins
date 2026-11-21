"""Session 3: get_thread, expand_comments, get_comment_context, search_comments.

Saved responses (tests/fixtures/comments/, see docs/probes.md):
- tree-wi7uhk.json: the whole tree, 22 comments (Session 1, request 5).
- tree-wi7uhk-limit5.json: the same tree with limit=5, so with archive `more` stubs.
- tree-wi7uhk-parent-jqqr5hr.json: tree?parent_id=t1_jqqr5hr (the comment plus its subtree).
- post-wi7uhk-full.json: posts/ids?ids=wi7uhk, full object.
- search-*.json: comments/search answers from the Session 3 syntax probes.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest
from fastmcp import Client

from reddit_mcp.arctic import estimate_tokens
from reddit_mcp.server import build_server
from reddit_mcp.tools.comments import parse_query, parse_tree
from support import load_fixture

pytestmark = pytest.mark.anyio

TREE = load_fixture("comments/tree-wi7uhk.json")
TREE5 = load_fixture("comments/tree-wi7uhk-limit5.json")
POST = load_fixture("comments/post-wi7uhk-full.json")
OP = "willswill"


def _index(items: list[dict], out: dict[str, dict]) -> dict[str, dict]:
    for it in items:
        if it.get("kind") != "t1":
            continue
        out[it["data"]["id"]] = it
        replies = it["data"].get("replies")
        if isinstance(replies, dict):
            _index(replies["data"]["children"], out)
    return out


ITEMS = _index(TREE["data"], {})  # id -> {"kind": "t1", "data": {...}}
FIELDS = ("id", "subreddit", "author", "created_utc", "retrieved_on", "score", "body", "link_id", "parent_id")


def flat(cid: str) -> dict[str, Any]:
    """A comment as comments/ids or comments/search return it with fields=."""
    d = ITEMS[cid]["data"]
    return {k: d[k] for k in FIELDS if k in d}


def subtree_reply(request):
    """comments/tree?parent_id=t1_X: the comment X with its subtree, from the full tree."""
    parent = request.url.params.get("parent_id", "").removeprefix("t1_")
    item = ITEMS.get(parent)
    return {"data": [copy.deepcopy(item)] if item else []}


def ids_reply(request):
    ids = request.url.params.get("ids", "").split(",")
    return {"data": [flat(i) for i in ids if i in ITEMS]}


def has_parent(request) -> bool:
    return "parent_id" in request.url.params


def setup_thread(fake_archive, tree=TREE):
    fake_archive.add_status()
    fake_archive.add("posts/ids", POST)
    fake_archive.add("comments/tree", tree)
    fake_archive.add("comments/tree", subtree_reply, match=has_parent)
    fake_archive.add("comments/ids", ids_reply)


async def call(client, tool, args, error=False):
    async with Client(build_server(client)) as c:
        r = await c.call_tool(tool, args, raise_on_error=False)
    if error:
        assert r.is_error, r
        return r.content[0].text
    assert not r.is_error, r.content[0].text
    return r.structured_content


def comments_in(nodes: list[dict]) -> list[dict]:
    out = []
    for n in nodes:
        if n.get("kind") == "more":
            continue
        out.append(n)
        out.extend(comments_in(n.get("replies", [])))
    return out


def stubs_in(nodes: list[dict]) -> list[dict]:
    out = []
    for n in nodes:
        if n.get("kind") == "more":
            out.append(n)
        else:
            out.extend(stubs_in(n.get("replies", [])))
    return out


def assert_labelled(c: dict) -> None:
    """Global criterion 4 (O1, O2)."""
    assert c["permalink"].startswith("https://www.reddit.com/r/") and c["permalink"].endswith(f"/{c['id']}/")
    assert isinstance(c["created_utc"], int)
    assert c["score_status"] in ("initial", "snapshot")


# ------------------------------------------------------------------ tree parsing


def test_parse_tree_counts_hidden_comments_behind_stubs():
    full = parse_tree(TREE["data"])
    assert full.total() == 22 and len(full.children) == 9 and full.complete()
    part = parse_tree(TREE5["data"])
    assert part.total() == 22  # 5 loaded + stubs of 15 and 2
    assert len(list(part.walk())) == 5
    assert len(part.children) + len(part.hidden_ids) == 9
    assert part.hidden_ids == ["jwyql9d", "kil2dnr", "l7qi7zn", "lkbkhk6", "mzriofp", "o6bp184", "oczc53l"]
    assert not part.complete()


# ------------------------------------------------------------------ get_thread


async def test_get_thread_reads_the_whole_archived_thread(client, fake_archive):
    setup_thread(fake_archive)
    data = await call(client, "get_thread", {"url_or_id": "https://www.reddit.com/r/buildapc/comments/wi7uhk/intel_9900k_underclockingpower_limit_experiments/"})
    assert "not live Reddit" in data["source"]
    counts = data["comment_counts"]
    assert counts == {"in_archive": 22, "top_level": 9, "loaded": 22, "by_op": 10, "shown": 22, "not_shown": 0}
    notes = " ".join(data["notes"])
    assert "num_comments (2)" in notes and "22 comments" in notes  # the stale snapshot is called out
    assert "90-95%" in notes  # O4
    post = data["post"]
    assert post["id"] == "wi7uhk" and post["author"] == OP and post["score"] == 9
    assert post["created"].startswith("2022-08-07") and post["score_status"] == "snapshot"
    # the whole post, less its 15 invisible "&#x200B;" entities (8 characters each), which are counted
    assert "truncated" not in post and len(post["selftext"]) == 6606 - 15 * 8
    assert post["stripped_invisible"] == 15
    shown = comments_in(data["comments"])
    assert len(shown) == 22 and not stubs_in(data["comments"])
    for c in shown:
        assert_labelled(c)
        assert "/comments/wi7uhk/_/" in c["permalink"]
    assert sum(1 for c in shown if c.get("op")) == 10
    assert all(c["author"] == OP for c in shown if c.get("op"))
    assert estimate_tokens(data) < 8000
    assert fake_archive.paths().count("comments/tree") == 1
    assert fake_archive.params(fake_archive.paths().index("comments/tree")) == {"link_id": "wi7uhk", "limit": "200"}


async def test_get_thread_sorts_locally_on_every_level(client, fake_archive):
    setup_thread(fake_archive)
    top = await call(client, "get_thread", {"url_or_id": "wi7uhk"})
    # top-level scores in archive order: 2, 1, 1, 1, 1, 2, 1, 1, 1 -> the two 2s first, oldest first
    assert [c["id"] for c in top["comments"][:3]] == ["ijao2ef", "lkbkhk6", "jqqr5hr"]
    new = await call(client, "get_thread", {"url_or_id": "wi7uhk", "sort": "new"})
    assert [c["id"] for c in new["comments"]][:2] == ["oczc53l", "o6bp184"]
    replies = next(c for c in new["comments"] if c["id"] == "jqqr5hr")["replies"]
    assert [r["id"] for r in replies] == ["jtw77wo", "jqr4am2"]  # newest reply first
    old = await call(client, "get_thread", {"url_or_id": "wi7uhk", "sort": "old"})
    created = [c["created_utc"] for c in old["comments"]]
    assert created == sorted(created)


async def test_get_thread_trims_to_max_comments_with_stubs(client, fake_archive):
    setup_thread(fake_archive)
    data = await call(client, "get_thread", {"url_or_id": "wi7uhk", "max_comments": 5, "sort": "old"})
    shown = comments_in(data["comments"])
    stubs = stubs_in(data["comments"])
    assert len(shown) == 5
    assert data["comment_counts"]["shown"] == 5 and data["comment_counts"]["not_shown"] == 17
    assert sum(s["count"] for s in stubs) == 17  # every comment is shown or counted in a stub
    top_stub = next(s for s in stubs if s["parent_id"] == "t3_wi7uhk")
    assert top_stub["ids"][0] == "jwyql9d"
    assert any("expand_comments" in n for n in data["notes"])


async def test_get_thread_depth_one_shows_top_level_only(client, fake_archive):
    setup_thread(fake_archive)
    data = await call(client, "get_thread", {"url_or_id": "wi7uhk", "depth": 1})
    assert len(comments_in(data["comments"])) == 9
    for c in data["comments"]:
        for r in c.get("replies", []):
            assert r["kind"] == "more" and r["parent_id"] == f"t1_{c['id']}"


async def test_get_thread_keeps_archive_stubs(client, fake_archive):
    setup_thread(fake_archive, tree=TREE5)
    data = await call(client, "get_thread", {"url_or_id": "wi7uhk", "sort": "old"})
    assert data["comment_counts"]["in_archive"] == 22 and data["comment_counts"]["loaded"] == 5
    stubs = stubs_in(data["comments"])
    top = next(s for s in stubs if s["parent_id"] == "t3_wi7uhk")
    assert top["count"] == 15 and top["ids"] == ["jwyql9d", "kil2dnr", "l7qi7zn", "lkbkhk6", "mzriofp", "o6bp184", "oczc53l"]
    nested = next(s for s in stubs if s["parent_id"] == "t1_jqr4am2")
    assert nested == {"kind": "more", "count": 2, "parent_id": "t1_jqr4am2", "ids": ["jqstn48"]}
    assert any("returned 5 of 22" in n for n in data["notes"])


async def test_get_thread_stays_under_budget_on_a_big_thread(client, fake_archive):
    big = []
    for i in range(150):
        item = copy.deepcopy(ITEMS["ijao2ef"])
        item["data"].update(id=f"c{i:04d}", body="long words " * 120, score=i % 7, created_utc=1700000000 + i, replies="")
        big.append(item)
    setup_thread(fake_archive, tree={"data": big})
    data = await call(client, "get_thread", {"url_or_id": "wi7uhk", "max_comments": 150})
    shown = comments_in(data["comments"])
    assert 5 < len(shown) < 150
    assert estimate_tokens(data) < 8000
    assert data["comment_counts"]["shown"] + sum(s["count"] for s in stubs_in(data["comments"])) == 150
    assert any("to keep the answer short" in n for n in data["notes"])
    assert all(c.get("truncated") for c in shown)  # 1,300-character bodies are cut to 800


async def test_get_thread_refuses_sorts_an_archive_cannot_do(client, fake_archive):
    setup_thread(fake_archive)
    text = await call(client, "get_thread", {"url_or_id": "wi7uhk", "sort": "best"}, error=True)
    assert text.startswith("not available from an archive: best")
    text = await call(client, "get_thread", {"url_or_id": "wi7uhk", "sort": "sideways"}, error=True)
    assert text.startswith("input error:") and "top, new, old" in text
    assert "comments/tree" not in fake_archive.paths()


async def test_get_thread_unknown_post(client, fake_archive):
    fake_archive.add_status()
    fake_archive.add("posts/ids", {"data": []})
    fake_archive.add("comments/tree", {"data": []})
    text = await call(client, "get_thread", {"url_or_id": "zzzzzz"}, error=True)
    assert text.startswith("not in the archive: post zzzzzz")


async def test_get_thread_refuses_share_links_without_a_request(client, fake_archive):
    text = await call(client, "get_thread", {"url_or_id": "https://www.reddit.com/r/buildapc/s/AbCdEf"}, error=True)
    assert "share link" in text
    assert fake_archive.requests == []


# ------------------------------------------------------------------ expand_comments


async def test_expand_comments_from_archive_stubs(client, fake_archive):
    setup_thread(fake_archive, tree=TREE5)
    stub_ids = ["jwyql9d", "kil2dnr", "l7qi7zn", "lkbkhk6", "mzriofp", "o6bp184", "oczc53l"]
    data = await call(client, "expand_comments", {"post_id": "wi7uhk", "more_ids": stub_ids, "sort": "old"})
    shown = comments_in(data["comments"])
    assert len(shown) == 15  # the stub's count
    assert [c["id"] for c in data["comments"]] == stub_ids
    assert all(c["parent_id"] == "t3_wi7uhk" for c in data["comments"])  # roots say where they attach
    for c in shown:
        assert_labelled(c)
    assert data["comment_counts"] == {"loaded": 15, "shown": 15, "not_shown": 0}
    subtree_calls = [i for i, p in enumerate(fake_archive.paths()) if p == "comments/tree" and "parent_id" in fake_archive.params(i)]
    assert len(subtree_calls) == 7
    assert fake_archive.params(subtree_calls[0])["parent_id"] == "t1_jwyql9d"


async def test_expand_comments_reuses_the_cached_tree(client, fake_archive):
    setup_thread(fake_archive)
    first = await call(client, "get_thread", {"url_or_id": "wi7uhk", "max_comments": 3, "sort": "old"})
    stub = next(s for s in stubs_in(first["comments"]) if s["parent_id"] == "t3_wi7uhk")
    before = len(fake_archive.requests)
    data = await call(client, "expand_comments", {"post_id": "wi7uhk", "more_ids": stub["ids"], "sort": "old"})
    assert len(fake_archive.requests) == before  # tree and post came from the cache
    assert {c["id"] for c in data["comments"]} == set(stub["ids"])


async def test_expand_comments_nested_stub_and_limits(client, fake_archive):
    setup_thread(fake_archive, tree=TREE5)
    data = await call(client, "expand_comments", {"post_id": "wi7uhk", "more_ids": ["t1_jqstn48"]})
    assert [c["id"] for c in comments_in(data["comments"])] == ["jqstn48", "jqvvdwm"]
    assert data["comments"][0]["parent_id"] == "t1_jqr4am2"
    many = [f"x{i}" for i in range(12)]
    data = await call(client, "expand_comments", {"post_id": "wi7uhk", "more_ids": many})
    assert len(data["not_found"]) == 10 and data["not_expanded"] == ["x10", "x11"]
    text = await call(client, "expand_comments", {"post_id": "wi7uhk", "more_ids": []}, error=True)
    assert "more_ids is empty" in text


# ------------------------------------------------------------------ get_comment_context


async def test_comment_context_walks_up_the_parents(client, fake_archive):
    setup_thread(fake_archive)
    url = "https://www.reddit.com/r/buildapc/comments/wi7uhk/_/k53ri4g/"
    data = await call(client, "get_comment_context", {"comment_id_or_url": url, "context": 8})
    assert [p["id"] for p in data["parents"]] == ["jwyql9d", "jx031mj", "k4e6ti6"]  # top-down
    assert data["more_parents_above"] is False
    focal = data["comment"]
    assert focal["id"] == "k53ri4g" and focal["op"] is True and "truncated" not in focal
    assert data["post"]["id"] == "wi7uhk"
    for c in [*data["parents"], focal]:
        assert_labelled(c)
    # 1 subtree request, 3 parent lookups (one per level), 1 post lookup
    assert [p for p in fake_archive.paths() if p != "STATUS"] == [
        "comments/tree", "comments/ids", "comments/ids", "comments/ids", "posts/ids"]


async def test_comment_context_limits_and_bare_ids(client, fake_archive):
    setup_thread(fake_archive)
    data = await call(client, "get_comment_context", {"comment_id_or_url": "t1_k53ri4g", "context": 1})
    assert [p["id"] for p in data["parents"]] == ["k4e6ti6"]
    assert data["more_parents_above"] is True
    assert fake_archive.paths()[0] == "comments/ids"  # a bare ID needs a lookup for its post
    data = await call(client, "get_comment_context", {"comment_id_or_url": "jqqr5hr", "context": 12, "sort": "new"})
    assert any("showing 8 parents" in n for n in data["notes"])
    assert data["parents"] == [] and data["more_parents_above"] is False  # a top-level comment
    assert [r["id"] for r in data["replies"]] == ["jtw77wo", "jqr4am2"]


async def test_comment_context_full_text_of_a_long_comment(client, fake_archive):
    long_item = copy.deepcopy(ITEMS["jx031mj"])
    long_item["data"]["body"] = "word " * 1000
    fake_archive.add_status()
    fake_archive.add("posts/ids", POST)
    fake_archive.add("comments/tree", {"data": [long_item]}, match=has_parent)
    fake_archive.add("comments/ids", ids_reply)
    data = await call(client, "get_comment_context", {"comment_id_or_url": "https://www.reddit.com/r/buildapc/comments/wi7uhk/_/jx031mj/", "context": 0})
    assert len(data["comment"]["body"]) > 4000 and "truncated" not in data["comment"]
    assert [r["id"] for r in comments_in(data["replies"])] == ["k4e6ti6", "k53ri4g"]


async def test_comment_context_unknown_comment(client, fake_archive):
    fake_archive.add_status()
    fake_archive.add("comments/ids", {"data": []})
    text = await call(client, "get_comment_context", {"comment_id_or_url": "zzzzzzz"}, error=True)
    assert text.startswith("not in the archive: comment zzzzzzz")


# ------------------------------------------------------------------ query syntax (T7)


def test_parse_query_forms():
    q = parse_query('"power limit" 9900k')
    assert q.archive_body() == '"power limit" 9900k' and not q.has_exclusions
    q = parse_query("undervolt OR underclock")
    assert q.archive_body() == "undervolt OR underclock"
    q = parse_query("undervolt -laptop NOT -\"gaming laptop\"")
    assert q.archive_body() == "undervolt" and q.has_exclusions
    assert q.show() == 'undervolt -laptop -"gaming laptop"'
    q = parse_query("author:u/willswill subreddit:r/buildapc undervolt AND bios")
    assert q.authors == ["willswill"] and q.subreddits == ["buildapc"] and q.archive_body() == "undervolt bios"
    q = parse_query("i9-9900K")
    assert q.archive_body() == '"i9 9900k"'  # a hyphenated model name is a phrase


def test_parse_query_refusals():
    with pytest.raises(ValueError, match="no title: field"):
        parse_query("title:undervolt")
    with pytest.raises(ValueError, match="at least one word that is not excluded"):
        parse_query("-laptop")
    with pytest.raises(ValueError, match="at least one word"):
        parse_query("undervolt OR -laptop")


def test_local_matching_follows_websearch_rules():
    bodies = {cid: it["data"]["body"] for cid, it in ITEMS.items()}

    def hits(query):
        q = parse_query(query)
        return sorted(cid for cid, b in bodies.items() if q.matches(b))

    assert hits("undervolt") == ["ijao2ef", "ijgpj9q", "jx031mj", "k53ri4g", "oczc53l"]
    assert hits("undervolt OR underclock") == sorted(
        ["ijao2ef", "ijgpj9q", "jqqr5hr", "jx031mj", "k4e6ti6", "k53ri4g", "oczc53l"])
    assert "oczc53l" not in hits("power -undervolt")  # 'undervolt/underclock' counts here
    assert set(hits('"power limit"')) <= set(hits("power limit"))
    # AND binds tighter than OR: (9900k AND bios) OR underclock
    assert set(hits("9900k bios OR underclock")) == set(hits("9900k bios")) | set(hits("underclock"))


# ------------------------------------------------------------------ search_comments


def setup_search(fake_archive, search_reply):
    fake_archive.add_status()
    fake_archive.add("posts/ids", POST)
    fake_archive.add("comments/search", search_reply)


async def test_search_passes_or_through_to_the_archive(client, fake_archive):
    setup_search(fake_archive, load_fixture("comments/search-wi7uhk-or.json"))
    data = await call(client, "search_comments", {"post": "wi7uhk", "query": "undervolt OR underclock"})
    i = fake_archive.paths().index("comments/search")
    sent = fake_archive.params(i)
    assert sent["body"] == "undervolt OR underclock" and sent["link_id"] == "wi7uhk" and sent["sort"] == "desc"
    assert "fields" in sent and "subreddit" not in sent
    assert data["count"] == 6 and data["query_sent"] == "undervolt OR underclock"
    assert data["coverage"] == [{"scope": "post wi7uhk", "method": "archive full-text search", "returned": 6}]
    assert data["threads"][0]["id"] == "wi7uhk" and data["threads"][0]["matching_comments"] == 6
    for c in data["comments"]:
        assert_labelled(c)
    assert any("90-95%" in n for n in data["notes"])  # O4


async def test_search_applies_exclusions_locally(client, fake_archive):
    power = [flat(cid) for cid, it in ITEMS.items() if "power" in it["data"]["body"].lower()]
    setup_search(fake_archive, {"data": power})
    data = await call(client, "search_comments", {"post": "wi7uhk", "query": "power -undervolt", "limit": 5})
    sent = fake_archive.params(fake_archive.paths().index("comments/search"))
    assert sent["body"] == "power" and sent["limit"] == "100"  # over-fetch, then exclude here
    assert data["count"] == 5
    assert all("undervolt" not in c["body"].lower() for c in data["comments"])
    cov = data["coverage"][0]
    assert cov["returned"] == len(power) and cov["after_local_exclusion"] == 7
    assert any("Exclusions" in n for n in data["notes"])


async def test_search_falls_back_to_a_labelled_local_scan_on_422(client, fake_archive, fake_time):
    listing = sorted((flat(cid) for cid in ITEMS), key=lambda c: -c["created_utc"])
    fake_archive.add_status()
    fake_archive.add("posts/ids", POST)

    def page(request):
        p = request.url.params
        before = int(p.get("before", 10**10))
        rows = [c for c in listing if c["created_utc"] < before][: int(p["limit"])]
        return {"data": rows}

    fake_archive.add("comments/search", page)
    fake_archive.add("comments/search", (422, {"error": "Timeout. Maybe slow down a bit"}), match=lambda r: "body" in r.url.params)
    fake_archive.elapsed = 0.3  # fast 422s: load shedding
    data = await call(client, "search_comments", {"subreddits": ["buildapc"], "query": "underclock", "scan_pages": 2})
    searches = [fake_archive.params(i) for i, p in enumerate(fake_archive.paths()) if p == "comments/search"]
    assert [("body" in s) for s in searches] == [True, True, True, False]  # 3 tries, then 1 page (all 22 fit)
    assert searches[-1]["limit"] == "100" and searches[-1]["subreddit"] == "buildapc"
    cov = data["coverage"][0]
    assert cov["method"].startswith("partial local scan") and "busy" in cov["method"]
    assert cov["scanned"] == 22 and cov["window_fully_scanned"] is True and cov["matched"] == 3
    assert {c["id"] for c in data["comments"]} == {"jqqr5hr", "k4e6ti6", "oczc53l"}
    assert any("Partial local scan" in n for n in data["notes"])


async def test_search_scan_pages_backwards_and_stops_at_the_cap(client, fake_archive):
    rows = [{"id": f"s{i:03d}", "subreddit": "buildapc", "author": "a", "created_utc": 1790000000 - i * 10,
             "retrieved_on": 1790000100, "score": 1, "body": "nothing here", "link_id": "t3_wi7uhk",
             "parent_id": "t3_wi7uhk"} for i in range(350)]
    fake_archive.add_status()
    fake_archive.add("posts/ids", {"data": []})

    def page(request):
        before = int(request.url.params.get("before", 10**10))
        return {"data": [r for r in rows if r["created_utc"] < before][:100]}

    fake_archive.add("comments/search", page)
    fake_archive.add("comments/search", (422, {"error": "Timeout"}), match=lambda r: "body" in r.url.params)
    data = await call(client, "search_comments", {"subreddits": ["buildapc"], "query": "undervolt", "time": "all", "scan_pages": 3})
    scans = [fake_archive.params(i) for i, p in enumerate(fake_archive.paths()) if p == "comments/search" and "body" not in fake_archive.params(i)]
    assert len(scans) == 3
    assert "before" not in scans[0] and int(scans[1]["before"]) == rows[99]["created_utc"] + 1
    cov = data["coverage"][0]
    # each later page starts 1 s after the last one's oldest item, so 1 item repeats and is skipped
    assert cov["scanned"] == 298 and cov["window_fully_scanned"] is False and data["count"] == 0
    assert any("No matching comments" in n for n in data["notes"])


async def test_search_subreddits_window_and_merge(client, fake_archive, fake_time):
    phrase = load_fixture("comments/search-buildapc-phrase.json")
    fake_archive.add_status()
    fake_archive.add("posts/ids", {"data": []})
    fake_archive.add("comments/search", phrase)
    fake_archive.add("comments/search", {"data": phrase["data"][:5]}, match=lambda r: r.url.params.get("subreddit") == "intel")
    data = await call(client, "search_comments", {"subreddits": ["r/buildapc", "intel"], "query": '"power limit"', "time": "month", "limit": 10})
    searches = [fake_archive.params(i) for i, p in enumerate(fake_archive.paths()) if p == "comments/search"]
    assert [s["subreddit"] for s in searches] == ["buildapc", "intel"]
    assert all(s["body"] == '"power limit"' and s["after"].isdigit() and s["before"].isdigit() for s in searches)
    assert data["count"] == 10  # merged, de-duplicated by id, newest first
    created = [c["created_utc"] for c in data["comments"]]
    assert created == sorted(created, reverse=True)
    assert len({c["id"] for c in data["comments"]}) == 10
    assert data["window"].endswith("UTC") and data["coverage"][0]["more_available"] is True


async def test_search_refusals(client, fake_archive):
    fake_archive.add_status()
    text = await call(client, "search_comments", {"query": "undervolt"}, error=True)
    assert text.startswith("not available from an archive: global search")
    text = await call(client, "search_comments", {"subreddits": ["buildapc"], "query": "x", "sort": "relevance"}, error=True)
    assert text.startswith("not available from an archive: relevance")
    text = await call(client, "search_comments", {"subreddits": ["buildapc"], "query": "x", "sort": "top"}, error=True)
    assert "no score sort" in text
    text = await call(client, "search_comments", {"subreddits": ["buildapc"], "query": "flair:Help chatter"}, error=True)
    assert "search_posts" in text
    text = await call(client, "search_comments", {"subreddits": ["buildapc"], "time": "3m"}, error=True)
    assert "ambiguous" in text
    assert [p for p in fake_archive.paths() if p != "STATUS"] == []


async def test_search_author_scope_from_the_query(client, fake_archive):
    setup_search(fake_archive, {"data": [flat("k53ri4g")]})
    data = await call(client, "search_comments", {"query": "author:willswill bios"})
    sent = fake_archive.params(fake_archive.paths().index("comments/search"))
    assert sent["author"] == "willswill" and sent["body"] == "bios" and "subreddit" not in sent
    assert data["coverage"][0]["scope"] == "u/willswill"
