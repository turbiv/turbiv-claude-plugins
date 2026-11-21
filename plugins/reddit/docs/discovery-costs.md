# Discovery tools: costs and probe findings (Session 4)

**Fact:** measured on 2026-11-20 between 22:57 and 23:40 UTC against the public Arctic Shift instance, with the
shipped settings: 1 s between requests, one request at a time, cache off for the measurement. No request went to
reddit.com.

## Cost of one call

"Requests" counts every HTTP request the server sent, including 422 retries and the status check that every
result makes (`make_result` reads the status feed for its warnings).

| Call | Requests | Seconds | Scanned | Result |
|---|---|---|---|---|
| `count_mentions`: r/MechanicalKeyboards + r/keyboards, 10 keyboard brands, last 3 months, `in=both`, default `max_requests=40` | 46 | 92.1 | 1,150 posts, 2,500 comments | sampled: 12–15 % of the posts and 3–4 % of the comments |
| `trending_posts`: r/MechanicalKeyboards + r/buildapc, last 24 h, default `max_requests=20` | 19 | 37.3 | 127 + 1,378 comments | complete: every archived comment of the 24 h in both subreddits |

**About 2 s per request.** Each answer takes about 1 s, and the client then waits 1 s before the next one.

**After the budget fix:** these are from the 3 final `keyboard` and `trending` eval runs, taken from the
`requests_used` of each tool result and the trace timestamps. The cache was on, but no answer could come from it,
because the windows end "now".

| Call (as Claude made it) | Requests | Seconds |
|---|---|---|
| `count_mentions`, 3 or 4 keyboard subreddits, 25 terms, 3 months, default budget 40 | 39, 41, 41 | 81.6, 87.5, 84.6 |
| `trending_posts`, AskReddit + worldnews + news + technology + gaming + movies, 24 h, default budget 20 | 21, 21, 22 | 41.5, 42.9, 48.2 |

- **`count_mentions`:** the budget now holds. At most `max_requests` archive requests, plus the status check.
- **`trending_posts`:** one run used 22. **Assumption:** the final post lookup by ID retried after a 422, and
  that lookup is outside the listing budget.

### `count_mentions` in detail

The window was 2026-08-20 23:10 UTC to 2026-11-20 23:10 UTC.

| Stream | Mode | Requests | Items scanned | Estimated items in window | Share scanned |
|---|---|---|---|---|---|
| r/MechanicalKeyboards posts | sampled | 6 | 500 | 3,336 | 15 % |
| r/keyboards posts | sampled | 7 | 650 | 5,251 | 12 % |
| r/MechanicalKeyboards comments | sampled | 13 | 1,300 | 36,751 | 4 % |
| r/keyboards comments | sampled | 13 | 1,200 | 39,726 | 3 % |

- **The estimates check out.** The archive's daily `time_series` for r/MechanicalKeyboards gave 3,445 posts and
  38,268 comments for 2026-08-22 to 2026-11-19. The scan estimated 3,336 posts and 36,751 comments from its
  sample.
- **The ranking:** Keychron (146 threads), Wooting (72), Razer (47), Akko (47), Logitech (46), NuPhy (38), HHKB
  (21), Ducky (17), Glorious (16), Leopold (3).
- **The 46 requests:** 39 listing pages, 1 title lookup, 1 status check, and 5 retries after 422s.
  - That run was before a fix: the scanner counted pages, not HTTP requests, so the 422 retries came on top of
    `max_requests`.
  - Now every retry uses up budget. So a call sends at most `max_requests` archive requests, plus the status
    check.
  - `requests_used` in the result reports the real number.

### What a full scan would cost

**Assumption:** at 100 items per request and about 2 s per request.

- **The volumes:** the 3-month window of r/MechanicalKeyboards holds about 3,400 posts and 38,000 comments
  (`time_series`).
- **Posts alone:** a full scan of the posts needs about 35 requests per subreddit, about 70 s.
- **Comments:** a full scan needs about 380 requests per subreddit, about 13 minutes. That is why comments are
  sampled.
- **To count more:** `max_requests` goes up to 100. The other ways are a narrower window, or `in=posts`.

## Eval results

All final runs were on 2026-11-20 and 2026-11-21 with Claude Code 2.1.311, the default model and Sonnet as judge.
Each case ran 3 times with the plugin and 3 times without it.

| Case | With the plugin | Without | Notes |
|---|---|---|---|
| `share-link` | 3/3 | 0/3 | |
| `find-subs` | 2/3 (live bar: 2 of 3) | 0/3 | the miss gave r/Coffee's subscribers but not its posts per day, though the tool had returned them |
| `trending` | 3/3 | 0/3 | all 3 runs picked AskReddit, worldnews, news, technology, gaming and movies, and labelled the method |
| `keyboard` | 3/3 | 0/3 | beats baseline; Keychron came first in every run |

**`find-subs`, first final run:** 2 of 3 with-plugin runs passed. The third run, and every baseline run, ended at
once with "Failed to authenticate: OAuth token revoked". That was a credential problem in the eval runner, not
the plugin. The case then ran again in full, and that run is the score in the table.

**Fixed during development:** these needed changes before they passed.

- **`find-subs`:** Claude did not call `subreddit_info`, so it had no posts per day. Now `find_subreddits`
  attaches posts per day to its 3 largest results.
- **`keyboard`:** the answer cited 1 thread link where the case needs 3. Now the tool's description and its
  result notes ask Claude to cite the example threads.

## Probe findings

Session 4 used 22 probe requests, 5–7 s apart, plus 4 for its live smoke test. The saved responses are in
`tests/fixtures/discovery/`.

| Endpoint | Result | What the tools do |
|---|---|---|
| `subreddits/search?subreddit_prefix=espresso` | first try: 422 in 0.31 s (load shedding); 40 s later: 200 in 1.1 s | `find_subreddits`: the client's 422 retry covers it |
| `subreddits/search?subreddit=Coffee` | 200, 0.97 s; full object with `_meta` totals (`num_posts`, `num_comments`); `retrieved_on` 2025-02-14 | subscriber counts are labelled with their snapshot date |
| `subreddits/search?min_subscribers=500000&limit=100` | 200 in **13.6 s**, 900 KB; the 100th largest has 7.7 M subscribers | no keyword-only topic scan over the largest subreddits: too slow, and r/espresso (650 k) is far below the top 100 |
| `time_series?key=r/espresso/posts/count&precision=day` | 200, 0.4–1.5 s; one point per UTC day; the newest point was 2026-11-19, 1–2 days behind | posts and comments per day for `subreddit_info` and `find_subreddits` |
| `subreddits/rules`, `subreddits/wikis/list`, `subreddits/wikis?paths=` | 200, 0.4–0.5 s each; the wiki content is HTML-escaped (`&gt;`) | the tools unescape it |
| `users/search?author=<the wi7uhk author>` | 200, 1.5 s; `_meta` with counts, karma, first and last activity | `get_user` |
| `users/interactions/subreddits` | 200, 2.9 s | `get_user` |
| `comments/search?subreddit=MechanicalKeyboards&after=-24h&limit=100` | 200, 1.25 s; the 100 comments covered 17 h | `trending_posts` |
| `comments/search?…&body=keychron` (3 months) | **200**, 3.4 s, 100 matches back to 2026-11-09 | works this time, but needs many pages per term; not used |
| `comments/search/aggregate?…&body=keychron&aggregate=created_utc&frequency=month` | 200, 2.6 s, **every count 0** | wrong answer: no tool uses the aggregates |
| `short_links?paths=/r/running/s/3TzXiyxaMD` (the README example) | resolved, 2.6 s, `found_in: t1_kfrotay` | `resolve_share_link` |
| `short_links` for 3 `/r/buildapc/s/…` links taken from post `url` fields | **empty** | the archive knows only share links it saw in archived content; the tool says so |
| `short_links?paths=/r/running/s/0MH2aME2Z9` | resolved to comment `k1unwm1` in post `16puhb3` | the `share-link` eval case |

## Helper change requests (for the coordinating session)

These are in the shared client. Session 4 did not change them.

1. **`limit` cap:** `ArcticShiftClient._prepare_params` caps `limit` at 100 on every path that ends in
   `/search`. But `subreddits/search` and `users/search` allow 1–1000. `find_subreddits` therefore asks for at
   most 100 name matches.
2. **No `fields=` whitelist for subreddits:** the client checks `fields=` against the post and comment names
   only. So the subreddit fields (`display_name`, `subscribers`, `public_description`, `over18`, …) are refused,
   and `subreddits/search` must ask for full objects (about 9 KB per subreddit). A `SUBREDDIT_FIELDS` whitelist
   would cut the payload.
3. **No request counter per call:** `requests_used` comes from `client.request_count`, which counts the whole
   client. Two tool calls that run at the same time would count each other's requests. A counter per call would
   fix it.
