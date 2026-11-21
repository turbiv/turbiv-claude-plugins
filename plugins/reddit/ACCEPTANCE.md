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

- [x] `list_posts(subreddits[], sort, time | after/before, limit)`:
  - `new` and `old` are native. (T1)
  - `top`, `comments` and `controversial` are computed on the client over a bounded window. The output states the window and the scan size. (T2, T3)
  - Done: the `scan` block gives the window, posts scanned, pages, `complete`/`truncated` and an estimate of the posts in the window.
    - When the window is bigger than `max_pages` (default 10, at most 30), the scan is a labelled sample: the newest page, then the newest page of equal slices of the rest of the window.
    - `controversial` is estimated from `score` and `upvote_ratio`, so it scans full objects.
    - T3: `top`/`comments`/`controversial` over a window that is all younger than 36 h is refused with "scores not final". In longer windows, posts under 36 h are left out of the ranking, and the result says how many.
    - A subreddit with no posts costs one more request, to tell "not in the archive at all" apart from "nothing in this window".
- [x] `search_posts(subreddits[], query, sort, time | after/before, limit)`:
  - It needs at least 1 subreddit or author. (T5)
  - It maps the Reddit operators `author:`, `title:`, `selftext:`, `flair:`, `nsfw:`, `url:`, `site:`, `self:` and `NOT`. (T7)
  - It sends the archive one keyword or one quoted phrase per field. It applies AND, OR and `-exclude` locally.
    Reason: in the probes only a quoted phrase ever worked on posts ([`docs/probes.md`](docs/probes.md), Q1 and Q6).
  - When the archive returns 422, it falls back to a labelled local scan. (T6)
  - Done, with one refinement: the archive gets **one keyword in total** (the most specific single term), not one per field, because each extra keyword field makes the query heavier.
    - `flair:` goes to `link_flair_text`, `nsfw:` to `over_18`, `spoiler:` to `spoiler`, `author:` to `author`. `url:` goes to the `url` prefix only when it starts with `http`; otherwise it is a local substring match.
    - `site:`, `self:`, OR groups, `-`/`NOT` and the other words are matched locally on tokens, so case, hyphens and punctuation do not matter.
    - Each scope reports its `method`: archive keyword search, or "local scan (T6)" with `partial` and the posts scanned.
- [x] Reddit's time filters `hour/day/week/month/year/all` and custom date ranges become absolute epoch seconds. "Last 3 months" works. (T8)
  - Done through the shared `resolve_window`. `before="2025"` means the end of 2025.
- [x] `deep_search(concepts[][], subreddits[], after?, before?, in: posts|comments|both, max_requests=30)` finds older and less exact matches:
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
  - Done. Details and refinements:
    - The subreddits share the budget round robin. A subreddit's `query` walk starts when its `title` walk ends.
    - A window is not halved below 1 day. A window that still fails there is skipped and listed in `windows_failed`. After 3 skipped windows in a row, the step gives up.
    - The comment step sends the anchor group's terms joined with `OR`. After two 422s it falls back to the single most specific term, because comment search syntax is not probed yet.
    - Model names go to the archive by their 3+-digit token (`i9-9900K` is sent as `9900k`). Fuzzy matching applies only to words of 5+ letters with no digits, so `9700k` never matches `9900k`. The matching uses `difflib` from the standard library, because adding `rapidfuzz` would change the shared `pyproject.toml`.
    - **Ranking refinement:** concept coverage first, then how many groups matched in the **title**, then the comment count. Reason: `num_comments` is a frozen early snapshot (`wi7uhk` shows 2, but has 22 archived comments). Without this tie-break, a thread that names both concepts in its title ranks below busy threads that mention one concept in the body.
    - Every distinct term of the anchor group is walked in turn: titles first, then title + selftext.
    - **Fast-422 refinement:** the pause grows from 10 s to 20, 40 and at most 60 s while fast 422s go on, and
      resets after a success. The live 422s came in bursts. After 240 s of waiting, the call stops and says the
      archive is busy.
    - A truncated result gives each unfinished step's `resume_before` and says how to continue per subreddit.
    - Live measurement: [`docs/deep-search.md`](docs/deep-search.md).
- [x] Results from several subreddits are merged and de-duplicated by `id`.
- [x] `get_posts(ids_or_urls[])` returns full posts. It accepts up to 500 IDs, and splits larger inputs.
  - Done: up to 2,000 IDs or URLs per call, sent 500 at a time, as full objects (`_meta`, `upvote_ratio`). `text_chars` goes up to 15,000 for the full text (O6). Unknown IDs are listed in `not_found`, and share links get a "resolve it first" note.

### Session 3: comments

- [x] `get_thread(url_or_id, max_comments, depth, sort)`:
  - It returns the post plus a trimmed comment tree, with `more` stubs. (T9)
    `comment_counts` gives the archived count, because the post's `num_comments` is often a stale snapshot.
  - It sorts `new`, `old` and `top` locally. (T10)
- [x] `expand_comments(post_id, more_ids[])` expands `more` stubs.
  It reuses the cached tree, and loads a stub's children with `tree?parent_id=`, at most 10 per call.
- [x] `get_comment_context(comment_id_or_url, context≤8)` walks up the parent comments. (T11)
  It also returns the comment's full text (O6) and its replies.
- [x] `search_comments(subreddits[], query, time | after/before, limit)`:
  - It passes words (AND), `"phrase"` and `OR` to the archive's `body` search. (T7)
    It applies `-exclude` and `NOT` locally: it sends the positive part, asks for 100 results, and filters them.
    Reason: in the Session 3 live test every form worked at least once, but exclusion on a subreddit never did
    (0 of 3; [`docs/probes.md`](docs/probes.md), Session 3, S3-1).
  - It uses the same 422 fallback as `search_posts`: a labelled, bounded local scan of the window. (T6)
  - It also takes `author` or `post` as the scope.
- [x] Comment results carry a completeness note while comment ingest lags. (O4)

### Session 4: discovery, users and mention counts

Done in `tools/discovery.py`. Tests: `tests/discovery/`. Costs and probe findings: [`docs/discovery-costs.md`](docs/discovery-costs.md).

- [x] `find_subreddits(name_or_prefix, min_subscribers, nsfw, keyword?)`:
  - It matches by name and prefix.
  - It has an optional local keyword filter over descriptions.
  - It does not claim topic search. (T12)
  - Added: the 3 largest results also get posts per day (`activity_for_top`, one time-series request each).
- [x] `subreddit_info(subreddit)` returns:
  - subscribers and description
  - activity: posts and comments per day from the daily `time_series`. If that fails, it estimates posts per day from the newest 100 posts.
    **Fact** (2026-11-21): the comment `aggregate` endpoint returned 0 for a term that `comments/search` matched 100 times. So no tool uses the aggregates.
  - rules and the list of wiki pages
- [x] `read_wiki(subreddit, page)` returns a wiki page. Long pages come in parts (`offset`, `next_offset`).
- [x] `get_user(username, time?)`:
  - It returns archived posts and comments, and the subreddits the user is active in.
  - It labels karma as stale archive karma.
  - It returns no account age. (T13)
  - The default window is the last year (T14).
- [x] `resolve_share_link(url)` resolves `/r/x/s/...` links. (T15) It also returns the target post and comment.
  **Fact:** the archive knows only share links that appeared in archived posts or comments.
- [x] `trending_posts(subreddits[], hours)`:
  - It ranks posts by the number of new comments in the last N hours, from `comments/search` sorted newest first.
  - It labels the method as "recent comment activity, not Reddit's hot".
  - Reason: `hot` is not possible (T4), and scores and `num_comments` are 1 or 0 for the first ~36 h.
  - With no subreddits it refuses and says r/all is not available.
  - Subreddits too big for the budget are sampled across the window. Posts are compared by estimated new comments.
- [x] `count_mentions(subreddits[], terms[], time | after/before, in: posts|comments|both)`:
  - It returns a count per term.
  - It also returns the number of distinct threads per term, with example links.
  - The scan is bounded, and the output states its size and any truncation. (T14)
  - How it works: it lists the window newest-first and matches terms locally. It does not use archive keyword search, which mostly fails under load (probes Q1).
    A window too big for `max_requests` (default 40, 422 retries included) is sampled in equal time slices. The output then adds scaled estimates.
  - The default window is the last 3 months. All-time needs `all_time=true` (T14).

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
