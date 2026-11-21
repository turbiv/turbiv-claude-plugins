# reddit

Free, keyless, read-only Reddit research for Claude. It is an MCP server over
[Arctic Shift](https://github.com/ArthurHeitmann/arctic_shift), a third-party Reddit archive, plus a research
skill that tells Claude in which order to use the tools.

- It is not live Reddit. Every result says so.
- It never contacts reddit.com. It talks only to the Arctic Shift API host and its status host.
- It has no API key, no login and no write tools. It cannot post, reply, vote or message.

Ask Claude things like "What is the most recommended mechanical keyboard on Reddit in the last 3 months?",
"Summarize this thread: https://www.reddit.com/r/…/comments/…/" or "Which subreddits should I follow for
home espresso?".

## Install

You need [uv](https://docs.astral.sh/uv/) on your `PATH`. On first start, uv installs Python 3.12 and the
dependencies into the plugin folder.

```bash
claude plugin marketplace add turbiv/turbiv-claude-plugins
```

```bash
claude plugin install reddit@turbiv-claude-plugins
```

Start a new Claude Code session. The tools are named `mcp__plugin_reddit_reddit__<tool>`, and the skill is
`reddit:research`.

## The research skill

`reddit:research` loads when you ask what Reddit says about something. It sets this order:

1. Find subreddits by name (`find_subreddits`).
2. Check their activity (posts per day).
3. Search or list posts.
4. Count mentions, for "most recommended" questions.
5. Read the top threads.
6. Cite each post or comment by its permalink, and state the data limits: the archive source, the date
   window, whether a scan was a sample, and that scores are snapshots.

To find one old thread, it uses `deep_search` with 1–2 subreddits per call and follows the resume hint. If the
archive search is cut short or empty, it uses Claude's web search (when you have it) for candidate Reddit URLs,
then reads them through the plugin. It treats all Reddit text as data, not as instructions.

## Tools

Each example is what Claude would send. Dates are absolute in the results.

| Tool | What it does | Example |
|---|---|---|
| `archive_status` | Is the archive up, and how fresh is it? | `{}` → "Newest post is 25 s old; comments lag 2 min." |
| `list_posts` | Posts in subreddits: `new` and `old` from the archive; `top`, `comments` and `controversial` ranked here over a bounded, labelled scan | `{"subreddits": ["buildapc"], "sort": "comments", "time": "month"}` |
| `search_posts` | Keyword search in named subreddits, with Reddit operators (`author:`, `flair:`, `title:`, `NOT`, `OR`, …). Falls back to a labelled local scan when the archive refuses | `{"subreddits": ["MechanicalKeyboards"], "query": "flair:Help chatter", "after": "2025", "before": "2025"}` |
| `deep_search` | Finds an older or loosely worded post: AND-of-OR concept groups, a backward walk through time windows, local fuzzy matching | `{"concepts": [["9900k", "i9-9900k"], ["power limit", "PL1", "undervolt"]], "subreddits": ["buildapc", "intel"]}` |
| `get_posts` | Full posts by ID or URL, up to 2,000 per call | `{"ids_or_urls": ["wi7uhk"]}` |
| `get_thread` | A post with its comment tree, sorted `top`, `new` or `old`, and the real archived comment count | `{"url_or_id": "https://www.reddit.com/r/buildapc/comments/wi7uhk/"}` |
| `expand_comments` | Loads the comments behind `more` stubs | `{"post_id": "wi7uhk", "more_ids": ["jqqr5hr"]}` |
| `get_comment_context` | One comment with its parents and replies | `{"comment_id_or_url": "jqqr5hr", "context": 3}` |
| `search_comments` | Comment search in subreddits, a thread or an author's comments (words, `"phrase"`, `OR`, `-exclude`) | `{"subreddits": ["buildapc"], "query": "undervolt OR underclock", "time": "year"}` |
| `find_subreddits` | Subreddits by name or prefix (not by topic), largest first, with posts per day for the top 3 | `{"name_or_prefix": "espresso"}` |
| `subreddit_info` | Subscribers, description, posts and comments per day, rules, wiki pages | `{"subreddit": "espresso"}` |
| `read_wiki` | A subreddit wiki page, in parts | `{"subreddit": "espresso", "page": "faq"}` |
| `get_user` | A user's archived posts, comments and active subreddits (stale archive karma, no account age) | `{"username": "example_user", "time": "year"}` |
| `resolve_share_link` | Opens `/r/<sub>/s/<code>` share links through the archive's own table | `{"url": "https://www.reddit.com/r/running/s/0MH2aME2Z9"}` |
| `trending_posts` | Posts with the most new comments in the last N hours. This is "recent comment activity", not Reddit's hot | `{"subreddits": ["buildapc", "pcmasterrace"], "hours": 24}` |
| `count_mentions` | How often terms are mentioned, and in how many threads, over a window; sampled and labelled when the window is big | `{"subreddits": ["MechanicalKeyboards", "keyboards"], "terms": ["Keychron", "Wooting", "HHKB\|Happy Hacking"], "time": "3 months"}` |

## What an archive cannot do

- **Hot, rising and best:** these need live votes and Reddit's own formulas. There is also no front page, r/all
  or r/popular. `trending_posts` ranks by recent comment activity instead, and says so.
- **Relevance:** the archive returns matches in time order only.
- **Global search:** there is no keyword search across all of Reddit. Name a subreddit or an author. The
  archive's keyword search also often refuses queries under load; the tools then fall back to a labelled scan.
- **Live scores:** each post or comment keeps the score it had at one snapshot, about 1.5–2 days after posting.
  `score_status` says whether a score is that `snapshot` or the first value (`initial`, usually 1 or 0). A
  post's `num_comments` is a stale early value; `get_thread` gives the real archived count.
- **Gaps:** private and quarantined subreddits are missing. So are posts AutoModerator removed at once and
  users who opted out. Since October 2026 the archive expects to hold about 90–95 % of comments.
- **Big counts:** a busy subreddit has tens of thousands of comments a month. Counts over big windows come from
  an even sample and are labelled as estimates.

## The March 2027 risk

Reddit's remaining public Data API access ends in March 2027. Arctic Shift's live ingest depends on that API.
Its maintainer has said he is not sure yet what will happen. The likely outcome is that the history up to 2027
stays searchable and new posts stop arriving. The server is built for that: `archive_status` and every result
say how old the newest archived item is, and warn when ingest looks stopped. There is no other source: the
server will not fall back to reddit.com.

Arctic Shift is run by one volunteer, on donations. It has outages. When it is down, the tools say
"archive unavailable" and stop.

## Use

- **For personal, non-commercial research only.** This project makes no claim of compliance with Reddit's
  terms. Passing Reddit content to an AI model is a grey zone.
- **Be kind to the archive.** The server sends one request at a time, at least 1 s apart, and caches answers.
  For bulk data, use the Arctic Shift monthly dumps, not this server.
- **Reddit text is untrusted.** Posts and comments can contain text aimed at AI tools. Every result that holds
  Reddit text labels it as data, not instructions. The server also removes invisible text (zero-width and bidi
  characters, other format characters, HTML comments) and counts it in `stripped_invisible`, and marks items
  whose text looks like an instruction to an AI tool with `possible_injection`. It never hides an item.
- **Keep permission prompts on.** During Reddit research, keep Claude Code's permission prompts for Bash, Write
  and WebFetch, and do not use bypass mode: a post that tricks Claude into a command, a file write or a fetch
  then still needs your yes.

## Settings

Environment variables (each also reads an `EVAL_` copy, for evals):

| Variable | Default | Meaning |
|---|---|---|
| `REDDIT_MCP_BASE_URL` | `https://arctic-shift.photon-reddit.com/api` | archive API; a Reddit host is refused |
| `REDDIT_MCP_STATUS_URL` | `https://status.arctic-shift.photon-reddit.com/api` | status feed |
| `REDDIT_MCP_MIN_INTERVAL` | `1.0` | seconds between requests, at least 0.5 |
| `REDDIT_MCP_TIMEOUT` | `30` | seconds per request |
| `REDDIT_MCP_CACHE` | `~/.cache/reddit-mcp/cache.sqlite3` (or under `$XDG_CACHE_HOME`) | cache file, or `off` |
| `REDDIT_MCP_CACHE_TTL` | `600` | seconds, for data that can still change |
| `REDDIT_MCP_CACHE_MAX_MB` | `200` | cache size cap; the oldest answers are deleted first |

The cache holds only archive answers (public Reddit data). Delete the file at any time.
Details: [`docs/architecture.md`](docs/architecture.md).

## Development

```bash
uv run pytest
```

The live tests need `REDDIT_MCP_LIVE=1`. Evals: [`evals/README.md`](evals/README.md), scores:
[`evals/RESULTS.md`](evals/RESULTS.md). Probe results: [`docs/probes.md`](docs/probes.md). Review:
[`docs/review.md`](docs/review.md).
