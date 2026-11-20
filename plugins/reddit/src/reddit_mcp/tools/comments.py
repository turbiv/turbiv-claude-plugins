"""Session 3: get_thread, expand_comments, get_comment_context, search_comments.

Rules from `reports/Keyless Reddit MCP sources.md` (Design constraints):

- T9: the thread tool reads `comments/tree` with a bounded `limit` and returns `more` stubs with
  child IDs; `expand_comments` loads them from the same (cached) tree or with `tree?parent_id=`.
- T10: comment sorts `top` (snapshot score), `new` and `old` are applied here, on every level.
  The archive's own order is never relied on (probes Q2: it is oldest first).
- T11: `get_comment_context` walks `parent_id` up through `comments/ids`, at most 8 levels.
- T7: `search_comments` passes words (AND), "phrases" and OR to the archive's `body` search.
  `-exclude` is applied here, on an over-fetched page (docs/probes.md, Session 3: on a subreddit
  the archive never answered an exclusion query). On HTTP 422 it falls back to a labelled local
  scan of the window, as `search_posts` does (T6).
- O4: every comment result carries the completeness note (make_result(comments=True)).
- O6: bodies are cut to 800 characters with `truncated: true`; `get_comment_context` returns
  the focal comment's full text.

Archive facts this module relies on (docs/probes.md):

- `comments/tree` items are `{"kind": "t1" | "more", "data": {...}}`. `replies` is a Listing or "".
- A `more` stub's `children` lists only *direct* child IDs; its `count` counts every comment
  behind it, replies included.
- `comments/tree?link_id=X&parent_id=t1_Y` returns comment Y itself with its whole subtree.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from fastmcp.exceptions import ToolError

from ..arctic import (
    COMMENT_TEXT_CHARS,
    DEFAULT_COMMENT_FIELDS,
    DEFAULT_MAX_TOKENS,
    MAX_LIMIT,
    InputError,
    QueryTooHeavy,
    archive_tool,
    estimate_tokens,
    iso,
    make_result,
    parse_comment_ref,
    parse_post_ref,
    resolve_window,
    shape_comment,
    shape_post,
    strip_prefix,
    unavailable_feature,
)
from ..context import ServerContext

TREE_LIMIT = 200  # T9: comments asked from comments/tree per thread (the same for every call, so it caches)
CONTEXT_TREE_LIMIT = 100  # replies under a focal comment
SUBTREE_FETCHES = 10  # expand_comments: tree?parent_id= requests per call
MAX_EXPAND_IDS = 100
MAX_CONTEXT = 8  # T11
POST_CHARS = 7000  # get_thread: most self posts in full (wi7uhk is 6,606 characters)
CONTEXT_POST_CHARS = 1500
FOCAL_CHARS = 10000  # O6: the full text of the focal comment
SEARCH_BODY_CHARS = 500
STUB_IDS = 50  # child IDs listed per stub
MAX_SUBREDDITS = 5
SCAN_PAGE = 100
BUDGET = DEFAULT_MAX_TOKENS - 500  # room for the MCP wrapper

TREE_SORTS = ("top", "new", "old")
SEARCH_SORTS = {"new": "desc", "old": "asc"}
_NOT_OFFERED = ("best", "confidence", "controversial", "qa", "live", "random", "hot", "relevance", "rising")
_DELETED = ("[deleted]", "[removed]")
THREAD_FIELDS = ("id", "subreddit", "author", "created_utc", "retrieved_on", "score", "num_comments", "title")


# ================================================================ the comment tree


@dataclass
class Node:
    """One comment of a tree (or the post as the root, with `raw` empty)."""

    raw: dict[str, Any]
    children: list[Node] = field(default_factory=list)
    hidden_ids: list[str] = field(default_factory=list)  # direct children behind archive `more` stubs
    hidden_count: int = 0  # every comment behind those stubs

    @property
    def id(self) -> str:
        return strip_prefix(self.raw.get("id")) or ""

    def total(self) -> int:
        """This comment plus every comment under it, loaded or behind a stub."""
        return (1 if self.raw else 0) + sum(c.total() for c in self.children) + self.hidden_count

    def complete(self) -> bool:
        return not self.hidden_count and all(c.complete() for c in self.children)

    def walk(self) -> Iterable[Node]:
        for c in self.children:
            yield c
            yield from c.walk()


def parse_tree(items: Any) -> Node:
    """`comments/tree` data -> a root Node whose children are the top-level items."""
    root = Node({})
    _add(items, root)
    return root


def _add(items: Any, parent: Node) -> None:
    for it in items or []:
        if not isinstance(it, dict):
            continue
        kind, data = it.get("kind"), it.get("data")
        if kind is None and "body" in it:  # a bare comment object
            kind, data = "t1", it
        if not isinstance(data, dict):
            continue
        if kind == "more":
            kids = [strip_prefix(x) for x in data.get("children") or [] if x]
            parent.hidden_ids.extend(k for k in kids if k and k != "_")
            parent.hidden_count += int(data.get("count") or len(kids))
        elif kind == "t1":
            node = Node(data)
            parent.children.append(node)
            replies = data.get("replies")
            if isinstance(replies, dict):
                _add((replies.get("data") or {}).get("children"), node)


def _sort_key(sort: str) -> Callable[[Node], tuple]:
    def created(n: Node) -> float:
        v = n.raw.get("created_utc")
        return float(v) if isinstance(v, (int, float)) else 0.0

    if sort == "new":
        return lambda n: (-created(n), n.id)
    if sort == "old":
        return lambda n: (created(n), n.id)
    return lambda n: (-(n.raw.get("score") or 0), created(n), n.id)  # top: snapshot score


def check_sort(sort: str, allowed: Iterable[str]) -> str:
    s = (sort or "").strip().lower()
    if s in _NOT_OFFERED:
        raise ToolError(unavailable_feature(s))
    if s not in allowed:
        raise InputError(f"sort must be one of {', '.join(allowed)}, not {sort!r}")
    return s


def display_order(roots: list[Node], sort: str, depth: int) -> list[Node]:
    """Pre-order with siblings sorted, down to `depth` levels. A comment always follows its
    parent, so any prefix of this list is a valid trimmed tree."""
    key = _sort_key(sort)
    out: list[Node] = []

    def visit(nodes: list[Node], d: int) -> None:
        for n in sorted(nodes, key=key):
            out.append(n)
            if d + 1 < depth:
                visit(n.children, d + 1)

    visit(roots, 0)
    return out


@dataclass
class Renderer:
    """Turns nodes into output dicts, with `more` stubs for whatever is not shown (T9)."""

    sort: str
    op: str | None
    shown: set[str]
    text_chars: int = COMMENT_TEXT_CHARS

    def children(self, node: Node, parent_fullname: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        hidden: list[str] = []
        count = 0
        for c in sorted(node.children, key=_sort_key(self.sort)):
            if c.id in self.shown:
                out.append(self.comment(c))
            else:
                hidden.append(c.id)
                count += c.total()
        hidden.extend(node.hidden_ids)
        count += node.hidden_count
        if count:
            out.append(stub(parent_fullname, hidden, count))
        return out

    def comment(self, node: Node, *, keep_parent: bool = False, text_chars: int | None = None) -> dict[str, Any]:
        c = comment_out(node.raw, self.op, text_chars or self.text_chars, keep_parent=keep_parent)
        replies = self.children(node, f"t1_{node.id}")
        if replies:
            c["replies"] = replies
        return c


def stub(parent_fullname: str, ids: list[str], count: int) -> dict[str, Any]:
    s: dict[str, Any] = {"kind": "more", "count": count, "parent_id": parent_fullname, "ids": ids[:STUB_IDS]}
    if len(ids) > STUB_IDS:
        s["ids_left_out"] = len(ids) - STUB_IDS
    if not ids:
        s["hint"] = "expand the parent comment's ID to load these"
    return s


def is_op(raw: dict[str, Any], op: str | None) -> bool:
    """True when the comment is by the post's author."""
    if raw.get("is_submitter"):
        return True
    return op is not None and op not in _DELETED and raw.get("author") == op


def comment_out(raw: dict[str, Any], op: str | None, text_chars: int, *, keep_parent: bool = False) -> dict[str, Any]:
    """shape_comment, minus what the tree already says, plus `op`."""
    c = shape_comment(raw, text_chars=text_chars)
    c.pop("is_submitter", None)
    c.pop("subreddit", None)
    c.pop("link_id", None)
    if not keep_parent:
        c.pop("parent_id", None)
    if is_op(raw, op):
        c["op"] = True
    if c.get("body") in _DELETED:
        c["body"] = f"{c['body']} (on Reddit; the archive has no text)"
    return c


def fit(make: Callable[[int], dict[str, Any]], k_max: int, budget: int = BUDGET) -> tuple[dict[str, Any], int]:
    """The result with the most shown comments (<= k_max) that stays within `budget` tokens."""
    full = make(k_max)
    if estimate_tokens(full) <= budget or k_max == 0:
        return full, k_max
    lo, hi = 0, k_max - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if estimate_tokens(make(mid)) <= budget:
            lo = mid
        else:
            hi = mid - 1
    return make(lo), lo


def _clamp(value: int, lo: int, hi: int, name: str) -> int:
    try:
        v = int(value)
    except (TypeError, ValueError):
        raise InputError(f"{name} must be a whole number") from None
    if not lo <= v <= hi:
        raise InputError(f"{name} must be {lo}-{hi}")
    return v


# ================================================================ archive calls


async def fetch_post(ctx: ServerContext, post_id: str) -> dict[str, Any] | None:
    # Full object: `_meta` gives the best score_status evidence and upvote_ratio (R3).
    found = await ctx.client.get_ids("posts", [post_id], full=True)
    return next((p for p in found if strip_prefix(p.get("id")) == post_id), None)


async def fetch_tree(ctx: ServerContext, post_id: str, parent: str | None = None, limit: int = TREE_LIMIT) -> Node:
    params = {"link_id": post_id, "limit": limit, "parent_id": parent}
    resp = await ctx.client.get("comments/tree", params)
    return parse_tree(resp.data)


async def fetch_comment(ctx: ServerContext, comment_id: str) -> dict[str, Any] | None:
    found = await ctx.client.get_ids("comments", [comment_id], fields=DEFAULT_COMMENT_FIELDS)
    return next((c for c in found if strip_prefix(c.get("id")) == comment_id), None)


def not_in_archive(what: str) -> ToolError:
    return ToolError(
        f"not in the archive: {what}. It may be from a private or quarantined subreddit, removed by "
        "AutoModerator at once, by a user who opted out, or too new for the archive."
    )


# ================================================================ comment search syntax (T7)


@dataclass(frozen=True)
class Term:
    words: tuple[str, ...]  # one word, or a phrase
    neg: bool = False

    def archive(self) -> str:
        text = " ".join(self.words)
        return f'"{text}"' if len(self.words) > 1 else text

    def show(self) -> str:
        return ("-" if self.neg else "") + self.archive()


@dataclass
class CommentQuery:
    """Postgres websearch semantics, as the archive's comment search: terms in a group are ANDed,
    groups are ORed, AND binds tighter than OR (`a b OR c` = (a AND b) OR c)."""

    groups: list[list[Term]] = field(default_factory=list)
    authors: list[str] = field(default_factory=list)
    subreddits: list[str] = field(default_factory=list)

    @property
    def has_terms(self) -> bool:
        return any(self.groups)

    @property
    def has_exclusions(self) -> bool:
        return any(t.neg for g in self.groups for t in g)

    def archive_body(self) -> str | None:
        """What goes to `body=`: words, phrases and OR. Exclusions stay local (probes, Session 3)."""
        parts = [" ".join(t.archive() for t in g if not t.neg) for g in self.groups]
        parts = [p for p in parts if p]
        return " OR ".join(parts) or None

    def show(self) -> str:
        return " OR ".join(" ".join(t.show() for t in g) for g in self.groups if g)

    def matches(self, text: str | None) -> bool:
        tokens = _tokens(text or "")
        return any(all(_has(tokens, t.words) != t.neg for t in g) for g in self.groups if g)


_QUERY_TOKEN = re.compile(r'(-?)"([^"]*)"?|(\S+)')
_POST_ONLY_FIELDS = ("title", "selftext", "flair", "url", "site", "self", "nsfw", "spoiler")
_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def _stem(word: str) -> str:
    """A light stem so that local matching is at least as lenient as the archive's English
    full-text search ('undervolting' matches 'undervolt')."""
    for suffix in ("ing", "ed", "es", "s"):
        if len(word) - len(suffix) >= 4 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _word_match(token: str, word: str) -> bool:
    stem = _stem(word)
    if len(stem) >= 4:
        return token.startswith(stem)
    return token == word or token == word + "s"


def _has(tokens: list[str], words: tuple[str, ...]) -> bool:
    n = len(words)
    for i in range(len(tokens) - n + 1):
        if all(_word_match(tokens[i + j], words[j]) for j in range(n)):
            return True
    return False


def parse_query(query: str) -> CommentQuery:
    """Reddit-style comment query -> CommentQuery.

    Accepts words, "phrases", OR (or `|`), AND (ignored: words are ANDed anyway), `-word`,
    `-"phrase"`, NOT word, `author:name` and `subreddit:name`. Post-only fields (title:, flair:,
    url:, site:, self:, nsfw:, ...) are refused: comments have none of them (T7).
    """
    q = CommentQuery()
    group: list[Term] = []
    negate_next = False
    for m in _QUERY_TOKEN.finditer(query or ""):
        dash, phrase, bare = m.group(1), m.group(2), m.group(3)
        if bare is not None:
            upper = bare.upper()
            if upper in ("OR", "|", "||"):
                if group:
                    q.groups.append(group)
                group = []
                continue
            if upper in ("AND", "&", "&&", "+"):
                continue
            if upper == "NOT":
                negate_next = True
                continue
            neg = bare.startswith("-") and len(bare) > 1
            text = bare[1:] if neg else bare
            if ":" in text and not text.startswith(("http:", "https:")):
                name, _, value = text.partition(":")
                name = name.lower()
                if name in ("author", "u", "user"):
                    if neg:
                        raise InputError("excluding an author is not supported; leave -author: out")
                    q.authors.append(value.removeprefix("u/").strip())
                    continue
                if name in ("subreddit", "r", "sub"):
                    if neg:
                        raise InputError("excluding a subreddit is not supported; leave -subreddit: out")
                    q.subreddits.append(value.removeprefix("r/").strip())
                    continue
                if name == "body":
                    text = value
                elif name in _POST_ONLY_FIELDS:
                    raise InputError(
                        f"comments have no {name}: field; search_comments searches comment text only. "
                        "Use search_posts for titles, flair, links or NSFW filters"
                    )
            words = tuple(_tokens(text))
        else:
            neg = dash == "-"
            words = tuple(_tokens(phrase))
        neg = neg or negate_next
        negate_next = False
        if words:
            group.append(Term(words, neg))
    if group:
        q.groups.append(group)
    for g in q.groups:
        if g and all(t.neg for t in g):
            raise InputError(
                "each part of the query (each side of OR) needs at least one word that is not excluded"
            )
    return q


# ================================================================ tools


def register(mcp: Any, ctx: ServerContext) -> None:
    @archive_tool(mcp, title="Read a thread")
    async def get_thread(
        url_or_id: str,
        max_comments: int = 100,
        depth: int = 8,
        sort: str = "top",
        post_chars: int = POST_CHARS,
    ) -> dict:
        """Read a Reddit post and its comment tree, as archived.

        - url_or_id: a post URL (…/comments/<id>/…), a redd.it link, or a post ID such as 'wi7uhk'.
          Share links (/r/<sub>/s/<code>) must be resolved first.
        - max_comments: comments to show (1-200). The answer may show fewer to stay short.
        - depth: reply levels to show (1 = top-level only, up to 10).
        - sort: 'top' (archived snapshot score), 'new' or 'old', applied on every level. Reddit's
          'best', 'controversial', 'Q&A' and 'live' sorts are not available from an archive.
        - post_chars: how much of the post text to show (500-20000).

        Comments not shown come back as {"kind": "more", "count", "parent_id", "ids"} stubs; pass
        the ids to expand_comments. `comment_counts` gives the real number of archived comments:
        the post's `num_comments` is a snapshot from when it was archived and is often stale.
        Comments marked op: true are by the post's author. When you report on the thread, say that it
        comes from the Arctic Shift archive, give comment_counts.in_archive as the number of comments,
        call scores archived snapshots, and cite the post and comments by their permalinks.
        """
        s = check_sort(sort, TREE_SORTS)
        max_comments = _clamp(max_comments, 1, TREE_LIMIT, "max_comments")
        depth = _clamp(depth, 1, 10, "depth")
        post_chars = _clamp(post_chars, 500, 20000, "post_chars")
        pid = parse_post_ref(url_or_id)

        raw_post = await fetch_post(ctx, pid)
        root = await fetch_tree(ctx, pid)
        if raw_post is None and not root.children:
            raise not_in_archive(f"post {pid}")
        op = raw_post.get("author") if raw_post else None
        post = shape_post(raw_post, text_chars=post_chars) if raw_post else {"id": pid}

        loaded = list(root.walk())
        total = root.total()
        order = display_order(root.children, s, depth)
        counts_base = {
            "in_archive": total,
            "top_level": len(root.children) + len(root.hidden_ids),
            "loaded": len(loaded),
            "by_op": sum(1 for n in loaded if is_op(n.raw, op)),
        }
        base_notes = _thread_notes(raw_post, total, len(loaded), s)
        envelope = await make_result(ctx.client, notes=base_notes, comments=True)

        def make(k: int) -> dict[str, Any]:
            shown = {n.id for n in order[:k]}
            comments = Renderer(s, op, shown).children(root, f"t3_{pid}")
            notes = list(envelope.get("notes", []))
            if k < total:
                notes.append(
                    f"{total - k} comment(s) are not shown: they are in the `more` stubs. Call "
                    "expand_comments with the post ID and a stub's ids to read them."
                )
            if k < min(max_comments, len(order)):
                notes.append(f"Showing {k} comments to keep the answer short; expand the stubs for the rest.")
            if any(_any_truncated(c) for c in comments) or post.get("truncated"):
                notes.append(
                    "Text marked truncated: true is cut short. get_comment_context(comment ID) returns a "
                    "comment's full text."
                )
            return {
                **{k2: v for k2, v in envelope.items() if k2 != "notes"},
                "notes": notes,
                "post": post,
                "sort": s,
                "comment_counts": {**counts_base, "shown": k, "not_shown": total - k},
                "comments": comments,
            }

        result, _ = fit(make, min(max_comments, len(order)))
        return result

    @archive_tool(mcp, title="Expand more comments")
    async def expand_comments(
        post_id: str,
        more_ids: list[str],
        sort: str = "top",
        depth: int = 8,
        max_comments: int = 100,
    ) -> dict:
        """Load comments hidden behind `more` stubs from get_thread (or expand_comments).

        - post_id: the post ID or URL the stub belongs to.
        - more_ids: the stub's `ids` (comment IDs, up to 100). Each comes back with its replies.
          To load the replies of a comment shown without them, pass that comment's own ID.
        - sort, depth, max_comments: as in get_thread.

        Comments that are still too many come back as new `more` stubs.
        """
        s = check_sort(sort, TREE_SORTS)
        depth = _clamp(depth, 1, 10, "depth")
        max_comments = _clamp(max_comments, 1, TREE_LIMIT, "max_comments")
        pid = parse_post_ref(post_id)
        wanted = list(dict.fromkeys(parse_comment_ref(i)[0] for i in more_ids or []))
        if not wanted:
            raise InputError("more_ids is empty: pass the ids of a `more` stub")
        if len(wanted) > MAX_EXPAND_IDS:
            raise InputError(f"at most {MAX_EXPAND_IDS} IDs per call; split the stub's ids")

        raw_post = await fetch_post(ctx, pid)
        op = raw_post.get("author") if raw_post else None
        tree = await fetch_tree(ctx, pid)  # the same request as get_thread: usually a cache hit
        index = {n.id: n for n in tree.walk()}

        roots: list[Node] = []
        not_expanded: list[str] = []
        not_found: list[str] = []
        fetches = 0
        for cid in wanted:
            node = index.get(cid)
            if node is not None and node.complete():
                roots.append(node)
                continue
            if fetches >= SUBTREE_FETCHES:
                not_expanded.append(cid)
                continue
            fetches += 1
            sub = await fetch_tree(ctx, pid, parent=f"t1_{cid}")
            found = next((n for n in [*sub.children, *sub.walk()] if n.id == cid), None)
            if found is None:
                not_found.append(cid)
            else:
                roots.append(found)
                index.update({n.id: n for n in found.walk()})
        # A requested comment inside another requested comment's subtree is already shown there.
        inner = {n.id for r in roots for n in r.walk()}
        roots = [r for r in roots if r.id not in inner]

        order = display_order(roots, s, depth)
        notes: list[str] = []
        if not_expanded:
            notes.append(
                f"{len(not_expanded)} ID(s) were not loaded (at most {SUBTREE_FETCHES} archive requests per "
                "call): pass not_expanded to expand_comments again."
            )
        if not_found:
            notes.append(f"{len(not_found)} ID(s) are not in the archive's tree for this post: see not_found.")
        envelope = await make_result(ctx.client, notes=notes, comments=True)
        total = sum(r.total() for r in roots)

        def make(k: int) -> dict[str, Any]:
            shown = {n.id for n in order[:k]}
            r = Renderer(s, op, shown)
            comments: list[dict[str, Any]] = []
            left: dict[str, list[Node]] = {}
            for root_node in sorted(roots, key=_sort_key(s)):
                if root_node.id in shown:
                    comments.append(r.comment(root_node, keep_parent=True))
                else:
                    left.setdefault(root_node.raw.get("parent_id") or f"t3_{pid}", []).append(root_node)
            for parent, nodes in left.items():
                comments.append(stub(parent, [n.id for n in nodes], sum(n.total() for n in nodes)))
            out_notes = list(envelope.get("notes", []))
            if k < total:
                out_notes.append(f"{total - k} comment(s) are still in `more` stubs; expand them the same way.")
            out = {
                **{k2: v for k2, v in envelope.items() if k2 != "notes"},
                "notes": out_notes,
                "post_id": pid,
                "sort": s,
                "requested": len(wanted),
                "comment_counts": {"loaded": total, "shown": k, "not_shown": total - k},
                "comments": comments,
            }
            if not_expanded:
                out["not_expanded"] = not_expanded
            if not_found:
                out["not_found"] = not_found
            return out

        result, _ = fit(make, min(max_comments, len(order)))
        return result

    @archive_tool(mcp, title="Comment in context")
    async def get_comment_context(
        comment_id_or_url: str,
        context: int = 3,
        replies: int = 10,
        sort: str = "top",
    ) -> dict:
        """Read one comment with the comments above it and its replies, like Reddit's ?context=N.

        - comment_id_or_url: a comment permalink (…/comments/<post>/<slug or _>/<comment>/) or a
          comment ID such as 'jx031mj' (with or without t1_).
        - context: parent comments to show above it (0-8).
        - replies: replies to show below it (0-50), sorted by `sort` ('top', 'new' or 'old').

        The focal comment comes back with its full text (other text is cut to 800 characters).
        Parents are listed from the top of the thread down to the direct parent.
        """
        s = check_sort(sort, TREE_SORTS)
        replies = _clamp(replies, 0, 50, "replies")
        notes: list[str] = []
        try:
            context = int(context)
        except (TypeError, ValueError):
            raise InputError("context must be a whole number 0-8") from None
        if context > MAX_CONTEXT:
            notes.append(f"context {context} is more than Reddit's maximum; showing {MAX_CONTEXT} parents.")
            context = MAX_CONTEXT
        context = max(0, context)
        cid, pid = parse_comment_ref(comment_id_or_url)

        focal_raw: dict[str, Any] | None = None
        if pid is None:
            focal_raw = await fetch_comment(ctx, cid)
            if focal_raw is None:
                raise not_in_archive(f"comment {cid}")
            pid = strip_prefix(focal_raw.get("link_id")) or ""
        focal: Node | None = None
        if replies > 0 or focal_raw is None:
            sub = await fetch_tree(ctx, pid, parent=f"t1_{cid}", limit=CONTEXT_TREE_LIMIT)
            focal = next((n for n in [*sub.children, *sub.walk()] if n.id == cid), None)
        if focal is None:
            if focal_raw is None:
                focal_raw = await fetch_comment(ctx, cid)
            if focal_raw is None:
                raise not_in_archive(f"comment {cid}")
            focal = Node(focal_raw)
            if replies > 0:
                notes.append("The archive's tree did not include this comment, so its replies are not shown.")

        chain: list[dict[str, Any]] = []
        parent = focal.raw.get("parent_id") or ""
        while len(chain) < context and parent.startswith("t1_"):
            raw = await fetch_comment(ctx, strip_prefix(parent) or "")
            if raw is None:
                notes.append(f"The parent comment {parent} is not in the archive; the chain stops there.")
                break
            chain.append(raw)
            parent = raw.get("parent_id") or ""
        more_above = parent.startswith("t1_")
        if more_above:
            notes.append("More parent comments are above the ones shown; raise `context` to see them.")

        raw_post = await fetch_post(ctx, pid)
        op = raw_post.get("author") if raw_post else None
        post = shape_post(raw_post, text_chars=CONTEXT_POST_CHARS) if raw_post else {"id": pid}
        if raw_post is None:
            notes.append(f"The post {pid} itself is not in the archive.")
        envelope = await make_result(ctx.client, notes=notes, comments=True)
        order = display_order(focal.children, s, 3)

        def make(k: int) -> dict[str, Any]:
            r = Renderer(s, op, {n.id for n in order[:k]})
            out_notes = list(envelope.get("notes", []))
            if k < len(order) or focal.hidden_count:
                out_notes.append("Some replies are in `more` stubs: pass their ids to expand_comments.")
            return {
                **{k2: v for k2, v in envelope.items() if k2 != "notes"},
                "notes": out_notes,
                "post": post,
                "parents": [comment_out(p, op, COMMENT_TEXT_CHARS, keep_parent=True) for p in reversed(chain)],
                "more_parents_above": more_above,
                "comment": comment_out(focal.raw, op, FOCAL_CHARS, keep_parent=True),
                "replies": r.children(focal, f"t1_{focal.id}") if replies > 0 else [],
            }

        result, _ = fit(make, min(replies, len(order)))
        return result

    @archive_tool(mcp, title="Search comments")
    async def search_comments(
        subreddits: list[str] | None = None,
        query: str = "",
        author: str | None = None,
        post: str | None = None,
        time: str | None = None,
        after: str | int | None = None,
        before: str | int | None = None,
        sort: str = "new",
        limit: int = 25,
        scan_pages: int = 3,
    ) -> dict:
        """Search archived comment text in one or more subreddits, by an author, or in one thread.

        - subreddits: up to 5 names, e.g. ["buildapc", "intel"]. A scope is required: subreddits,
          author or post. The archive has no Reddit-wide search.
        - query: words (all must appear), "an exact phrase", OR between alternatives, -word or
          NOT word to exclude, author:name, subreddit:name. AND binds tighter than OR:
          `9900k undervolt OR underclock` means (9900k AND undervolt) OR underclock; write
          `undervolt OR underclock` alone for an either-or. Matching is full-text with stemming
          ('undervolting' matches 'undervolt'). Empty query: the newest comments in the scope.
        - author: a username, without u/.
        - post: a post ID or URL, to search inside one thread.
        - time: hour, day, week, month, year, all, or a span such as '3 months'. Or give after /
          before: dates such as '2025-01-01', '2025' or epoch seconds. Default: all time.
        - sort: 'new' or 'old'. Relevance and score sorts are not available from the archive.
        - limit: results (1-100).
        - scan_pages: if the archive's search times out (HTTP 422), the tool lists the window
          instead and filters it here; this caps that scan at scan_pages x 100 comments per scope.

        The result says how each scope was searched (`coverage`), and lists the threads the
        comments belong to (`threads`).
        """
        direction = SEARCH_SORTS.get((sort or "").strip().lower())
        if direction is None:
            s = (sort or "").strip().lower()
            if s in _NOT_OFFERED:
                raise ToolError(unavailable_feature(s))
            raise InputError(
                f"sort must be 'new' or 'old', not {sort!r}: the archive has no score sort for search"
            )
        limit = _clamp(limit, 1, MAX_LIMIT, "limit")
        scan_pages = _clamp(scan_pages, 0, 10, "scan_pages")
        q = parse_query(query)
        subs = [x.strip().removeprefix("r/").removeprefix("/r/") for x in [*(subreddits or []), *q.subreddits]]
        subs = list(dict.fromkeys(x for x in subs if x))
        authors = [a for a in [author.removeprefix("u/").strip() if author else None, *q.authors] if a]
        if len(set(authors)) > 1:
            raise InputError("give one author at a time")
        who = authors[0] if authors else None
        link = parse_post_ref(post) if post else None
        if not subs and not who and not link:
            raise ToolError(unavailable_feature("global search"))
        if len(subs) > MAX_SUBREDDITS:
            raise InputError(f"at most {MAX_SUBREDDITS} subreddits per call")
        window = resolve_window(time, after, before)

        body = q.archive_body()
        local_filter = q.has_exclusions  # exclusions are applied here (probes, Session 3)
        per_scope = MAX_LIMIT if local_filter else limit
        scopes: list[dict[str, Any]] = (
            [{"subreddit": x} for x in subs] if subs else [{}]
        )
        found: dict[str, dict[str, Any]] = {}
        coverage: list[dict[str, Any]] = []
        notes: list[str] = []
        for scope in scopes:
            params = {
                **scope,
                "author": who,
                "link_id": link,
                "body": body,
                "sort": direction,
                "limit": per_scope,
                **window.params(),
            }
            label = _scope_label(scope.get("subreddit"), who, link)
            try:
                resp = await ctx.client.get("comments/search", params, fields=DEFAULT_COMMENT_FIELDS)
            except QueryTooHeavy as e:
                if not body:
                    raise
                items, cov = await _scan(ctx, params, q, window, direction, scan_pages, limit, e)
                cov["scope"] = label
                coverage.append(cov)
            else:
                items = [c for c in resp.data or [] if isinstance(c, dict)]
                cov = {"scope": label, "method": "archive full-text search" if body else "archive listing",
                       "returned": len(items)}
                if resp.narrowed:
                    cov["narrowed"] = "; ".join(resp.notes)
                if local_filter:
                    kept = [c for c in items if q.matches(c.get("body"))]
                    cov["after_local_exclusion"] = len(kept)
                    items = kept
                if len(items) >= limit or len(resp.data or []) >= int(resp.params.get("limit", per_scope)):
                    cov["more_available"] = True
                coverage.append(cov)
            for c in items:
                found.setdefault(strip_prefix(c.get("id")) or "", c)

        rows = sorted(found.values(), key=lambda c: c.get("created_utc") or 0, reverse=direction == "desc")
        rows = rows[:limit]
        threads = await _threads(ctx, rows)
        if q.has_exclusions:
            notes.append("Exclusions (-word, NOT) were applied by this tool after the archive's search.")
        if any(c.get("method", "").startswith("partial local scan") for c in coverage):
            notes.append(
                "Partial local scan: the archive's search failed, so only the newest (or oldest) part of the "
                "window was read and filtered here. Older matches may exist; narrow the window to reach them."
            )
        if not rows:
            notes.append(
                "No matching comments. The archive matches whole words with stemming; a word joined to "
                "another by '/' (e.g. 'undervolt/underclock') may not match in the archive's own search."
            )
        items = [_search_row(c) for c in rows]
        return await make_result(
            ctx.client,
            notes=notes,
            comments=True,
            items_key="comments",
            query=q.show() or None,
            query_sent=body,
            window=window.describe(),
            sort=sort.strip().lower(),
            coverage=coverage,
            threads=threads,
            items=items,
        )


def _thread_notes(raw_post: dict[str, Any] | None, total: int, loaded: int, sort: str) -> list[str]:
    notes: list[str] = [
        "When you report this thread, say it comes from the Arctic Shift archive (not live Reddit), give "
        f"{total} (comment_counts.in_archive) as the number of comments, and call scores archived snapshots."
    ]
    if raw_post is None:
        notes.append("The post itself is not in the archive; only its comments are shown.")
    else:
        n = raw_post.get("num_comments")
        if isinstance(n, int) and n != total:
            notes.append(
                f"The post's num_comments ({n}) is a snapshot from when it was archived; the archive holds "
                f"{total} comments for this thread. Use comment_counts, not num_comments."
            )
    if loaded < total:
        notes.append(
            f"The archive returned {loaded} of {total} comments in one request; the sort ranks those "
            f"{loaded} only, and the rest are in `more` stubs."
        )
    if sort == "top":
        notes.append("Sorted by archived snapshot score, then oldest first; Reddit's 'best' sort needs live votes.")
    return notes


def _any_truncated(c: dict[str, Any]) -> bool:
    return bool(c.get("truncated")) or any(_any_truncated(r) for r in c.get("replies", []) if "body" in r)


def _scope_label(sub: str | None, author: str | None, link: str | None) -> str:
    parts = []
    if sub:
        parts.append(f"r/{sub}")
    if author:
        parts.append(f"u/{author}")
    if link:
        parts.append(f"post {link}")
    return ", ".join(parts)


def _search_row(c: dict[str, Any]) -> dict[str, Any]:
    out = shape_comment(c, text_chars=SEARCH_BODY_CHARS)
    out.pop("is_submitter", None)
    if out.get("body") in _DELETED:
        out["body"] = f"{out['body']} (on Reddit; the archive has no text)"
    return out


async def _scan(
    ctx: ServerContext,
    params: dict[str, Any],
    q: CommentQuery,
    window: Any,
    direction: str,
    pages: int,
    want: int,
    error: QueryTooHeavy,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """T6: list the window without `body=` and filter it here. Bounded by `pages` requests."""
    reason = "busy (fast HTTP 422)" if getattr(error, "fast", False) else "timed out (HTTP 422)"
    cov: dict[str, Any] = {"method": f"partial local scan: the archive's search {reason}", "scanned": 0}
    if pages == 0:
        cov["method"] += "; scan_pages is 0, so nothing was scanned"
        return [], cov
    base = {k: v for k, v in params.items() if k not in ("body", "after", "before", "limit")}
    after, before = window.after, window.before
    seen: set[str] = set()
    matches: list[dict[str, Any]] = []
    span: list[float] = []
    exhausted = False
    for _ in range(pages):
        page_params = {**base, "limit": SCAN_PAGE, "after": after, "before": before}
        resp = await ctx.client.get("comments/search", page_params, fields=DEFAULT_COMMENT_FIELDS)
        data = [c for c in resp.data or [] if isinstance(c, dict)]
        new = [c for c in data if (strip_prefix(c.get("id")) or "") not in seen]
        if not new:
            exhausted = True
            break
        for c in new:
            seen.add(strip_prefix(c.get("id")) or "")
            if isinstance(c.get("created_utc"), (int, float)):
                span.append(c["created_utc"])
            if q.matches(c.get("body")):
                matches.append(c)
        cov["scanned"] += len(new)
        if len(data) < int(resp.params.get("limit", SCAN_PAGE)):
            exhausted = True
            break
        if len(matches) >= want:
            break
        times = [c["created_utc"] for c in new if isinstance(c.get("created_utc"), (int, float))]
        if not times:
            break
        if direction == "desc":
            before = int(min(times)) + 1  # +1 and de-duplication: items can share a second
        else:
            after = int(max(times)) - 1
    if span:
        cov["scanned_span"] = f"{iso(min(span))} to {iso(max(span))}"
    cov["window_fully_scanned"] = exhausted
    cov["matched"] = len(matches)
    return matches, cov


async def _threads(ctx: ServerContext, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The posts the comments belong to: title and permalink, one posts/ids call."""
    counts: dict[str, int] = {}
    for c in rows:
        link = strip_prefix(c.get("link_id"))
        if link:
            counts[link] = counts.get(link, 0) + 1
    if not counts:
        return []
    posts = await ctx.client.get_ids("posts", list(counts), fields=THREAD_FIELDS)
    by_id = {strip_prefix(p.get("id")): p for p in posts}
    out = []
    for link, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        p = by_id.get(link)
        if p is None:
            out.append({"id": link, "matching_comments": n, "note": "post not in the archive"})
            continue
        t = shape_post(p)
        t.pop("selftext", None)
        t.pop("retrieved_on", None)
        title = t.get("title") or ""
        if len(title) > 150:
            t["title"] = title[:150] + " …"
        t["matching_comments"] = n
        out.append(t)
    return out
