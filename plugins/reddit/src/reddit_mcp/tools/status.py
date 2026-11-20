"""archive_status (Session 1): how fresh the archive is, in plain words (L1, L2)."""

from __future__ import annotations

from typing import Any

from ..arctic import ARCHIVE_NOTICE, archive_tool, get_freshness, iso
from ..context import ServerContext


def register(mcp: Any, ctx: ServerContext) -> None:
    @archive_tool(mcp, title="Archive status")
    async def archive_status() -> dict:
        """Check whether the Reddit archive is up and how fresh its data is.

        Returns, in plain words: whether the archive API is available, how old the newest
        archived post and comment are (the ingest lag), how far the second pass that freezes
        scores has got, and any warning (a component down, or ingest that looks stopped).
        Call it when a search fails or comes back empty, or before you rely on recent data.
        """
        f = await get_freshness(ctx.client, max_age=30.0)
        return {
            "source": ARCHIVE_NOTICE,
            "summary": f.summary(),
            "available": f.api_available,
            "warnings": f.warnings,
            "checked_at": iso(f.checked_at),
            "components": f.components,
        }
