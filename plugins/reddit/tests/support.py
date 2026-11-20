"""Shared test helpers (imported by conftest.py and by tests). Sessions 2-4 use these; do not change them.

- `fake_archive`: a `FakeArchive` that answers like Arctic Shift and records every request.
- `fake_time`: a `FakeTime` (monotonic clock, wall clock, recorded sleeps; sleeping is instant).
- `client`: an `ArcticShiftClient` wired to both, with an in-memory cache.
- `load_fixture("posts/buildapc-title-phrase.json")`: a saved response from tests/fixtures/.
- Every test runs with real sockets blocked, except tests marked `live` (REDDIT_MCP_LIVE=1).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from reddit_mcp.arctic import ArcticShiftClient, ResponseCache, Settings

FIXTURES = Path(__file__).parent / "fixtures"
BASE = "https://arctic.test/api"
STATUS = "https://status.test/api"
# 2026-11-20 22:32:00 UTC: the moment the status fixture was saved.
PROBE_TIME = 1795213920.0


def load_fixture(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text())


@dataclass
class FakeTime:
    mono: float = 1000.0
    wall_start: float = PROBE_TIME
    sleeps: list[float] = field(default_factory=list)

    def monotonic(self) -> float:
        return self.mono

    def wall(self) -> float:
        return self.wall_start + (self.mono - 1000.0)

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.mono += max(0.0, seconds)
        await asyncio.sleep(0)

    def advance(self, seconds: float) -> None:
        self.mono += seconds


Reply = Any  # dict body | (status, body) | (status, body, headers) | Exception | callable(request)


@dataclass
class Route:
    path: str
    replies: list[Reply]
    match: Callable[[httpx.Request], bool] | None = None
    repeat_last: bool = True


class FakeArchive:
    """Answers requests like Arctic Shift. Unknown paths get HTTP 404.

    `add(path, *replies, match=None)`: each request to `path` (without the base, e.g.
    "posts/search"; "STATUS" for the status feed) takes the next reply; the last one repeats.
    A reply is a JSON body (status 200), `(status, body)`, `(status, body, headers)`, an
    exception to raise (e.g. `httpx.ConnectError("down")`), or `callable(request) -> reply`.
    `requests` lists every request; `elapsed` sets how long each answer takes on `fake_time`.
    """

    def __init__(self, time: FakeTime):
        self.time = time
        self.routes: list[Route] = []
        self.requests: list[httpx.Request] = []
        self.in_flight = 0
        self.max_in_flight = 0
        self.elapsed = 0.1

    def add(self, path: str, *replies: Reply, match: Callable[[httpx.Request], bool] | None = None) -> "FakeArchive":
        self.routes.insert(0, Route(path, list(replies), match))
        return self

    def add_status(self, body: Any = None) -> "FakeArchive":
        return self.add("STATUS", body if body is not None else load_fixture("status/status-2026-11-20.json"))

    def paths(self) -> list[str]:
        return [self._path(r) for r in self.requests]

    def params(self, i: int = -1) -> dict[str, str]:
        return dict(self.requests[i].url.params)

    @staticmethod
    def _path(request: httpx.Request) -> str:
        url = str(request.url).split("?")[0]
        if url == STATUS:
            return "STATUS"
        assert url.startswith(BASE + "/"), f"request to a host outside the fake archive: {url}"
        return url[len(BASE) + 1 :]

    async def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            await asyncio.sleep(0)
            self.time.advance(self.elapsed)
            path = self._path(request)
            for route in self.routes:
                if route.path == path and (route.match is None or route.match(request)):
                    reply = route.replies.pop(0) if len(route.replies) > 1 else route.replies[0]
                    return self._respond(reply, request)
            return httpx.Response(404, json={"data": None, "error": f"no fake route for {path}"})
        finally:
            self.in_flight -= 1

    def _respond(self, reply: Reply, request: httpx.Request) -> httpx.Response:
        if callable(reply) and not isinstance(reply, type):
            reply = reply(request)
        if isinstance(reply, BaseException):
            raise reply
        if isinstance(reply, httpx.Response):
            return reply
        status, body, headers = 200, reply, {}
        if isinstance(reply, tuple):
            status, body, *rest = reply
            headers = rest[0] if rest else {}
        if isinstance(body, (dict, list)) or body is None:
            return httpx.Response(status, json=body, headers=headers)
        return httpx.Response(status, text=str(body), headers=headers)


def make_client(fake_archive: FakeArchive, fake_time: FakeTime, **settings: Any) -> ArcticShiftClient:
    s = Settings(base_url=BASE, status_url=STATUS, cache_path=None, **settings)
    return ArcticShiftClient(
        s,
        transport=httpx.MockTransport(fake_archive.handler),
        cache=ResponseCache(None, ttl=s.cache_ttl, clock=fake_time.wall),
        sleep=fake_time.sleep,
        clock=fake_time.monotonic,
        wall=fake_time.wall,
    )


