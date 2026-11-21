"""Session 2: list_posts, search_posts, deep_search, get_posts.

Only Session 2 edits this file (plus its tests under tests/posts/ and its eval cases).
Import shared code from `reddit_mcp.arctic`; do not change it. See docs/architecture.md.

Rules from `reports/Keyless Reddit MCP sources.md` that this module carries:

- T1: `new`/`old` are the archive's own order, paged by `created_utc` and de-duplicated by `id`.
- T2/T3: `top`, `comments` and `controversial` are computed here over a bounded window; the
  result states the window and the scan size. Scores younger than ~36 h are never ranked.
- T4/T5: hot, relevance, r/all and global keyword search are refused with a clear message.
- T6: a keyword search that the archive rejects with 422 falls back to a labelled local scan.
- T7: Reddit operators (`author:`, `title:`, `flair:`, `nsfw:`, `url:`, `site:`, `self:`, `NOT`, ...)
  map to archive parameters or local filters. The archive gets one keyword or quoted phrase;
  AND, OR and `-exclude` are applied here (docs/probes.md, Q1 and Q6).
- T8: every time filter becomes absolute epoch seconds (`resolve_window`).
"""

from __future__ import annotations

import difflib
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from fastmcp.exceptions import ToolError
from pydantic import Field

from ..arctic import (
    DEFAULT_COMMENT_FIELDS,
    DEFAULT_POST_FIELDS,
    MAX_LIMIT,
    POST_TEXT_CHARS,
    ArcticShiftClient,
    InputError,
    QueryTooHeavy,
    Window,
    archive_tool,
    iso,
    make_result,
    parse_post_ref,
    permalink_comment,
    resolve_window,
    shape_post,
    strip_prefix,
    unavailable_feature,
)
from ..context import ServerContext

# ---------------------------------------------------------------- constants

# Reddit opened in June 2005; nothing in the archive is older.
ARCHIVE_START = 1117584000  # 2005-06-01 00:00 UTC
# Scores and num_comments are the first value (1 or 0) until the second pass at ~36 h (T3).
SCORE_FINAL_AGE = 36 * 3600
PAGE = MAX_LIMIT  # 100 items per page (R4)

# A scan for a computed sort does not need the body text.
SCAN_FIELDS = tuple(f for f in DEFAULT_POST_FIELDS if f != "selftext")
LIST_FIELDS = DEFAULT_POST_FIELDS

NATIVE_SORTS = {"new": "desc", "old": "asc"}
COMPUTED_SORTS = ("top", "comments", "controversial")
REFUSED_SORTS = {"hot", "rising", "best", "confidence", "relevance", "qa", "live"}
LIVE_FEEDS = {"all": "r/all", "popular": "r/popular", "frontpage": "front page", "home": "front page"}

MAX_SUBREDDITS = 10
DEFAULT_SCAN_PAGES = 10
MAX_SCAN_PAGES = 30
DEFAULT_SEARCH_PAGES = 5
MAX_IDS = 2000
MAX_TEXT_CHARS = 15000  # one post must still fit the 8,000-token result budget
LIST_TEXT_CHARS = 300

# deep_search
FAST_422_WAIT = 10.0  # docs/probes.md, Q7
MAX_422_WAIT = 60.0
MAX_TOTAL_WAIT = 360.0  # stop a deep_search that has waited this long on a busy archive  # the wait doubles after each fast 422 in a row (docs/deep-search.md)
MIN_WINDOW = 86400  # do not halve a window below one day
MAX_FAILED_WINDOWS = 3  # skipped windows in a row before a step gives up
FUZZY_RATIO = 0.85
DEEP_TEXT_CHARS = 300
MAX_ANCHORS = 4  # distinct terms of the anchor group sent to the archive, in turn

_SUB_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_]{1,20}$")
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    "a an and are as at be but by for from has have how i in is it my of on or so that the this to "
    "was what when where which who why with you your".split()
)


def _now(client: ArcticShiftClient) -> float:
    """The client's wall clock (a fake one in tests)."""
    return client.now()


async def _sleep(client: ArcticShiftClient, seconds: float) -> None:
    """The client's sleep (instant in tests)."""
    await client.sleep(seconds)


# ---------------------------------------------------------------- input checks


def _clean_subs(subreddits: Iterable[str] | str | None) -> list[str]:
    """'r/buildapc', '/r/Intel/', 'a+b', 'a, b' -> ['buildapc', 'Intel', 'a', 'b'].

    r/all, r/popular and the front page are live feeds: refused (T4).
    """
    if subreddits is None:
        return []
    raw = [subreddits] if isinstance(subreddits, str) else list(subreddits)
    out: list[str] = []
    seen: set[str] = set()
    for entry in raw:
        for part in re.split(r"[+,\s]+", str(entry).strip()):
            s = part.strip().strip("/")
            if not s:
                continue
            if "/r/" in f"/{s}":
                s = f"/{s}".split("/r/", 1)[1].split("/", 1)[0]
            if s.lower() in LIVE_FEEDS:
                raise ToolError(unavailable_feature(LIVE_FEEDS[s.lower()]))
            if not _SUB_RE.match(s):
                raise InputError(f"{part!r} is not a subreddit name")
            if s.lower() not in seen:
                seen.add(s.lower())
                out.append(s)
    if len(out) > MAX_SUBREDDITS:
        raise InputError(f"at most {MAX_SUBREDDITS} subreddits per call")
    return out


def _check_sort(sort: str) -> str:
    s = (sort or "new").strip().lower()
    if s in REFUSED_SORTS:
        raise ToolError(unavailable_feature("best" if s == "confidence" else s))
    if s not in NATIVE_SORTS and s not in COMPUTED_SORTS:
        raise InputError(f"sort must be one of new, old, top, comments, controversial; not {sort!r}")
    return s


def _check_limit(limit: int, top: int = MAX_LIMIT) -> int:
    if not isinstance(limit, int) or not 1 <= limit <= top:
        raise InputError(f"limit must be 1-{top}")
    return limit


def _check_pages(pages: int, top: int = MAX_SCAN_PAGES) -> int:
    if not isinstance(pages, int) or not 1 <= pages <= top:
        raise InputError(f"max_pages must be 1-{top}")
    return pages


def _check_text_chars(n: int) -> int:
    if not isinstance(n, int) or not 0 <= n <= MAX_TEXT_CHARS:
        raise InputError(f"text_chars must be 0-{MAX_TEXT_CHARS}")
    return n


def _unfinal_refusal(sort: str, window: Window, now: float) -> None:
    """T3: a score ranking over posts that are all younger than ~36 h is meaningless."""
    if window.after is not None and now - window.after <= SCORE_FINAL_AGE:
        what = "comment counts" if sort == "comments" else "scores"
        raise ToolError(
            f"scores not final: sort={sort!r} over {window.label or window.describe()} cannot be ranked. "
            f"Every post in that window is younger than about 36 hours, and the archive keeps the "
            f"{what} it saw at posting time (usually 1 or 0) until its second pass at about 36 h. "
            "A ranking would be by noise. Instead: list the posts with sort='new' (no ranking), use a "
            "window that ends at least 2 days ago, or rank by recent comment activity if a tool for "
            "that is available. The archive has no live scores."
        )


# ---------------------------------------------------------------- shaping


def _shape(item: Mapping[str, Any], now: float, text_chars: int) -> dict[str, Any]:
    post = shape_post(item, now=now, text_chars=max(text_chars, 1))
    if text_chars == 0:
        post.pop("selftext", None)
        post.pop("truncated", None)
    return post


def _created(item: Mapping[str, Any]) -> int:
    c = item.get("created_utc")
    return int(c) if isinstance(c, (int, float)) else 0


def _is_final(item: Mapping[str, Any], now: float) -> bool:
    meta = item.get("_meta")
    if isinstance(meta, Mapping) and meta.get("retrieved_2nd_on"):
        return True
    return now - _created(item) >= SCORE_FINAL_AGE


def _controversy(item: Mapping[str, Any]) -> float:
    """Reddit's controversy formula, magnitude ** balance, on votes estimated from score and
    upvote_ratio (the archive has no real down votes)."""
    ratio = item.get("upvote_ratio")
    score = item.get("score")
    if not isinstance(ratio, (int, float)) or not isinstance(score, (int, float)):
        return 0.0
    r = min(1.0, max(0.0, float(ratio)))
    if abs(2 * r - 1) < 0.02:
        total = max(abs(float(score)), 1.0) / 0.02
    else:
        total = abs(float(score) / (2 * r - 1))
    ups, downs = r * total, (1 - r) * total
    if ups <= 0 or downs <= 0:
        return 0.0
    balance = downs / ups if ups > downs else ups / downs
    return (ups + downs) ** balance


_RANK = {
    "top": lambda p: (p.get("score") or 0, p.get("num_comments") or 0),
    "comments": lambda p: (p.get("num_comments") or 0, p.get("score") or 0),
    "controversial": lambda p: (_controversy(p), p.get("num_comments") or 0),
}


# ---------------------------------------------------------------- paging (T1)


@dataclass
class Walk:
    """What one paged walk over one subreddit saw."""

    subreddit: str
    items: list[dict[str, Any]] = field(default_factory=list)
    pages: int = 0
    exhausted: bool = False  # reached the end of the window
    reached: int | None = None  # oldest (desc) or newest (asc) created_utc seen
    scanned: int = 0  # items the archive returned (before local filtering)


def _next_cursor(page: list[Mapping[str, Any]], order: str, new_ids: int) -> int:
    """The next `before` (desc) or `after` (asc). Several items can share a second, so the
    cursor stays on the last second (and de-duplication drops repeats) unless a whole page
    brought nothing new."""
    last = _created(page[-1])
    if order == "desc":
        return last + 1 if new_ids else last
    return last - 1 if new_ids else last


async def _walk(
    client: ArcticShiftClient,
    params: Mapping[str, Any],
    window: Window,
    *,
    order: str,
    fields: Sequence[str] | None,
    full: bool = False,
    max_pages: int,
    want: int | None = None,
    keep: Any = None,
    seen: set[str] | None = None,
    retry_422: int = 2,
) -> Walk:
    """Page `posts/search` through `window` in `order` ('desc' or 'asc').

    Stops at the end of the window, after `max_pages` pages, or once `want` items passed `keep`.
    Raises the client's errors, with the items so far on `exc.partial_walk`.
    """
    walk = Walk(subreddit=str(params.get("subreddit", "")))
    seen = set() if seen is None else seen
    after, before = window.after, window.before
    while walk.pages < max_pages:
        p = {**params, "sort": order, "limit": PAGE, "after": after, "before": before}
        try:
            resp = await client.get("posts/search", p, fields=fields, full=full, retry_422=retry_422)
        except Exception as e:  # noqa: BLE001 - re-raised with what was gathered
            e.partial_walk = walk  # type: ignore[attr-defined]
            raise
        walk.pages += 1
        page = [x for x in (resp.data or []) if isinstance(x, Mapping)]
        fresh = [x for x in page if strip_prefix(x.get("id")) not in seen]
        walk.scanned += len(fresh)
        for x in fresh:
            seen.add(strip_prefix(x.get("id")))
            if keep is None or keep(x):
                walk.items.append(dict(x))
        if page:
            walk.reached = _created(page[-1])
        full_page = len(page) >= int(resp.params.get("limit", PAGE))
        if not page or not full_page:
            walk.exhausted = True
            break
        if want is not None and len(walk.items) >= want:
            break
        cursor = _next_cursor(page, order, len(fresh))
        if order == "desc":
            before = cursor
        else:
            after = cursor
    return walk


# ---------------------------------------------------------------- bounded scan (T2)


@dataclass
class Scan:
    subreddit: str
    items: list[dict[str, Any]] = field(default_factory=list)
    pages: int = 0
    complete: bool = False
    method: str = "every post in the window"
    estimated_total: int | None = None
    reached: int | None = None


async def _scan(
    client: ArcticShiftClient,
    sub: str,
    window: Window,
    *,
    now: float,
    pages: int,
    fields: Sequence[str] | None,
    full: bool,
    extra: Mapping[str, Any] | None = None,
) -> Scan:
    """Fetch posts of `sub` in `window` for a client-side ranking, within `pages` requests.

    1. One page, newest first. If it is not full, the window is complete.
    2. From that page's time span, estimate the posts in the window.
    3. If the rest fits in the budget, walk it. If not, cut the rest of the window into equal
       slices and take the newest page of each, so the sample covers the whole window rather
       than only its newest days.
    """
    base = {k: v for k, v in {"subreddit": sub, **(extra or {})}.items() if v is not None and v != ""}
    lo = window.after if window.after is not None else ARCHIVE_START
    hi = window.before if window.before is not None else int(now)
    scan = Scan(subreddit=sub)
    seen: set[str] = set()
    first = await _walk(client, base, Window(lo, hi, ""), order="desc", fields=fields, full=full,
                        max_pages=1, seen=seen)
    scan.items, scan.pages, scan.reached = first.items, first.pages, first.reached
    if first.exhausted or not first.items:
        scan.complete = True
        scan.estimated_total = len(scan.items)
        return scan
    oldest = first.reached or hi
    span = max(1, hi - oldest)
    scan.estimated_total = int(len(first.items) * (hi - lo) / span)
    left = pages - 1
    if left <= 0:
        scan.method = f"only the newest {len(scan.items)} posts (page budget 1)"
        return scan
    remaining_pages = (scan.estimated_total - len(scan.items)) / PAGE
    if remaining_pages <= left:
        rest = await _walk(client, base, Window(lo, oldest + 1, ""), order="desc", fields=fields,
                           full=full, max_pages=left, seen=seen)
        scan.items += rest.items
        scan.pages += rest.pages
        scan.reached = rest.reached or scan.reached
        scan.complete = rest.exhausted
        if not scan.complete:
            scan.method = f"the newest {len(scan.items)} posts, back to {iso(scan.reached)}"
        return scan
    # Spread the budget evenly across the rest of the window.
    step = (oldest - lo) / left
    for i in range(left):
        s_hi = int(oldest - i * step)
        s_lo = int(oldest - (i + 1) * step)
        part = await _walk(client, base, Window(s_lo, s_hi, ""), order="desc", fields=fields,
                           full=full, max_pages=1, seen=seen)
        scan.items += part.items
        scan.pages += part.pages
    scan.reached = lo
    scan.method = (
        f"a sample: the newest {len(first.items)} posts, then the newest page of each of {left} "
        f"equal slices of the rest of the window"
    )
    return scan


def _scan_report(scans: list[Scan], window: Window, ranked: int, excluded: int) -> dict[str, Any]:
    est = sum(s.estimated_total or 0 for s in scans)
    scanned = sum(len(s.items) for s in scans)
    complete = all(s.complete for s in scans)
    return {
        "method": "ranked on the client: the archive sorts by time only",
        "window": window.describe(),
        "posts_scanned": scanned,
        "pages": sum(s.pages for s in scans),
        "complete": complete,
        "truncated": not complete,
        "estimated_posts_in_window": est if not complete else scanned,
        "ranked": ranked,
        "left_out_unfinal": excluded,
        "per_subreddit": [
            {"subreddit": s.subreddit, "posts_scanned": len(s.items), "pages": s.pages,
             "coverage": s.method if not s.complete else "every post in the window",
             **({"estimated_posts_in_window": s.estimated_total} if not s.complete else {})}
            for s in scans
        ],
    }


# ---------------------------------------------------------------- empty subreddits


async def _explain_empty(client: ArcticShiftClient, subs: list[str], window: Window) -> list[str]:
    """For a subreddit with no results: one cheap request to tell 'not in the archive at all'
    apart from 'nothing in this window'."""
    notes = []
    for sub in subs:
        if window.after is None and window.before is None:
            newest: list[Any] = []
        else:
            resp = await client.get("posts/search", {"subreddit": sub, "limit": 1, "sort": "desc"},
                                    fields=("id", "subreddit", "created_utc"))
            newest = [x for x in (resp.data or []) if isinstance(x, Mapping)]
        if newest:
            notes.append(
                f"r/{sub}: no posts in {window.describe()}; its newest archived post is from "
                f"{iso(newest[0].get('created_utc'))}."
            )
        else:
            notes.append(
                f"r/{sub}: the archive has no posts at all from this subreddit. It may not exist, or it "
                "may be private, quarantined or banned (the archive excludes those), or never have had "
                "a post. Check the spelling of the name."
            )
    return notes


# ---------------------------------------------------------------- query parsing (T7)

_FIELD_ALIASES = {
    "author": "author", "user": "author",
    "subreddit": "subreddit", "sr": "subreddit",
    "title": "title",
    "selftext": "selftext", "body": "selftext", "text": "selftext",
    "flair": "flair", "flair_name": "flair", "flair_text": "flair", "link_flair_text": "flair",
    "nsfw": "nsfw", "over_18": "nsfw",
    "spoiler": "spoiler",
    "url": "url",
    "site": "site",
    "self": "self", "is_self": "self",
}
_BOOL_TRUE = {"yes", "true", "1", "y", "on"}
_BOOL_FALSE = {"no", "false", "0", "n", "off"}
_QUERY_TOKEN = re.compile(r'(-?)(?:([A-Za-z_]+):)?("([^"]*)"?|[^\s()]+)|([()])')


@dataclass(frozen=True)
class Term:
    field: str  # text (title + selftext), title, selftext, author, subreddit, flair, nsfw, spoiler, url, site, self
    value: str
    phrase: bool = False
    negated: bool = False

    def show(self) -> str:
        v = f'"{self.value}"' if self.phrase or " " in self.value else self.value
        f = "" if self.field == "text" else f"{self.field}:"
        return f"{'-' if self.negated else ''}{f}{v}"


@dataclass
class Query:
    clauses: list[list[Term]]  # AND of OR groups

    def show(self) -> str:
        parts = []
        for c in self.clauses:
            s = " OR ".join(t.show() for t in c)
            parts.append(f"({s})" if len(c) > 1 else s)
        return " AND ".join(parts)


def parse_query(q: str) -> Query:
    """Reddit search syntax -> AND of OR groups.

    Words are ANDed. `a OR b` makes one group. `"a phrase"` is one term. `-x` and `NOT x` exclude.
    `field:value` maps an operator: author, subreddit, title, selftext, flair, nsfw, spoiler,
    url, site, self. Parentheses are ignored (OR binds its neighbours). `AND` is the default.
    """
    if not q or not q.strip():
        raise InputError("empty query")
    terms: list[Term | str] = []
    negate_next = False
    for m in _QUERY_TOKEN.finditer(q):
        if m.group(5):  # parenthesis
            continue
        minus, fname, raw, quoted = m.group(1), m.group(2), m.group(3), m.group(4)
        phrase = quoted is not None
        value = (quoted if phrase else raw).strip()
        if not phrase and not fname and value in ("OR", "|", "||"):
            terms.append("OR")
            continue
        if not phrase and not fname and value in ("AND", "&&"):
            continue
        if not phrase and not fname and value == "NOT":
            negate_next = True
            continue
        field_name = _FIELD_ALIASES.get((fname or "").lower())
        if fname and field_name is None:  # unknown "x:y": treat it as text
            value, field_name = f"{fname}:{value}", "text"
        if not value:
            continue
        terms.append(Term(field_name or "text", value, phrase or " " in value, bool(minus) or negate_next))
        negate_next = False
    clauses: list[list[Term]] = []
    join = False
    for t in terms:
        if t == "OR":
            join = bool(clauses)
            continue
        assert isinstance(t, Term)
        if join:
            clauses[-1].append(t)
        else:
            clauses.append([t])
        join = False
    if not clauses:
        raise InputError(f"no search terms in {q!r}")
    return Query(clauses)


def _bool_value(t: Term) -> bool:
    v = t.value.lower()
    if v in _BOOL_TRUE:
        return not t.negated
    if v in _BOOL_FALSE:
        return t.negated
    raise InputError(f"{t.field}: takes yes or no, not {t.value!r}")


# ---------------------------------------------------------------- local text matching


def tokens(text: str | None) -> list[str]:
    """Lower-case alphanumeric tokens: 'i9-9900K power-limit' -> ['i9', '9900k', 'power', 'limit']."""
    return _TOKEN_RE.findall((text or "").lower())


def _core(term_tokens: list[str]) -> str | None:
    """The model-number token of a term, e.g. 'i9-9900K' -> '9900k' (3+ digits)."""
    best = None
    for t in term_tokens:
        if sum(ch.isdigit() for ch in t) >= 3 and (best is None or len(t) > len(best)):
            best = t
    return best


class TextIndex:
    """Tokens of one text, ready for phrase, compact and fuzzy matching."""

    def __init__(self, text: str | None):
        self.toks = tokens(text)
        self.set = set(self.toks)
        self.compact = "".join(self.toks)
        self.bigrams = {a + b for a, b in zip(self.toks, self.toks[1:])}
        self._starts: set[int] = set()
        self._ends: set[int] = set()
        pos = 0
        for t in self.toks:
            self._starts.add(pos)
            pos += len(t)
            self._ends.add(pos)

    def compact_has(self, s: str) -> bool:
        """`s` occurs in the text with spaces removed, starting and ending on token edges."""
        if not s:
            return False
        i = self.compact.find(s)
        while i != -1:
            if i in self._starts and i + len(s) in self._ends:
                return True
            i = self.compact.find(s, i + 1)
        return False


class TermMatcher:
    """Matches one term against a `TextIndex`.

    - Phrase match on tokens, so case, hyphens and punctuation do not matter.
    - Model names: 'i9-9900K' = 'i9 9900k' = '9900k' (the 3+-digit token alone also matches),
      and '9900 K' matches through the text with spaces removed.
    - With `fuzzy`, alphabetic words of 5+ letters also match a typo or inflection at a
      similarity ratio of 0.85 or more ('undervolting' ~ 'undervolted'). Words with digits are
      never fuzzy: '9700k' is not '9900k'.
    """

    def __init__(self, term: str, *, fuzzy: bool = False):
        self.term = term
        self.toks = tokens(term)
        self.core = _core(self.toks)
        self.fuzzy = fuzzy
        self.joined = "".join(self.toks)
        self.variants: list[set[str]] = [{t} for t in self.toks]

    def expand(self, vocab: Iterable[str]) -> None:
        """Add fuzzy variants of each word from the vocabulary of the texts to match."""
        if not self.fuzzy:
            return
        vocab = list(vocab)
        for i, t in enumerate(self.toks):
            if len(t) < 5 or not t.isalpha():
                continue
            for w in vocab:
                if w == t or abs(len(w) - len(t)) > 3 or not w.isalpha():
                    continue
                sm = difflib.SequenceMatcher(None, t, w)
                if sm.real_quick_ratio() >= FUZZY_RATIO and sm.quick_ratio() >= FUZZY_RATIO and sm.ratio() >= FUZZY_RATIO:
                    self.variants[i].add(w)

    def matches(self, idx: TextIndex) -> bool:
        if not self.toks:
            return False
        n = len(self.toks)
        if n == 1:
            if self.variants[0] & idx.set:
                return True
            if len(self.joined) >= 6 and self.joined in idx.bigrams:  # 'under volt'
                return True
        else:
            first = self.variants[0]
            for j, tok in enumerate(idx.toks[: len(idx.toks) - n + 1]):
                if tok in first and all(idx.toks[j + k] in self.variants[k] for k in range(1, n)):
                    return True
            if self.joined in idx.set:  # 'powerlimit'
                return True
        if self.core and self.core in idx.set:
            return True
        if self.core:  # '9900 K': match across token gaps, but only on token edges
            return idx.compact_has(self.joined) or idx.compact_has(self.core)
        return False


def _post_fields(item: Mapping[str, Any]) -> dict[str, TextIndex]:
    return {"title": TextIndex(item.get("title")), "selftext": TextIndex(item.get("selftext"))}


def _domain(url: str | None) -> str:
    try:
        return (urlsplit(url or "").hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def _is_self(item: Mapping[str, Any]) -> bool:
    if isinstance(item.get("is_self"), bool):
        return item["is_self"]
    url = item.get("url") or ""
    pid = strip_prefix(item.get("id")) or ""
    return not url or f"/comments/{pid}" in url


def _term_hits(t: Term, item: Mapping[str, Any], idx: dict[str, TextIndex]) -> bool:
    """Whether `item` has `t` (ignoring t.negated)."""
    f = t.field
    if f in ("text", "title", "selftext"):
        m = TermMatcher(t.value)
        if f == "text":
            return m.matches(idx["title"]) or m.matches(idx["selftext"])
        return m.matches(idx[f])
    if f == "author":
        return (item.get("author") or "").lower() == t.value.lower().removeprefix("u/")
    if f == "subreddit":
        return (item.get("subreddit") or "").lower() == t.value.lower().removeprefix("r/")
    if f == "flair":
        flair = item.get("link_flair_text") or ""
        return flair.lower() == t.value.lower() or TermMatcher(t.value).matches(TextIndex(flair))
    if f == "nsfw":
        return bool(item.get("over_18")) == _bool_value(Term(f, t.value))
    if f == "spoiler":
        return bool(item.get("spoiler")) == _bool_value(Term(f, t.value))
    if f == "self":
        return _is_self(item) == _bool_value(Term(f, t.value))
    if f == "url":
        return t.value.lower() in (item.get("url") or "").lower()
    if f == "site":
        d, want = _domain(item.get("url")), t.value.lower().removeprefix("www.")
        return d == want or d.endswith("." + want)
    return False


def query_matches(q: Query, item: Mapping[str, Any], satisfied: set[int] = frozenset()) -> bool:  # type: ignore[assignment]
    """Every clause must have one term that holds (a negated term holds when absent).
    Clauses in `satisfied` were already applied by the archive."""
    idx = _post_fields(item)
    for i, clause in enumerate(q.clauses):
        if i in satisfied:
            continue
        if not any(_term_hits(t, item, idx) != t.negated for t in clause):
            return False
    return True


# ---------------------------------------------------------------- query -> archive params


def _specificity(value: str) -> float:
    """How narrow a term is as an archive anchor. A model number ('9900k', 'i9-9900K') beats
    any phrase: it is rare, and a post about the thing must name it. Length counts a little,
    up to 12 letters, so a long phrase from a synonym list does not win on length alone."""
    toks = tokens(value)
    if not toks or all(t in _STOPWORDS for t in toks):
        return -1.0
    score = min(len("".join(toks)), 12) * 0.5
    if _core(toks):
        score += 20
    elif any(ch.isdigit() for ch in value):
        score += 8
    if len(toks) > 1:
        score += 1
    return score


def _archive_value(value: str) -> str:
    """One keyword, or one quoted phrase: the only forms the archive took (probes Q6)."""
    toks = tokens(value)
    core = _core(toks)
    if core and len(toks) > 1:
        return core  # 'i9-9900K' -> '9900k': the archive's phrase match would need 'i9' too
    if len(toks) == 1:
        return toks[0]
    return '"' + " ".join(toks) + '"'


@dataclass
class Plan:
    params: dict[str, Any]  # non-keyword archive filters: author, link_flair_text, over_18, ...
    keyword: tuple[str, str] | None  # (archive param, value): the one anchor term
    keyword_clause: int | None
    satisfied: set[int]  # clause indexes the archive applies
    subreddits: list[str]
    notes: list[str]


def plan_query(q: Query, subreddits: list[str]) -> Plan:
    params: dict[str, Any] = {}
    satisfied: set[int] = set()
    subs = list(subreddits)
    notes: list[str] = []
    anchor: tuple[float, int, str, str] | None = None
    for i, clause in enumerate(q.clauses):
        if len(clause) != 1 or clause[0].negated:
            continue
        t = clause[0]
        if t.field == "author" and "author" not in params:
            params["author"] = t.value.removeprefix("u/")
            satisfied.add(i)
        elif t.field == "subreddit":
            name = _clean_subs([t.value])
            subs += [s for s in name if s.lower() not in {x.lower() for x in subs}]
            satisfied.add(i)
        elif t.field == "flair" and "link_flair_text" not in params:
            params["link_flair_text"] = t.value
            satisfied.add(i)
        elif t.field == "nsfw":
            params["over_18"] = _bool_value(t)
            satisfied.add(i)
        elif t.field == "spoiler":
            params["spoiler"] = _bool_value(t)
            satisfied.add(i)
        elif t.field == "url" and t.value.lower().startswith(("http://", "https://")) and "url" not in params:
            params["url"] = t.value
            satisfied.add(i)
        elif t.field in ("text", "title", "selftext"):
            s = _specificity(t.value)
            if s > 0 and (anchor is None or s > anchor[0]):
                param = {"text": "query", "title": "title", "selftext": "selftext"}[t.field]
                anchor = (s, i, param, _archive_value(t.value))
    keyword, keyword_clause = None, None
    if anchor is not None:
        _, i, param, value = anchor
        keyword, keyword_clause = (param, value), i
        # The archive's match on the anchor is a token match, the same as the local one,
        # except for a shortened model name; check that clause locally as well.
        if value == _archive_value(q.clauses[i][0].value) and tokens(value) == tokens(q.clauses[i][0].value):
            satisfied.add(i)
    local = [c for j, c in enumerate(q.clauses) if j not in satisfied]
    if local:
        notes.append(
            "applied locally (the archive takes only one keyword or quoted phrase, and no OR, NOT "
            "or site:/self: filters): " + " AND ".join(Query([c]).show() for c in local)
        )
    return Plan(params, keyword, keyword_clause, satisfied, subs, notes)


# ---------------------------------------------------------------- deep_search engine


@dataclass
class Step:
    """One walk backward through time: one subreddit, one archive field, one term."""

    sub: str
    kind: str  # 'title', 'query' (posts) or 'body' (comments)
    value: str
    lo: int
    hi: int
    span: int | None = None  # current window length; None = the whole remaining range
    pages: int = 0
    items: int = 0
    fast_retry: bool = False
    failed_in_row: int = 0
    status: str = "waiting"  # waiting, active, done, gave up
    oldest: int | None = None
    newest: int | None = None
    windows: int = 0
    fallback_from: str | None = None
    seen: set[str] = field(default_factory=set)

    @property
    def path(self) -> str:
        return "comments/search" if self.kind == "body" else "posts/search"

    def label(self) -> str:
        return f"{self.kind}={self.value}"


@dataclass
class DeepState:
    posts: dict[str, dict[str, Any]] = field(default_factory=dict)
    comments: dict[str, list[dict[str, Any]]] = field(default_factory=dict)  # link_id -> comments
    failed: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    cache_hits: int = 0
    wait: float = FAST_422_WAIT  # pause after the next fast 422; doubles while they continue
    waited: float = 0.0
    fast_422s: int = 0  # load-shedding refusals: bounded by MAX_TOTAL_WAIT, not by max_requests


def _anchor_terms(concepts: list[list[str]]) -> tuple[int, list[str]]:
    """The anchor group and its distinct archive values.

    The anchor is the group with the most specific term (a smaller group wins a tie: it is
    tighter). Its terms keep the caller's order, because in a synonym list the first term is
    usually the main one ('chatter' before 'double typing')."""
    best_group, best = 0, (-2.0, 0)
    for gi, group in enumerate(concepts):
        key = (max(_specificity(t) for t in group), -len(group))
        if key > best:
            best_group, best = gi, key
    values: list[str] = []
    for term in concepts[best_group]:
        if _specificity(term) <= 0:
            continue
        v = _archive_value(term)
        if v not in values:
            values.append(v)
    return best_group, values


async def _deep_step(client: ArcticShiftClient, st: Step, state: DeepState, now: float) -> None:
    """One request for `st`, with the 422 rules (docs/probes.md, Q7; docs/deep-search.md):
    fast 422 (load shedding) -> wait (10 s, growing to 60 s while they go on) and retry the same
    window: halving does not change the odds of a fast 422, and smaller windows cost more pages.
    A slow 422 (a real timeout) -> halve the window; a window at the one-day floor that still
    fails is skipped and logged."""
    st.status = "active"
    win_lo = st.lo if st.span is None else max(st.lo, st.hi - st.span)
    params = {"subreddit": st.sub, st.kind: st.value, "sort": "desc", "limit": PAGE,
              "after": win_lo if win_lo > ARCHIVE_START else None, "before": st.hi}
    fields = DEFAULT_COMMENT_FIELDS if st.kind == "body" else DEFAULT_POST_FIELDS
    before_count = client.call_requests
    try:
        resp = await client.get(st.path, params, fields=fields, retry_422=0)
    except QueryTooHeavy as e:
        if e.fast:
            # The archive sheds load in bursts of about 30-60 s: pause longer each time and retry
            # the same window. A fast refusal costs the archive almost nothing, so it does not use
            # up max_requests; MAX_TOTAL_WAIT bounds how many there can be.
            state.fast_422s += 1
            await _sleep(client, state.wait)
            state.waited += state.wait
            state.wait = min(state.wait * 2, MAX_422_WAIT)
            if st.kind == "body" and " OR " in st.value and st.fast_retry:
                # The OR form was refused twice: fall back to the single most specific term.
                st.fast_retry = False
                st.fallback_from, st.value = st.label(), st.value.split(" OR ")[0]
                return
            st.fast_retry = True
            return
        st.fast_retry = False
        if st.kind == "body" and " OR " in st.value:
            # The OR form failed twice: fall back to the single most specific term.
            st.fallback_from, st.value = st.label(), st.value.split(" OR ")[0]
            return
        span = st.span if st.span is not None else st.hi - st.lo
        if span > MIN_WINDOW:
            st.span = max(MIN_WINDOW, span // 2)
            return
        state.failed.append({
            "subreddit": st.sub, "step": st.label(), "from": iso(win_lo), "to": iso(st.hi),
            "reason": "HTTP 422 " + ("fast (archive busy)" if e.fast else "slow (timeout)") + " at the one-day floor",
        })
        st.failed_in_row += 1
        st.hi = win_lo
        if st.failed_in_row >= MAX_FAILED_WINDOWS or st.hi <= st.lo:
            st.status = "gave up"
        return
    if client.call_requests == before_count:
        state.cache_hits += 1
    state.wait = FAST_422_WAIT
    st.fast_retry = False
    st.failed_in_row = 0
    st.pages += 1
    page = [x for x in (resp.data or []) if isinstance(x, Mapping)]
    new = 0
    for x in page:
        xid = strip_prefix(x.get("id"))
        if not xid or xid in st.seen:
            continue
        st.seen.add(xid)
        new += 1
        if st.kind == "body":
            link = strip_prefix(x.get("link_id"))
            if link:
                state.comments.setdefault(link, []).append(dict(x))
        else:
            state.posts.setdefault(xid, dict(x))
    st.items += len(page)
    if page:
        st.oldest = _created(page[-1]) if st.oldest is None else min(st.oldest, _created(page[-1]))
        st.newest = _created(page[0]) if st.newest is None else max(st.newest, _created(page[0]))
    if len(page) >= PAGE:
        st.hi = _next_cursor(page, "desc", new)
        return
    # This window is done: move to the one before it, and let the window grow again.
    st.windows += 1
    st.hi = win_lo
    if st.span is not None:
        st.span = min(st.span * 2, max(MIN_WINDOW, st.hi - st.lo))
    if st.hi <= st.lo or win_lo <= ARCHIVE_START:
        st.status = "done"


def _step_report(st: Step) -> dict[str, Any]:
    out = {
        "subreddit": st.sub,
        "step": st.label(),
        "status": {"waiting": "not started (budget)", "active": "stopped (budget)"}.get(st.status, st.status),
        "pages": st.pages,
        "items": st.items,
        "searched_back_to": iso(st.lo if st.status == "done" else st.hi),
        "newest_match": iso(st.newest) if st.newest else None,
        "oldest_match": iso(st.oldest) if st.oldest else None,
    }
    if st.status == "active":
        out["resume_before"] = st.hi
    if st.fallback_from:
        out["note"] = f"fell back from {st.fallback_from}"
    return {k: v for k, v in out.items() if v is not None}


# ---------------------------------------------------------------- tools


def register(mcp: Any, ctx: ServerContext) -> None:
    client = ctx.client

    @archive_tool(mcp, title="List posts")
    async def list_posts(
        subreddits: list[str],
        sort: str = "new",
        time: str | None = None,
        after: str | int | None = None,
        before: str | int | None = None,
        limit: int = 25,
        max_pages: int = DEFAULT_SCAN_PAGES,
        text_chars: int = LIST_TEXT_CHARS,
    ) -> dict:
        """List posts in one or more subreddits, like a subreddit's new/top tabs.

        - subreddits: names without 'r/' (1-10). Results from several are merged, de-duplicated.
        - sort: 'new' (default) and 'old' are the archive's own order. 'top' (score),
          'comments' (comment count) and 'controversial' are ranked here over a bounded scan of
          the window (at most max_pages pages of 100 posts): the result's `scan` says the
          window, how many posts were scanned, and whether the scan was complete or a sample.
          'hot', 'rising', 'best' and 'relevance' are not possible from an archive.
        - time: Reddit's filter hour/day/week/month/year/all, or a span such as 'last 3 months'.
          Or give after/before: epoch seconds or dates ('2025', '2025-03', '2025-03-01').
          before='2025' means up to the end of 2025.
        - Scores and comment counts are frozen at about 36 h after posting; younger posts have
          the first value (usually 1 or 0). So 'top' or 'comments' over the last day is refused,
          and in longer windows posts younger than 36 h are left out of the ranking.
        - limit: posts to return (1-100). text_chars: selftext length per post (0 = none).
        """
        subs = _clean_subs(subreddits)
        if not subs:
            raise InputError("name at least one subreddit")
        s = _check_sort(sort)
        _check_limit(limit)
        _check_pages(max_pages)
        _check_text_chars(text_chars)
        now = _now(client)
        window = resolve_window(time, after, before, now=now)
        notes: list[str] = []
        if s in NATIVE_SORTS:
            order = NATIVE_SORTS[s]
            seen: set[str] = set()
            items: list[dict[str, Any]] = []
            per_sub_pages = max(1, -(-limit // PAGE))
            empty = []
            for sub in subs:
                w = await _walk(client, {"subreddit": sub}, window, order=order,
                                fields=LIST_FIELDS if text_chars else SCAN_FIELDS,
                                max_pages=per_sub_pages, want=limit, seen=seen)
                if not w.items:
                    empty.append(sub)
                items += w.items[:limit]
            items.sort(key=_created, reverse=(order == "desc"))
            items = items[:limit]
            if empty:
                notes += await _explain_empty(client, empty, window)
            posts = [_shape(x, now, text_chars) for x in items]
            return await make_result(
                client, items=posts, notes=notes, subreddits=subs, sort=s, window=window.describe(),
                order=f"{'newest' if order == 'desc' else 'oldest'} first (the archive's own order)",
            )
        # Computed sorts (T2, T3).
        _unfinal_refusal(s, window, now)
        full = s == "controversial"  # upvote_ratio is only in full objects
        per_sub = max(1, max_pages // len(subs))
        scans = []
        for sub in subs:
            scans.append(await _scan(client, sub, window, now=now, pages=per_sub,
                                     fields=None if full else SCAN_FIELDS, full=full))
        pool: dict[str, dict[str, Any]] = {}
        for sc in scans:
            for x in sc.items:
                pool.setdefault(strip_prefix(x.get("id")) or "", x)
        final = [x for x in pool.values() if _is_final(x, now)]
        excluded = len(pool) - len(final)
        final.sort(key=_RANK[s], reverse=True)
        top = final[:limit]
        if text_chars and top:
            full_items = {strip_prefix(x.get("id")): x for x in await client.get_ids(
                "posts", [x["id"] for x in top], full=True)}
            top = [full_items.get(strip_prefix(x.get("id")), x) for x in top]
        empty = [sc.subreddit for sc in scans if not sc.items]
        if empty:
            notes += await _explain_empty(client, empty, window)
        if excluded:
            notes.append(
                f"{excluded} post(s) younger than about 36 h were left out of the ranking: their "
                "scores and comment counts are still the first value (1 or 0)."
            )
        if s == "comments":
            notes.append("num_comments is the archive's snapshot estimate, not a live count.")
        if s == "controversial":
            notes.append("controversy is estimated from score and upvote_ratio; the archive has no down votes.")
        report = _scan_report(scans, window, len(final), excluded)
        if report["truncated"]:
            notes.append(
                f"The scan was bounded: {report['posts_scanned']} of about "
                f"{report['estimated_posts_in_window']} posts in the window. Posts outside the scan "
                "are not ranked; raise max_pages (up to 30) or narrow the window for more."
            )
        posts = [_shape(x, now, text_chars) for x in top]
        return await make_result(client, items=posts, notes=notes, subreddits=subs, sort=s,
                                 window=window.describe(), scan=report)

    @archive_tool(mcp, title="Search posts")
    async def search_posts(
        query: str,
        subreddits: list[str] | None = None,
        sort: str = "new",
        time: str | None = None,
        after: str | int | None = None,
        before: str | int | None = None,
        limit: int = 25,
        max_pages: int = DEFAULT_SEARCH_PAGES,
        text_chars: int = LIST_TEXT_CHARS,
    ) -> dict:
        """Search posts in named subreddits (or by author) with Reddit search syntax.

        - Needs at least one subreddit, or an author: operator. The archive has no search across
          all of Reddit: pick the subreddits that fit the topic (find_subreddits can help).
        - query syntax: words are ANDed; `a OR b`; "exact phrase"; `-word` or `NOT word`;
          operators author:, title:, selftext:, flair: (link flair), nsfw:yes/no, spoiler:yes/no,
          url: (prefix), site: (domain), self:yes/no, subreddit:.
          The archive gets one keyword or quoted phrase; the rest is applied here. The result's
          `method` says what the archive matched and what was filtered locally.
        - The archive's keyword search often times out under load. Then the tool lists the
          window without the keyword and filters it locally (`method` says "local scan",
          `partial: true`; a big window is sampled evenly): matches outside the scanned pages are
          missed. Then narrow the window, or raise max_pages (up to 30).
        - sort: 'new' (default), 'old', or 'top'/'comments' ranked here over the matches found
          (max_pages pages of 100). 'relevance' and 'hot' are not possible.
        - time / after / before: as in list_posts; absolute dates are best ('2025', '2025-03-01').
        """
        if not query or not query.strip():
            raise InputError("empty query")
        s = _check_sort(sort)
        if s == "controversial":
            raise InputError("search sorts are new, old, top and comments")
        _check_limit(limit)
        _check_pages(max_pages)
        _check_text_chars(text_chars)
        q = parse_query(query)
        plan = plan_query(q, _clean_subs(subreddits))
        if not plan.subreddits and "author" not in plan.params:
            raise ToolError(unavailable_feature("global search"))
        if len(plan.subreddits) > MAX_SUBREDDITS:
            raise InputError(f"at most {MAX_SUBREDDITS} subreddits per call")
        now = _now(client)
        window = resolve_window(time, after, before, now=now)
        if s in COMPUTED_SORTS:
            _unfinal_refusal(s, window, now)
        notes = list(plan.notes)
        order = "asc" if s == "old" else "desc"
        want = limit if s in NATIVE_SORTS else None
        scopes = plan.subreddits or [None]
        per_scope = max(1, max_pages // len(scopes))
        async def local_scan(sub: str | None, base: dict[str, Any], win: Window, pages: int,
                             info: dict[str, Any]) -> list[dict[str, Any]]:
            """List `win` with the archive's non-keyword filters and match the query here. Newest
            first, a window too big for `pages` is sampled evenly (labelled), not cut at its newest days."""
            if order == "asc" or win.after is None:  # no start date: newest first, not a 20-year sample
                w = await _walk(client, base, win, order=order, fields=LIST_FIELDS, max_pages=pages,
                                want=want, keep=keep_local, seen=seen)
                info.update(pages=w.pages, complete=w.exhausted, partial=not w.exhausted, posts_scanned=w.scanned)
                if not w.exhausted and w.reached is not None:
                    info["scanned_up_to" if order == "asc" else "scanned_back_to"] = iso(w.reached)
                if sub and w.scanned == 0 and not plan.params:
                    empty_listings.append(sub)
                return w.items
            extra = {k: v for k, v in base.items() if k != "subreddit"}
            sc = await _scan(client, sub or "", win, now=now, pages=pages, fields=LIST_FIELDS, full=False, extra=extra)
            fresh = []
            for x in sc.items:
                xid = strip_prefix(x.get("id"))
                if xid in seen:
                    continue
                seen.add(xid)
                if keep_local(x):
                    fresh.append(x)
            info.update(pages=sc.pages, complete=sc.complete, partial=not sc.complete, posts_scanned=len(sc.items))
            if not sc.complete:
                info["coverage"] = sc.method
                info["estimated_posts_in_window"] = sc.estimated_total
            if sub and not sc.items and not plan.params:
                empty_listings.append(sub)
            return fresh

        satisfied_local = plan.satisfied - {plan.keyword_clause}
        keep_kw = lambda x: query_matches(q, x, plan.satisfied)  # noqa: E731
        keep_local = lambda x: query_matches(q, x, satisfied_local)  # noqa: E731
        matched: list[dict[str, Any]] = []
        seen: set[str] = set()
        methods: list[dict[str, Any]] = []
        empty_listings: list[str] = []
        for sub in scopes:
            base = {**plan.params, **({"subreddit": sub} if sub else {})}
            info: dict[str, Any] = {"scope": f"r/{sub}" if sub else f"u/{plan.params.get('author')}"}
            walk: Walk | None = None
            if plan.keyword:
                sent = {**base, plan.keyword[0]: plan.keyword[1]}
                try:
                    walk = await _walk(client, sent, window, order=order, fields=LIST_FIELDS,
                                       max_pages=per_scope, want=want, keep=keep_kw, seen=seen, retry_422=1)
                    info["method"] = f"archive keyword search ({plan.keyword[0]}={plan.keyword[1]}), then local filters"
                except QueryTooHeavy as e:
                    partial: Walk = getattr(e, "partial_walk", None) or Walk(sub or "")
                    matched += partial.items
                    resume = window
                    if partial.reached is not None:
                        resume = (Window(window.after, partial.reached + 1, "") if order == "desc"
                                  else Window(partial.reached - 1, window.before, ""))
                    info["method"] = (
                        f"local scan (T6): the archive's keyword search ({plan.keyword[0]}={plan.keyword[1]}) "
                        f"failed with HTTP 422 ({'archive busy' if e.fast else 'timeout'}), so the tool "
                        "listed the window and matched the whole query locally"
                    )
                    matched += await local_scan(sub, base, resume, max(1, per_scope - partial.pages), info)
                    methods.append(info)
                    continue
                matched += walk.items
                info.update(pages=walk.pages, complete=walk.exhausted)
                if not walk.exhausted and walk.reached is not None:
                    info["scanned_back_to" if order == "desc" else "scanned_up_to"] = iso(walk.reached)
            else:
                info["method"] = "listing with the archive filters, matched locally"
                matched += await local_scan(sub, base, window, per_scope, info)
            methods.append(info)
        if s in COMPUTED_SORTS:
            pool = [x for x in matched if _is_final(x, now)]
            excluded = len(matched) - len(pool)
            pool.sort(key=_RANK[s], reverse=True)
            if excluded:
                notes.append(f"{excluded} match(es) younger than about 36 h were left out of the ranking (scores not final).")
            if any(not m["complete"] for m in methods):
                notes.append("Ranked over the matches found within the page budget, not every match in the window.")
            matched = pool
        else:
            matched.sort(key=_created, reverse=(order == "desc"))
        if any(m.get("partial") for m in methods):
            notes.append(
                "partial: at least one scope was a bounded local scan, so matches outside the scanned "
                "pages are missed. Narrow the window (after/before) to scan it completely."
            )
        matched = matched[:limit]
        if empty_listings:
            notes += await _explain_empty(client, empty_listings, window)
        posts = [_shape(x, now, text_chars) for x in matched]
        extra: dict[str, Any] = {"archive_filters": plan.params} if plan.params else {}
        return await make_result(
            client, items=posts, notes=notes, query=q.show(), **extra,
            subreddits=plan.subreddits, sort=s, window=window.describe(), method=methods,
        )

    @archive_tool(mcp, title="Deep search")
    async def deep_search(
        concepts: list[list[str]],
        subreddits: list[str],
        after: str | int | None = None,
        before: str | int | None = None,
        search_in: Annotated[Literal["posts", "comments", "both"], Field(alias="in")] = "posts",
        max_requests: int = 30,
        limit: int = 10,
    ) -> dict:
        """Find older or loosely worded posts that a plain search misses, e.g. "that 2022 thread
        about power limits on a 9900K".

        - concepts: AND of OR groups that you write, e.g.
          [["9900k", "i9-9900k", "9900kf"], ["power limit", "PL1", "PL2", "undervolt", "TDP"]].
          Put model names, synonyms and spellings in the groups.
        - subreddits: 1-2 fitting subreddits per call, the most likely first (e.g. buildapc,
          intel). They share max_requests round robin, so each extra subreddit makes every
          search shallower: with 3 subreddits and in='both' each step gets about 1/6 of the
          budget and old posts are not reached. Search more subreddits in a second call. Up to
          8 are accepted. For an old post, an after/before range also helps.
        - after / before: an optional date range (epoch seconds or '2022', '2022-08-01').
        - in: 'posts' (default and cheapest: title, then title+selftext), 'comments' (comment
          bodies, grouped by post), or 'both' (splits the budget again).
        - max_requests: archive requests to spend (1-60, default 30). One request is one page of
          100 items; the archive is slow, so 30 requests take one to several minutes. Instant
          refusals (fast HTTP 422, the archive shedding load) are retried after a growing pause
          and do not count; after 6 minutes of such pauses the call stops. The status check, and
          a retry after a rate limit (HTTP 429), can add one request each. For one old thread,
          max_requests=60 with 1-2 subreddits reaches furthest back.

        How it works: the group with the most specific term is the anchor. Its distinct terms go to
        the archive one at a time, as one keyword (most specific first), and the tool
        walks back through time windows (100 items per page), halving a window when the archive
        times out. It then matches every concept group locally on title, selftext and matched
        comments, with model-name normalization (i9-9900K = i9 9900k = 9900k) and typo tolerance,
        and ranks by how many groups matched, then by comment count.

        The result lists the candidates, each with `matched: ...`, and a `coverage` report: the
        windows scanned and failed, the requests used, and whether the search was truncated
        (then each unfinished step has a `resume_before`, and `coverage.continue_with.before`).
        A truncated result has `next_call`: call deep_search again with exactly those arguments
        (the subreddit furthest behind, from where it stopped), up to 3 calls in all. If it is
        still truncated or empty, use your web search tool (when you have one) for candidate
        reddit.com URLs, then read them with get_thread or get_posts.
        """
        if not concepts or not all(isinstance(g, list) and g for g in concepts):
            raise InputError("concepts must be a list of non-empty term groups, e.g. [['9900k'], ['power limit', 'PL1']]")
        if len(concepts) > 6 or any(len(g) > 15 for g in concepts):
            raise InputError("at most 6 concept groups of at most 15 terms each")
        groups = [[str(t).strip() for t in g if str(t).strip()] for g in concepts]
        if not all(groups):
            raise InputError("a concept group has only empty terms")
        subs = _clean_subs(subreddits)
        if not subs:
            raise ToolError(unavailable_feature("global search"))
        if len(subs) > 8:
            raise InputError("at most 8 subreddits")
        if not isinstance(max_requests, int) or not 1 <= max_requests <= 60:
            raise InputError("max_requests must be 1-60")
        _check_limit(limit, 50)
        now = _now(client)
        window = resolve_window(None, after, before, now=now)
        lo = window.after if window.after is not None else ARCHIVE_START
        hi = window.before if window.before is not None else int(now)

        anchor_group, anchors = _anchor_terms(groups)
        if not anchors:
            raise InputError("no usable search term: every term is a stop word")
        primary = anchors[0]
        start = client.call_requests
        state = DeepState()

        def spent() -> int:
            """Requests that count against max_requests: all but the fast 422s."""
            return client.call_requests - start - state.fast_422s

        alts = anchors[:MAX_ANCHORS]
        steps: list[Step] = []
        for sub in subs:
            if search_in in ("posts", "both"):
                # Every distinct term of the anchor group in the title, then in title + selftext.
                steps += [Step(sub, "title", a, lo, hi) for a in alts]
                steps += [Step(sub, "query", a, lo, hi) for a in alts]
            if search_in in ("comments", "both"):
                body = " OR ".join(alts) if len(alts) > 1 else primary
                steps.append(Step(sub, "body", body, lo, hi))

        # Within a subreddit the posts steps run one after another; subreddits (and the
        # comment step) take turns, one request each.
        def runnable(st: Step) -> bool:
            if st.status in ("done", "gave up"):
                return False
            if st.kind == "body":
                return True
            for x in steps:
                if x is st:
                    return True
                if x.sub == st.sub and x.kind != "body" and x.status not in ("done", "gave up"):
                    return False
            return True

        reserve = 1 if search_in != "posts" else 0  # posts/ids for comment hits
        max_steps = max_requests * 4  # bounds the loop when the cache answers
        n_steps = 0
        busy_stop = False
        while n_steps < max_steps and spent() < max_requests - reserve:
            if state.waited >= MAX_TOTAL_WAIT:
                busy_stop = True
                break
            ready = [st for st in steps if runnable(st)]
            if not ready:
                break
            for st in ready:
                if spent() >= max_requests - reserve:
                    break
                await _deep_step(client, st, state, now)
                n_steps += 1
        truncated = any(st.status in ("waiting", "active") for st in steps)

        # Comment step: fetch the posts the matching comments belong to.
        if state.comments:
            missing = [lid for lid in sorted(state.comments, key=lambda k: -len(state.comments[k]))
                       if lid not in state.posts][:500]
            if missing and spent() < max_requests:
                for x in await client.get_ids("posts", missing, fields=DEFAULT_POST_FIELDS):
                    pid = strip_prefix(x.get("id"))
                    if pid:
                        state.posts[pid] = dict(x)
            elif missing:
                state.notes.append(f"{len(missing)} post(s) with matching comments were not fetched (budget).")

        # Local step: match every concept group.
        matchers = [[TermMatcher(t, fuzzy=True) for t in g] for g in groups]
        indexes: dict[str, dict[str, TextIndex]] = {}
        vocab: set[str] = set()
        for pid, p in state.posts.items():
            idx = _post_fields(p)
            bodies = " \n ".join(c.get("body") or "" for c in state.comments.get(pid, []))
            idx["comments"] = TextIndex(bodies)
            indexes[pid] = idx
            for v in idx.values():
                vocab |= v.set
        for g in matchers:
            for m in g:
                m.expand(vocab)
        candidates = []
        for pid, p in state.posts.items():
            idx = indexes[pid]
            hits: list[str] = []
            covered = in_title = 0
            for gi, g in enumerate(matchers):
                where = None
                # the title first: a group named in the title is the strongest evidence
                for fname in ("title", "selftext", "comments"):
                    m = next((m for m in g if m.matches(idx[fname])), None)
                    if m is not None:
                        where = f"{m.term} ({'comment' if fname == 'comments' else fname})"
                        in_title += fname == "title"
                        break
                if where is None and gi == anchor_group and pid not in state.comments:
                    where = f"{primary} (archive match)"
                if where:
                    covered += 1
                    hits.append(where)
            if covered:
                candidates.append((covered, in_title, p.get("num_comments") or 0, p.get("score") or 0, pid, hits))
        # Concept coverage first (title coverage breaks ties), then the comment count.
        candidates.sort(key=lambda c: c[:4], reverse=True)
        out = []
        for covered, _, _, _, pid, hits in candidates[:limit]:
            post = _shape(state.posts[pid], now, DEEP_TEXT_CHARS)
            post["matched"] = "; ".join(hits)
            post["concepts_matched"] = f"{covered}/{len(groups)}"
            cs = state.comments.get(pid)
            if cs:
                post["matching_comments"] = len(cs)
                post["comment_links"] = [
                    permalink_comment(c.get("subreddit") or post["subreddit"], pid, c.get("id") or "")
                    for c in sorted(cs, key=lambda c: -(c.get("score") or 0))[:3]
                ]
            out.append(post)

        used = client.call_requests - start
        oldest_open = [st.hi for st in steps if st.status == "active"]
        not_started = [st.label() + f" in r/{st.sub}" for st in steps if st.status == "waiting"]
        coverage: dict[str, Any] = {
            "requests_used": used,
            "fast_422s_not_counted": state.fast_422s,
            "max_requests": max_requests,
            "answered_from_cache": state.cache_hits,
            "seconds_waited_after_422": round(state.waited),
            "truncated": truncated,
            "window": Window(lo if window.after is not None else None, window.before, "").describe(),
            "archive_terms": alts,
            "posts_examined": len(state.posts),
            "comments_examined": sum(len(v) for v in state.comments.values()),
            "full_matches": sum(1 for c in candidates if c[0] == len(groups)),
            # Steps not started are listed (capped) under not_started, not here, to keep this short.
            "steps": [_step_report(st) for st in steps if st.status != "waiting"][:16],
            "windows_failed": state.failed[:10],
        }
        if truncated and oldest_open:
            coverage["continue_with"] = {"before": max(oldest_open), "before_date": iso(max(oldest_open))}
        if not_started:
            coverage["not_started"] = not_started[:10] + (
                [f"... and {len(not_started) - 10} more"] if len(not_started) > 10 else [])
        notes = list(state.notes)
        next_call: dict[str, Any] | None = None
        active = sorted((st for st in steps if st.status == "active"), key=lambda st: -st.hi)
        if active:
            # Go on with the subreddit that is furthest behind, alone, so it gets the whole budget.
            behind = active[0]
            next_call = {"concepts": groups, "subreddits": [behind.sub], "before": behind.hi,
                         "max_requests": max_requests, "in": search_in}
            if window.after is not None:
                next_call["after"] = window.after
            notes.insert(0, (
                f"NEXT STEP: older posts in r/{behind.sub} were not searched yet (it reached "
                f"{iso(behind.hi)}). If no candidate is clearly the thread wanted, call deep_search again "
                "with exactly the arguments in next_call. Do this before a web search."
            ))
        if busy_stop:
            notes.append(
                f"stopped early: the archive kept refusing keyword queries (fast HTTP 422, load shedding) "
                f"and the tool had waited {state.waited:.0f} s. Call deep_search again with the same "
                "concepts and subreddits and before=coverage.continue_with.before to go on from where it "
                "stopped; if that also stops early, run a web search for candidate reddit.com URLs and "
                "read them with get_thread or get_posts."
            )
        if truncated:
            notes.append(
                "truncated: the request budget ran out before every subreddit was searched back to the "
                "start of the window. Older posts were not searched. To go further back, call again "
                "for one subreddit at a time with its resume_before as `before`: "
                + "; ".join(
                    f"r/{st.sub} ({st.label()}) reached {iso(st.hi)}: before={st.hi}"
                    for st in steps if st.status == "active"
                )
                + ". Or narrow after/before to the years that matter. If no candidate is clearly the "
                "thread wanted, also run a web search for candidate reddit.com URLs and read them "
                "with get_thread or get_posts."
            )
        if not out:
            notes.append(
                "No candidates. The archive's keyword search may have failed (see windows_failed), or "
                "the wording differs. Try other terms, a date range, or a web search for candidate "
                "reddit.com URLs and read them with get_thread or get_posts."
            )
        extra = {"next_call": next_call} if next_call else {}
        result = await make_result(
            client, items=out, items_key="candidates", notes=notes, **extra,
            concepts=[" OR ".join(g) for g in groups], subreddits=subs, searched=search_in,
            coverage=coverage,
        )
        # Counted after make_result, so the status check is included, as in count_mentions.
        coverage["requests_used"] = client.call_requests - start
        coverage["counted_against_max_requests"] = spent()
        return result

    @archive_tool(mcp, title="Get posts")
    async def get_posts(ids_or_urls: list[str], text_chars: int = POST_TEXT_CHARS) -> dict:
        """Fetch full posts by ID or URL: 'wi7uhk', 't3_wi7uhk', a reddit.com/r/<sub>/comments/<id>/
        URL or a redd.it link. Up to 2,000 per call; the archive is asked 500 at a time.

        - text_chars: selftext length per post (default 1,500; up to 15,000 for the full text).
        - Share links (/r/<sub>/s/<code>) must be resolved to a post URL first.
        - IDs the archive does not have are listed under `not_found`.
        """
        if not ids_or_urls:
            raise InputError("give at least one post ID or URL")
        if len(ids_or_urls) > MAX_IDS:
            raise InputError(f"at most {MAX_IDS} IDs per call (the archive's monthly dumps are for bulk use)")
        _check_text_chars(text_chars)
        ids: list[str] = []
        bad: list[str] = []
        for ref in ids_or_urls:
            try:
                pid = parse_post_ref(str(ref))
            except InputError as e:
                bad.append(f"{ref}: {e}")
                continue
            if pid not in ids:
                ids.append(pid)
        if not ids:
            raise InputError("no valid post ID or URL: " + "; ".join(bad))
        now = _now(client)
        found = {strip_prefix(x.get("id")): x for x in await client.get_ids("posts", ids, full=True)
                 if isinstance(x, Mapping)}
        posts = [_shape(found[i], now, text_chars) for i in ids if i in found]
        missing = [i for i in ids if i not in found]
        notes = []
        if missing:
            notes.append(
                f"{len(missing)} ID(s) not in the archive: the post may be from a private or "
                "quarantined subreddit, removed at once, or the ID is wrong."
            )
        if bad:
            notes.append("could not read: " + "; ".join(bad))
        return await make_result(client, items=posts, notes=notes, requested=len(ids),
                                 not_found=missing or None)
