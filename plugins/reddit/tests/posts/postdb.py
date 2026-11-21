"""A small fake post database that answers posts/search and posts/ids like Arctic Shift.

It filters on subreddit, author, link_flair_text, over_18, after/before (exclusive), sorts by
created_utc, honours limit and fields=, and does a token phrase match for title/selftext/query
(the archive's behaviour in docs/probes.md, Q6). `fail` lets a test script 422 answers.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

import httpx
from support import PROBE_TIME

DAY = 86400


def toks(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (s or "").lower())


def phrase_in(phrase: str, text: str) -> bool:
    p, t = toks(phrase.strip('"')), toks(text)
    return bool(p) and any(t[i : i + len(p)] == p for i in range(len(t) - len(p) + 1))


def post(pid: str, sub: str = "buildapc", *, age_days: float = 10, title: str = "a post", selftext: str = "",
         score: int = 5, num_comments: int = 3, **kw: Any) -> dict[str, Any]:
    created = int(PROBE_TIME - age_days * DAY)
    return {
        "id": pid, "subreddit": sub, "author": kw.pop("author", "someone"), "created_utc": created,
        "retrieved_on": created + 10, "score": score, "num_comments": num_comments, "title": title,
        "selftext": selftext, "link_flair_text": kw.pop("flair", None), "over_18": kw.pop("over_18", False),
        "url": kw.pop("url", f"https://www.reddit.com/r/{sub}/comments/{pid}/x/"), **kw,
    }


class FakeDB:
    def __init__(self, fake_archive):
        self.posts: list[dict[str, Any]] = []
        self.comments: list[dict[str, Any]] = []
        self.fail: Callable[[dict[str, str]], Any] | None = None  # params -> reply or None
        fake_archive.add("posts/search", self._search)
        fake_archive.add("posts/ids", self._ids)
        fake_archive.add("comments/search", self._comment_search)
        fake_archive.add_status()

    def add(self, *posts: dict[str, Any]) -> "FakeDB":
        self.posts.extend(posts)
        return self

    @staticmethod
    def _project(item: dict[str, Any], params: dict[str, str]) -> dict[str, Any]:
        if "fields" not in params:
            return dict(item)
        return {k: item.get(k) for k in params["fields"].split(",")}

    def _filter(self, items, p):
        out = []
        for x in items:
            if "subreddit" in p and x["subreddit"].lower() != p["subreddit"].lower():
                continue
            if "author" in p and x["author"] != p["author"]:
                continue
            if "link_flair_text" in p and x.get("link_flair_text") != p["link_flair_text"]:
                continue
            if "over_18" in p and bool(x.get("over_18")) != (p["over_18"] == "true"):
                continue
            if "after" in p and not x["created_utc"] > int(p["after"]):
                continue
            if "before" in p and not x["created_utc"] < int(p["before"]):
                continue
            if "title" in p and not phrase_in(p["title"], x.get("title", "")):
                continue
            if "selftext" in p and not phrase_in(p["selftext"], x.get("selftext", "")):
                continue
            if "query" in p and not (phrase_in(p["query"], x.get("title", "")) or phrase_in(p["query"], x.get("selftext", ""))):
                continue
            if "body" in p and not any(phrase_in(t.strip(), x.get("body", "")) for t in p["body"].split(" OR ")):
                continue
            out.append(x)
        out.sort(key=lambda x: x["created_utc"], reverse=p.get("sort", "desc") == "desc")
        return out[: int(p.get("limit", 25))]

    def _search(self, request: httpx.Request):
        p = dict(request.url.params)
        if self.fail:
            r = self.fail(p)
            if r is not None:
                return r
        return {"data": [self._project(x, p) for x in self._filter(self.posts, p)]}

    def _comment_search(self, request: httpx.Request):
        p = dict(request.url.params)
        if self.fail:
            r = self.fail(p)
            if r is not None:
                return r
        return {"data": [self._project(x, p) for x in self._filter(self.comments, p)]}

    def _ids(self, request: httpx.Request):
        p = dict(request.url.params)
        want = p["ids"].split(",")
        return {"data": [self._project(x, p) for x in self.posts if x["id"] in want]}


