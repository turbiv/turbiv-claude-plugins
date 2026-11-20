# Architecture

The plugin starts one stdio MCP server: `uv run --directory ${CLAUDE_PLUGIN_ROOT} reddit-mcp` (see `.mcp.json`).
The server talks only to the Arctic Shift API host and its status host.

```
src/reddit_mcp/
  server.py          build_server(client=None) -> FastMCP; main(). Registers every module in tools.MODULES.
  context.py         ServerContext(client): what each register(mcp, ctx) receives.
  arctic/            the client module. Shared by all sessions; owned by Session 1.
    config.py        Settings (env vars, D1 host guard, R1 floor)
    client.py        ArcticShiftClient, field whitelists, batch sizes
    cache.py         ResponseCache (SQLite), NullCache
    errors.py        InputError, ArchiveError and its subclasses, format_error()
    freshness.py     the status feed in plain words; ingest warnings (L1, L2, O4)
    helpers.py       labels, archive_tool, shaping, trimming, time, IDs, make_result
  tools/
    status.py        Session 1: archive_status
    posts.py         Session 2
    comments.py      Session 3
    discovery.py     Session 4
tests/
  conftest.py        fixtures: client, fake_archive, fake_time; blocks real sockets
  support.py         FakeArchive, FakeTime, make_client, load_fixture, PROBE_TIME
  fixtures/<area>/   saved archive responses (client, status, posts, comments, discovery)
  posts/ comments/ discovery/   each session's own tests go here
evals/<case>/        claude plugin eval cases (see evals/README.md)
```

## Ownership

- **Sessions 2, 3 and 4** each edit only:
  - their own `tools/<module>.py`
  - `tests/<module>/` and `tests/fixtures/<module>/`
  - their own eval case folders
- **The shared parts:** `arctic/`, `server.py`, `context.py`, `conftest.py` and `support.py` are shared. Do not
  change them. If you need a change there, leave a note for the coordinating session.

## Writing a tool module

```python
from ..arctic import (
    DEFAULT_POST_FIELDS, InputError, archive_tool, make_result, resolve_window, shape_post,
)
from ..context import ServerContext


def register(mcp, ctx: ServerContext) -> None:
    @archive_tool(mcp)
    async def list_posts(subreddits: list[str], sort: str = "new", time: str | None = None,
                         after: str | None = None, before: str | None = None, limit: int = 25) -> dict:
        """List posts in one or more subreddits. ..."""
        window = resolve_window(time, after, before)            # T8: absolute epoch seconds
        resp = await ctx.client.get(
            "posts/search",
            {"subreddit": subreddits[0], "sort": "desc", "limit": limit, **window.params()},
            fields=DEFAULT_POST_FIELDS,                          # R3: required
        )
        posts = [shape_post(p) for p in resp.data]               # O1, O2, O6
        return await make_result(ctx.client, items=posts, window=window.describe())
```

- **What `archive_tool` does:**
  - It registers the function with read-only annotations.
  - It appends `SOURCE_NOTE` to the description.
  - It turns `ArchiveError` and `InputError` into a `ToolError` whose text starts with the error category.
    For example: `archive unavailable: …`, `the query is too heavy for the archive …`, `input error: …`.
- **What `make_result` does:**
  - It puts `source` (the archive notice) first, then `warnings` (stalled ingest, comment lag), then `notes`.
  - It cuts the item list to fit the 8,000-token budget. A cut sets `truncated: true` and `omitted_items`.
  - Pass `comments=True` for results that hold comments: this adds the completeness note (O4).
- **A feature the archive cannot give:** `raise ToolError(unavailable_feature("hot"))`. Examples are hot, rising,
  best, relevance, r/all and global search.

## The client: `ArcticShiftClient`

`await client.get(path, params=None, *, fields=None, full=False, retry_422=2, use_cache=True, ttl=None) -> ArchiveResponse`

- **`path`:** relative to the base URL, e.g. `"posts/search"`, `"comments/tree"`, `"subreddits/search"`.
- **`params`:**
  - `None` values are dropped. Lists are joined with commas. Booleans become `true` or `false`.
  - `fields` is not allowed in `params`.
- **`fields`:** required for `posts/search`, `posts/ids`, `comments/search` and `comments/ids`. The names must be
  in `POST_FIELDS` or `COMMENT_FIELDS`. `full=True` asks for full objects instead. You need full objects for
  `permalink`, `upvote_ratio`, `controversiality`, `domain`, `is_self`, `removed_by_category` and `_meta`.
- **Refused before any request, with `InputError`:**
  - `limit` above 100 on a search, or `limit=auto`
  - `after` or `before` that are not epoch seconds (use `to_epoch` or `resolve_window`)
  - `query`, `title`, `selftext` or `body` without a `subreddit`, `author`, `link_id` or `parent_id` (T5)
  - any host that is not one of the two archive hosts (D1)
- **What it returns:** `ArchiveResponse` has these fields:
  - `.data`: the `data` member of the JSON body
  - `.params`: what was actually sent, after any 422 narrowing
  - `.narrowed` and `.notes`: whether a 422 retry changed `limit`, and how
  - `.from_cache`, `.attempts`, `.elapsed`
- **Pacing:** one request in flight, and at least `min_interval` seconds (default 1 s, floor 0.5 s) between the
  end of one request and the start of the next (R1). Calls from parallel tools queue behind each other.
- **The cache:**
  - **Immutable:** `*/ids` answers where every item is final, and search answers with an absolute `before`
    more than 72 h ago where every item is final. Final means `_meta.retrieved_2nd_on` is set, or the item is
    more than 72 h old.
  - **Everything else:** a TTL of `REDDIT_MCP_CACHE_TTL` (default 600 s), or the call's own `ttl`.
  - Errors are never cached.

`await client.get_ids("posts" | "comments", ids, fields=..., full=False) -> list`

- Splits the IDs into calls of 500 (R5). Strips `t1_` and `t3_` prefixes. Removes duplicates.

`await client.get_batched(path, param, values, batch_size, params=None, **get_kwargs) -> list`

- The generic splitter. Use the limits `SHORT_LINKS_BATCH` (1000), `RULES_BATCH` (1000), `WIKI_PATHS_BATCH` (100)
  and `IDS_BATCH` (500).

`await client.status(max_age=60) -> dict`

- The raw status feed. Prefer `get_freshness(client)`, which returns a `Freshness` with `.summary()` and
  `.warnings`.

## Errors

All errors are raised by the client. With `archive_tool`, a tool rarely needs to catch them.

| Exception | When | What to know |
|---|---|---|
| `InputError` (a `ValueError`) | bad input, found before any request | |
| `QueryRejected` | HTTP 400 or another 4xx, or an `error` member in a 200 answer | `.error` is the archive's text, verbatim (E4) |
| `QueryTooHeavy` | HTTP 422 after 2 retries; each retry halved `limit` (E2) | `.attempts`, `.suggestions`, `.fast`: True when every 422 came in under 1 s, which means the archive is busy, not that the query is invalid (probes Q7) |
| `RateLimited` | HTTP 429 twice. The client waited for `x-ratelimit-reset-at`, at most 65 s, between the two (E1) | |
| `ArchiveUnavailable` | 5xx, Cloudflare 52x/530, DNS failure, refused connection, timeout, or a body that is not JSON (E3) | `.outage` is False when the status page says the API is up; then it is more likely a query error. `.components`, `.status_error`. The text says there is no fallback to reddit.com (E5) |

To narrow a query yourself, pass `retry_422=0` and catch `QueryTooHeavy`. `deep_search` does this.

## Helpers (`reddit_mcp.arctic`)

| Helper | What it does |
|---|---|
| `permalink_post(sub, id)` | `https://www.reddit.com/r/{sub}/comments/{id}/` (O2) |
| `permalink_comment(sub, link_id, id)` | `https://www.reddit.com/r/{sub}/comments/{link_id}/_/{id}/` |
| `score_status(item, now=None)` | `"snapshot"` or `"initial"`; the evidence rules are in its docstring and in probes Q5 (O1) |
| `shape_post(item)`, `shape_comment(item)` | the output dict for one item: `permalink`, `created_utc`, `created`, `score`, `score_status`, trimmed text with `truncated: true` (selftext 1,500 chars, body 800), `retrieved_on`, `retrieved_2nd_on`, `upvote_ratio` clamped to 0–1; no `downs` |
| `trim_text(text, max_chars)` | returns `(text, truncated)` |
| `estimate_tokens(obj)`, `fit_to_budget(result, key, max_tokens=8000)` | output size (criterion 7) |
| `to_epoch(value)` | epoch seconds or ms, `"2025"`, `"2025-03"`, ISO dates and datetimes, `"3 months"`, `"2d"`; a bare `m` is refused as ambiguous |
| `resolve_window(time, after, before)` | returns a `Window(after, before, label)`. `time` takes `hour`/`day`/`week`/`month`/`year`/`all` or a span such as `"last 3 months"`. Months are calendar months. `before="2025"` means the end of 2025. `.params()` gives the dict to send, `.describe()` the text to show |
| `parse_post_ref(ref)` | the post ID from an ID, `t3_` ID, comment URL or redd.it link; share links raise `InputError` |
| `parse_comment_ref(ref)` | `(comment_id, post_id or None)` |
| `strip_prefix(id)`, `chunked(seq, n)`, `iso(ts)`, `age_words(seconds)` | small utilities |
| `ARCHIVE_NOTICE`, `SOURCE_NOTE`, `COMMENT_COMPLETENESS_NOTE`, `unavailable_feature(name)` | the standard labels (O3, O4, T4) |
| `make_result(client, items=..., notes=..., comments=False, **fields)` | the result envelope |

## Settings (environment)

| Variable | Default | Meaning |
|---|---|---|
| `REDDIT_MCP_BASE_URL` | `https://arctic-shift.photon-reddit.com/api` | archive API (D3); a Reddit host is refused |
| `REDDIT_MCP_STATUS_URL` | `https://status.arctic-shift.photon-reddit.com/api` | status feed |
| `REDDIT_MCP_MIN_INTERVAL` | `1.0` | seconds between requests; never below 0.5 |
| `REDDIT_MCP_TIMEOUT` | `30` | seconds per request |
| `REDDIT_MCP_CACHE` | `~/.cache/reddit-mcp/cache.sqlite3` | cache file, or `off` |
| `REDDIT_MCP_CACHE_TTL` | `600` | seconds, for data that is not final |
| `REDDIT_MCP_USER_AGENT` | `reddit-research-mcp/<version> (…; +<project URL>)` | R6 |

`claude plugin eval` lets a case set only `EVAL_*` variables. So each setting also reads an `EVAL_` copy, for
example `EVAL_REDDIT_MCP_BASE_URL`. The plain name wins when both are set.

## Tests

- **Async tests:** use `pytestmark = pytest.mark.anyio`. The `client` fixture is wired to `fake_archive` and
  `fake_time`.
- **Fake answers:** `fake_archive.add("posts/search", reply, ...)` answers like the archive. A reply is a JSON
  body, `(status, body[, headers])`, an exception, or `callable(request)`. The last reply repeats.
  `fake_archive.add_status()` serves the saved status feed.
- **What was sent:** `fake_archive.requests`, `.paths()` and `.params(i)` show what the client sent.
  `fake_time.sleeps` shows the pacing.
- **Saved responses:** `load_fixture("comments/tree-wi7uhk.json")` loads one; they are listed in
  `docs/probes.md`.
- **Tool tests:** run the tools through `fastmcp.Client(build_server(client))`. `tests/test_status.py` is an
  example.
- **The guard:** real sockets are blocked. A test marked `@pytest.mark.live` runs only with `REDDIT_MCP_LIVE=1`.
  Keep live tests to a few requests.
- **Checks on every tool:** `tests/test_server.py` checks every registered tool, including yours. Each must be
  read-only, carry the source note, have no name that sounds like a write, and take no key or login parameter.
