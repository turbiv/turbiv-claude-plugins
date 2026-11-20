# Reddit research MCP: acceptance criteria

## Goal

A plugin `reddit` in this marketplace. It gives Claude a free, keyless, read-only MCP server to research Reddit.
Example question it must answer: "What is the most recommended mechanical keyboard on Reddit in the last 3 months?"

The only data source is the Arctic Shift archive API. Reddit's own keyless routes are closed:

- Anonymous `.json` returns 403.
- RSS ended on 2026-11-13.
- New API keys closed on 2026-10-31.

Background and the full constraint list (IDs D1, R1, E1, T1, O1, L1, ...):
[`reports/Keyless Reddit MCP sources.md`](../../reports/Keyless%20Reddit%20MCP%20sources.md), section "Design constraints".
Each session reads that section before it starts.

## Stack

- Python 3.12, FastMCP, httpx, run with `uv`.
- Local SQLite cache.
- The plugin's `.mcp.json` starts the server with `${CLAUDE_PLUGIN_ROOT}`.

## Global criteria (every session)

1. The server sends requests only to the Arctic Shift API host and status host. It sends nothing to reddit.com. (D1, E5)
2. The server has no API key, login, or write tools. (D2)
3. One request at a time, with at least 1 s between requests. No parallel requests, no IP rotation. (R1, R2)
4. Every post and comment in the output has:
   - a permalink built on the client
   - `created_utc`
   - `score_status` (`initial` or `snapshot`)

   (O1, O2)
5. Every tool description and every result header says the data comes from a third-party archive, not live Reddit. (O3)
6. A tool that cannot do what was asked returns a clear message. It does not return a silent wrong result. Examples: `hot`, `relevance`, global keyword search. (T4, T5)
7. A default tool result stays under about 8,000 tokens. Long text is truncated with `truncated: true`. (O6)
8. Unit tests use saved responses and make no network calls. One live smoke test runs only when `REDDIT_MCP_LIVE=1` is set.
9. `uv run pytest` passes before the session ends.
10. Every session writes the use-case evals it owns, from [`EVALS.md`](EVALS.md), and makes them pass with `claude plugin eval plugins/reddit --case <id>`.

## Sessions

Session 1 runs first. Sessions 2, 3 and 4 can run in parallel after it, because they touch different tool modules. Session 5 runs last.

### Session 1: foundation and live probes

- [x] The folder `plugins/reddit/` has `.claude-plugin/plugin.json`, `.mcp.json`, `pyproject.toml` and `README.md`.
- [x] `.claude-plugin/marketplace.json` lists the `reddit` plugin.
- [x] An Arctic Shift client module has these features:
  - request pacing (R1)
  - a `fields=` whitelist (R3)
  - batch splitting (R5)
  - a descriptive User-Agent (R6)
  - the SQLite cache (R7)
- [x] Error handling: 429 wait-and-retry-once (E1), bounded 422 narrowing (E2), outage vs. query error from the status feed (E3), and verbatim 400 errors (E4).
- [x] An `archive_status` tool reports post and comment freshness in plain words. (L1, L2)
- [x] Live probes answer the 5 open questions from the report. The answers are recorded in `plugins/reddit/docs/probes.md`. Limit: at most 20 requests.
  - Does keyword search work on small subreddits?
  - Which order does `comments/tree` use for child comments?
  - Does the offset unit `m` mean month or minute?
  - Is an unfiltered global newest-first feed allowed and fast?
  - Do comments older than 48 h carry `_meta.retrieved_2nd_on`?
  - Which syntax does post search (`title`, `query`) accept: two words (AND), `OR`, `"phrase"`, `-exclude`?
    - On 2026-11-21, `"power limit"` worked.
    - Two words, `OR` and `-` returned 422 in under 0.5 s.
    - Test each one 3 times, with spacing.
    - Answers: [`docs/probes.md`](docs/probes.md). Probes used 20 requests.
  - Is a 422 that returns in under 1 s a rejected query or a rate limit? `deep_search` uses the answer to choose between narrowing the query and waiting.
- [x] Claude Code loads the plugin, and Claude can call `archive_status`.
- [x] It creates 3 tool modules for the parallel sessions:
  - `tools/posts.py` for Session 2
  - `tools/comments.py` for Session 3
  - `tools/discovery.py` for Session 4

  The server already registers each module. Sessions 2–4 then edit only their own module, its tests, and its eval cases.
- [x] Shared helpers are in the client module: permalink building, `score_status`, output trimming, and time-filter conversion. Sessions 2–4 import them and do not change them.

### Session 2: posts, listings and search

- [ ] `list_posts(subreddits[], sort, time | after/before, limit)`:
  - `new` and `old` are native. (T1)
  - `top`, `comments` and `controversial` are computed on the client over a bounded window. The output states the window and the scan size. (T2, T3)
- [ ] `search_posts(subreddits[], query, sort, time | after/before, limit)`:
  - It needs at least 1 subreddit or author. (T5)
  - It maps the Reddit operators `author:`, `title:`, `selftext:`, `flair:`, `nsfw:`, `url:`, `site:`, `self:` and `NOT`. (T7)
  - It sends the archive one keyword or one quoted phrase per field. It applies AND, OR and `-exclude` locally.
    Reason: in the probes only a quoted phrase ever worked on posts ([`docs/probes.md`](docs/probes.md), Q1 and Q6).
  - When the archive returns 422, it falls back to a labelled local scan. (T6)
- [ ] Reddit's time filters `hour/day/week/month/year/all` and custom date ranges become absolute epoch seconds. "Last 3 months" works. (T8)
- [ ] `deep_search(concepts[][], subreddits[], after?, before?, in: posts|comments|both, max_requests=30)` finds older and less exact matches:
  - `concepts` is AND-of-OR groups, for example `[["9900k","i9-9900k","9900kf"], ["power limit","PL1","PL2","undervolt","underclock","TDP"]]`. Claude writes the groups.
  - Server step:
    - Send the most specific term as `title`, then as `query` (title + selftext).
    - Walk time windows backward, 100 items per page.
    - On a slow 422 (1 s or more, a real timeout), halve the window.
    - On a fast 422 (under 1 s, load shedding), wait at least 10 s and retry the same window once. After a second fast 422, halve the window. `QueryTooHeavy.fast` tells the two apart ([`docs/probes.md`](docs/probes.md), Q7).
  - Comment step: `comments/search` with phrase/OR syntax, grouped by `link_id`, then `posts/ids`.
  - Local step:
    - Match the other concept groups on title and selftext.
    - Normalize model names, for example `i9-9900K` = `i9 9900k` = `9900k`.
    - Allow typos (fuzzy ratio ≥ 85).
    - Rank by concept coverage first, then by comment count.
  - Output: the top candidates, each with "matched: …". A coverage report lists the windows scanned, the windows that failed, the requests used, and whether the search was truncated.
- [ ] Results from several subreddits are merged and de-duplicated by `id`.
- [ ] `get_posts(ids_or_urls[])` returns full posts. It accepts up to 500 IDs, and splits larger inputs.

### Session 3: comments

- [ ] `get_thread(url_or_id, max_comments, depth, sort)`:
  - It returns the post plus a trimmed comment tree, with `more` stubs. (T9)
  - It sorts `new`, `old` and `top` locally. (T10)
- [ ] `expand_comments(post_id, more_ids[])` expands `more` stubs.
- [ ] `get_comment_context(comment_id_or_url, context≤8)` walks up the parent comments. (T11)
- [ ] `search_comments(subreddits[], query, time | after/before, limit)`:
  - It passes phrase, OR and exclusion syntax to the archive. (T7)
    Comment search syntax is not probed yet. Session 3 checks it in its live test. If the archive rejects a form, the tool applies it locally, as `search_posts` does.
  - It uses the same 422 fallback as `search_posts`.
- [ ] Comment results carry a completeness note while comment ingest lags. (O4)

### Session 4: discovery, users and mention counts

- [ ] `find_subreddits(name_or_prefix, min_subscribers, nsfw, keyword?)`:
  - It matches by name and prefix.
  - It has an optional local keyword filter over descriptions.
  - It does not claim topic search. (T12)
- [ ] `subreddit_info(subreddit)` returns:
  - subscribers and description
  - activity (posts per day from the aggregate or time-series endpoints)
  - rules and the list of wiki pages
- [ ] `read_wiki(subreddit, page)` returns a wiki page.
- [ ] `get_user(username, time?)`:
  - It returns archived posts and comments, and the subreddits the user is active in.
  - It labels karma as stale archive karma.
  - It returns no account age. (T13)
- [ ] `resolve_share_link(url)` resolves `/r/x/s/...` links. (T15)
- [ ] `trending_posts(subreddits[], hours)`:
  - It ranks posts by the number of new comments in the last N hours, from `comments/search` sorted newest first.
  - It labels the method as "recent comment activity, not Reddit's hot".
  - Reason: `hot` is not possible (T4), and scores and `num_comments` are 1 or 0 for the first ~36 h.
- [ ] `count_mentions(subreddits[], terms[], time | after/before, in: posts|comments|both)`:
  - It returns a count per term.
  - It also returns the number of distinct threads per term, with example links.
  - The scan is bounded, and the output states its size and any truncation. (T14)

### Session 5: research skill, docs and end-to-end check

- [ ] The plugin has a skill that sets the research order:
  1. Find subreddits.
  2. Check their activity.
  3. Search or list posts.
  4. Count mentions.
  5. Read the top threads.
  6. Cite permalinks and state the data limits.

  If archive search does not find a known post, the skill tells Claude to use its web search for candidate Reddit URLs, then read them through the plugin.
- [ ] The README covers:
  - install
  - every tool with one example
  - what is not possible: hot, relevance, global search, live scores
  - the March 2027 risk
  - personal, non-commercial use only (L3)
- [ ] Run the full eval suite with `claude plugin eval plugins/reddit`. Every case in [`EVALS.md`](EVALS.md) meets its pass rate, and the "beats baseline" cases beat the no-plugin run. Record the scores in `plugins/reddit/evals/RESULTS.md`.
- [ ] End-to-end: install the plugin from the marketplace in a fresh Claude Code session, then run the `read-post`, `find-post` and `keyboard` prompts by hand.
- [ ] A code review of the full plugin reports no open correctness issues.

## Out of scope

- Writing, voting or posting.
- Reddit OAuth, borrowed client IDs, and any reddit.com fallback.
- Bulk export. Point users to the Arctic Shift monthly dumps. (D4)
- Paid data sources.
