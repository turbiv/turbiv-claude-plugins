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
