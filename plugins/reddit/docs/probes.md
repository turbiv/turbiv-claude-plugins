# Live probes, Session 1

**Fact:** run on 2026-11-20 between 22:32 and 22:36 UTC (2026-11-21 local time) against the public Arctic Shift
instance. 20 requests in all, one at a time, at least 3.5 s apart. No request went to reddit.com.

- Requests 1–19 came from one script. Request 20 ran 2 min later, after a 30 s pause.
- The User-Agent was `reddit-research-mcp/0.1.0 (read-only research client for the Arctic Shift archive; probe run)`.
- Every search sent `fields=`, except requests 6 and 7. Those two needed full objects: `_meta` is not a selectable field (R3).
- `comments/tree` has no `fields` parameter.
- The raw log is in [`probes-log.json`](probes-log.json). The time column there is when each answer arrived.
- The saved responses are test fixtures in `tests/fixtures/`.

## Requests

Base `https://arctic-shift.photon-reddit.com/api`. "Result" is the number of items, or the error text.

| # | UTC | Request | HTTP | Time | Result |
|---|---|---|---|---|---|
| 1 | 22:32:00 | `https://status.arctic-shift.photon-reddit.com/api` | 200 | 0.11 s | status JSON |
| 2 | 22:32:05 | `/posts/search?limit=5&sort=desc&fields=id,subreddit,created_utc,retrieved_on` | 200 | 0.92 s | 5 |
| 3 | 22:32:09 | `/posts/search?subreddit=AskReddit&before=3m&limit=1&sort=desc&fields=id,created_utc` | 200 | 1.20 s | 1 |
| 4 | 22:32:13 | `/posts/search?subreddit=HHKB&query=topre&limit=10&sort=desc&fields=id,title,created_utc,num_comments,score,selftext` | 422 | 0.37 s | Timeout. Maybe slow down a bit |
| 5 | 22:32:18 | `/comments/tree?link_id=wi7uhk&limit=200` | 200 | 0.81 s | 9 top-level, 22 comments |
| 6 | 22:32:22 | `/comments/search?subreddit=AskReddit&before=1794868320&limit=2&sort=desc` (4 days back, full objects) | 200 | 0.82 s | 2 |
| 7 | 22:32:26 | `/comments/search?subreddit=AskReddit&before=1791325920&limit=2&sort=desc` (45 days back, full objects) | 200 | 0.78 s | 2 |
| 8 | 22:32:30 | `/posts/search?subreddit=buildapc&title=power limit&limit=5&sort=desc&fields=id,title,created_utc` | 422 | 0.35 s | Timeout. Maybe slow down a bit |
| 9 | 22:32:34 | `… title=undervolt OR underclock …` | 422 | 0.42 s | Timeout. Maybe slow down a bit |
| 10 | 22:32:44 | `… title="power limit" …` | **200** | 6.19 s | 5 |
| 11 | 22:32:48 | `… title=undervolt -laptop …` | 422 | 0.37 s | Timeout. Maybe slow down a bit |
| 12 | 22:32:51 | `… title=power limit …` | 422 | 0.37 s | Timeout. Maybe slow down a bit |
| 13 | 22:32:55 | `… title=undervolt OR underclock …` | 422 | 0.36 s | Timeout. Maybe slow down a bit |
| 14 | 22:32:59 | `… title="power limit" …` | 422 | 0.23 s | Timeout. Maybe slow down a bit |
| 15 | 22:33:03 | `… title=undervolt -laptop …` | 422 | 0.23 s | Timeout. Maybe slow down a bit |
| 16 | 22:33:12 | `… title=power limit …` | 422 | **5.48 s** | Timeout. Maybe slow down a bit |
| 17 | 22:33:16 | `… title=undervolt OR underclock …` | 422 | 0.32 s | Timeout. Maybe slow down a bit |
| 18 | 22:33:19 | `… title="power limit" …` | 422 | 0.24 s | Timeout. Maybe slow down a bit |
| 19 | 22:33:23 | `… title=undervolt -laptop …` | 422 | 0.18 s | Timeout. Maybe slow down a bit |
| 20 | 22:35:34 | `/posts/search?subreddit=HHKB&title=topre&limit=10&sort=desc&fields=id,title,created_utc,num_comments,score` | 422 | 0.59 s | Timeout. Maybe slow down a bit |

Requests 8–19 are on `subreddit=buildapc`, with `limit=5&sort=desc&fields=id,title,created_utc`.

Every response had `x-ratelimit-reset` (seconds) and `x-ratelimit-reset-at` (epoch ms on a whole minute). None
had a `Remaining` or `Limit` header. No request got a 429.

## Answers

### Q1. Does keyword search work on small subreddits?

**No, not reliably.** On r/HHKB, a small subreddit:

- `query=topre` returned 422 in 0.37 s (request 4).
- 2 min later, `title=topre` returned 422 in 0.59 s (request 20).

So subreddit size does not save keyword search. **Assumption:** these 422s are load shedding (see Q7), so
other runs may succeed. The tools must treat archive keyword search as an extra that works sometimes. The main
path is listing a date window and filtering it locally (T6).

### Q2. Which order does `comments/tree` use for child comments?

**Oldest first.** In the tree of `wi7uhk`, all 9 top-level comments came in ascending `created_utc` order,
from 2022-08-07 to 2026-03-28. Replies inside each branch were in the same order. The order is not by score:
the scores ran 2, 1, 1, 1, 1, 2, 1, 1, 1.

This thread has only old, sequential IDs, so it cannot tell "by time" apart from "by ID". Since Reddit's
October 2026 change to random comment IDs, these two orders differ. **T10 stays:** sort locally, and never
rely on the archive's order.

The tree had no `more` stubs, because 22 comments is under `limit=200`. Every comment since 2023-07 had
`_meta.retrieved_2nd_on`. The two 2022 comments (Pushshift era) had no `_meta` at all.

### Q3. Does the offset unit `m` mean month or minute?

**Month.** `before=3m` returned a newest post from 2026-08-20 21:31 UTC, which is 92.0 days before the probe.
**T8 stays:** the client never sends relative offsets. It sends only epoch seconds, and it rejects `3m`
before any request.

### Q4. Is an unfiltered global newest-first feed allowed and fast?

**Yes, for posts.** `posts/search` with no subreddit or author returned 200 in 0.92 s. Its 5 posts were 13 s
old, all from different subreddits, including `u_…` profile subreddits. Comments were not tested.

### Q5. Do comments older than 48 h carry `_meta.retrieved_2nd_on`?

**Usually, not always.**

- **4 days back** (new random IDs, e.g. `19sqrqjazs0si`): 1 of 2 had it.
  - The one with it got its second pass 13.8 h after posting, not 36 h.
  - The other had no `_meta` at all. It was first archived 80 h after posting, so its first value is already late.
- **45 days back** (old IDs): 2 of 2 had it, at 39 h and at 103 h after posting.
- **The `wi7uhk` tree:** all 20 comments since 2023-07 had it.

`helpers.score_status()` uses this evidence. It returns `snapshot` in these cases:

- `_meta.retrieved_2nd_on` is set.
- The item was first archived 36 h or more after posting.
- The item is from the Pushshift era (before 2023-07-10).
- A `fields=` object, which cannot carry `_meta`, is more than 72 h old. **Assumption:** these had a second pass.

Otherwise it returns `initial`.

### Q6. Which syntax does post search (`title`) accept?

Each form was sent 3 times, round robin, 3.5 s apart, on r/buildapc:

| Form | Example | 200 | 422 | 422 times |
|---|---|---|---|---|
| two words (AND) | `power limit` | 0 | 3 | 0.35 s, 0.37 s, 5.48 s |
| `OR` | `undervolt OR underclock` | 0 | 3 | 0.42 s, 0.36 s, 0.32 s |
| `"phrase"` | `"power limit"` | 1 | 2 | 0.23 s, 0.24 s (the 200 took 6.19 s) |
| `-exclude` | `undervolt -laptop` | 0 | 3 | 0.37 s, 0.23 s, 0.18 s |

- **Only a quoted phrase has ever worked.** It worked once here, and once in the earlier 2026-11-21 test.
- **The phrase match:** all 5 results had the words "power limit" next to each other. Case did not matter, and
  "power-limit" with a hyphen also matched. So `title` is a tokenized phrase match, not a substring match.
- **The other forms:** two words, `OR` and `-exclude` never succeeded. Two words once ran 5.5 s before timing
  out. So AND is not rejected outright; it is too heavy.

**Not tested:** these forms in `query` (title plus selftext). The budget allowed only `title`. One word in
`query` failed fast on r/HHKB (Q1).

**Rule change:** post search sends the archive one keyword or one quoted phrase per field. It applies AND, OR
and `-exclude` locally. ACCEPTANCE.md, Session 2, now says this.

### Q7. Is a 422 that returns in under 1 s a rejected query or a rate limit?

**Neither exactly: it is load shedding.** It is not a fixed verdict on the query, and it is not the 429 rate limit.

- **Same query, different answers:** the same `"power limit"` query returned 200 in 6.19 s (request 10), then
  422 in 0.23 s (request 14) and 0.24 s (request 18).
- **Not the rate limit:** no fast 422 came with a 429 status or with different rate-limit headers.
- **When fast 422s came:** after the 6.2 s success, every keyword query fast-failed for about 20 s. Then one ran
  for 5.5 s and timed out (request 16), and the fast failures went on.
- **Not only after heavy queries:** the first keyword queries of the run (requests 4, 8, 9) also fast-failed.
  So the trigger is probably server-wide load, not only this client's heavy queries.
- **Two kinds of 422:**
  - A fast 422 (under 1 s) means "busy right now". Rewriting the syntax does not help, and an immediate retry
    rarely does.
  - A slow 422 (1 s or more; 5.5 s here) is a real timeout. Narrowing the window or the limit can help.

**Assumption:** a wait of 10 s or more before the next keyword query helps. The data is too thin to set an
exact wait.

**What changed:**

- **Client:** after a fast 422, it waits 3 s (the top of E2's 1–3 s range) before its retry.
  `QueryTooHeavy.fast` tells the caller which kind of 422 it was. The message then says to wait, not to rewrite
  the query.
- **Rule change:** `deep_search` waits 10 s or more after a fast 422 and retries the same window once. It
  halves the window only after a slow 422, or after a second fast one. ACCEPTANCE.md, Session 2, now says this.

## Other findings

- **The `read-post` eval facts were wrong.**
  - The archive holds **22 comments** on `wi7uhk`: 9 top-level and 13 replies. The newest is from 2026-04-09.
  - OP (u/willswill) wrote **10** of them.
  - The post's `num_comments` of 2 is its frozen 2022 snapshot.
  - EVALS.md now has the right facts for `read-post` and `thread-follow-up`.
- **Status feed at 22:32 UTC:**
  - All components were up.
  - The newest post was 25 s old, the newest comment 90 s old.
  - The post second pass was at 36.0 h. `trailingIdNotifier` comments were at 39.4 h.
  - `archiverTrailing.mostRecentCommentAt` was `null`.
  - `idNotifier.mostRecentCommentAt` was 31 days old. The old ID scan for comments has stopped; comments now
    arrive another way.
  - `archive_status` reports these numbers in plain words.

## Rules changed because of these probes

| File | Where | Change | Probe |
|---|---|---|---|
| ACCEPTANCE.md | Session 1 | The probe questions are ticked; the answers are here | all |
| ACCEPTANCE.md | Session 2, `search_posts` | It sends one keyword or one quoted phrase; AND, OR and `-exclude` are applied locally | Q1, Q6 |
| ACCEPTANCE.md | Session 2, `deep_search` | Fast 422: wait 10 s or more and retry once. Slow 422 or a second fast one: halve the window | Q7 |
| ACCEPTANCE.md | Session 3, `search_comments` | Comment search syntax is not probed yet; Session 3 checks it in its live test and uses the posts fallback | Q6 |
| EVALS.md | `read-post`, `thread-follow-up`, facts | 22 archived comments (9 top-level), OP replied 10 times; `num_comments` 2 is a stale snapshot | Q2 |
| client | E2 retry | Fast 422: wait 3 s, and suggest waiting rather than rewriting | Q7 |

# Live probes, Session 3

**Fact:** run on 2026-11-20 between 22:56 and 23:00 UTC (2026-11-21 local time) against the public Arctic Shift
instance. 26 requests in all (budget 30), one at a time, at least 6 s apart. No request went to reddit.com.

- Requests 1–25 came from one script. Request 26 ran 50 s later, to save the post as a fixture.
- The User-Agent was the same as in Session 1.
- The raw log is [`tests/fixtures/comments/probe-log-s3.json`](../tests/fixtures/comments/probe-log-s3.json); the
  time column is when each answer arrived.
- Saved responses, used by `tests/comments/`: `tree-wi7uhk-limit5.json` (2), `tree-wi7uhk-parent-jqqr5hr.json`
  (4), `ids-wi7uhk-3.json` (5), `search-wi7uhk-undervolt.json` (6), `search-wi7uhk-or.json` (9),
  `search-wi7uhk-exclude.json` (10), `search-buildapc-phrase.json` (12), `post-wi7uhk-full.json` (26).

## Requests

Base `https://arctic-shift.photon-reddit.com/api`. `fields=…` is
`id,subreddit,author,created_utc,retrieved_on,score,body,link_id,parent_id`. Requests 11–25 also had
`limit=25&sort=desc&after=1792623395&before=1795215395` (the last 30 days).

| # | UTC | Request | HTTP | Time | Result |
|---|---|---|---|---|---|
| 1 | 22:56:35 | status feed | 200 | 0.11 s | all components up |
| 2 | 22:56:41 | `/comments/tree?link_id=wi7uhk&limit=5` | 200 | 0.72 s | 5 comments, 2 `more` stubs |
| 3 | 22:56:48 | `/comments/tree?link_id=wi7uhk&limit=50&start_depth=1&start_breadth=2` | 200 | 0.66 s | all 22, no stubs |
| 4 | 22:56:55 | `/comments/tree?link_id=wi7uhk&parent_id=t1_jqqr5hr&limit=50` | 200 | 0.78 s | jqqr5hr and its 4 replies |
| 5 | 22:57:02 | `/comments/ids?ids=jqstn48,jqr4am2,jqqr5hr&fields=…` | 200 | 0.89 s | 3 |
| 6 | 22:57:09 | `/comments/search?link_id=wi7uhk&body=undervolt&limit=100&fields=…` | 200 | 1.64 s | 4 |
| 7 | 22:57:16 | `… link_id=wi7uhk&body="power limit" …` | 422 | 0.34 s | Timeout. Maybe slow down a bit |
| 8 | 22:57:22 | `… link_id=wi7uhk&body=power limit …` | 422 | 0.26 s | Timeout. Maybe slow down a bit |
| 9 | 22:57:29 | `… link_id=wi7uhk&body=undervolt OR underclock …` | 200 | 1.24 s | 6 |
| 10 | 22:57:36 | `… link_id=wi7uhk&body=power -undervolt …` | 200 | 1.04 s | 8 |
| 11 | 22:57:47 | `/comments/search?subreddit=buildapc&body=undervolt …` | 200 | 5.04 s | 25 |
| 12 | 22:57:57 | `… body="power limit" …` | 200 | 3.28 s | 25 |
| 13 | 22:58:05 | `… body=power limit …` | 200 | 2.24 s | 25 |
| 14 | 22:58:11 | `… body=undervolt OR underclock …` | 422 | 0.33 s | Timeout. Maybe slow down a bit |
| 15 | 22:58:18 | `… body=undervolt -laptop …` | 422 | 0.37 s | Timeout. Maybe slow down a bit |
| 16 | 22:58:26 | `… body=undervolt …` | 200 | 2.52 s | 25 |
| 17 | 22:58:33 | `… body="power limit" …` | 422 | 0.43 s | Timeout. Maybe slow down a bit |
| 18 | 22:58:43 | `… body=power limit …` | 200 | 4.34 s | 25 |
| 19 | 22:58:53 | `… body=undervolt OR underclock …` | 200 | 3.84 s | 25 |
| 20 | 22:58:59 | `… body=undervolt -laptop …` | 422 | 0.26 s | Timeout. Maybe slow down a bit |
| 21 | 22:59:05 | `… body=undervolt …` | 422 | 0.19 s | Timeout. Maybe slow down a bit |
| 22 | 22:59:12 | `… body="power limit" …` | 422 | 0.33 s | Timeout. Maybe slow down a bit |
| 23 | 22:59:18 | `… body=power limit …` | 422 | 0.15 s | Timeout. Maybe slow down a bit |
| 24 | 22:59:27 | `… body=undervolt OR underclock …` | 200 | 3.68 s | 25 |
| 25 | 22:59:34 | `… body=undervolt -laptop …` | 422 | 0.29 s | Timeout. Maybe slow down a bit |
| 26 | 23:00:28 | `/posts/ids?ids=wi7uhk` (full object) | 200 | 0.59 s | 1 |

No request got a 429. Every 422 came in under 0.5 s, so by Q7 every one was load shedding, not a real timeout.

## Answers

### S3-1. Which comment search syntax does `body` accept?

**All four forms work.** Comment search is Postgres full-text search, and it applies the websearch syntax
correctly whenever the archive is not shedding load.

| Form | Example | r/buildapc, 30 days: 200 / sent | One thread (`link_id`): 200 / sent |
|---|---|---|---|
| one word | `undervolt` | 2 / 3 | 1 / 1 |
| `"phrase"` | `"power limit"` | 1 / 3 | 0 / 1 |
| two words (AND) | `power limit` | 2 / 3 | 0 / 1 |
| `OR` | `undervolt OR underclock` | 2 / 3 | 1 / 1 |
| `-exclude` | `undervolt -laptop`, `power -undervolt` | **0 / 3** | 1 / 1 |

What the successful answers contained (checked word by word):

- **Phrase:** 25 of 25 had "power limit" with the words next to each other.
- **AND:** 25 of 25 had both words; 13 had them next to each other. So two words are a real AND, not a phrase.
- **OR:** 25 of 25 had one of the words; 24 had "undervolt" and 2 "underclock" (newest first).
- **Exclusion, in `wi7uhk`:** `power -undervolt` returned the 7 "power" comments without "undervolt", plus
  `oczc53l`. That comment says "undervolt/underclock": Postgres reads a slash-joined pair as one path token, so
  the word "undervolt" does not match it. The one-word query `undervolt` missed `oczc53l` for the same reason.
- **Stemming:** `underclock` matched "underclocking"; `power` matched "power-limit".
- **Load:** the 200s took 1.0–5.0 s, much slower than post listings (under 1 s). In a thread they took 1–1.6 s.

Comparison with Session 1 (posts, Q6): there only a quoted phrase ever worked, 1 time in 3. On comments every
form worked at least once, except exclusion at subreddit scope.

**Assumption:** exclusion is not refused by the archive. It worked in a thread, and every failure was a fast
422. But 0 of 3 is the worst score, and Postgres must check the excluded word on every candidate row. So the
tool does not rely on it.

**Rule change (T7, `search_comments`):** words (AND), `"phrases"` and `OR` pass through to the archive.
`-word`, `-"phrase"` and `NOT word` are applied by the tool: it sends only the positive part, asks for 100
results, filters them, and says so in `notes` and `coverage.after_local_exclusion`. ACCEPTANCE.md, Session 3,
says this.

### S3-2. What does a `more` stub in `comments/tree` look like?

`{"kind": "more", "data": {"count", "id", "name", "parent_id", "depth", "children": [...]}}`.

- `children` lists only the **direct** child IDs. `count` counts **every** comment behind the stub, replies
  included. With `limit=5`: a top-level stub of `count` 15 with 7 IDs (7 top-level comments + 8 replies), and a
  nested stub of `count` 2 with 1 ID. 5 + 15 + 2 = 22.
- `id` is the first child's ID; `depth` was 1 in both stubs, so it is not the real depth.
- `replies` is `""` for a comment with no replies, and a Listing otherwise.

So to expand a stub, the tool needs each child's subtree, not only the children: `get_thread` adds up `count`
for the totals, and `expand_comments` loads each child with `tree?parent_id=` (S3-4).

### S3-3. What do `start_depth` and `start_breadth` do?

**Nothing visible when `limit` covers the thread.** With `limit=50`, `start_depth=1` and `start_breadth=2`
still returned all 22 comments, 4 levels deep. They probably only shape which comments come first when the
limit cuts the tree. The tool does not use them: it limits depth and breadth itself (T10 sorts locally anyway).

### S3-4. What does `comments/tree?parent_id=t1_X` return?

**Comment X itself, with its whole subtree.** `parent_id=t1_jqqr5hr` returned jqqr5hr with its 4 replies, 3
levels deep. `expand_comments` and `get_comment_context` use this: one request gives a comment and all its
replies.

### S3-5. Does `comments/ids` keep the order asked for?

**Yes, in this one test.** Asked for `jqstn48,jqr4am2,jqqr5hr`, it answered in that order. The tool does not
depend on it: it matches by `id`.

## Rules changed because of these probes

| File | Where | Change | Probe |
|---|---|---|---|
| ACCEPTANCE.md | Session 3, `search_comments` | Words, phrase and OR pass through; `-exclude` / `NOT` is applied locally on an over-fetched page | S3-1 |
| EVALS.md | `read-post`, `thread-follow-up` | The case folders exist; `thread-follow-up` replays a recorded turn 1 | — |

## Live probes, Session 5

**Fact:** run on 2026-11-21 against the public instance, one request at a time, at least 3 s apart, 4 requests.
No request went to reddit.com.

### S5-1. Which `fields=` does `subreddits/search` accept?

`subreddits/search?subreddit_prefix=espresso&limit=3&sort_type=subscribers&sort=desc&fields=…`

| `fields=` asked for | Answer |
|---|---|
| … `title` … | HTTP 400 in 0.34 s: `'title' is not a valid field` |
| … `subreddit_type` … | HTTP 400 in 0.35 s: `'subreddit_type' is not a valid field` |
| … `_meta` … | HTTP 400 in 0.47 s: `'_meta' is not a valid field` |
| `display_name,subscribers,retrieved_on,over18,created_utc,public_description,id` | HTTP 200 in 1.05 s, 1,323 bytes for 3 subreddits |

- So a slim subreddit object is about 0.4 KB. A full one is about 9 KB, mostly the sidebar `description`.
- The client's `SUBREDDIT_FIELDS` whitelist holds the 7 names that passed. `find_subreddits` asks for 6 of
  them, and so it no longer shows the archived post and comment totals (`_meta`). `subreddit_info` still asks
  for the full object.
- `description` and `quarantine` were not tested, so they are not in the whitelist.
