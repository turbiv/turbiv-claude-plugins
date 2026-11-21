"""Network audit (global criterion 1, D1, E5): every tool, called with Reddit URLs and usual
arguments, contacts only the archive API host and the status host. Nothing goes to reddit.com.

A recording transport answers every request with a plausible saved response, so the tools run
their normal paths (listings, ids, trees, share links, wiki, users, time series, the status feed).
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest
from fastmcp import Client

from reddit_mcp.arctic import DEFAULT_BASE_URL, DEFAULT_STATUS_URL, ArcticShiftClient, ResponseCache, Settings
from reddit_mcp.server import build_server
from support import BASE, STATUS, FakeTime, load_fixture

pytestmark = pytest.mark.anyio

SRC = Path(__file__).parent.parent / "src" / "reddit_mcp"

REPLIES = {
    "posts/search": load_fixture("posts/buildapc-title-phrase.json"),
    "posts/ids": load_fixture("comments/post-wi7uhk-full.json"),
    "comments/search": load_fixture("comments/search-wi7uhk-undervolt.json"),
    "comments/ids": load_fixture("discovery/comment-k8so54m.json"),
    "comments/tree": load_fixture("comments/tree-wi7uhk.json"),
    "subreddits/search": load_fixture("discovery/prefix-espresso.json"),
    "subreddits/rules": load_fixture("discovery/rules-espresso.json"),
    "subreddits/wikis/list": load_fixture("discovery/wikilist-espresso.json"),
    "subreddits/wikis": load_fixture("discovery/wiki-espresso-faq.json"),
    "time_series": load_fixture("discovery/ts-espresso-posts-day.json"),
    "users/search": load_fixture("discovery/user-example.json"),
    "users/interactions/subreddits": load_fixture("discovery/user-subs-example.json"),
    "short_links": load_fixture("discovery/shortlink-running-2.json"),
}

CALLS = {
    "archive_status": [{}],
    "list_posts": [{"subreddits": ["buildapc"]}, {"subreddits": ["r/buildapc"], "sort": "top", "time": "month"}],
    "search_posts": [{"subreddits": ["buildapc"], "query": '"power limit" 9900k'}],
    "deep_search": [{"concepts": [["9900k"], ["power limit", "PL1"]], "subreddits": ["buildapc"],
                     "in": "both", "max_requests": 4}],
    "get_posts": [{"ids_or_urls": ["https://www.reddit.com/r/buildapc/comments/wi7uhk/x/", "https://redd.it/wi7uhk"]}],
    "get_thread": [{"url_or_id": "https://old.reddit.com/r/buildapc/comments/wi7uhk/intel/"}],
    "expand_comments": [{"post_id": "wi7uhk", "more_ids": ["jqqr5hr"]}],
    "get_comment_context": [{"comment_id_or_url": "https://www.reddit.com/r/buildapc/comments/wi7uhk/_/jqqr5hr/"}],
    "search_comments": [{"subreddits": ["buildapc"], "query": "undervolt"}],
    "find_subreddits": [{"name_or_prefix": "espresso"}],
    "subreddit_info": [{"subreddit": "https://www.reddit.com/r/espresso/"}],
    "read_wiki": [{"subreddit": "espresso", "page": "faq"}],
    "get_user": [{"username": "https://www.reddit.com/user/example_user/"}],
    "resolve_share_link": [{"url": "https://www.reddit.com/r/running/s/0MH2aME2Z9"}],
    "trending_posts": [{"subreddits": ["buildapc"], "hours": 24, "max_requests": 3}],
    "count_mentions": [{"subreddits": ["buildapc"], "terms": ["9900k"], "time": "week", "max_requests": 3}],
}


class Recorder:
    def __init__(self, time: FakeTime):
        self.time = time
        self.urls: list[str] = []

    async def handler(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url).split("?")[0]
        self.urls.append(str(request.url))
        self.time.advance(0.1)
        if url == STATUS:
            return httpx.Response(200, json=load_fixture("status/status-2026-11-20.json"))
        path = url[len(BASE) + 1 :] if url.startswith(BASE + "/") else url
        return httpx.Response(200, json=REPLIES.get(path, {"data": []}))


async def test_every_tool_contacts_only_the_archive_hosts():
    t = FakeTime()
    rec = Recorder(t)
    s = Settings(base_url=BASE, status_url=STATUS, cache_path=None)
    client = ArcticShiftClient(
        s, transport=httpx.MockTransport(rec.handler), cache=ResponseCache(None, clock=t.wall),
        sleep=t.sleep, clock=t.monotonic, wall=t.wall,
    )
    async with Client(build_server(client)) as c:
        names = {tool.name for tool in await c.list_tools()}
        assert names == set(CALLS), "add the new tool to CALLS in this audit"
        ok = total = 0
        for name, arg_sets in CALLS.items():
            for args in arg_sets:
                r = await c.call_tool(name, args, raise_on_error=False)
                ok += not r.is_error
                total += 1
    hosts = {urlsplit(u).hostname for u in rec.urls}
    assert hosts == {"arctic.test", "status.test"}, hosts
    assert not any(re.search(r"reddit\.com|redd\.it", urlsplit(u).hostname or "") for u in rec.urls)
    assert len(rec.urls) > 30 and ok == total  # every call ran its normal path


def test_default_hosts_are_arctic_shift():
    s = Settings(cache_path=None)
    assert s.allowed_hosts == {"arctic-shift.photon-reddit.com", "status.arctic-shift.photon-reddit.com"}
    assert DEFAULT_BASE_URL.startswith("https://arctic-shift.photon-reddit.com/")
    assert DEFAULT_STATUS_URL.startswith("https://status.arctic-shift.photon-reddit.com/")


def test_only_the_client_makes_http_requests():
    """No module but the client opens a connection or names an HTTP library."""
    pattern = re.compile(r"\b(httpx|requests|urllib\.request|urlopen|aiohttp|socket|http\.client)\b")
    for path in SRC.rglob("*.py"):
        rel = path.relative_to(SRC).as_posix()
        if rel == "arctic/client.py":
            continue
        code = "\n".join(line for line in path.read_text().splitlines() if not line.lstrip().startswith("#"))
        imports = [m for m in re.findall(r"^\s*(?:import|from)\s+(\S+)", code, re.M) if pattern.search(m)]
        assert not imports, f"{rel} imports {imports}"


def test_no_request_to_a_reddit_url_in_the_source():
    """reddit.com URLs appear only as permalink text and in the forbidden-host list."""
    allowed = {"arctic/helpers.py", "arctic/config.py", "server.py"}
    for path in SRC.rglob("*.py"):
        rel = path.relative_to(SRC).as_posix()
        text = path.read_text()
        if re.search(r"\.get\(\s*f?[\"']https?://", text):
            raise AssertionError(f"{rel} requests an absolute URL")
        if re.search(r"https?://([a-z0-9-]+\.)*(reddit\.com|redd\.it)\b", text):
            assert rel in allowed, rel
