# Arctic Shift Reddit archive API as the data source for a keyless Reddit MCP server

Research date: 2026-11-20. Primary sources: the `ArthurHeitmann/arctic_shift` GitHub repo (api/README.md, README.md, file_content_explanations.md, commits, releases, issues), the status page's JSON feed, and 5 light live API probes made 2026-11-20 21:55–21:56 UTC, each at least 3 s apart and each using `fields=` or `limit=1..3`. Abbreviations used below: AS = Arctic Shift; API README = https://github.com/ArthurHeitmann/arctic_shift/blob/master/api/README.md

Live probes, for reference in citations:
- P1: `GET /api/posts/search?subreddit=AskReddit&limit=2&sort=desc&fields=id,created_utc,retrieved_on,score,num_comments` returned 200.
- P2: `GET /api/comments/search?subreddit=AskReddit&limit=2&sort=desc&fields=id,created_utc,retrieved_on,score` returned 200.
- P3: `GET /api/posts/search?subreddit=AskReddit&limit=1&sort=desc&before=3d` (full object) returned 200.
- P4: `GET /api/posts/search?subreddit=AskReddit&query=python&limit=3&sort=desc&fields=id,title,created_utc` returned 422.
- P5: `GET /api/posts/search?subreddit=rust&query=async%20runtime&limit=3&sort=desc&fields=id,title,created_utc,score` returned 422.

---

## 1. Complete API reference (every endpoint, parameter and limit)

### Takeaway
AS exposes about 20 read-only GET endpoints under `https://arctic-shift.photon-reddit.com/api/`. They cover ID lookup, post/comment search, comment trees, aggregations, subreddits (search/rules/wikis), users (search/interactions/flairs), short-link resolution and time series. Search sorts only by `created_utc` (asc/desc). `limit` is at most 100, or `"auto"` for 100–1000. Keyword search on posts works only together with `subreddit` or `author`, and not on very active ones.

### Cited Findings

**General**
- Base URL `https://arctic-shift.photon-reddit.com`, status page `https://status.arctic-shift.photon-reddit.com`, search UI `/search`. The API is provided with "No uptime or performance guarantees :)" — [API README](https://github.com/ArthurHeitmann/arctic_shift/blob/master/api/README.md)
- Responses are JSON shaped `{"data": [...]}`. Errors come back as `{"data":null,"error":"..."}` — [P1/P4 live probe](https://arctic-shift.photon-reddit.com/api/posts/search?subreddit=AskReddit&limit=2&sort=desc&fields=id,created_utc); [issue #85](https://github.com/ArthurHeitmann/arctic_shift/issues/85)
- Responses carry `access-control-allow-origin: *`, `server: cloudflare` and `x-powered-by: Express`, plus a weak `etag`. No authentication or API key is needed — [P1 live probe headers]
- The API source code is not public. The maintainer gives "security through obscurity" around throttling, rate limits and request queuing as one reason — [issue #41](https://github.com/ArthurHeitmann/arctic_shift/issues/41)

**ID lookup**: `/api/posts/ids`, `/api/comments/ids`, `/api/subreddits/ids`, `/api/users/ids` — [API README](https://github.com/ArthurHeitmann/arctic_shift/blob/master/api/README.md)

| Param | Type | Default | Notes |
|---|---|---|---|
| `ids` | ID[] | | comma-separated, **limit 500** |
| `md2html` | bool | false | adds `selftext_html`/`body_html` |
| `fields` | string | | comma-separated field list |

**Post and comment search**: `/api/posts/search`, `/api/comments/search` — [API README](https://github.com/ArthurHeitmann/arctic_shift/blob/master/api/README.md)

Common parameters:

| Param | Type | Default | Notes |
|---|---|---|---|
| `author` | string | | `u/` prefix ignored |
| `subreddit` | string | | `r/` prefix ignored |
| `author_flair_text` | string | | keyword search, same limits as `title`/`body` |
| `after` / `before` | Date | | filters on `created_utc` |
| `limit` | int 1–100 or `"auto"` | 25 | `auto` returns 100–1000 results, depending on server capacity |
| `sort` | `asc`/`desc` | | sorts by `created_utc` only |
| `md2html` | bool | false | |
| `fields` | string | | see selectable fields |
| `format` | `json`/`rss`/`jsonfeed` | json | added 2026-08-09 ([commit ec2e6b7](https://github.com/ArthurHeitmann/arctic_shift/commit/ec2e6b75b0dbb40788dc297a2ef73e61a0629522), [issue #60](https://github.com/ArthurHeitmann/arctic_shift/issues/60)) |

Post-only parameters: `crosspost_parent_id` (ID), `over_18` (bool), `spoiler` (bool), `title`, `selftext`, `link_flair_text`, `query` (keyword search over title and selftext; "Only in use with `author` or `subreddit` parameter (not supported with very active users or subreddits)"), `url` (prefix match), `url_exact` (bool, default false).

Comment-only parameters: `body` (keyword search; only together with `author`, `subreddit`, `link_id` or `parent_id`; not supported with very active users or subreddits), `link_id` (post ID), `parent_id` (comment ID, or empty for top-level comments).

**Comment tree**: `/api/comments/tree` — [API README](https://github.com/ArthurHeitmann/arctic_shift/blob/master/api/README.md)

| Param | Type | Default | Notes |
|---|---|---|---|
| `link_id` | ID | | required |
| `parent_id` | ID | | unset means the whole post |
| `limit` | int 1–25000 | 50 | "Something like 9999 returns all comments" |
| `start_breadth` | int ≥0 | 4 | collapsing |
| `start_depth` | int ≥0 | 4 | collapsing |
| `md2html` | bool | false | |

- When `limit` is exceeded, comments collapse into Reddit-style `"kind": "more"` objects with a `children` ID list. `start_breadth` and `start_depth` drop by 1 per level, and anything outside them collapses — [API README](https://github.com/ArthurHeitmann/arctic_shift/blob/master/api/README.md)
- The tree limit was raised and "optimizations and limits" were added in Aug 2025 for very large threads — [issue #33](https://github.com/ArthurHeitmann/arctic_shift/issues/33); [commit "update comments tree limit" 2025-08-23](https://github.com/ArthurHeitmann/arctic_shift/commits/master/api/README.md)

**Aggregations**: `/api/posts/search/aggregate`, `/api/comments/search/aggregate`. All search filters apply. "Very active users or subreddits have a high chance of timing out." — [API README](https://github.com/ArthurHeitmann/arctic_shift/blob/master/api/README.md)

| Param | Type | Default | Notes |
|---|---|---|---|
| `aggregate` | `created_utc`/`author`/`subreddit` | | |
| `frequency` | interval string | | required when `aggregate=created_utc` (e.g. `year`) |
| `limit` | int ≥1 or empty | empty | empty means no limit |
| `min_count` | int ≥0 | | not used with created_utc |
| `sort` | asc/desc | asc for created_utc, else desc | |

**Subreddit search**: `/api/subreddits/search`. "List of subreddits and their data is only updated infrequently. Aggregate `_meta` data is updated more frequently." — [API README](https://github.com/ArthurHeitmann/arctic_shift/blob/master/api/README.md)

Parameters: `subreddit`, `subreddit_prefix`, `after`/`before` (subreddit creation date), `min_subscribers`, `max_subscribers`, `over18`, `limit` 1–1000 (default 25), `sort` asc/desc (default desc), `sort_type` `created_utc`/`subscribers`/`subreddit` (default subscribers), `fields`.

**Subreddit rules**: `/api/subreddits/rules?subreddits=a,b`, up to 1000 names — [API README](https://github.com/ArthurHeitmann/arctic_shift/blob/master/api/README.md)

**Wikis**: `/api/subreddits/wikis` takes `paths` (up to 100), `subreddit` (all pages) and `limit` (default and max 100). `/api/subreddits/wikis/list?subreddit=` lists all wiki paths — [API README](https://github.com/ArthurHeitmann/arctic_shift/blob/master/api/README.md)
- The subreddit, rules and wiki datasets have no release schedule; the requester says "released only once a year in January". The maintainer says most of the data stays the same — [issue #38](https://github.com/ArthurHeitmann/arctic_shift/issues/38)

**User search**: `/api/users/search` holds only aggregate data (names, IDs, post/comment counts, first/last activity, karma). It "is only updated infrequently", and IDs may be `null` — [API README](https://github.com/ArthurHeitmann/arctic_shift/blob/master/api/README.md)

Parameters: `author`, `author_prefix`, `min_num_posts`, `min_num_comments`, `active_since`, `min_karma`, `limit` 1–1000 (default 25), `sort` (default desc), `sort_type` `author`/`total_karma` (default total_karma; "Karma is the sum of post/comment scores").
- The maintainer said in Oct 2026: "The /users endpoints have not been update recently and currently has outdated data". A user measured AS karma running about 2x lower than real karma, and the user object has no account age — [issue #69](https://github.com/ArthurHeitmann/arctic_shift/issues/69)

**User interactions** ("For very active users (especially bots), this has a high chance of timing out"; narrow with after/before) — [API README](https://github.com/ArthurHeitmann/arctic_shift/blob/master/api/README.md)
- `/api/users/interactions/users` (aggregated counts) and `/api/users/interactions/users/list` (individual interactions). Parameters: `author` (required), `subreddit`, `after`, `before`, `min_count`, `limit` (default 100, empty means no limit). Interactions are: commented under a post or comment, or someone replied to the author's post or comment.
- `/api/users/interactions/subreddits`: `author` (required), `weight_posts` (1.0), `weight_comments` (1.0), `before`, `after`, `min_count`, `limit` (default 100, empty means no limit).

**Aggregate flairs**: `/api/users/aggregate_flairs?author=` groups a user's `author_flair_text` values by subreddit — [API README](https://github.com/ArthurHeitmann/arctic_shift/blob/master/api/README.md). An open bug report says it returns HTTP 500 for an author with no flairs — [issue #79](https://github.com/ArthurHeitmann/arctic_shift/issues/79)

**Short links**: `/api/short_links?paths=/r/running/s/3TzXiyxaMD,...` takes up to 1000 paths (case sensitive) and returns the full link — [API README](https://github.com/ArthurHeitmann/arctic_shift/blob/master/api/README.md)

**Time series**: `/api/time_series` takes `key`, `precision` (`year`/`quarter`/`month`/`week`/`day`/`hour`/`minute`), `after` and `before`. Keys: `global/posts/count`, `global/comments/count`, `global/{posts,comments}/sum_score`, `global/{posts,comments}/sum_retrieved_after_seconds`, `r/<sub>/posts/count`, `r/<sub>/comments/count`, `r/<sub>/{posts,comments}/sum_score`, `r/<sub>/subscribers`. "Data might not be 100% accurate, and might take a few hours or days to fully update." — [API README](https://github.com/ArthurHeitmann/arctic_shift/blob/master/api/README.md)
- The subscriber history comes from the `subreddit_subscribers` field on each archived post — [issue #45](https://github.com/ArthurHeitmann/arctic_shift/issues/45)

**Data type notes** — [API README](https://github.com/ArthurHeitmann/arctic_shift/blob/master/api/README.md)
- Selectable `fields`:
  - Posts and comments: `author, author_fullname, author_flair_text, created_utc, distinguished, id, retrieved_on, subreddit, subreddit_id, score`.
  - Posts: `crosspost_parent, link_flair_text, num_comments, over_18, post_hint, selftext, spoiler, title, url`.
  - Comments: `body, link_id, parent_id`.
  - Subreddits: `created_utc, description, public_description, display_name, id, over18, retrieved_on, subscribers, title` plus `_meta` fields.
- Asking for a field outside the list gives 400, for example `'permalink' is not a valid field` — [issue #85](https://github.com/ArthurHeitmann/arctic_shift/issues/85). Fields such as `permalink`, `upvote_ratio`, `controversiality` and `_meta` are therefore only available in full objects.
- A full post object (P3) had 111 keys, including `permalink`, `upvote_ratio`, `subreddit_subscribers`, `removed_by_category`, `link_flair_richtext`, `media`, `secure_media`, `thumbnail`, `is_self`, `domain`, `_meta` — [P3 live probe]
- Booleans accept `true/1/yes/y` and `false/0/no/n`. IDs are base36, optionally prefixed `t3_`/`t1_`. A `u/` or `r/` prefix is ignored.
- Dates accept epoch seconds, epoch milliseconds, partial ISO 8601 (`2020-01-01`, `2020-01-01 00:00:00`, `2020-01-01T00:00:00.000Z`) or an offset from now (`1year`, `3m`, `2d`, `1hour`, `5min`, `10s`).
- Keyword search: "This section is now out of date! ... Currently: when searching posts: simply keyword search only (fast), when searching comments: postgres FTS features (slow)". The documented FTS syntax (`websearch_to_tsquery`) is: `w1 w2` (AND), `"w1 w2"` (phrase / followed-by), `w1 OR w2`, `w1 -w2`. This wording was changed on 2026-01-21 — [API README](https://github.com/ArthurHeitmann/arctic_shift/blob/master/api/README.md); [commit 216d9fb](https://github.com/ArthurHeitmann/arctic_shift/commit/216d9fb9832983a77f628eab304bd651318dd62c)
- No negative filters exist (for example, you cannot exclude subreddits): "negative filters can be very slow" — [issue #49](https://github.com/ArthurHeitmann/arctic_shift/issues/49)
- No Reddit-wide comment or post keyword search exists: "such a query could take hours" — [issue #8](https://github.com/ArthurHeitmann/arctic_shift/issues/8)
- Sorting by score is not supported. An open feature request asks for it; the maintainer said his "focus is on keeping the API running reliably" — [issue #56](https://github.com/ArthurHeitmann/arctic_shift/issues/56)

### Inferences
- The `query`/`title`/`selftext` parameters are the only full-text tools, and they need a subreddit or author scope. An MCP `search` tool therefore cannot offer Reddit-wide keyword search through AS.
- The `fields` whitelist leaves out `permalink`. The MCP server can build permalinks itself (`/r/{subreddit}/comments/{id}/`), or request full objects when it needs `upvote_ratio`, `_meta` or media.
- Offset date syntax: `3m` and `5min` are listed separately, so `m` probably means month, not minute. This is unconfirmed; use `min`, `hour`, `d` or `year` explicitly.

### Gaps
- No public list of errors or HTTP status codes exists beyond 422, 429 and 500 seen in issues.
- Whether `/api/users/ids` takes the same parameters as the others (the docs point to "see notes" only) is not stated.
- The `frequency` interval vocabulary for aggregations is not listed; only `year` appears in examples.
- The comment tree endpoint's child ordering (by time? by score?) is not documented.
- Whether a search with no `subreddit`/`author` filter (global newest) is allowed or fast was not probed.

---

## 2. Data freshness, and whether scores and num_comments are updated after ingest

### Takeaway
New posts are archived about 10–15 s after creation. Comments currently take minutes, and ingest has fallen 1–2 days behind during incidents, because Reddit switched to random comment IDs in Oct 2026. Each item gets exactly one re-scrape, about 36 h after creation (one sample showed 48 h). It updates score, num_comments, upvote_ratio, controversiality, locked/stickied and deletion flags. Nothing is refreshed after that, so scores are frozen snapshots, and items younger than about 36 h show `score` 1/0 and `num_comments` 0.

### Cited Findings
- "After roughly 36 hours, all data is updated and should then be the same as that released in .zst dumps. Before that, `score`, `num_comments`, etc. will be 1 or 0, since data is archived initially the moment it was posted." — [API README](https://github.com/ArthurHeitmann/arctic_shift/blob/master/api/README.md)
- Since 2023-11 everything is retrieved a second time with a 36 h delay. The 2nd pass updates `archived, controversiality, downs, hide_score, locked, num_comments, num_crossposts, over_18, score, score_hidden, spoiler, stickied, ups, upvote_ratio`. It also adds `_meta.retrieved_2nd_on`, `_meta.was_deleted_later`, `_meta.was_initially_deleted` (with restored body), `_meta.removal_type`, `_meta.is_edited` and `_meta.note="initially_unavailable"` — [file_content_explanations.md](https://github.com/ArthurHeitmann/arctic_shift/blob/master/file_content_explanations.md)
- The API began serving the updated 2nd-pass values in May 2024 — [issue #2](https://github.com/ArthurHeitmann/arctic_shift/issues/2)
- "Each post and comment is retrieved once shortly after it was created and a second time 36 hours later" — [issue #21](https://github.com/ArthurHeitmann/arctic_shift/issues/21). "Most content will only have been retrieved once or twice, and since then the scores have not been updated"; Reddit fuzzes votes by "+/- a couple of percent"; `downs` is always 0 and `ups` equals `score` — [issue #24](https://github.com/ArthurHeitmann/arctic_shift/issues/24)
- Original text is preserved: "Posts and comments are archived within a few seconds of their creation. And after 1.5 days the upvotes and some other data is updated." — [issue #39](https://github.com/ArthurHeitmann/arctic_shift/issues/39)

Observed lags (live, 2026-11-20 21:55 UTC):
- **Posts (P1):** the newest r/AskReddit post was 28 s old at request time. `retrieved_on − created_utc` was 13 s and 8 s; `score: 1`, `num_comments: 0`.
- **Comments (P2):** the newest r/AskReddit comment was 681 s (about 11 min) old. Retrieval lag was 466 s and 653 s (about 8–11 min). The comment IDs are 13 characters (e.g. `19sxuik88o98i`), which is the new random ID format.
- **2nd pass (P3):** the 3-day-old post `1xyxhjz` had `retrieved_on` 16 s after creation and `_meta.retrieved_2nd_on` exactly 172,800 s (48 h) after creation, with `num_comments` 297, `score` 0 and `upvote_ratio` 0.458. This conflicts with the documented 36 h; the status feed below shows the posts trailing pass running at 36.0 h.

Status feed: `https://status.arctic-shift.photon-reddit.com/api` returns JSON with components `api`, `archiver`, `archiverTrailing`, `idNotifier` and `trailingIdNotifier`. Each has `isAvailable`, `failedAt`, `lastUpdateAt`, `mostRecentPostAt`, `mostRecentCommentAt` and `archiver.hasClients` — [status JSON](https://status.arctic-shift.photon-reddit.com/api); [status main.js](https://status.arctic-shift.photon-reddit.com/main.js)
- **Thresholds in main.js:** a component is green if updated within 2 min. The API's newest item must be under 3 min old, the archiver's under 1.5 min, and the ID notifier's under 30 s. The trailing components must sit at 36 h ± 2 min.
- **Snapshot at 21:56:46 UTC:**
  - archiver: newest post 9 s old, newest comment about 5.5 min old.
  - api: newest comment 34 s old.
  - archiverTrailing: newest post 36.0 h old; `mostRecentCommentAt` was `null`.
  - trailingIdNotifier: newest comment about 38.8 h old.
  - idNotifier: `mostRecentCommentAt` about 31 days old (about 2026-10-20), so comment ID scanning has stopped.

Comment ingest changed in Oct 2026:
- Reddit moved to non-monotonic, random comment IDs. Before that, "at least 99% of content was captured" by sequential ID scanning through `/api/info` — [issue #54](https://github.com/ArthurHeitmann/arctic_shift/issues/54)
- The maintainer expects comments to be "90%+ complete, ideally 95%" with the workaround, and says "it might take some time for most comments to be picked up". "As of today all comments have the new ids" was posted 2026-10-21 — [issue #53](https://github.com/ArthurHeitmann/arctic_shift/issues/53)
- On 2026-10-21: "Posts should be fine. Comments currently have a 1 - 2 day delay" — [issue #84](https://github.com/ArthurHeitmann/arctic_shift/issues/84). On 2026-10-15: disruptions "because of change reddit has made", then "mostly caught up" the next day — [issue #82](https://github.com/ArthurHeitmann/arctic_shift/issues/82)
- The archiver now reads at least some values from "reddits new gql api" — [issue #92](https://github.com/ArthurHeitmann/arctic_shift/issues/92)
- Volume is over 1M new posts and 10M new comments per day (2024 figure) — [issue #26](https://github.com/ArthurHeitmann/arctic_shift/issues/26). The October 2026 dump has 42,117,701 posts — [issue #92](https://github.com/ArthurHeitmann/arctic_shift/issues/92)
- Monthly dumps are released about 10–14 days after month end; for example "October 2026" was published 2026-11-14 — [releases](https://github.com/ArthurHeitmann/arctic_shift/releases)

### Inferences
- Treat every score as a single snapshot: the ingest value for items under 36 h old, or the 36–48 h value for older items. For a thread that is days, months or years old, `score` and `num_comments` reflect its state at about day 1.5, not today.
- "hot", "rising" and "top of the hour/day" cannot be computed meaningfully. MCP tool output should label score as "score at ~36h snapshot" and expose `retrieved_on` / `_meta.retrieved_2nd_on`.
- Because the comments trailing archiver reports `null`, the 2nd pass for comments may be disrupted after the ID change. Comment scores fetched now may stay at ingest values (1). This needs verification by checking `_meta.retrieved_2nd_on` on a comment older than 2 days. I did not test it to stay within the 5-probe budget.

### Gaps
- No re-scrape after the 2nd pass is documented anywhere.
- It is unclear why the sample post's second retrieval came at 48 h instead of 36 h (a schedule change, backlog, or 2nd-pass time keyed differently).
- Whether comment `num_comments`-style fields and comment scores are currently being re-scraped was not checked.

---

## 3. Rate limits, the "Timeout. Maybe slow down a bit" error, terms of use and bots

### Takeaway
Rate limits are dynamic. They are computed from server load and request complexity, use a 1-minute window, and no numbers are published. A 429 means "wait for the reset" (see `X-RateLimit-Reset` / `X-RateLimit-Reset-At`). A 422 "Timeout. Maybe slow down a bit" means the server aborted the query, either from overload or because the query is too complex; retry after a short wait, or narrow the query. Automated and even commercial clients are allowed "as is", as long as they respect the limits and do not try to bypass them. There is no license, terms page, API key or User-Agent rule.

### Cited Findings
- "If you're a normal user and only make a couple requests per second, you have nothing to worry about. ... Rate limits are calculated dynamically based on server load and request complexity. If you receive a 429 rate limit error code, you have to wait until your limits reset. You can use the `X-RateLimit-Reset` (seconds until reset) or `X-RateLimit-Reset-At` (timestamp of next reset) headers. Remember, this is a free service, so be considerate. If you want to process massive amounts of data, use the monthly dumps instead." — [API README](https://github.com/ArthurHeitmann/arctic_shift/blob/master/api/README.md)
- The 2026-07-25 doc change removed the earlier `X-RateLimit-Remaining` header reference and the line "Rate limits can change at any time" — [commit 06ab00b](https://github.com/ArthurHeitmann/arctic_shift/commit/06ab00b1e801c814e893d3803fae0aaec437d00b)
- **Observed headers (P1/P2):** `x-ratelimit-reset: 34` then `29` (seconds), and `x-ratelimit-reset-at: 1795211760000` (epoch **milliseconds**, on a whole minute, 21:56:00 UTC). There was **no** `X-RateLimit-Remaining` or `X-RateLimit-Limit` header, and `cf-cache-status: MISS`.
- **The maintainer on 429 vs 422:** "429 means that you made too made requests, and you should only retry once the current time period (1 minute) has elapsed. 422 is returned when the server aborts a request for one of various reason ... 1. Server is receiving too many requests and can't handle all of them. 2. A query took too long and timed out. There are certain requests which are too complex and will always time out." He also said: "When getting a 422, wait a short moment and try again", and "The 422 response is for some requests quite frequent." He declines to switch to 503 — [issue #66](https://github.com/ArthurHeitmann/arctic_shift/issues/66)
- In the same issue, a client hit 422 with `limit=100`, and the same cursor with `limit=50` succeeded immediately — [issue #66](https://github.com/ArthurHeitmann/arctic_shift/issues/66)
- The README section "Query timeout" says: "Query timed out" means a parameter combination that isn't optimized. Reduce `limit` or add `after`/`before`/`subreddit`/`author`. It "usually happens with `body`, `selftext` or `title`", and "Sometimes the database needs to warm up ... try again a second time" — [API README](https://github.com/ArthurHeitmann/arctic_shift/blob/master/api/README.md)
- The older message `"Slow down a little"` was a hard per-query time cap on big subreddits (r/conspiracy aggregate). The suggested fixes were a shorter time frame, downloading the data, or asking the maintainer to run it manually — [issue #12](https://github.com/ArthurHeitmann/arctic_shift/issues/12)
- **Live keyword probes:** `query=python` on r/AskReddit (P4) and `query="async runtime"` on r/rust (P5) both returned **HTTP 422 `{"data":null,"error":"Timeout. Maybe slow down a bit"}` in about 0.45–0.50 s**. The speed suggests fast rejection, not a real query timeout.
- **Commercial or automated use (Nov 2026):** an Apify paid actor asked for permission. The maintainer replied: "the data is provided as is. You have the freedom and responsibility to do whatever you want with it. Just adhere to the rate limits and don't try to bypass them. You could download the dumps and create your own database." The asker noted the repo "has no license or terms page" — [issue #91](https://github.com/ArthurHeitmann/arctic_shift/issues/91)
- The maintainer asked a user to stop posting AI-written walls of text in issues — [issue #66](https://github.com/ArthurHeitmann/arctic_shift/issues/66)
- **Compliance:** "If you wanted to be 100% compliant with reddits policies, you'd have to collect all the data yourself. However using 3rd party reddit datasets is pretty common in academic work" — [issue #39](https://github.com/ArthurHeitmann/arctic_shift/issues/39)
- **Contact:** Discord (raiderbv), email arctic.shift.contact@gmail.com, GitHub issues, and a removal/support Google Form — [README](https://github.com/ArthurHeitmann/arctic_shift/blob/master/README.md)
- **Self-hosting:** the API code is not released, though parameter-parsing and SQL-building files may be shared privately — [issue #41](https://github.com/ArthurHeitmann/arctic_shift/issues/41)

### Inferences
- Recommended client behaviour for an MCP server:
  - Run one request at a time. Throttle to 1 request/s or less, well under the "couple per second" comfort level, since many MCP users may share the service.
  - Always send `fields=`.
  - On 429, sleep until `X-RateLimit-Reset-At` (ms), which is at most about 60 s.
  - On 422, retry once or twice after 1–3 s with a smaller `limit` or a narrower `after`/`before` window, then give up with a clear message. Do not loop, because some queries always 422.
  - Use a descriptive User-Agent as courtesy, even though no rule requires one.
- Keyword search (`query`/`title`/`body`) should be treated as best-effort. Both probes failed on popular subreddits, so an MCP `search` tool needs a fallback, such as fetching a date-bounded window with `fields=title,selftext` and filtering client-side, or reporting failure honestly.

### Gaps
- No numeric rate limit is published, and the window was only observed indirectly (reset-at aligned to the minute).
- No documented User-Agent requirement, terms of use or license; none found in the repo.
- Whether `query` on posts currently works for any subreddit was not established within the probe budget; both of my probes failed.

---

## 4. Coverage gaps: deleted/removed content, excluded subreddits, opt-outs

### Takeaway
AS captures content seconds after posting, so later edits, deletions and mod removals usually do not erase the text. AutoMod or spam-filter removals at post time are never visible. Private and quarantined subreddits are excluded. Data before 2023-04 comes from Pushshift dumps. Users can opt out through a Google Form, which filters them from both the API and the dumps. Since Oct 2026, comment completeness has been about 90–95%, down from about 99%.

### Cited Findings
- "Content from private or quarantined subreddits is not included." All data is retrieved through the official Reddit API, and data for 2023-03 and earlier comes from the Pushshift dumps — [file_content_explanations.md](https://github.com/ArthurHeitmann/arctic_shift/blob/master/file_content_explanations.md); [issue #21](https://github.com/ArthurHeitmann/arctic_shift/issues/21)
- "The only exception is content that was removed by the auto moderator immediately after posting. It's not possible to view those comments" — [issue #39](https://github.com/ArthurHeitmann/arctic_shift/issues/39). "Comments show up the way they were archived. If at the time of archiving they were removed, that is how the'll look like" — [issue #90](https://github.com/ArthurHeitmann/arctic_shift/issues/90)
- Real-time archiving started around 2023-07-10; data before that has more or less final upvote numbers — [issue #2](https://github.com/ArthurHeitmann/arctic_shift/issues/2)
- The 2nd pass records `_meta.was_deleted_later`, `_meta.was_initially_deleted` (with the text restored) and `_meta.removal_type` — [file_content_explanations.md](https://github.com/ArthurHeitmann/arctic_shift/blob/master/file_content_explanations.md)
- **Removal requests:** via the Google Form. The maintainer has "functionality to filter users from data dumps and API requests", and the number of requests is "relatively small" — [issue #4](https://github.com/ArthurHeitmann/arctic_shift/issues/4); [README](https://github.com/ArthurHeitmann/arctic_shift/blob/master/README.md); [issue #75](https://github.com/ArthurHeitmann/arctic_shift/issues/75)
- **Comment completeness:** "at least 99%" before random IDs, and an expected "90%+ complete, ideally 95%" after them — [issue #54](https://github.com/ArthurHeitmann/arctic_shift/issues/54); [issue #53](https://github.com/ArthurHeitmann/arctic_shift/issues/53)
- **Known data holes:**
  - r/texas comments are missing for 2023-06-13 to 06-28 (the API-protest period) — [issue #34](https://github.com/ArthurHeitmann/arctic_shift/issues/34)
  - Some 2023-06 comments have a numeric `parent_id`, and the API wrongly returns the post as their parent (open) — [issue #88](https://github.com/ArthurHeitmann/arctic_shift/issues/88)
  - 479 October 2026 posts had `upvote_ratio` outside 0–1; it is clamped from now on — [issue #92](https://github.com/ArthurHeitmann/arctic_shift/issues/92)
- AS cannot make live Reddit API calls on request, so there is no on-demand enrichment — [issue #69](https://github.com/ArthurHeitmann/arctic_shift/issues/69)

### Inferences
- An MCP server built on AS will sometimes show content that Reddit itself now shows as deleted. Opted-out users will be silently absent. The tool should state that results are an archive, not live Reddit.

### Gaps
- No list of opted-out users or subreddits is published (by design). No documented subreddit-level opt-out exists, and no list of excluded subreddits beyond "private or quarantined" was found.

---

## 5. Project health, maintainer activity, status page, funding, shutdown risk

### Takeaway
The project is active but run by one person (ArthurHeitmann). Monthly dumps have shipped without a break through October 2026, and issues are usually fixed within hours. October 2026 was rough: at least 7 outage or 500 issues, plus the comment-ID change. The largest risk is Reddit ending public Data API access in March 2027; the maintainer is "Not sure yet what exactly will happen."

### Cited Findings
- **Repo stats (2026-11-20):** 1,892 stars, 12 open issues, not archived, last push 2026-11-14, Discussions disabled — [GitHub API repo metadata](https://github.com/ArthurHeitmann/arctic_shift)
- **Release cadence:** monthly "update schemas and download links" commits every month from 2025-11 through 2026-10. Recent API doc changes: `format` param (2026-08-09), rate-limit docs (2026-07-25), text-search docs (2026-01-21) — [commits](https://github.com/ArthurHeitmann/arctic_shift/commits/master); [releases](https://github.com/ArthurHeitmann/arctic_shift/releases)
- **Oct–Nov 2026 incidents** — [issue #77](https://github.com/ArthurHeitmann/arctic_shift/issues/77), [#82](https://github.com/ArthurHeitmann/arctic_shift/issues/82), [#84](https://github.com/ArthurHeitmann/arctic_shift/issues/84), [#85](https://github.com/ArthurHeitmann/arctic_shift/issues/85), [#86](https://github.com/ArthurHeitmann/arctic_shift/issues/86), [#87](https://github.com/ArthurHeitmann/arctic_shift/issues/87), [#89](https://github.com/ArthurHeitmann/arctic_shift/issues/89):
  - 2026-10-09/10: Cloudflare 52x errors and NXDOMAIN; "down for a few hours", back next day.
  - 2026-10-15: ingest disruption.
  - 2026-10-21: comments 1–2 days behind.
  - 2026-10-22 and 10-23: HTTP 500 on all `author` queries; "New day. New issue. Fixed again".
  - 2026-10-26: Cloudflare Tunnel Error 1033 (site offline), fixed the same day.
  - 2026-10-27: UI 500.
  - 2026-10-28: author search 500, fixed within about 4.5 h.
- Maintenance in May 2026 lasted "a few hours" — [issue #55](https://github.com/ArthurHeitmann/arctic_shift/issues/55)
- **Status page:** a JS page that polls `/api` every 30 s and shows yes/maybe/no per component (API, Archiver, Archiver trailing, ID Notifier, ID Notifier trailing, Clients). It has **no uptime history or percentages** — [status main.js](https://status.arctic-shift.photon-reddit.com/main.js); [status JSON](https://status.arctic-shift.photon-reddit.com/api). All components showed `isAvailable: true` on 2026-11-20.
- **Funding:** donations only (PayPal, Buy Me a Coffee). No guarantees — [README](https://github.com/ArthurHeitmann/arctic_shift/blob/master/README.md); [API README](https://github.com/ArthurHeitmann/arctic_shift/blob/master/api/README.md)
- **Infrastructure:** served through a Cloudflare Tunnel — [issue #86](https://github.com/ArthurHeitmann/arctic_shift/issues/86). The maintainer says he lacks the compute for heavy queries — [issue #12](https://github.com/ArthurHeitmann/arctic_shift/issues/12)
- **Reddit platform risk:** Reddit announced on 2026-09-30 that public Data API access ends in March 2027. New access requests stopped after 2026-10-31; from 2027-01-12 Reddit removes access for unregistered apps; RSS ended 2026-11-13 — [TechCrunch](https://techcrunch.com/2026/09/30/reddit-is-killing-rss-feeds-ending-public-api-access-because-of-ai-bots/). Asked about this, the maintainer said: "Not sure yet what exactly will happen." — [issue #76](https://github.com/ArthurHeitmann/arctic_shift/issues/76)
- Sources disagree on the user base: one commenter called the archive "arcticshift going away" (Sept 2026), but that was speculation; the maintainer later said he has workarounds — [issue #53](https://github.com/ArthurHeitmann/arctic_shift/issues/53)
- **Dump distribution is fragile:** torrent and filen.io links have been reported dead several times — [issue #42](https://github.com/ArthurHeitmann/arctic_shift/issues/42); [#81](https://github.com/ArthurHeitmann/arctic_shift/issues/81); [#83](https://github.com/ArthurHeitmann/arctic_shift/issues/83)

### Inferences
- The historical archive (2005 to now) will very likely stay queryable. Live ingest after March 2027 is uncertain. AS already reads some data from Reddit's GraphQL API ([issue #92](https://github.com/ArthurHeitmann/arctic_shift/issues/92)), which may or may not survive the Data API shutdown.
- An MCP server should treat AS as a best-effort source with expected multi-hour outages. It should check the status JSON (cheap, separate host) before blaming user queries.

### Gaps
- No uptime history or SLA data exists anywhere. I found no third-party uptime monitor for AS.
- The maintainer's stated plan for post-March-2027 ingest is unknown.

---

## 6. Backup sources: PullPush.io and other free Reddit archive APIs in 2026

### Takeaway
PullPush actively refuses keyless automated clients: it returns 429 with an explicit "no free scraping resources for agents" message and points to a paid service. Its data is reportedly stale. I found no other free, keyless, live Reddit archive API in 2026; the alternatives are paid vendors (Apify actors that wrap AS/PullPush, redditapis.com, Xpoz) or AS's own offline dumps.

### Cited Findings
- **Live check of PullPush (2026-11-20):**
  - `https://pullpush.io/` returned HTTP 403.
  - `https://api.pullpush.io/reddit/search/submission/?subreddit=rust&size=1` returned HTTP 429 with `{"error":"Rate limit exceeded. This website does not provide free scraping resources for agents. Please contact the administrator on Discord if you're interested in a paid scraping service."}`
  - (The first request from this IP, sent with a browser-like UA.)
- A user wrote in May 2026 that PullPush search "has data only till May, 2025" — [issue #56](https://github.com/ArthurHeitmann/arctic_shift/issues/56). This is user-reported and unverified.
- PullPush and AS are independent; PullPush helps distribute AS torrents — [issue #21](https://github.com/ArthurHeitmann/arctic_shift/issues/21). In 2024 the AS maintainer pointed users to PullPush for Reddit-wide search — [issue #8](https://github.com/ArthurHeitmann/arctic_shift/issues/8)
- 2026 web results are mostly vendor marketing. They name AS as the main free Pushshift successor and list paid options (Apify archive scrapers built on PullPush/AS, redditapis.com, Xpoz) — [redditapis.com Pushshift alternative](https://www.redditapis.com/pushshift-alternative); [dev.to (Apify author)](https://dev.to/benthepythondev/pushshift-alternative-scrape-historical-reddit-posts-comments-2026-13k2); [xpoz.ai](https://www.xpoz.ai/blog/comparisons/best-reddit-api-alternatives-2026/)
- The Apify actor author confirmed they use AS as a fallback when Reddit refuses — [issue #91](https://github.com/ArthurHeitmann/arctic_shift/issues/91)
- **Offline backup:** AS monthly .zst dumps and per-subreddit/user downloads via `https://arctic-shift.photon-reddit.com/download-tool` — [README](https://github.com/ArthurHeitmann/arctic_shift/blob/master/README.md)

### Inferences
- In practice there is no free keyless fallback archive. The realistic fallback for a keyless MCP is live Reddit `.json` endpoints (which Reddit is restricting; outside this note's scope), or degrading gracefully when AS is down.

### Gaps
- I did not verify PullPush's actual data cutoff, or whether it serves non-agent browser traffic.
- I found no other independent free archive API; searches returned only vendor pages. The r/pushshift and r/DataHoarder discussions could not be read (reddit.com is blocked for the fetch tool).

---

## 7. Mapping Reddit features onto Arctic Shift

### Takeaway
AS natively supports only chronological retrieval ("new"), filtered by subreddit, author, date, flair, URL, NSFW and spoiler, plus scoped keyword search, ID lookup and full comment trees. Score-based orderings (hot, top, rising, controversial, best, comments) must be computed client-side over a bounded window. They are unreliable for content under about 36 h old (score 1/0) and stale for older content (a frozen ~36–48 h snapshot).

### Cited Findings
Every row draws on the [API README](https://github.com/ArthurHeitmann/arctic_shift/blob/master/api/README.md) unless another source is named in the row.

| Reddit feature | AS support | How / caveats |
|---|---|---|
| **sort=new** (subreddit listing, user submitted/comments) | **Yes, native** | `posts/search` or `comments/search` with `subreddit=` or `author=` and `sort=desc`. Page with `before=<last created_utc>`. `limit` ≤100 or `auto` (100–1000). Posts arrive about 10–15 s after creation; comments currently minutes, at times 1–2 days ([#84](https://github.com/ArthurHeitmann/arctic_shift/issues/84); P1/P2) |
| **sort=old / ascending** | Yes | `sort=asc` |
| **sort=top** + t=hour/day | **No, meaningless** | No score sort ([#56](https://github.com/ArthurHeitmann/arctic_shift/issues/56)). Items under 36 h old have score 1/0 |
| **sort=top** + t=week/month/year/all | **Client-side only** | Fetch the window with `after=7d`/`1year`/…, `fields=id,title,score,num_comments,created_utc`, page through, then sort locally. Feasible for small/medium subs; for big subs the window holds tens of thousands of posts, so cap the pages and say so. Scores are ~36 h snapshots ([#24](https://github.com/ArthurHeitmann/arctic_shift/issues/24)) |
| **sort=hot** | **No** | Needs current score plus age; fresh items have score 1. At best an approximation over items 1.5–7 days old |
| **sort=rising** | **No** | Needs live vote velocity; not available |
| **sort=controversial** | **No (approximation)** | `controversiality`/`upvote_ratio` exist only in full objects (not in `fields`); compute client-side over a window |
| **sort=comments** (num_comments) | **Client-side only** | `num_comments` is selectable; sort locally; same 36 h caveat |
| **sort=relevance** (search) | **No** | No ranking; keyword matches come back in `created_utc` order |
| **t= time filter** (hour, day, week, month, year, all) | **Yes as a date filter** | `after=1hour` / `1d` / `7d` / `1month`? (unit unconfirmed; `3m` documented) / `1year`, or omit; also absolute dates or epochs |
| **Search: plain keywords** | **Partial** | Posts: `query` (title+selftext), `title`, `selftext` need `subreddit` or `author`; "not supported with very active users or subreddits". Both live probes (r/AskReddit, r/rust) returned 422. No global search ([#8](https://github.com/ArthurHeitmann/arctic_shift/issues/8)) |
| **Search: "phrase", OR, -exclude** | **Comments only (documented)** | Comment `body` uses Postgres `websearch_to_tsquery`; posts are "simply keyword search only" (section marked out of date) |
| **Search operators** `author:` `subreddit:` `title:` `selftext:` `flair:` `nsfw:` `spoiler:` `url:` `site:` `self:` | **Mostly via params** | `author`, `subreddit`, `title`, `selftext`, `link_flair_text`, `author_flair_text`, `over_18`, `spoiler`, `url` (prefix of full URL, or `url_exact`). No `site:`/domain filter (only URL prefix), no `self:` filter, no negative/exclude filters ([#49](https://github.com/ArthurHeitmann/arctic_shift/issues/49)) |
| **/r/all, /r/popular, front page** | **No** | No popularity data. A global newest feed without filters may work but was not tested |
| **Post + comments page** (`/comments/{id}`) | **Yes** | `posts/ids?ids=` (≤500 IDs) plus `comments/tree?link_id=t3_…&limit=…` (≤25000) |
| **Comment sort** (best/confidence, top, new, controversial, old, q&a) | **No server-side sort** | The tree's child order is undocumented. Re-sort locally by `score` (snapshot) or `created_utc`. "best" (Wilson) is impossible: there is no vote split (`downs`=0) ([#24](https://github.com/ArthurHeitmann/arctic_shift/issues/24)) |
| **Comment depth / limit / "load more"** | **Yes** | `start_depth`, `start_breadth`, `limit`. Collapsed nodes are `kind: more` with `children` IDs; expand with `comments/ids` (≤500) or `comments/tree?parent_id=` |
| **Single comment thread / context** | Yes | `comments/tree?link_id=&parent_id=t1_…`. Parent-chain "context=N" walk via `comments/ids` |
| **User overview / profile** | **Partial** | Posts/comments by `author` (new order). `users/search` holds stale aggregate karma (self-computed), no account age ([#69](https://github.com/ArthurHeitmann/arctic_shift/issues/69)). Top-subreddit activity via `users/interactions/subreddits` |
| **Subreddit about** | **Partial, stale** | `subreddits/search?subreddit=` or `subreddits/ids`: description, subscribers, created, over18. Infrequently updated ([#38](https://github.com/ArthurHeitmann/arctic_shift/issues/38)) |
| **Subreddit rules / wiki** | Yes (stale snapshots) | `subreddits/rules`, `subreddits/wikis`, `subreddits/wikis/list` |
| **Subreddit discovery / search** | **Partial** | Name prefix only (`subreddit_prefix`); filter by subscriber range, creation date, NSFW; sort by subscribers, created or name; `limit` ≤1000. No description/topic keyword search |
| **Subreddit growth / activity** | Yes (extra) | `time_series` keys `r/<sub>/subscribers`, `posts/count`, `comments/count` |
| **Crossposts / duplicates** | Partial | `crosspost_parent_id=` finds crossposts of a post. "Other discussions" by URL via `url=` prefix |
| **Share links** `/r/x/s/…` | Yes | `short_links?paths=` (≤1000) |
| **Removed/deleted content** | Better than Reddit | Original text kept unless removed at post time ([#39](https://github.com/ArthurHeitmann/arctic_shift/issues/39)) |
| **RSS** | Yes (extra) | `format=rss` / `jsonfeed` on search ([#60](https://github.com/ArthurHeitmann/arctic_shift/issues/60)) |
| **Live vote counts, awards, online users, media galleries** | **No / snapshot** | Values are as of the archive passes; media IDs/gallery lookup was requested as a feature ([#70](https://github.com/ArthurHeitmann/arctic_shift/issues/70)) |

### Inferences
- **Minimal honest MCP tool set:**
  - `get_subreddit_posts(sub, sort=new|top|comments, t)`: top and comments are computed locally over a capped window and labelled with the snapshot caveat.
  - `get_post_with_comments(id, depth, limit, sort=new|old|top-snapshot)`.
  - `get_user_activity(author)`.
  - `search_posts(sub|author, keywords, t)`: catch the 422 and fall back to a local filter.
  - `find_subreddits(prefix, min_subscribers)`.
  - `resolve_share_link`.
- Hot and rising should either be left out or explicitly approximated. Relevance should be presented as "newest matching".

### Gaps
- Not verified live: comment-tree ordering, whether an unfiltered global feed is fast, whether keyword search succeeds on small subreddits, and the `month` / `week` offset units.
