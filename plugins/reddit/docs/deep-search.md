# deep_search on the `find-post` case: live measurement, Session 2

**Fact:** measured on 2026-11-20 between 23:08 and 23:15 UTC (2026-11-21 local time) against the public Arctic
Shift instance, with the real `deep_search` tool from `tools/posts.py`.

- 40 requests in all, the whole Session 2 probe budget. One at a time, at least 5 s apart
  (`REDDIT_MCP_MIN_INTERVAL=5`). Two other sessions used the same IP at the time.
- No request went to reddit.com.
- The User-Agent was `reddit-research-mcp/0.1.0 (… Session 2 probe run)`.

The `find-post` eval runs came after this. They are extra to the probe budget, and their results are at the end.

## The question

Can `deep_search` find `wi7uhk` from the archive alone? `wi7uhk` is "Intel 9900K Underclocking/Power Limit
Experiments", r/buildapc, 2022-08-07.

The probe used the eval's concept groups:

```json
[["9900k", "i9-9900k", "9900kf", "9900ks"],
 ["power limit", "PL1", "PL2", "undervolt", "underclock", "TDP"]]
```

## Run 1: three subreddits, the default budget

The probe called `subreddits=["buildapc","intel","overclocking"]` with `max_requests=30`, no date range, and
`in=posts`.

| | |
|---|---|
| Requests used | 30, plus 1 status-feed request for the result header |
| Wall time | 273 s |
| HTTP 200 | 9 (all full pages of 100) |
| HTTP 422 | 21: 19 fast (0.07–0.58 s), 2 slow (13.3 s and 5.4 s) |
| Posts examined | 894 |
| Candidates with both concept groups | 55 |
| `wi7uhk` found | **no** |
| Truncated | yes. All three `query=9900k` steps were not started. |

Windows scanned, all with `title=9900k`:

| Subreddit | Pages | Reached back to |
|---|---|---|
| r/buildapc | 3 | 2024-02-18 |
| r/intel | 2 | 2021-10-22 |
| r/overclocking | 4 | 2020-11-17 |

- **No window failed for good.** Every 422 window was retried or halved, and later succeeded. No window reached
  the 1-day floor.
- **Halvings:** windows were halved 9 times. Twice it was after a slow 422. Seven times it was after a second
  fast 422.
- **The fast-422 rule:** after the 10 s wait, a retry of the same window succeeded 2 times out of 10.

### Requests, run 1

The times are when the tool asked. The client then paces each request at least 5 s after the previous answer.

| # | UTC | Subreddit | `after` – `before` | HTTP | Time | Items |
|---|---|---|---|---|---|---|
| 1 | 23:09:07 | buildapc | – now | 422 | 13.33 s | |
| 2 | 23:09:20 | intel | – now | 200 | 7.65 s | 100 |
| 3 | 23:09:33 | overclocking | – now | 422 | 0.29 s | |
| 4 | 23:09:48 | buildapc | 2016-02-25 – now | 422 | 0.24 s | |
| 5 | 23:09:58 | intel | – 2023-01-18 | 422 | 0.58 s | |
| 6 | 23:10:09 | overclocking | – now | 422 | 0.24 s | |
| 7 | 23:10:09 | buildapc | 2016-02-25 – now | 422 | 0.36 s | |
| 8 | 23:10:14 | intel | – 2023-01-18 | 422 | 0.25 s | |
| 9 | 23:10:20 | overclocking | 2016-02-25 – now | 422 | 5.44 s | |
| 10 | 23:10:30 | buildapc | 2021-07-09 – now | 422 | 0.36 s | |
| 11 | 23:10:45 | intel | 2014-03-26 – 2023-01-18 | 422 | 0.28 s | |
| 12 | 23:10:56 | overclocking | 2021-07-09 – now | 200 | 3.67 s | 100 |
| 13 | 23:10:59 | buildapc | 2021-07-09 – now | 200 | 5.63 s | 100 |
| 14 | 23:11:10 | intel | 2014-03-26 – 2023-01-18 | 422 | 0.29 s | |
| 15 | 23:11:15 | overclocking | 2017-10-24 – 2023-03-08 | 200 | 3.04 s | 100 |
| 16 | 23:11:23 | buildapc | 2020-02-09 – 2025-06-22 | 200 | 5.26 s | 100 |
| 17 | 23:11:34 | intel | 2018-08-22 – 2023-01-18 | 422 | 0.21 s | |
| 18 | 23:11:49 | overclocking | 2016-05-21 – 2021-10-03 | 200 | 3.95 s | 100 |
| 19 | 23:11:53 | buildapc | 2019-06-23 – 2024-11-04 | 200 | 4.39 s | 100 |
| 20 | 23:12:02 | intel | 2018-08-22 – 2023-01-18 | 422 | 0.07 s | |
| 21 | 23:12:07 | overclocking | 2015-10-05 – 2021-02-16 | 422 | 0.20 s | |
| 22 | 23:12:22 | buildapc | 2018-10-07 – 2024-02-18 | 422 | 0.52 s | |
| 23 | 23:12:33 | intel | 2020-11-04 – 2023-01-18 | 200 | 5.82 s | 100 |
| 24 | 23:12:39 | overclocking | 2015-10-05 – 2021-02-16 | 422 | 0.27 s | |
| 25 | 23:12:44 | buildapc | 2018-10-07 – 2024-02-18 | 422 | 0.19 s | |
| 26 | 23:12:49 | intel | 2019-08-09 – 2021-10-22 | 422 | 0.38 s | |
| 27 | 23:13:05 | overclocking | 2018-06-11 – 2021-02-16 | 422 | 0.28 s | |
| 28 | 23:13:15 | buildapc | 2021-06-13 – 2024-02-18 | 422 | 0.15 s | |
| 29 | 23:13:25 | intel | 2019-08-09 – 2021-10-22 | 422 | 0.21 s | |
| 30 | 23:13:25 | overclocking | 2018-06-11 – 2021-02-16 | 200 | 4.26 s | 100 |

All 30 requests are `posts/search` with `title=9900k&sort=desc&limit=100` and the post `fields=` list.

The top candidates were 2-of-2 matches from r/overclocking and r/intel, for example `137jcd4`, `kgr43v`,
`uhxsr1` and `1q66gzx`. None of them is `wi7uhk`.

## Run 2: r/buildapc only, from where run 1 stopped

The probe called `subreddits=["buildapc"]`, `after=2022-01-01`, `before=1708292812` (run 1's `resume_before`) and
`max_requests=3`.

| # | `after` – `before` | HTTP | Time | Items |
|---|---|---|---|---|
| 1 | 2022-01-01 – 2024-02-18 | 200 | 4.21 s | 100 |
| 2 | 2022-01-01 – 2023-05-04 | 422 | 0.29 s (fast) | |
| 3 | 2022-01-01 – 2023-05-04 | 200 | 2.51 s (after the 10 s wait) | 100 |

- It used 3 requests and took 27 s.
- It reached back to **2022-09-25**, and found 5 two-group matches, for example `15m56e1`, "Weird power limits
  on old 9900k".
- `wi7uhk` (2022-08-07) is about 7 weeks older than that, so the next page would hold it.
- The probe budget was spent, so the probe stopped here.

## Results

- **Was `wi7uhk` found from the archive alone? Not within the measured budget.**
  - In one call with three subreddits and `max_requests=30`: no.
  - With r/buildapc alone it would be, in about 6 successful `title=9900k` pages. The search reached 2022-09-25
    after 5 successful pages, in 33 requests over two calls.
- **The cost for r/buildapc alone** is about 6 successful pages:
  - 2026-11 back to 2024-02: 300 posts with 9900K in the title, about 9 a month.
  - 2024-02 back to 2022-09: 200 posts, about 12 a month.
  - At the success rates seen, 30 % in run 1 and 67 % in run 2, that is **about 9–20 requests**, or 1–3 minutes.
  - So `deep_search(subreddits=["buildapc"])` with the default 30 requests reaches `wi7uhk` most of the time.
    Three subreddits share 30 requests round robin, and do not.
- **The EVALS.md assumption was too high.** It assumed 1,000–3,000 posts with 9900K in the title in r/buildapc
  from 2018. The measurement is about 500 from 2022-09 to now. The years 2018–2022 are not measured.
- **The 422 rate under load is the main cost.** 70 % of run 1's requests were 422s. A failed request costs as
  much budget as a page.
  - The 10 s wait after a fast 422 rarely helped: 2 of 10 retries succeeded.
  - Halving the window did not change the odds of a fast 422. The successes came at all window sizes.
  - This fits probes Q7: a fast 422 is server load, not query size.
  - The rule stays as written, because the data is thin. A longer pause may help: see "Changes" below.

### The web-search path

The `find-post` eval grants `WebSearch`, so this path is measured by the eval runs below. Without a skill, Claude
did not try the web-search fallback in the first run. Session 5's skill tells it to.

## Cost of a date-window scan of r/buildapc

These numbers are for a plain listing, which list_posts and the local-scan fallback use. One page of 100 posts
with `fields=id,created_utc` was fetched at two dates:

| Page before | 100 posts span | Posts per day | Posts per 30-day month | Pages per month | Time per month at 1 s spacing |
|---|---|---|---|---|---|
| 2026-11-03 | 7.9 h | about 300 | about 9,100 | about 91 | about 2 min (0.3 s answers) |
| 2022-08-01 | 3.4 h | about 720 | about 21,500 | about 215 | about 5–8 min (1.2 s answers) |

- **The aggregate endpoint did not help.** `posts/search/aggregate?aggregate=created_utc&frequency=month` over
  one year of r/buildapc failed 3 times: 422 at 0.25 s, 0.30 s and 9.6 s. So it cannot count posts per month
  for a subreddit this size.
- **A full month cannot be listed by default.** The default `list_posts` bound is 10 pages, about 11 % of a
  current r/buildapc month. `max_pages=30` covers about a third. That is why `top` and `comments` label their
  result as a sample spread evenly over the window.
- **Listing back to 2022-08 is out of reach.** It would take about 7,000 pages. A walk with one keyword anchor
  takes 6 pages.

## Changes made because of this measurement

- **Ranking:** concept coverage first, then the number of groups matched in the **title**, then
  `num_comments`.
  - Reason: `wi7uhk` has a frozen `num_comments` of 2. It names both concepts in its title, but by comment
    count alone it would rank below busier threads that name one concept in the body.
  - The tie-break stays inside "coverage first".
- **Truncated results:** each unfinished step now has a `resume_before`. The note says how to continue one
  subreddit at a time.
- **The docstring:** it now says that subreddits share the budget. 2–3 subreddits, most likely first, are best,
  and `in='both'` divides the budget again.
- **Every distinct term of the anchor group is walked in turn,** not only the most specific one. Before this
  change, a single synonym group such as `chatter / double typing / …` searched only the first term. The
  `search-syntax` eval run showed this.

## find-post eval runs

See the table in [`../EVALS.md`](../EVALS.md) for pass rates. Details per run:

<!-- filled in after the runs -->
