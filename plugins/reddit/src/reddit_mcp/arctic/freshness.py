"""Freshness from the status feed, in plain words (L1, L2, O4).

The feed (`https://status.arctic-shift.photon-reddit.com/api`, a separate host) looks like::

    {"lastUpdateAt": <ms>,
     "api":              {"isAvailable", "failedAt", "lastUpdateAt", "mostRecentPostAt", "mostRecentCommentAt"},
     "archiver":         {... "hasClients"},
     "archiverTrailing": {...},   # the second pass that freezes scores (~36 h behind)
     "idNotifier":       {...},
     "trailingIdNotifier": {...}}

All times are epoch milliseconds; `mostRecent*At` can be null.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .errors import ArchiveError
from .helpers import age_words, iso

# L2: the newest archived post older than this means ingest may have stopped.
POST_STALL_SECONDS = 6 * 3600
# O4: comment ingest lag above this gets a note on comment results.
COMMENT_LAG_SECONDS = 30 * 60

_COMPONENT_WORDS = {
    "api": "API",
    "archiver": "live archiver",
    "archiverTrailing": "second-pass archiver (freezes scores)",
    "idNotifier": "new-ID scanner",
    "trailingIdNotifier": "second-pass ID scanner",
}


def _sec(ms: Any) -> float | None:
    return float(ms) / 1000.0 if isinstance(ms, (int, float)) and not isinstance(ms, bool) else None


@dataclass
class Freshness:
    checked_at: float
    api_available: bool | None
    newest_post_age: float | None
    newest_comment_age: float | None
    post_second_pass_age: float | None
    comment_second_pass_age: float | None
    components: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        parts = []
        if self.api_available is True:
            parts.append("The archive API is up.")
        elif self.api_available is False:
            parts.append("The archive API is DOWN according to its status page.")
        else:
            parts.append("The status page does not say whether the API is up.")
        if self.newest_post_age is not None:
            parts.append(f"Newest post is {age_words(self.newest_post_age)} old.")
        if self.newest_comment_age is not None:
            parts.append(
                f"Newest comment is {age_words(self.newest_comment_age)} old "
                f"(comments lag {age_words(self.newest_comment_age)})."
            )
        if self.post_second_pass_age is not None:
            parts.append(
                f"The second pass, which freezes scores, is at {age_words(self.post_second_pass_age)} for posts: "
                "posts younger than that still show their first score (1 or 0)."
            )
        if self.comment_second_pass_age is not None:
            parts.append(f"For comments it is at {age_words(self.comment_second_pass_age)}.")
        else:
            parts.append("The status page shows no second-pass time for comments.")
        return " ".join(parts)


def parse_freshness(body: Mapping[str, Any], now: float) -> Freshness:
    def comp(name: str) -> Mapping[str, Any]:
        c = body.get(name)
        return c if isinstance(c, Mapping) else {}

    def age(name: str, key: str) -> float | None:
        t = _sec(comp(name).get(key))
        return None if t is None else max(0.0, now - t)

    api = comp("api")
    avail = api.get("isAvailable") if isinstance(api.get("isAvailable"), bool) else None
    comment_trailing = age("archiverTrailing", "mostRecentCommentAt")
    if comment_trailing is None:
        comment_trailing = age("trailingIdNotifier", "mostRecentCommentAt")
    f = Freshness(
        checked_at=now,
        api_available=avail,
        newest_post_age=age("api", "mostRecentPostAt"),
        newest_comment_age=age("api", "mostRecentCommentAt"),
        post_second_pass_age=age("archiverTrailing", "mostRecentPostAt"),
        comment_second_pass_age=comment_trailing,
    )
    for name, c in body.items():
        if not isinstance(c, Mapping):
            continue
        is_av = c.get("isAvailable")
        entry = {
            "name": name,
            "what": _COMPONENT_WORDS.get(name, name),
            "available": is_av if isinstance(is_av, bool) else None,
        }
        if c.get("failedAt"):
            entry["failed_at"] = iso(_sec(c.get("failedAt"))) or c.get("failedAt")
        for k in ("mostRecentPostAt", "mostRecentCommentAt"):
            t = _sec(c.get(k))
            if t is not None:
                entry["newest_post_age" if "Post" in k else "newest_comment_age"] = age_words(now - t)
        f.components.append(entry)
        if is_av is False:
            when = f" since {entry['failed_at']}" if entry.get("failed_at") else ""
            f.warnings.append(f"status page: the {entry['what']} is down{when}")
    if f.newest_post_age is not None and f.newest_post_age > POST_STALL_SECONDS:
        f.warnings.append(
            f"the archive may have stopped ingesting: the newest post is {age_words(f.newest_post_age)} old, "
            "so recent Reddit activity is missing"
        )
    if f.newest_comment_age is not None and f.newest_comment_age > COMMENT_LAG_SECONDS:
        f.warnings.append(
            f"comment ingest lags {age_words(f.newest_comment_age)}: comments newer than that are missing"
        )
    return f


async def get_freshness(client: Any, *, max_age: float = 600.0) -> Freshness:
    """Raises ArchiveUnavailable when the status feed cannot be read."""
    body = await client.status(max_age=max_age)
    return parse_freshness(body, client._wall())


async def freshness_warnings(client: Any, *, comments: bool = False) -> list[str]:
    """Warnings for a result (L2, O4). Never raises: no status means no warnings."""
    if client is None:
        return []
    try:
        f = await get_freshness(client)
    except ArchiveError:
        return []
    if comments:
        return f.warnings
    return [w for w in f.warnings if not w.startswith("comment ingest")]
