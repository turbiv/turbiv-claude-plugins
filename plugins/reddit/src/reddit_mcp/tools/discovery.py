"""Session 4: find_subreddits, subreddit_info, read_wiki, get_user, resolve_share_link,
trending_posts, count_mentions.

Only Session 4 edits this file (plus its tests under tests/discovery/ and its eval cases).
Import shared code from `reddit_mcp.arctic`; do not change it. See docs/architecture.md.

Design notes (rules from `docs/research/synthesis.md`, probes in docs/probes.md and
docs/discovery-costs.md):

- Archive keyword search and the aggregate endpoints are unreliable under load (a comment
  `body` aggregate returned 0 for a term that had 100 matches). So the counting tools never
  rely on them. They list a time window newest-first and match terms locally.
- A window too large for the request budget is sampled: equal time slices, one page each.
  Every result states the scan mode, the items scanned, the estimated total and the requests
  used (T14). Counts from a sample are sample counts, plus a labelled scaled estimate.
- `trending_posts` ranks by recent comment activity, never by Reddit's `hot` (T4).
"""

from __future__ import annotations

import html
import math
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from pydantic import Field

from ..arctic import (
    DEFAULT_COMMENT_FIELDS,
    DEFAULT_POST_FIELDS,
    SHORT_LINKS_BATCH,
    InputError,
    QueryTooHeavy,
    RateLimited,
    archive_tool,
    iso,
    make_result,
    parse_comment_ref,
    parse_post_ref,
    permalink_comment,
    permalink_post,
    resolve_window,
    shape_comment,
    shape_post,
    strip_prefix,
    trim_text,
    unavailable_feature,
)
from ..arctic.helpers import REDDIT_WEB
from ..context import ServerContext

PAGE = 100  # R4: the most a search call returns

MAX_SUBREDDITS = 10
MAX_TERMS = 25
MAX_REQUESTS_CAP = 100  # D4: no tool call scans without a bound
BOTS = frozenset({"automoderator"})

SUBREDDIT_NOTE = (
    "Subreddit data (subscribers, descriptions) is a snapshot the archive refreshes only now and "
    "then; 'subscribers_as_of' gives its date. Private, quarantined and banned subreddits are not "
    "in the archive."
)

_SUB_NAME = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.]{0,49}$")
_USER_NAME = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


# ---------------------------------------------------------------- names


def _sub_name(value: str) -> str:
    """'r/Coffee', '/r/Coffee/', 'www.reddit.com/r/Coffee/' -> 'Coffee'."""
    s = (value or "").strip()
    if "reddit.com" in s.lower():
        parts = [p for p in urlsplit(s if "://" in s else "https://" + s).path.split("/") if p]
        s = parts[1] if len(parts) >= 2 and parts[0].lower() == "r" else ""
    s = re.sub(r"^/?r/", "", s, flags=re.I).strip("/")
    if not _SUB_NAME.match(s):
        raise InputError(f"not a subreddit name: {value!r}")
    return s


def _sub_list(subreddits: Sequence[str] | str | None, *, what: str) -> list[str]:
    if isinstance(subreddits, str):
        subreddits = [p for p in re.split(r"[,\s]+", subreddits) if p]
    names = list(dict.fromkeys(_sub_name(s) for s in subreddits or []))
    if not names:
        raise InputError(f"{what} needs at least one subreddit")
    if len(names) > MAX_SUBREDDITS:
        raise InputError(f"at most {MAX_SUBREDDITS} subreddits per call")
    return names


def _user_name(value: str) -> str:
    s = (value or "").strip()
    if "reddit.com" in s.lower():
        parts = [p for p in urlsplit(s if "://" in s else "https://" + s).path.split("/") if p]
        s = parts[1] if len(parts) >= 2 and parts[0].lower() in ("u", "user") else ""
    s = re.sub(r"^/?(u|user)/", "", s, flags=re.I).strip("/")
    if not _USER_NAME.match(s):
        raise InputError(f"not a Reddit username: {value!r}")
    return s


def _sub_link(name: str) -> str:
    return f"{REDDIT_WEB}/r/{name}/"


def _clamp(value: int, lo: int, hi: int, name: str) -> int:
    try:
        v = int(value)
    except (TypeError, ValueError):
        raise InputError(f"{name} must be a whole number") from None
    if not lo <= v <= hi:
        raise InputError(f"{name} must be {lo}-{hi}")
    return v


# ---------------------------------------------------------------- bounded window scan (T14)


@dataclass
class Scan:
    """One subreddit and one kind (posts or comments) listed over a window."""

    label: str
    after: int
    before: int
    items: list[dict[str, Any]] = field(default_factory=list)
    requests: int = 0
    mode: str = "complete"  # complete | partial | sampled
    est_total: float = 0.0
    covered: float = 0.0  # seconds of the window actually listed
    failed: list[str] = field(default_factory=list)
    stopped: str | None = None

    @property
    def scanned(self) -> int:
        return len(self.items)

    @property
    def complete(self) -> bool:
        return self.mode == "complete" and not self.failed

    @property
    def scale(self) -> float:
        """Estimated items per scanned item (1.0 when the window was listed in full)."""
        if self.complete or not self.items:
            return 1.0
        return max(1.0, self.est_total / len(self.items))

    def describe(self) -> dict[str, Any]:
        span = max(1, self.before - self.after)
        out: dict[str, Any] = {
            "stream": self.label,
            "mode": self.mode,
            "items_scanned": self.scanned,
            "estimated_items_in_window": round(self.est_total),
            "share_scanned": (
                f"{min(1.0, self.scanned / self.est_total):.0%}" if self.est_total
                else ("unknown" if self.failed else "100%")
            ),
            "time_listed": f"{min(1.0, self.covered / span):.0%} of the window",
            "requests": self.requests,
        }
        if self.failed:
            out["failed_slices"] = self.failed
        if self.stopped:
            out["stopped"] = self.stopped
        return out


class _Pager:
    """Fetches pages for one stream and keeps the bookkeeping."""

    def __init__(self, client: Any, path: str, params: Mapping[str, Any], fields: Sequence[str], scan: Scan,
                 limit: int = 10**6):
        self.client, self.path, self.params, self.fields, self.scan = client, path, dict(params), fields, scan
        self.limit = limit  # this stream's request budget
        self.seen: set[str] = set()

    async def page(self, after: int, before: int) -> tuple[list[dict[str, Any]], bool] | None:
        """One page newest-first in [after, before). Returns (items, full) or None on a 422.
        `scan.requests` counts real HTTP requests, so 422 and 429 retries use up budget too.
        The 422 retry is skipped when only one request of the budget is left."""
        sent = self.client.call_requests
        try:
            resp = await self.client.get(
                self.path,
                {**self.params, "sort": "desc", "limit": PAGE, "after": after, "before": before},
                fields=self.fields,
                retry_422=1 if self.limit - self.scan.requests >= 2 else 0,
            )
        except QueryTooHeavy as e:
            self.scan.requests += max(1, self.client.call_requests - sent)
            kind = "busy (fast 422)" if e.fast else "timed out (422)"
            self.scan.failed.append(f"{iso(after)} to {iso(before)}: archive {kind}")
            return None
        except RateLimited:
            self.scan.requests += self.client.call_requests - sent
            raise
        self.scan.requests += self.client.call_requests - sent  # 0 for a cache hit
        data = [x for x in (resp.data or []) if isinstance(x, Mapping)]
        limit = int(resp.params.get("limit", PAGE))
        new = []
        for x in data:
            xid = str(x.get("id"))
            if xid not in self.seen:
                self.seen.add(xid)
                new.append(dict(x))
        self.scan.items.extend(new)
        return data, len(data) >= limit


def _oldest(items: Iterable[Mapping[str, Any]], default: int) -> int:
    ts = [int(x["created_utc"]) for x in items if isinstance(x.get("created_utc"), (int, float))]
    return min(ts) if ts else default


async def scan_window(
    client: Any,
    path: str,
    params: Mapping[str, Any],
    fields: Sequence[str],
    after: int,
    before: int,
    pages: int,
    *,
    label: str,
) -> Scan:
    """List [after, before) newest-first with at most `pages` HTTP requests (422 retries count).

    1. One page over the whole window. Fewer than a full page: the window is complete.
    2. Otherwise estimate the volume from that page. If the rest fits the budget, page back in
       time to the start ('complete', or 'partial' if the estimate was low).
    3. If it does not fit, sample: split the rest of the window into equal slices and fetch the
       newest page of each ('sampled'). Counts then cover a spread-out sample of the window.
    """
    scan = Scan(label=label, after=after, before=before)
    pages = max(1, pages)
    pager = _Pager(client, path, params, fields, scan, limit=pages)
    try:
        first = await pager.page(after, before)
        if first is None:  # the archive refused the whole window: sample it in slices instead
            await _sample(pager, after, before, pages)
            return scan
        data, full = first
        if not full:
            scan.mode, scan.est_total, scan.covered = "complete", float(len(data)), float(before - after)
            return scan
        oldest = _oldest(data, before)
        listed = max(1, before - oldest)
        density = len(data) / listed
        rest_pages = math.ceil(density * max(0, oldest - after) / PAGE)
        scan.covered = float(listed)
        if rest_pages <= pages - scan.requests:
            await _page_back(pager, after, oldest, pages, density)
        else:
            scan.est_total = float(len(data))
            await _sample(pager, after, oldest, pages, base_density=density)
    except RateLimited as e:
        scan.stopped = f"rate limited by the archive (retry after about {e.wait_seconds:.0f} s)"
        scan.mode = "partial" if scan.mode == "complete" else scan.mode
        if not scan.est_total:
            scan.est_total = float(len(scan.items))
    return scan


async def _page_back(pager: _Pager, after: int, oldest: int, limit: int, density: float) -> None:
    scan = pager.scan
    cursor = oldest
    for _ in range(limit):  # also bounds a run of cache hits
        if scan.requests >= limit:
            break
        got = await pager.page(after, cursor + 1)
        if got is None:
            break
        data, full = got
        new_oldest = _oldest(data, cursor)
        if not full:
            scan.mode, scan.covered = "complete", float(scan.before - scan.after)
            scan.est_total = float(len(scan.items))
            return
        if new_oldest >= cursor:  # a full page inside one second: step past it
            new_oldest = cursor - 1
        cursor = new_oldest
        density = len(scan.items) / max(1, scan.before - cursor)
    scan.mode = "partial"
    scan.covered = float(scan.before - cursor)
    scan.est_total = len(scan.items) + density * max(0, cursor - after)


async def _sample(pager: _Pager, after: int, before: int, limit: int, base_density: float | None = None) -> None:
    """One page from each of the equal slices of [after, before) that the budget left over
    allows. Slices a retry left no budget for are estimated from the others' density."""
    scan = pager.scan
    scan.mode = "sampled"
    slices = limit - scan.requests
    if slices <= 0 or before <= after:
        scan.est_total += (base_density or 0.0) * max(0, before - after)
        return
    width = (before - after) / slices
    densities: list[float] = []
    missing = 0.0
    for i in range(slices):
        b = int(before - i * width)
        a = int(before - (i + 1) * width) if i < slices - 1 else after
        if b <= a:
            continue
        if scan.requests >= limit:
            missing += b - a
            if not scan.stopped:
                scan.stopped = "request budget used up (422 retries); the rest of the window is estimated"
            continue
        got = await pager.page(a, b)
        if got is None:
            missing += b - a
            continue
        data, full = got
        if not full:
            scan.est_total += len(data)
            scan.covered += b - a
            densities.append(len(data) / (b - a))
            continue
        old = _oldest(data, a)
        listed = max(1, b - old)
        scan.covered += listed
        d = len(data) / listed
        densities.append(d)
        scan.est_total += d * (b - a)
    if missing:
        ds = densities or ([base_density] if base_density else [])
        scan.est_total += (sum(ds) / len(ds) if ds else 0.0) * missing


# ---------------------------------------------------------------- term matching


def _term_regex(alt: str) -> re.Pattern[str]:
    """'Wooting 60HE' matches 'wooting 60he', 'Wooting-60 HE', 'wooting60he'; 'Keychron' also
    matches "Keychron's" and 'Keychrons'. Letters and digits must not touch the match."""
    tokens = re.findall(r"[A-Za-z]+|\d+|[^\sA-Za-z\d_-]+", alt)
    if not tokens:
        raise InputError(f"empty search term: {alt!r}")
    body = r"[\s_-]?".join(re.escape(t) for t in tokens)
    return re.compile(rf"(?<![A-Za-z0-9]){body}(?:'?s)?(?![A-Za-z0-9])", re.I)


@dataclass
class Term:
    label: str
    patterns: list[re.Pattern[str]]

    @classmethod
    def parse(cls, raw: str) -> "Term":
        alts = [a.strip() for a in (raw or "").split("|") if a.strip()]
        if not alts:
            raise InputError(f"empty search term: {raw!r}")
        return cls(alts[0], [_term_regex(a) for a in alts])

    def find(self, text: str) -> re.Match[str] | None:
        for p in self.patterns:
            m = p.search(text)
            if m:
                return m
        return None


def _snippet(text: str, m: re.Match[str], width: int = 160) -> str:
    flat = re.sub(r"\s+", " ", text)
    pos = len(re.sub(r"\s+", " ", text[: m.start()]))
    start = max(0, pos - width // 2)
    piece = flat[start : start + width].strip()
    return ("…" if start > 0 else "") + piece + ("…" if start + width < len(flat) else "")


def _item_text(kind: str, item: Mapping[str, Any]) -> str:
    if kind == "posts":
        parts = [item.get("title") or "", item.get("selftext") or ""]
    else:
        parts = [item.get("body") or ""]
    text = "\n".join(p for p in parts if p and p not in ("[removed]", "[deleted]"))
    return html.unescape(text)


# ---------------------------------------------------------------- registration


def register(mcp: Any, ctx: ServerContext) -> None:
    """Register this module's tools on `mcp`."""

    client = ctx.client

    async def _fetch_posts(ids: Iterable[str]) -> dict[str, dict[str, Any]]:
        ids = [i for i in dict.fromkeys(strip_prefix(i) for i in ids) if i]
        if not ids:
            return {}
        posts = await client.get_ids("posts", ids, fields=DEFAULT_POST_FIELDS)
        return {strip_prefix(p.get("id")): p for p in posts if isinstance(p, Mapping)}

    # ------------------------------------------------------------ find_subreddits (T12)

    @archive_tool(mcp, title="Find subreddits by name")
    async def find_subreddits(
        name_or_prefix: str,
        min_subscribers: int | None = None,
        nsfw: bool | None = None,
        keyword: str | None = None,
        limit: int = 15,
        activity_for_top: int = 3,
    ) -> dict:
        """Find subreddits whose NAME starts with `name_or_prefix` (e.g. 'espresso' finds
        r/espresso, r/espressocirclejerk, r/EspressoMachines), largest first, with subscriber
        counts and public descriptions.

        This is name and prefix matching only: the archive has no topic search. To find
        communities about a topic, call it with several likely name stems (for home espresso:
        'espresso', 'coffee', 'barista'). `keyword` keeps only results whose name or public
        description contains that word (a local filter over the name matches, not a topic
        search). `nsfw`: true for NSFW only, false to exclude NSFW.

        The `activity_for_top` largest results (default 3, max 10) also get posts per day over
        the last 4 weeks (one request each). `subreddit_info` gives full activity, rules and
        wiki pages for the ones you pick.
        """
        prefix = _sub_name(name_or_prefix)
        limit = _clamp(limit, 1, 50, "limit")
        activity_for_top = _clamp(activity_for_top, 0, 10, "activity_for_top")
        params: dict[str, Any] = {
            "subreddit_prefix": prefix,
            # Slim objects (SUBREDDIT_FIELDS, about 0.4 KB each instead of 9 KB), so a keyword
            # filter can look at many more name matches.
            "limit": 500 if keyword else max(limit, 25),
            "min_subscribers": min_subscribers,
            "over18": nsfw,
            "sort_type": "subscribers",
            "sort": "desc",
        }
        resp = await client.get("subreddits/search", params, fields=FIND_SUB_FIELDS)
        subs = [s for s in (resp.data or []) if isinstance(s, Mapping)]
        scanned = len(subs)
        notes = [
            "Matched by subreddit name prefix only; the archive cannot search subreddits by topic.",
            SUBREDDIT_NOTE,
        ]
        if keyword:
            kw = keyword.strip().lower()
            subs = [
                s for s in subs
                if kw in " ".join(str(s.get(k) or "") for k in ("display_name", "public_description")).lower()
            ]
            notes.append(
                f"keyword filter {keyword!r}: kept {len(subs)} of the {scanned} largest name matches "
                "(local filter over names and public descriptions)"
            )
        if not subs:
            notes.append(
                f"No archived subreddit name starts with {prefix!r}. Try other name stems; private, "
                "quarantined and banned subreddits are not in the archive."
            )
        items = [_shape_sub(s, matched=f"name starts with '{prefix}'") for s in subs[:limit]]
        for item, sub in zip(items[:activity_for_top], subs):
            try:
                act = await _activity(sub.get("display_name") or item["name"][2:], "posts")
            except QueryTooHeavy:
                act = None
            if act:
                item["posts_per_day"] = act["posts_per_day"]
                item["posts_per_day_through"] = act["through"]
        if items[:activity_for_top]:
            notes.append(
                "posts_per_day: average archived posts per UTC day over the last 4 weeks, from the "
                "archive's daily time series (largest results only; subreddit_info for the others)"
            )
        return await make_result(client, items_key="subreddits", items=items, notes=notes, query={
            "name_or_prefix": prefix, "min_subscribers": min_subscribers, "nsfw": nsfw, "keyword": keyword,
        })

    # ------------------------------------------------------------ subreddit_info

    @archive_tool(mcp, title="Subreddit info and activity")
    async def subreddit_info(subreddit: str) -> dict:
        """About one subreddit: subscribers, title and description, activity (posts and comments
        per day over the last 4 weeks, from the archive's daily time series), the rules, and the
        list of wiki pages (read one with `read_wiki`). Uses about 5 archive requests."""
        name = _sub_name(subreddit)
        resp = await client.get("subreddits/search", {"subreddit": name})
        found = [s for s in (resp.data or []) if isinstance(s, Mapping)]
        if not found:
            return await make_result(client, found=False, subreddit=name, notes=[
                f"r/{name} is not in the archive. It may not exist, or it is private, quarantined "
                "or banned; the archive does not hold those.",
            ])
        sub = found[0]
        display = sub.get("display_name") or name
        info = _shape_sub(sub, full=True)
        notes = [SUBREDDIT_NOTE]

        activity: dict[str, Any] = {}
        for kind in ("posts", "comments"):
            try:
                activity[kind] = await _activity(display, kind)
            except QueryTooHeavy:
                activity[kind] = None
        if activity.get("posts") is None:
            activity["posts"] = await _activity_from_listing(display)
        if activity.get("comments") is None:
            activity.pop("comments", None)
            notes.append("comments per day: the archive's time series was not available")

        rules: list[dict[str, Any]] = []
        try:
            r = await client.get("subreddits/rules", {"subreddits": display})
            for entry in r.data or []:
                if isinstance(entry, Mapping):
                    for rule in entry.get("rules") or []:
                        desc, cut = trim_text(rule.get("description"), 300)
                        rules.append({k: v for k, v in {
                            "priority": rule.get("priority"),
                            "rule": rule.get("short_name"),
                            "applies_to": rule.get("kind"),
                            "description": desc,
                            "truncated": True if cut else None,
                        }.items() if v is not None})
        except QueryTooHeavy:
            notes.append("rules: the archive was busy; try again later")

        wiki: list[str] = []
        try:
            w = await client.get("subreddits/wikis/list", {"subreddit": display})
            wiki = [_wiki_page_name(p) for p in (w.data or []) if isinstance(p, str)]
        except QueryTooHeavy:
            notes.append("wiki pages: the archive was busy; try again later")

        return await make_result(
            client,
            found=True,
            subreddit=info,
            activity=activity,
            rules=rules or "the archive holds no rules for this subreddit",
            wiki_pages=wiki[:100] or "the archive holds no wiki pages for this subreddit",
            notes=notes + (["read a wiki page with read_wiki(subreddit, page)"] if wiki else []),
        )

    async def _activity(display: str, kind: str) -> dict[str, Any] | None:
        now = client.now()
        resp = await client.get(
            "time_series",
            {"key": f"r/{display}/{kind}/count", "precision": "day", "after": int(now - 35 * 86400)},
            ttl=3600,
        )
        points = [
            p for p in (resp.data or [])
            if isinstance(p, Mapping) and isinstance(p.get("date"), (int, float)) and p["date"] + 86400 <= now
        ]
        points.sort(key=lambda p: p["date"])
        if not points:
            return None
        last28 = points[-28:]
        last7 = points[-7:]
        avg = sum(float(p.get("value") or 0) for p in last28) / len(last28)
        avg7 = sum(float(p.get("value") or 0) for p in last7) / len(last7)
        return {
            f"{kind}_per_day": round(avg, 1),
            f"{kind}_per_day_last_7_days": round(avg7, 1),
            "days_averaged": len(last28),
            "through": iso(points[-1]["date"] + 86400 - 1)[:10],
            "method": "archive daily time series (archived items per UTC day; the newest day or two may still be filling in)",
        }

    async def _activity_from_listing(display: str) -> dict[str, Any] | None:
        now = int(client.now())
        try:
            resp = await client.get(
                "posts/search",
                {"subreddit": display, "sort": "desc", "limit": PAGE, "before": now},
                fields=("id", "created_utc"),
            )
        except QueryTooHeavy:
            return None
        data = [p for p in resp.data or [] if isinstance(p.get("created_utc"), (int, float))]
        if not data:
            return {"posts_per_day": 0, "method": "no archived posts found"}
        span = max(3600, now - min(p["created_utc"] for p in data))
        return {
            "posts_per_day": round(len(data) / (span / 86400), 1),
            "method": f"estimate from the newest {len(data)} archived posts (time series not available)",
        }

    # ------------------------------------------------------------ read_wiki

    @archive_tool(mcp, title="Read a subreddit wiki page")
    async def read_wiki(subreddit: str, page: str = "index", offset: int = 0, max_chars: int = 12000) -> dict:
        """Read one wiki page of a subreddit from the archive's snapshot (for example 'index',
        'faq', 'guides/brewing-basics'; `subreddit_info` lists the pages). The archive keeps one
        older snapshot per page, not the live wiki. Long pages come in parts: pass the returned
        `next_offset` as `offset` to read on."""
        name = _sub_name(subreddit)
        page_name = _wiki_page_name(page or "index")
        offset = _clamp(offset, 0, 10_000_000, "offset")
        max_chars = _clamp(max_chars, 500, 20000, "max_chars")
        candidates = list(dict.fromkeys([
            f"/r/{name.lower()}/wiki/{page_name.lower()}",
            f"/r/{name}/wiki/{page_name}",
        ]))
        entry: Mapping[str, Any] | None = None
        for path in candidates:
            r = await client.get("subreddits/wikis", {"paths": path})
            hits = [x for x in r.data or [] if isinstance(x, Mapping) and x.get("content") is not None]
            if hits:
                entry = hits[0]
                break
        if entry is None:
            w = await client.get("subreddits/wikis/list", {"subreddit": name})
            pages = [_wiki_page_name(p) for p in (w.data or []) if isinstance(p, str)]
            return await make_result(client, found=False, subreddit=name, page=page_name, notes=[
                f"The archive has no wiki page {page_name!r} for r/{name}.",
                f"Pages it has: {', '.join(pages[:60])}" if pages else f"The archive holds no wiki pages for r/{name}.",
            ])
        content = html.unescape(str(entry.get("content") or ""))
        part = content[offset : offset + max_chars]
        more = offset + max_chars < len(content)
        revised = _num(entry.get("revision_date"))
        retrieved = _num(entry.get("retrieved_on"))
        fields = dict(
            found=True,
            subreddit=name,
            page=page_name,
            url=f"{REDDIT_WEB}/r/{name}/wiki/{page_name}/",
            revision_date=iso(revised),
            revision_author=entry.get("revision_author"),
            snapshot_taken=iso(retrieved),
            length_chars=len(content),
            offset=offset,
            content=part,
            truncated=True if more else None,
            next_offset=offset + max_chars if more else None,
        )
        notes = [f"Archived snapshot of the wiki page, taken {iso(retrieved) or 'at an unknown date'}; the live page may have changed since."]
        return await make_result(client, notes=notes, **{k: v for k, v in fields.items() if v is not None})

    # ------------------------------------------------------------ get_user (T13)

    @archive_tool(mcp, title="Archived user activity")
    async def get_user(
        username: str,
        time: str | None = "year",
        after: str | None = None,
        before: str | None = None,
        limit: int = 10,
    ) -> dict:
        """A Reddit user's archived activity: post and comment totals, the subreddits they are
        most active in, and their newest posts and comments in the window (default: the last
        year; `time` takes hour/day/week/month/year/all or a span such as '3 months').

        Karma here is the archive's own sum of archived scores: stale and often far below
        Reddit's real karma. There is no account age: the archive does not know when an account
        was created."""
        user = _user_name(username)
        limit = _clamp(limit, 1, 25, "limit")
        window = resolve_window(None if (after or before) else time, after, before)
        notes: list[str] = [
            "No account age: the archive does not hold account creation dates.",
        ]

        r = await client.get("users/search", {"author": user})
        rows = [x for x in r.data or [] if isinstance(x, Mapping)]
        if not rows:
            return await make_result(client, found=False, username=user, notes=[
                f"u/{user} is not in the archive. The name may be wrong, the account may have no "
                "archived activity, or the user opted out of the archive.",
            ])
        row = rows[0]
        meta = row.get("_meta") if isinstance(row.get("_meta"), Mapping) else {}
        profile = {
            "username": row.get("author") or user,
            "profile": f"{REDDIT_WEB}/user/{row.get('author') or user}/",
            "archived_posts": meta.get("num_posts"),
            "archived_comments": meta.get("num_comments"),
            "archive_karma": {
                "post": meta.get("post_karma"),
                "comment": meta.get("comment_karma"),
                "total": meta.get("total_karma"),
                "label": "stale archive karma: the sum of archived scores, not Reddit karma (often about half of it or less)",
            },
            "first_archived_post": iso(meta.get("earliest_post_at")),
            "first_archived_comment": iso(meta.get("earliest_comment_at")),
            "last_archived_post": iso(meta.get("last_post_at")),
            "last_archived_comment": iso(meta.get("last_comment_at")),
            "stats_updated": iso(max([v for v in (meta.get("post_stats_updated_at"), meta.get("comment_stats_updated_at")) if isinstance(v, (int, float))], default=None)),
            "account_age": None,
        }
        profile = {k: v for k, v in profile.items() if v is not None or k == "account_age"}
        profile["account_age"] = "not available from the archive"
        notes.append("first_archived_* is the oldest activity the archive holds, not the account creation date.")

        active: list[dict[str, Any]] | str = []
        try:
            a = await client.get(
                "users/interactions/subreddits", {"author": user, "limit": 15, **window.params()}
            )
            active = [
                {"subreddit": x.get("subreddit"), "posts_and_comments": x.get("count"),
                 "link": _sub_link(x.get("subreddit"))}
                for x in a.data or [] if isinstance(x, Mapping) and x.get("subreddit")
            ]
        except QueryTooHeavy:
            active = "the archive timed out on this user's subreddit list; try a narrower window"

        posts: list[dict[str, Any]] | str
        comments: list[dict[str, Any]] | str
        try:
            p = await client.get(
                "posts/search", {"author": user, "sort": "desc", "limit": limit, **window.params()},
                fields=DEFAULT_POST_FIELDS,
            )
            posts = [shape_post(x, text_chars=300) for x in p.data or [] if isinstance(x, Mapping)]
        except QueryTooHeavy:
            posts = "the archive timed out on this user's posts; try a narrower window"
        try:
            c = await client.get(
                "comments/search", {"author": user, "sort": "desc", "limit": limit, **window.params()},
                fields=DEFAULT_COMMENT_FIELDS,
            )
            comments = [shape_comment(x, text_chars=300) for x in c.data or [] if isinstance(x, Mapping)]
        except QueryTooHeavy:
            comments = "the archive timed out on this user's comments; try a narrower window"

        return await make_result(
            client,
            comments=True,
            found=True,
            user=profile,
            window=window.describe(),
            active_subreddits=active,
            newest_posts=posts,
            newest_comments=comments,
            notes=notes,
        )

    # ------------------------------------------------------------ resolve_share_link (T15)

    @archive_tool(mcp, title="Resolve Reddit share links")
    async def resolve_share_link(url: str | list[str]) -> dict:
        """Resolve Reddit share links such as www.reddit.com/r/running/s/0MH2aME2Z9 (the
        '/s/' links the Reddit app makes) to the full post or comment, and return that post (and
        comment) from the archive. Use it before reading a thread when the user gives a /s/ link.

        It uses only the archive's short_links table, which knows share links that appeared in
        archived posts and comments; it never opens reddit.com. Up to 1000 links per call."""
        raw = [url] if isinstance(url, str) else list(url or [])
        raw = [u for part in raw for u in re.split(r"[\s,]+", part or "") if u]
        if not raw:
            raise InputError("give at least one share link")
        if len(raw) > SHORT_LINKS_BATCH:
            raise InputError(f"at most {SHORT_LINKS_BATCH} links per call")
        parsed: list[tuple[str, str | None]] = []  # (input, share path or None)
        for u in raw:
            parsed.append((u, _share_path(u)))
        paths = [p for _, p in parsed if p]
        resolved: dict[str, Mapping[str, Any]] = {}
        if paths:
            rows = await client.get_batched("short_links", "paths", paths, SHORT_LINKS_BATCH)
            for row in rows:
                if isinstance(row, Mapping) and row.get("original_path") and row.get("resolved_path"):
                    resolved[str(row["original_path"])] = row

        links: list[dict[str, Any]] = []
        post_ids: list[str] = []
        comment_ids: list[str] = []
        for given, path in parsed:
            entry: dict[str, Any] = {"share_link": given}
            target: str | None = None
            if path is None:
                try:
                    parse_post_ref(given)
                    target = given
                    entry["note"] = "not a share link; it is already a full Reddit link"
                except InputError:
                    entry.update(resolved=False, note="not a Reddit share link (/r/<sub>/s/<code> or /u/<user>/s/<code>)")
                    links.append(entry)
                    continue
            else:
                row = resolved.get(path)
                if row is None:
                    entry.update(
                        resolved=False,
                        note=(
                            "the archive does not know this share link: it only knows links that "
                            "appeared in archived posts or comments. Ask the user to open it and "
                            "paste the full /comments/ URL; this server does not contact reddit.com."
                        ),
                    )
                    links.append(entry)
                    continue
                target = REDDIT_WEB + str(row["resolved_path"])
                entry["seen_in"] = row.get("found_in")
            clean = target.split("?", 1)[0].split("#", 1)[0]
            entry["resolved"] = True
            entry["url"] = clean if clean.endswith("/") else clean + "/"
            try:
                pid = parse_post_ref(clean)
                entry["post_id"] = pid
                post_ids.append(pid)
            except InputError:
                entry["note"] = "resolves to a link that is not a post (for example a profile or subreddit)"
            try:
                cid, _ = parse_comment_ref(clean)
                entry["comment_id"] = cid
                comment_ids.append(cid)
            except InputError:
                pass
            links.append(entry)

        posts = await _fetch_posts(post_ids)
        comments: dict[str, Mapping[str, Any]] = {}
        if comment_ids:
            rows = await client.get_ids("comments", comment_ids, fields=DEFAULT_COMMENT_FIELDS)
            comments = {strip_prefix(c.get("id")): c for c in rows if isinstance(c, Mapping)}
        for entry in links:
            pid = entry.get("post_id")
            if pid:
                if pid in posts:
                    entry["post"] = shape_post(posts[pid])
                else:
                    entry["post"] = None
                    entry["post_note"] = "the post is not in the archive"
            cid = entry.get("comment_id")
            if cid:
                if cid in comments:
                    entry["comment"] = shape_comment(comments[cid])
                else:
                    entry["comment_note"] = "the comment is not in the archive"
        n_ok = sum(1 for e in links if e.get("resolved"))
        return await make_result(
            client,
            comments=bool(comment_ids),
            items_key="links",
            items=links,
            notes=[f"resolved {n_ok} of {len(links)} link(s) through the archive's short_links table"],
        )

    # ------------------------------------------------------------ trending_posts (T4)

    @archive_tool(mcp, title="Trending posts by recent comment activity")
    async def trending_posts(
        subreddits: list[str],
        hours: int = 24,
        limit: int = 15,
        max_requests: int = 20,
    ) -> dict:
        """Posts with the most NEW comments in the last `hours` hours in the given subreddits
        (1-10), most active first. This is "recent comment activity", NOT Reddit's hot ranking:
        an archive has no live votes, so hot, rising, r/all and r/popular are not available, and
        the scores of posts under about 36 h old are not final.

        For "what is trending on Reddit" with no topic, ask for a topic or pick a few large
        subreddits (for example AskReddit, worldnews, news, technology, gaming, movies) and say
        which you picked. Large subreddits are sampled across the window; the result states the
        comments scanned and the share of the window covered. About 1-2 s per request."""
        if not subreddits:
            raise InputError(
                unavailable_feature("r/all") + " Name 1-10 subreddits: ask the user for a topic, or "
                "pick a few large ones (AskReddit, worldnews, news, technology, gaming) and say so."
            )
        subs = _sub_list(subreddits, what="trending_posts")
        hours = _clamp(hours, 1, 168, "hours")
        limit = _clamp(limit, 1, 50, "limit")
        max_requests = _clamp(max_requests, 1, MAX_REQUESTS_CAP, "max_requests")
        if max_requests < len(subs) + 1:
            raise InputError(
                f"max_requests must be at least {len(subs) + 1} for {len(subs)} subreddit(s): one page "
                "each, plus one to fetch the posts"
            )
        page_budget = max_requests - 1  # 1 request to fetch the posts
        sent_before = client.call_requests
        now = int(client.now())
        after = now - hours * 3600
        scans: list[Scan] = []
        remaining = page_budget
        for i, sub in enumerate(subs):
            share = max(1, remaining // (len(subs) - i))
            s = await scan_window(
                client, "comments/search", {"subreddit": sub},
                ("id", "link_id", "created_utc", "author", "subreddit"),
                after, now, share, label=f"r/{sub} comments",
            )
            remaining -= s.requests
            scans.append(s)

        seen: Counter[str] = Counter()
        est: defaultdict[str, float] = defaultdict(float)
        authors: defaultdict[str, set[str]] = defaultdict(set)
        latest: dict[str, int] = {}
        post_sub: dict[str, str] = {}
        for s in scans:
            for c in s.items:
                if str(c.get("author") or "").lower() in BOTS:
                    continue
                link = strip_prefix(c.get("link_id"))
                if not link:
                    continue
                seen[link] += 1
                est[link] += s.scale
                if c.get("author") and c["author"] != "[deleted]":
                    authors[link].add(c["author"])
                latest[link] = max(latest.get(link, 0), int(c.get("created_utc") or 0))
                post_sub[link] = c.get("subreddit") or post_sub.get(link, "")
        ranked = sorted(est, key=lambda k: (-est[k], -len(authors[k]), -latest[k]))[:limit]
        posts = await _fetch_posts(ranked) if ranked else {}
        sampled = any(not s.complete for s in scans)
        items = []
        for rank, link in enumerate(ranked, 1):
            p = posts.get(link)
            base = shape_post(p, text_chars=200) if p else {
                "id": link, "subreddit": post_sub.get(link),
                "permalink": permalink_post(post_sub.get(link) or "", link),
                "created": "unknown: the post is not in the archive",
                "score_status": "none: the post is not in the archive",
                "note": "post not in the archive",
            }
            entry = {
                "rank": rank,
                "new_comments_seen": seen[link],
                "new_comments_estimated": round(est[link]) if sampled else None,
                "distinct_commenters_seen": len(authors[link]),
                "latest_comment": iso(latest[link]),
                **base,
            }
            items.append({k: v for k, v in entry.items() if v is not None})
        notes = [
            f"Method: recent comment activity, not Reddit's hot. Posts are ranked by the number of "
            f"new archived comments in the last {hours} h (AutoModerator excluded). Reddit's hot, "
            "rising, r/all and r/popular need live votes and are not available from an archive.",
            "Scores and num_comments of posts under about 36 h old are first-seen values (score_status 'initial'), not final.",
        ]
        if sampled:
            notes.append(
                "Some subreddits had more comments than the request budget covers: their comments "
                "were sampled in equal time slices across the window. new_comments_estimated scales "
                "the sample up; compare posts by it. Raise max_requests for a fuller count."
            )
        result = await make_result(
            client,
            comments=True,
            items_key="posts",
            items=items,
            notes=notes,
            method="recent comment activity, not Reddit's hot",
            counts=(
                "SAMPLE: new_comments_seen counts only the sampled comments; new_comments_estimated "
                "scales them up" if sampled else "every archived comment of the window was counted"
            ),
            window=f"last {hours} h: {iso(after)} to {iso(now)}",
            subreddits=[f"r/{s}" for s in subs],
            coverage=[s.describe() for s in scans],
            requests_used=0,
        )
        result["requests_used"] = client.call_requests - sent_before  # HTTP requests, status check included
        return result

    # ------------------------------------------------------------ count_mentions (T14)

    @archive_tool(mcp, title="Count mentions of terms")
    async def count_mentions(
        subreddits: list[str],
        terms: list[str],
        time: str | None = None,
        after: str | None = None,
        before: str | None = None,
        in_: Annotated[Literal["posts", "comments", "both"], Field(alias="in")] = "both",
        max_requests: int = 40,
        all_time: bool = False,
    ) -> dict:
        """Count how often each term is mentioned in posts and/or comments of 1-10 subreddits
        in a time window, for questions like "most recommended mechanical keyboard in the last 3
        months". Give the candidates as `terms` (up to 25, e.g. ["Keychron", "Wooting",
        "HHKB|Happy Hacking"]; use '|' for aliases of one term). For each term it returns the
        mentions (posts or comments that contain it), the distinct threads and authors, and
        example thread links with a snippet, ranked by distinct threads.

        Window: `time` ('3 months', 'month', 'year', ...) or `after`/`before`; the default is
        the last 3 months. All-time needs `all_time=true`. `in` is posts, comments or both.

        Bounded scan: it lists the window newest-first, at most `max_requests` archive requests
        (default 40, retries included, plus one status check; about 1.5 minutes), and matches the terms locally (archive keyword search
        is unreliable). Windows bigger than the budget are SAMPLED in equal time slices; the
        result states each subreddit's scan size, the share scanned and any truncation, and
        adds scaled estimates. Matching is whole-word and case-insensitive; a mention is not
        always a recommendation, so read the snippets and the top threads. In the answer, give the
        exact window, the counts, and the example thread links for the top terms."""
        subs = _sub_list(subreddits, what="count_mentions (the archive has no Reddit-wide search)")
        if isinstance(terms, str):
            terms = [t for t in terms.split(",") if t.strip()]
        parsed = [Term.parse(t) for t in dict.fromkeys(t.strip() for t in terms or [] if t and t.strip())]
        if not parsed:
            raise InputError("give at least one term")
        if len(parsed) > MAX_TERMS:
            raise InputError(f"at most {MAX_TERMS} terms per call")
        where = in_
        if where not in ("posts", "comments", "both"):
            raise InputError("in must be posts, comments or both")
        max_requests = _clamp(max_requests, 2, MAX_REQUESTS_CAP, "max_requests")
        sent_before = client.call_requests
        if time is None and after is None and before is None:
            time = "3 months"
        window = resolve_window(time, after, before)
        now = int(client.now())
        if window.after is None and not all_time:
            raise InputError(
                "an all-time count is heavy and needs all_time=true; or give a window such as "
                "time='12 months' (T14)"
            )
        w_after = window.after if window.after is not None else 1119484800  # 2005-06-23
        w_before = min(window.before or now, now)
        if w_after >= w_before:
            raise InputError("the window is empty")

        kinds = ["posts", "comments"] if where == "both" else [where]
        streams = len(kinds) * len(subs)
        if max_requests < streams + 1:
            raise InputError(
                f"max_requests must be at least {streams + 1} here: one page per subreddit and kind "
                f"({streams}), plus one for the thread titles"
            )
        pages = max_requests - 1  # 1 request for thread titles
        if where == "both":
            post_pages = max(len(subs), pages // 3)
            budgets = {"posts": post_pages, "comments": max(len(subs), pages - post_pages)}
        else:
            budgets = {where: pages}

        scans: list[tuple[str, Scan]] = []
        carry = 0
        for kind in kinds:
            remaining = budgets[kind] + carry
            for i, sub in enumerate(subs):
                share = max(1, remaining // (len(subs) - i))
                s = await scan_window(
                    client,
                    f"{kind}/search",
                    {"subreddit": sub},
                    _SCAN_FIELDS[kind],
                    w_after,
                    w_before,
                    share,
                    label=f"r/{sub} {kind}",
                )
                remaining -= s.requests
                scans.append((kind, s))
            carry = max(0, remaining)

        # ---- local matching
        stats = {t.label: _TermStats() for t in parsed}
        post_meta: dict[str, Mapping[str, Any]] = {}
        for kind, s in scans:
            for item in s.items:
                if str(item.get("author") or "").lower() in BOTS:
                    continue
                if kind == "posts":
                    post_meta[str(item.get("id"))] = item
                text = _item_text(kind, item)
                if not text:
                    continue
                for t in parsed:
                    m = t.find(text)
                    if m:
                        stats[t.label].add(kind, item, s.scale, _snippet(text, m))

        # ---- thread titles for the examples
        example_threads: set[str] = set()
        for st in stats.values():
            example_threads.update(st.top_threads(3, post_meta))
        missing = [tid for tid in example_threads if tid not in post_meta]
        if missing:
            try:
                post_meta.update(await _fetch_posts(missing[:500]))
            except QueryTooHeavy:
                pass

        sampled = any(not s.complete for _, s in scans)
        rows = []
        for t in parsed:
            st = stats[t.label]
            rows.append(st.row(t, post_meta, sampled))
        rows.sort(key=lambda r: (-r["threads"], -r["mentions"], r["term"].lower()))
        for i, r in enumerate(rows, 1):
            r["rank"] = i

        scanned = {k: sum(s.scanned for kk, s in scans if kk == k) for k in kinds}
        notes = [
            "Method: the window was listed newest-first and each term matched locally (whole word, "
            "case-insensitive, aliases with '|'). 'mentions' counts posts/comments containing the "
            "term at least once; 'threads' counts distinct posts. Ranked by threads, then mentions. "
            "AutoModerator is excluded. A mention is not always a recommendation: read the snippets.",
            "When you answer, state the exact window and cite the example thread links (examples[].thread) "
            "of the top terms, so the user can check the discussions.",
        ]
        if sampled:
            notes.append(
                "TRUNCATED SCAN: the window held more items than the request budget covers, so it "
                "was sampled (see coverage). Counts are from the sample; estimated_* scale them to "
                "the whole window and are rough. Raise max_requests or narrow the window for fuller counts."
            )
        failed = [f for _, s in scans for f in s.failed]
        if failed:
            notes.append(f"{len(failed)} slice(s) failed (archive busy or timed out); see coverage.failed_slices")
        result = await make_result(
            client,
            comments="comments" in kinds,
            items_key="terms",
            items=rows,
            notes=notes,
            window=window.describe() if window.after is not None else f"all time ({iso(w_after)} to {iso(w_before)})",
            window_epoch={"after": w_after, "before": w_before},
            subreddits=[f"r/{s}" for s in subs],
            searched=where,
            scan_truncated=sampled or bool(failed),
            counts=(
                "SAMPLE counts: mentions, threads and authors count only the sampled part of the window; "
                "estimated_mentions_in_window scales them up (rough)" if sampled
                else "full counts over every archived item listed in the window"
            ),
            items_scanned=scanned,
            coverage=[s.describe() for _, s in scans],
            requests_used=0,
        )
        result["requests_used"] = client.call_requests - sent_before  # HTTP requests, status check included
        return result


_SCAN_FIELDS = {
    "posts": ("id", "subreddit", "author", "created_utc", "title", "selftext", "num_comments"),
    "comments": ("id", "subreddit", "author", "created_utc", "body", "link_id"),
}


@dataclass
class _TermStats:
    mentions: Counter[str] = field(default_factory=Counter)  # kind -> items
    estimated: float = 0.0
    threads: Counter[str] = field(default_factory=Counter)  # thread id -> mentions
    thread_sub: dict[str, str] = field(default_factory=dict)
    thread_example: dict[str, tuple[str, str]] = field(default_factory=dict)  # id -> (permalink, snippet)
    authors: set[str] = field(default_factory=set)

    def add(self, kind: str, item: Mapping[str, Any], scale: float, snippet: str) -> None:
        self.mentions[kind] += 1
        self.estimated += scale
        sub = item.get("subreddit") or ""
        iid = strip_prefix(item.get("id")) or ""
        if kind == "posts":
            thread, link = iid, permalink_post(sub, iid)
        else:
            thread = strip_prefix(item.get("link_id")) or ""
            link = permalink_comment(sub, thread, iid)
        if not thread:
            return
        self.threads[thread] += 1
        self.thread_sub.setdefault(thread, sub)
        self.thread_example.setdefault(thread, (link, snippet))
        author = item.get("author")
        if author and author != "[deleted]":
            self.authors.add(author)

    def top_threads(self, n: int, post_meta: Mapping[str, Mapping[str, Any]]) -> list[str]:
        def key(t: str) -> tuple[int, int]:
            nc = post_meta.get(t, {}).get("num_comments")
            return (-self.threads[t], -(nc if isinstance(nc, int) else 0))

        return sorted(self.threads, key=key)[:n]

    def row(self, term: Term, post_meta: Mapping[str, Mapping[str, Any]], sampled: bool) -> dict[str, Any]:
        total = sum(self.mentions.values())
        examples = []
        for t in self.top_threads(3, post_meta):
            meta = post_meta.get(t, {})
            sub = meta.get("subreddit") or self.thread_sub.get(t, "")
            link, snip = self.thread_example[t]
            examples.append({k: v for k, v in {
                "thread": permalink_post(sub, t),
                "title": meta.get("title"),
                "created_utc": meta.get("created_utc"),
                "created": iso(meta.get("created_utc")),
                "mentions_in_thread": self.threads[t],
                "example": link,
                "snippet": snip,
            }.items() if v is not None})
        out: dict[str, Any] = {
            "term": term.label,
            "mentions": total,
            "in_posts": self.mentions.get("posts", 0),
            "in_comments": self.mentions.get("comments", 0),
            "threads": len(self.threads),
            "authors": len(self.authors),
        }
        if sampled:
            out["estimated_mentions_in_window"] = round(self.estimated)
        out["examples"] = examples
        return out


# ---------------------------------------------------------------- small helpers


def _num(v: Any) -> float | None:
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str) and v.strip().replace(".", "", 1).isdigit():
        return float(v)
    return None


def _wiki_page_name(page: str) -> str:
    """'/r/espresso/wiki/faq', 'www.reddit.com/r/x/wiki/faq/' or 'faq' -> 'faq'."""
    s = (page or "").strip()
    if "://" in s:
        s = urlsplit(s).path
    s = re.sub(r"^/?r/[^/]+/wiki/?", "", s, flags=re.I)
    s = re.sub(r"^/?wiki/", "", s, flags=re.I).strip("/")
    if not s:
        return "index"
    if not re.fullmatch(r"[A-Za-z0-9_./-]{1,200}", s) or ".." in s:
        raise InputError(f"not a wiki page name: {page!r}")
    return s


_SHARE = re.compile(r"^/?((?:r|u|user)/[^/\s?#]+/s/[A-Za-z0-9]+)/?$")


def _share_path(value: str) -> str | None:
    """'www.reddit.com/r/running/s/0MH2aME2Z9?x=1' -> '/r/running/s/0MH2aME2Z9'.
    Case is kept: the archive matches share paths case-sensitively."""
    s = (value or "").strip()
    if "reddit.com" in s.lower():
        u = urlsplit(s if "://" in s else "https://" + s)
        host = (u.hostname or "").lower()
        if not (host == "reddit.com" or host.endswith(".reddit.com")):
            return None
        s = u.path
    else:
        s = s.split("?", 1)[0].split("#", 1)[0]
    m = _SHARE.match(s)
    return "/" + m.group(1) if m else None


# What find_subreddits asks for. The archive refuses `title`, `subreddit_type` and `_meta` in
# fields= (probed 2026-11-21), so archived totals come only from subreddit_info's full object.
FIND_SUB_FIELDS = ("display_name", "subscribers", "retrieved_on", "over18", "created_utc", "public_description")


def _shape_sub(sub: Mapping[str, Any], *, matched: str | None = None, full: bool = False) -> dict[str, Any]:
    name = sub.get("display_name") or ""
    meta = sub.get("_meta") if isinstance(sub.get("_meta"), Mapping) else {}
    desc, cut = trim_text(html.unescape(str(sub.get("public_description") or "")), 300)
    out: dict[str, Any] = {
        "name": f"r/{name}",
        "link": _sub_link(name),
        "title": sub.get("title"),
        "subscribers": sub.get("subscribers"),
        "subscribers_as_of": (iso(sub.get("retrieved_on")) or "")[:10] or None,
        "nsfw": True if sub.get("over18") else None,
        "type": sub.get("subreddit_type") if sub.get("subreddit_type") not in (None, "public") else None,
        "created": (iso(sub.get("created_utc")) or "")[:10] or None,
        "public_description": desc or None,
        "archived_posts": meta.get("num_posts"),
        "archived_comments": meta.get("num_comments"),
        "matched": matched,
    }
    if full:
        side, side_cut = trim_text(html.unescape(str(sub.get("description") or "")), 2000)
        out["sidebar"] = side or None
        out["sidebar_truncated"] = True if side_cut else None
        out["public_description_truncated"] = True if cut else None
    return {k: v for k, v in out.items() if v is not None}
