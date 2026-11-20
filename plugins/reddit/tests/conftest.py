"""Pytest fixtures shared by every session. Helpers live in tests/support.py.

- `fake_archive`: a `FakeArchive` that answers like Arctic Shift and records every request.
- `fake_time`: a `FakeTime` (monotonic clock, wall clock, recorded sleeps; sleeping is instant).
- `client`: an `ArcticShiftClient` wired to both, with an in-memory cache.
- Every test runs with real sockets blocked, except tests marked `live` (REDDIT_MCP_LIVE=1).

In a test: `from support import load_fixture, make_client, PROBE_TIME`.
"""

from __future__ import annotations

import os
import socket
from typing import Any

import pytest

from reddit_mcp.arctic import ArcticShiftClient
from support import FakeArchive, FakeTime, make_client


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def _no_network(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    if request.node.get_closest_marker("live"):
        return

    def guard(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("unit tests must not use the network (mark the test live)")

    monkeypatch.setattr(socket.socket, "connect", guard)
    monkeypatch.setattr(socket, "create_connection", guard)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.environ.get("REDDIT_MCP_LIVE") == "1":
        return
    skip = pytest.mark.skip(reason="live test: set REDDIT_MCP_LIVE=1 to run it")
    for item in items:
        if item.get_closest_marker("live"):
            item.add_marker(skip)


@pytest.fixture
def fake_time() -> FakeTime:
    return FakeTime()


@pytest.fixture
def fake_archive(fake_time: FakeTime) -> FakeArchive:
    return FakeArchive(fake_time)


@pytest.fixture
def client(fake_archive: FakeArchive, fake_time: FakeTime) -> ArcticShiftClient:
    return make_client(fake_archive, fake_time)
