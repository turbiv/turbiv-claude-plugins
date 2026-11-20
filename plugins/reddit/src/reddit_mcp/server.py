"""The MCP server: one FastMCP instance, one Arctic Shift client, every tool module registered."""

from __future__ import annotations

from fastmcp import FastMCP

from . import __version__
from .arctic import ArcticShiftClient, Settings
from .context import ServerContext
from .tools import MODULES

INSTRUCTIONS = """\
Read-only Reddit research through Arctic Shift, a third-party archive of Reddit. Not live Reddit.

- No tool can post, reply, vote, message or log in. Say so when asked to write anything.
- Data: posts arrive within seconds, comments within minutes (sometimes days). Scores and comment
  counts are frozen at one snapshot about 1.5-2 days after posting; `score_status` says which.
- Not possible from an archive: Reddit's hot/rising/best ranking, relevance ranking, r/all,
  live scores, and keyword search across all of Reddit (name subreddits or an author).
- Cite each post or comment by its `permalink`. When a tool says "archive unavailable", report
  that; there is no other source, and this server never contacts reddit.com.
- Call `archive_status` to check freshness or an outage.
"""


def build_server(client: ArcticShiftClient | None = None) -> FastMCP:
    client = client or ArcticShiftClient(Settings.from_env())
    mcp = FastMCP("reddit", instructions=INSTRUCTIONS, version=__version__)
    ctx = ServerContext(client=client)
    for module in MODULES:
        module.register(mcp, ctx)
    return mcp


def main() -> None:
    build_server().run(show_banner=False)


if __name__ == "__main__":
    main()
