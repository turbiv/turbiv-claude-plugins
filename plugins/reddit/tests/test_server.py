"""Server-wide rules every tool must keep (global criteria 1, 2, 5). Sessions 2-4's tools are
checked here too, as soon as they register."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastmcp import Client

from reddit_mcp.arctic import SOURCE_NOTE
from reddit_mcp.server import INSTRUCTIONS, build_server
from reddit_mcp.tools import MODULES

pytestmark = pytest.mark.anyio

SRC = Path(__file__).parent.parent / "src" / "reddit_mcp"
WRITE_WORDS = re.compile(r"(^|_)(post|reply|submit|vote|upvote|downvote|delete|edit|send|message|comment|login|create)$")


async def list_tools(client):
    async with Client(build_server(client)) as c:
        return await c.list_tools()


async def test_every_module_is_registered():
    assert [m.__name__.rsplit(".", 1)[1] for m in MODULES] == ["status", "posts", "comments", "discovery"]


async def test_archive_status_is_registered(client):
    assert "archive_status" in {t.name for t in await list_tools(client)}


async def test_every_tool_is_read_only_and_labelled(client):
    for t in await list_tools(client):
        assert t.annotations and t.annotations.read_only_hint is True, t.name
        assert t.annotations.destructive_hint is False, t.name
        assert SOURCE_NOTE in (t.description or ""), t.name
        assert not WRITE_WORDS.search(t.name), f"{t.name} sounds like a write tool"


async def test_no_key_or_login_parameters(client):
    for t in await list_tools(client):
        props = set((t.input_schema or {}).get("properties", {}))
        assert not props & {"api_key", "token", "password", "client_id", "client_secret", "cookie"}, t.name


def test_instructions_say_read_only_and_archive():
    assert "Read-only" in INSTRUCTIONS and "not live reddit" in INSTRUCTIONS.lower()
    assert "never contacts reddit.com" in INSTRUCTIONS


def test_source_never_requests_reddit():
    """reddit.com appears only in permalink building and the forbidden-host list (D1)."""
    allowed = {"arctic/helpers.py", "arctic/config.py", "server.py"}
    for path in SRC.rglob("*.py"):
        rel = path.relative_to(SRC).as_posix()
        text = path.read_text()
        # the archive's own host is photon-reddit.com; that is not Reddit
        if re.search(r"https?://([a-z0-9-]+\.)*reddit\.com\b", text):
            assert rel in allowed, f"{rel} mentions a reddit.com URL"
    helpers = (SRC / "arctic" / "helpers.py").read_text()
    assert 'REDDIT_WEB = "https://www.reddit.com"' in helpers
