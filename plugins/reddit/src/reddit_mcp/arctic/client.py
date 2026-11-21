"""The Arctic Shift HTTP client. Every request the server makes goes through `ArcticShiftClient`.

What it enforces, with the rule IDs from `reports/Keyless Reddit MCP sources.md`:

- D1/E5: only the configured archive and status hosts, never a Reddit host.
- R1/R2: one request in flight, at least `min_interval` seconds between requests.
- R3: `fields=` is required on post/comment search and ids calls, and only whitelisted names pass.
- R4: `limit` is at most 100 (1000 on `subreddits/search` and `users/search`).
- R5: `get_batched` / `get_ids` split large inputs into calls of the documented size.
- R6: a descriptive User-Agent.
- R7: a SQLite response cache; final data is immutable, the rest has a TTL.
- T5: keyword search without a subreddit/author scope is rejected before any network call.
- T8: relative date offsets (`3m`, `2d`) are never sent; only epoch seconds.
- E1: 429 waits for the reset (at most 65 s) and retries once.
- E2: 422 retries at most twice, 1-3 s apart, halving `limit` each time.
- E3: 5xx / 52x / DNS / timeout -> `ArchiveUnavailable`, with the status feed's verdict.
- E4: 400 -> `QueryRejected` with the archive's error text verbatim.
"""

from __future__ import annotations

import asyncio
import contextlib
import contextvars
import json
import time
from collections.abc import Awaitable, Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

import httpx

from .cache import NullCache, ResponseCache, open_cache
from .config import Settings, is_forbidden_host
from .errors import (
    ArchiveUnavailable,
    Attempt,
    ComponentStatus,
    InputError,
    QueryRejected,
    QueryTooHeavy,
    RateLimited,
)

# --- R3: the fields= whitelist (issue #85). Any other name is HTTP 400. ---
COMMON_FIELDS = frozenset(
    {
        "author",
        "author_fullname",
        "author_flair_text",
        "created_utc",
        "distinguished",
        "id",
        "retrieved_on",
        "subreddit",
        "subreddit_id",
        "score",
    }
)
POST_FIELDS = COMMON_FIELDS | {
    "crosspost_parent",
    "link_flair_text",
    "num_comments",
    "over_18",
    "post_hint",
    "selftext",
    "spoiler",
    "title",
    "url",
}
COMMENT_FIELDS = COMMON_FIELDS | {"body", "link_id", "parent_id"}
# Subreddit objects. Probed on 2026-11-21 (docs/probes.md, Session 5): the archive refuses
# `title`, `subreddit_type` and `_meta` with HTTP 400; these pass. A full object is about 9 KB,
# mostly the sidebar `description`; these fields are about 0.4 KB.
SUBREDDIT_FIELDS = frozenset(
    {"created_utc", "display_name", "id", "over18", "public_description", "retrieved_on", "subscribers"}
)
# Only in full objects (request with full=True): permalink, upvote_ratio, controversiality,
# domain, is_self, removed_by_category, _meta.
FULL_ONLY_FIELDS = frozenset(
    {"permalink", "upvote_ratio", "controversiality", "domain", "is_self", "removed_by_category", "_meta"}
)

DEFAULT_POST_FIELDS = (
    "id",
    "subreddit",
    "author",
    "created_utc",
    "retrieved_on",
    "score",
    "num_comments",
    "title",
    "selftext",
    "link_flair_text",
    "over_18",
    "url",
)
DEFAULT_COMMENT_FIELDS = (
    "id",
    "subreddit",
    "author",
    "created_utc",
    "retrieved_on",
    "score",
    "body",
    "link_id",
    "parent_id",
)

# --- R4/R5: documented limits. ---
MAX_LIMIT = 100
# These two search paths accept up to 1000 (Arctic Shift API docs; Session 4 probes).
BIG_LIMIT_PATHS = {"subreddits/search": 1000, "users/search": 1000}
IDS_BATCH = 500
SHORT_LINKS_BATCH = 1000
RULES_BATCH = 1000
WIKI_PATHS_BATCH = 100

# Paths where fields= is required, and which whitelist applies.
_FIELDS_REQUIRED = {
    "posts/search": POST_FIELDS,
    "posts/ids": POST_FIELDS,
    "comments/search": COMMENT_FIELDS,
    "comments/ids": COMMENT_FIELDS,
}
_KEYWORD_PARAMS = ("query", "title", "selftext", "body")
_SCOPE_PARAMS = ("subreddit", "author", "link_id", "parent_id")

# R7: data older than this cannot change in the archive any more.
FINAL_AGE = 72 * 3600


class RequestCounter:
    """HTTP requests sent during one tool call (see `ArcticShiftClient.count_requests`)."""

    __slots__ = ("n",)

    def __init__(self) -> None:
        self.n = 0


# Each MCP tool call runs in its own asyncio task with its own copy of the context, so a counter
# set here belongs to one call only: parallel calls do not count each other's requests.
_CALL_COUNTER: contextvars.ContextVar[RequestCounter | None] = contextvars.ContextVar(
    "reddit_mcp_call_counter", default=None
)


@dataclass
class ArchiveResponse:
    """What `get` returns. `params` is what was actually sent (after any 422 narrowing)."""

    data: Any
    params: dict[str, Any]
    path: str
    status: int = 200
    elapsed: float = 0.0
    from_cache: bool = False
    attempts: list[Attempt] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def narrowed(self) -> bool:
        return len(self.attempts) > 1


def _encode(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple, set, frozenset)):
        return ",".join(str(v) for v in value)
    return str(value)


def _is_epoch(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    return isinstance(value, str) and value.isdigit()


def item_is_final(item: Mapping[str, Any], now: float) -> bool:
    """True when the archive will never change this item again (R7)."""
    meta = item.get("_meta")
    if isinstance(meta, Mapping) and meta.get("retrieved_2nd_on"):
        return True
    created = item.get("created_utc")
    return isinstance(created, (int, float)) and now - created > FINAL_AGE


class ArcticShiftClient:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        cache: ResponseCache | NullCache | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
        wall: Callable[[], float] = time.time,
    ):
        self.settings = settings or Settings.from_env()
        if cache is None:
            path = self.settings.cache_path
            cache = open_cache(path, ttl=self.settings.cache_ttl,
                               max_bytes=int(self.settings.cache_max_mb * 1024 * 1024))
        self.cache = cache
        self._sleep = sleep
        self._clock = clock
        self._wall = wall
        self._http = httpx.AsyncClient(
            transport=transport,
            timeout=self.settings.timeout,
            headers={"User-Agent": self.settings.user_agent, "Accept": "application/json"},
            follow_redirects=False,
        )
        self._lock = asyncio.Lock()
        self._last_done: float | None = None
        self._blocked_until = 0.0  # after a 429, no request goes out before this (E1)
        self.request_count = 0  # real HTTP requests sent by this client in all (not cache hits)
        self._status_cache: tuple[float, dict[str, Any]] | None = None

    async def aclose(self) -> None:
        await self._http.aclose()
        self.cache.close()

    # ------------------------------------------------------------------ clock and counters

    def now(self) -> float:
        """Wall-clock epoch seconds. Tools use this (not time.time()) so tests run on a fake clock."""
        return float(self._wall())

    async def sleep(self, seconds: float) -> None:
        """Sleep with the client's sleep function (instant in tests)."""
        await self._sleep(max(0.0, float(seconds)))

    @staticmethod
    @contextlib.contextmanager
    def count_requests() -> Iterator[RequestCounter]:
        """Count the HTTP requests sent inside this block, by this task and the tasks it starts.

        `archive_tool` opens one for every tool call, so `call_requests` is per call."""
        counter = RequestCounter()
        token = _CALL_COUNTER.set(counter)
        try:
            yield counter
        finally:
            _CALL_COUNTER.reset(token)

    @property
    def call_requests(self) -> int:
        """HTTP requests sent so far in the current tool call (status checks and retries
        included, cache hits not). Outside a tool call it is the client-wide `request_count`."""
        counter = _CALL_COUNTER.get()
        return counter.n if counter is not None else self.request_count

    # ------------------------------------------------------------------ public API

    async def get(
        self,
        path: str,
        params: Mapping[str, Any] | None = None,
        *,
        fields: Iterable[str] | None = None,
        full: bool = False,
        retry_422: int = 2,
        use_cache: bool = True,
        ttl: float | None = None,
    ) -> ArchiveResponse:
        """GET `<base_url>/<path>` and return the `data` member of the JSON body.

        - `fields`: names to request (R3). Required for post/comment search and ids calls
          unless `full=True` asks for full objects on purpose.
        - `retry_422`: how many 422 retries (0-2). Each retry halves `limit`.
        - `ttl`: cache lifetime for data that is not final; `None` uses the default.
        """
        path = path.strip("/")
        sent = self._prepare_params(path, params or {}, fields, full)
        retry_422 = max(0, min(2, retry_422))
        url = f"{self.settings.base_url}/{path}"

        key = self.cache.key(url, sent)
        if use_cache:
            hit = self.cache.get(key)
            if hit is not None:
                return ArchiveResponse(data=json.loads(hit), params=sent, path=path, from_cache=True)

        attempts: list[Attempt] = []
        notes: list[str] = []
        current = dict(sent)
        last_error: str | None = None
        for i in range(retry_422 + 1):
            resp, attempt = await self._send(url, current)
            attempts.append(attempt)
            if resp.status_code == 422:
                last_error = _error_text(resp)
                fast = all(a.elapsed < 1.0 for a in attempts)
                if i == retry_422:
                    raise QueryTooHeavy(
                        attempts=attempts, suggestions=_suggestions(path, current, fast=fast), error=last_error
                    )
                before = current.get("limit", 25)
                current = _halve_limit(current)
                notes.append(f"HTTP 422; retried with limit {before} -> {current['limit']}")
                # A fast 422 is load shedding, not a syntax verdict (docs/probes.md, Q7):
                # wait the longest gap E2 allows.
                await self._sleep(3.0 if attempt.elapsed < 1.0 else self.settings.retry_delay_422)
                continue
            data = self._parse_ok(resp, attempts)
            immutable = self._is_immutable(path, current, data)
            if use_cache:
                # Stored under the params actually sent only: a narrowed answer (smaller limit) must
                # never stand in for the full one, or a short page would read as the end of a window.
                self.cache.put(self.cache.key(url, current), json.dumps(data), immutable=immutable, ttl=ttl)
            return ArchiveResponse(
                data=data,
                params=current,
                path=path,
                status=resp.status_code,
                elapsed=attempt.elapsed,
                attempts=attempts,
                notes=notes,
            )
        raise AssertionError("unreachable")  # pragma: no cover

    async def get_batched(
        self,
        path: str,
        param: str,
        values: Sequence[str],
        batch_size: int,
        params: Mapping[str, Any] | None = None,
        **kw: Any,
    ) -> list[Any]:
        """R5: call `path` once per `batch_size` values of `param` and join the `data` lists."""
        out: list[Any] = []
        seen: set[str] = set()
        unique = [v for v in values if not (v in seen or seen.add(v))]
        for start in range(0, len(unique), batch_size):
            chunk = unique[start : start + batch_size]
            resp = await self.get(path, {**(params or {}), param: ",".join(chunk)}, **kw)
            data = resp.data
            if isinstance(data, list):
                out.extend(data)
            elif data is not None:
                out.append(data)
        return out

    async def get_ids(
        self, kind: str, ids: Sequence[str], *, fields: Iterable[str] | None = None, full: bool = False
    ) -> list[dict[str, Any]]:
        """`posts/ids` or `comments/ids` for any number of IDs, 500 per call (R5).

        `kind` is "posts" or "comments". IDs may carry a t3_/t1_ prefix.
        """
        if kind not in {"posts", "comments"}:
            raise InputError(f"kind must be 'posts' or 'comments', not {kind!r}")
        bare = [i.split("_", 1)[1] if i[:3] in {"t1_", "t3_"} else i for i in ids]
        return await self.get_batched(f"{kind}/ids", "ids", bare, IDS_BATCH, fields=fields, full=full)

    async def status(self, *, max_age: float = 60.0) -> dict[str, Any]:
        """The raw status feed (`status_url`), cached in memory for `max_age` seconds.

        Raises `ArchiveUnavailable` (with `status_error`) when the feed cannot be read.
        """
        now = self.now()
        if self._status_cache and now - self._status_cache[0] < max_age:
            return self._status_cache[1]
        try:
            resp, attempt = await self._send(self.settings.status_url, {})
        except ArchiveUnavailable as e:
            raise ArchiveUnavailable(
                "the status feed could not be reached", status_error=e.cause, attempts=e.attempts
            ) from e
        if resp.status_code != 200:
            raise ArchiveUnavailable(
                "the status feed failed", status_error=f"HTTP {resp.status_code}", attempts=[attempt]
            )
        try:
            body = resp.json()
        except ValueError:
            raise ArchiveUnavailable(
                "the status feed failed", status_error="not JSON", attempts=[attempt]
            ) from None
        self._status_cache = (now, body)
        return body

    # ------------------------------------------------------------------ internals

    def _prepare_params(
        self, path: str, params: Mapping[str, Any], fields: Iterable[str] | None, full: bool
    ) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, v in params.items():
            if v is None:
                continue
            out[k] = _encode(v)
        if "fields" in out:
            raise InputError("pass fields with the fields= argument, not in params")

        whitelist = _FIELDS_REQUIRED.get(path)
        if fields is not None:
            names = [f.strip() for f in fields if f and f.strip()]
            if path == "subreddits/search":
                allowed = SUBREDDIT_FIELDS
            else:
                allowed = whitelist or (POST_FIELDS | COMMENT_FIELDS)
            bad = [n for n in names if n not in allowed]
            if bad:
                hint = " (only in full objects: request full=True)" if set(bad) & FULL_ONLY_FIELDS else ""
                raise InputError(f"fields not allowed for {path}: {', '.join(bad)}{hint}")
            out["fields"] = ",".join(dict.fromkeys(names))
        elif whitelist is not None and not full:
            raise InputError(f"{path} needs fields= (R3), or full=True for full objects")

        # R4
        if "limit" in out:
            if out["limit"] == "auto":
                raise InputError("limit=auto is not used; pass a number up to 100")
            try:
                n = int(out["limit"])
            except ValueError:
                raise InputError(f"limit must be a number, not {out['limit']!r}") from None
            cap = BIG_LIMIT_PATHS.get(path, MAX_LIMIT)
            if path.endswith("/search") and not 1 <= n <= cap:
                raise InputError(f"limit must be 1-{cap}")

        # T8: only absolute epoch seconds go out.
        for k in ("after", "before"):
            if k in out and not _is_epoch(out[k]):
                raise InputError(
                    f"{k}={out[k]!r} is not epoch seconds; convert it with helpers.to_epoch() first"
                )

        # T5: no global keyword search.
        if path in ("posts/search", "comments/search") and any(k in out for k in _KEYWORD_PARAMS):
            if not any(out.get(k) for k in _SCOPE_PARAMS):
                raise InputError(
                    "keyword search needs a subreddit or author: the archive has no Reddit-wide search"
                )
        return out

    def _check_url(self, url: str) -> None:
        host = (urlsplit(url).hostname or "").lower()
        if is_forbidden_host(host) or host not in self.settings.allowed_hosts:
            raise InputError(f"refusing to contact {host!r}: only the archive hosts are allowed")

    async def _send(self, url: str, params: dict[str, Any]) -> tuple[httpx.Response, Attempt]:
        """One paced request, with the E1 wait-and-retry-once. Raises ArchiveUnavailable (E3)."""
        self._check_url(url)
        resp, attempt = await self._paced(url, params)
        if resp.status_code == 429:
            self._blocked_until = self._clock() + self._rate_limit_wait(resp)
            resp, attempt2 = await self._paced(url, params)
            if resp.status_code == 429:
                wait = self._rate_limit_wait(resp)
                self._blocked_until = self._clock() + wait  # the next call waits too (E1)
                raise RateLimited(wait, attempts=[attempt, attempt2])
            attempt = attempt2
        if resp.status_code >= 500:  # includes Cloudflare 52x and 530 (error 1033)
            await self._raise_unavailable(f"HTTP {resp.status_code}", [attempt], url)
        return resp, attempt

    async def _paced(self, url: str, params: dict[str, Any]) -> tuple[httpx.Response, Attempt]:
        async with self._lock:
            ready = max(
                self._blocked_until,
                self._last_done + self.settings.min_interval if self._last_done is not None else 0.0,
            )
            wait = ready - self._clock()
            if wait > 0:
                await self._sleep(wait)
            start = self._clock()
            self.request_count += 1
            counter = _CALL_COUNTER.get()
            if counter is not None:
                counter.n += 1
            try:
                resp = await self._http.get(url, params=params)
            except httpx.TimeoutException as e:
                attempt = Attempt(params, None, self._clock() - start, f"timeout: {e.__class__.__name__}")
                self._last_done = self._clock()
                cause = f"no answer within {self.settings.timeout:.0f} s"
            except httpx.TransportError as e:
                attempt = Attempt(params, None, self._clock() - start, f"{e.__class__.__name__}: {e}")
                self._last_done = self._clock()
                cause = f"could not connect ({e.__class__.__name__}: {e})"
            else:
                self._last_done = self._clock()
                return resp, Attempt(params, resp.status_code, self._last_done - start)
        if url == self.settings.status_url:
            raise ArchiveUnavailable(cause, status_error=cause, attempts=[attempt])
        await self._raise_unavailable(cause, [attempt], url)
        raise AssertionError("unreachable")  # pragma: no cover

    async def _raise_unavailable(self, cause: str, attempts: list[Attempt], url: str) -> None:
        if url == self.settings.status_url:
            raise ArchiveUnavailable(cause, status_error=cause, attempts=attempts)
        try:
            body = await self.status(max_age=30.0)
        except ArchiveUnavailable as e:
            raise ArchiveUnavailable(cause, status_error=e.status_error, attempts=attempts) from None
        raise ArchiveUnavailable(cause, components=parse_components(body), attempts=attempts)

    def _rate_limit_wait(self, resp: httpx.Response) -> float:
        cap = self.settings.max_rate_limit_wait
        reset_at = resp.headers.get("x-ratelimit-reset-at")
        reset = resp.headers.get("x-ratelimit-reset")
        wait: float | None = None
        if reset_at:
            try:
                wait = float(reset_at) / 1000.0 - self._wall()
            except ValueError:
                wait = None
        if wait is None and reset:
            try:
                wait = float(reset)
            except ValueError:
                wait = None
        if wait is None:
            wait = 60.0
        return max(1.0, min(cap, wait))

    def _parse_ok(self, resp: httpx.Response, attempts: list[Attempt]) -> Any:
        if resp.status_code >= 400:
            raise QueryRejected(_error_text(resp), status=resp.status_code, attempts=attempts)
        try:
            body = resp.json()
        except ValueError:
            raise ArchiveUnavailable(
                f"HTTP {resp.status_code} with a body that is not JSON", attempts=attempts
            ) from None
        if isinstance(body, dict):
            if body.get("error"):
                raise QueryRejected(str(body["error"]), status=resp.status_code, attempts=attempts)
            return body.get("data")
        return body

    def _is_immutable(self, path: str, params: Mapping[str, Any], data: Any) -> bool:
        now = self.now()
        if not isinstance(data, list) or not data:
            return False
        if not all(isinstance(x, Mapping) and item_is_final(x, now) for x in data):
            return False
        if path.endswith("/ids"):
            # Final only when every ID asked for came back: a missing one may be backfilled later.
            asked = {i for i in str(params.get("ids", "")).split(",") if i}
            got = {str(x.get("id")) for x in data if isinstance(x, Mapping)}
            return bool(asked) and asked <= got
        if path in ("posts/search", "comments/search"):
            before = params.get("before")
            return before is not None and _is_epoch(before) and now - float(before) > FINAL_AGE
        return False


def _error_text(resp: httpx.Response) -> str:
    try:
        body = resp.json()
    except ValueError:
        return resp.text.strip()[:500] or f"HTTP {resp.status_code}"
    if isinstance(body, dict) and body.get("error"):
        return str(body["error"])
    return json.dumps(body)[:500]


def _halve_limit(params: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(params)
    try:
        n = int(out.get("limit", 25))
    except ValueError:
        n = 25
    out["limit"] = str(max(1, n // 2))
    return out


def _suggestions(path: str, params: Mapping[str, Any], *, fast: bool = False) -> list[str]:
    s: list[str] = []
    if fast:
        s.append("the archive answered at once, which means it is busy rather than that the query is invalid: wait 10 s or more before another keyword query")
    if "after" not in params or "before" not in params:
        s.append("add a narrower date window (after and before)")
    else:
        s.append("halve the date window")
    if any(k in params for k in ("query", "selftext", "body")):
        s.append("search the title only, or use one distinctive keyword")
    elif "title" in params:
        s.append("use one distinctive keyword")
    if "subreddit" not in params and "author" not in params:
        s.append("add a subreddit or author")
    s.append("list the window without a keyword and filter it locally")
    return s


def parse_components(body: Any) -> list[ComponentStatus]:
    """Turn the status feed into a list of components (api, archiver, ...)."""
    items: list[tuple[str, Any]] = []
    if isinstance(body, Mapping):
        src = body.get("components", body)
        if isinstance(src, Mapping):
            items = list(src.items())
        elif isinstance(src, list):
            items = [(str(c.get("name", i)), c) for i, c in enumerate(src) if isinstance(c, Mapping)]
    out = []
    for name, comp in items:
        if not isinstance(comp, Mapping):
            continue
        avail = comp.get("isAvailable")
        out.append(
            ComponentStatus(
                name=name,
                is_available=avail if isinstance(avail, bool) else None,
                failed_at=comp.get("failedAt"),
                raw=dict(comp),
            )
        )
    return out
