# Reddit research MCP: use-case evals

These cases test the plugin the way a user uses it: a real prompt to Claude, with graders on the answer and the tool calls.
They run with Claude Code's eval runner: `claude plugin eval plugins/reddit`.

## Rules

- Each case is a folder `plugins/reddit/evals/<id>/` with `case.yaml` (or `prompt.md` plus `graders/*.md`).
  Run `claude plugin eval init --bare <id>` for a blank template.
- The session that builds a case's tools writes that case and makes it pass. The "Owner" column gives the session.
- Session 5 runs the full suite and records the scores in `plugins/reddit/evals/RESULTS.md`.
- The runner also runs every case once without the plugin and reports the score difference (`--ablation with-without`, the default).
  The cases marked "Beats baseline" must score higher with the plugin than without it.
- Live cases need the real MCP server: `--mocks off`. Arctic Shift is unreliable, so live cases pass at 2 of 3 runs.
  Mocked cases must pass 3 of 3.
- Graders in every case:
  - No tool call goes to reddit.com.
  - Every factual claim about a post cites a permalink.
  - The answer says the data comes from an archive.

## Cases

| ID | Prompt | Owner | Type | Pass criteria |
|---|---|---|---|---|
| `read-post` | "Summarize this post: https://www.reddit.com/r/buildapc/comments/wi7uhk/intel_9900k_underclockingpower_limit_experiments/" | 3 | Live, beats baseline | Calls `get_thread` with ID `wi7uhk`. The summary matches the post body and its 2 comments. It does not invent more comments. It gives the date (2022-08-07) and labels the score (9) as a snapshot. |
| `find-post` | "I want to know what power limits I should set for my Intel i9 9900K." | 2 + 5 | Live, beats baseline | Calls `deep_search` with at least 2 concept groups (the CPU model, and power-limit terms) over at least 2 fitting subreddits (r/buildapc, r/intel, r/overclocking). `wi7uhk` is in its candidates, and the answer cites it. Fallback, which passes with a note: Claude's web search finds the URL, then the plugin reads it. |
| `trending` | "What is currently trending on Reddit?" | 4 | Live | Says that Reddit's `hot` and `r/all` are not available from an archive. Asks for a topic, or picks a set of large subreddits and says which. Ranks posts by recent comment activity and labels that method. Does not present the list as Reddit's own "hot". |
| `keyboard` | "What is the most recommended mechanical keyboard on Reddit in the last 3 months?" | 4 + 5 | Live, beats baseline | Uses `count_mentions` over at least 2 subreddits. Gives mention counts and at least 3 thread links. States the exact date window. |
| `find-subs` | "Which subreddits should I follow for home espresso?" | 4 | Live | Lists r/espresso and r/Coffee with subscriber counts and posts per day. Does not claim topic search. |
| `most-discussed` | "What were the 5 most discussed posts in r/buildapc last month?" | 2 | Live | Sorts by comment count on the client. States the window, the number of posts scanned, and any truncation. |
| `thread-follow-up` | Turn 1: `read-post`. Turn 2: "What did the commenters say, and did OP reply?" | 3 | Live | Reads the comment tree. Reports only the comments that exist. Says correctly whether OP replied. |
| `search-syntax` | "Find posts in r/MechanicalKeyboards with the flair 'Help' about key chatter from 2025." | 2 | Live | Maps the flair to `link_flair_text` and 2025 to an absolute date range. Every result is from 2025. |
| `share-link` | "Open this link: https://www.reddit.com/r/<sub>/s/<code>" | 4 | Live | Resolves the share link to the right post. Session 4 picks a real link and writes it into the case. |
| `global-search` | "Search all of Reddit for 'Framework laptop hinge'." | 2 | Live | Says that the archive has no global keyword search. Picks fitting subreddits (for example r/framework) and searches them. |
| `today-top` | "Show the top posts of today in r/buildapc." | 2 | Mocked | Refuses, or warns that scores of posts under about 36 h are not final. Does not rank by score 1 or 0. |
| `write-refusal` | "Reply to that thread and say thanks." | 1 | Mocked | Says that the plugin is read-only. Calls no tool that could write. |
| `archive-down` | Any search prompt, with the Arctic Shift base URL set to an unreachable host. | 1 | Mocked | Reports "archive unavailable". Does not fall back to reddit.com. Does not invent an answer. |
| `no-such-sub` | "What's new in r/thisdoesnotexist12345?" | 2 | Mocked | Says clearly that the subreddit is not in the archive, or that it is private or quarantined. Does not invent posts. |

## Facts for the read-post and find-post cases

**Fact:** checked against Arctic Shift on 2026-11-21.

- `wi7uhk`: "Intel 9900K Underclocking/Power Limit Experiments", r/buildapc, by u/willswill.
- Created 2022-08-07 (`created_utc` 1659849574). Score 9, 2 comments.
- `posts/search?subreddit=buildapc&title=9900k` returned HTTP 200 in 7.4 s. The results were newest first and all from 2026, so the 2022 post is far back in the results.
- Two narrower queries returned HTTP 422 `"Timeout. Maybe slow down a bit"` in 0.35 s:
  - the same `title` search with `after=2022-08-01&before=2022-09-01`
  - `title=9900k power limit`

- `title=9900k&before=2022-08-10` returned `wi7uhk` as result 2 of 25. So a time-window walk with one anchor term reaches it.
- `query=9900k` with a 2022 window returned HTTP 200, and also matched posts that mention 9900K only in the body.
- These returned 422:
  - `title=underclocking` with no window
  - a per-year count aggregate for `title=9900k`

**Assumption:** r/buildapc has 1,000–3,000 posts with 9900K in the title from 2018 to 2026. That is 10–30 pages, which fits the default `max_requests=30`. Session 2 measures it.
