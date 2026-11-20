# reddit

Free, keyless, read-only Reddit research for Claude. It is an MCP server over
[Arctic Shift](https://github.com/ArthurHeitmann/arctic_shift), a third-party Reddit archive.
It is not live Reddit, and it never contacts reddit.com.

> **Status:** version 0.1.0 is the foundation. It has the archive client, the cache, the shared helpers and one tool,
> `archive_status`. The listing, search, thread, user and mention tools come next. This README is completed with
> them.

## Install

You need [uv](https://docs.astral.sh/uv/) on your `PATH`. On first start, uv installs Python 3.12 and the
dependencies into the plugin folder.

```bash
claude plugin marketplace add turbiv/turbiv-claude-plugins
```

```bash
claude plugin install reddit@turbiv-claude-plugins
```

## Tools

| Tool | What it does |
|---|---|
| `archive_status` | Is the archive up, and how fresh is it? "Newest post is 25 s old; comments lag 2 min; scores freeze at 36 h." |

## What an archive cannot do

- **Live scores:** each post or comment keeps the score it had at one snapshot, about 1.5–2 days after posting.
  `score_status` says whether a score is that snapshot or the first value (1 or 0).
- **Ranking:** there is no `hot`, `rising`, `best`, relevance ranking, front page, r/all or r/popular.
- **Global search:** there is no keyword search across all of Reddit. Name a subreddit or an author.
- **Gaps:** private and quarantined subreddits are missing. So are posts AutoModerator removed at once and
  users who opted out. Since October 2026 the archive expects to hold about 90–95% of comments.

## Settings

Environment variables: `REDDIT_MCP_BASE_URL`, `REDDIT_MCP_STATUS_URL`, `REDDIT_MCP_MIN_INTERVAL` (seconds between
requests, at least 0.5, default 1), `REDDIT_MCP_TIMEOUT`, `REDDIT_MCP_CACHE` (a file path, or `off`) and
`REDDIT_MCP_CACHE_TTL`. Details: [`docs/architecture.md`](docs/architecture.md).

## Use

For personal, non-commercial research only. Arctic Shift is a free service run by volunteers, so this server
sends one request at a time, at least 1 s apart. For bulk data, use the Arctic Shift monthly dumps. This project
makes no claim of compliance with Reddit's terms.

## Development

```bash
uv run pytest
```

The one live test needs `REDDIT_MCP_LIVE=1`. Evals: [`evals/README.md`](evals/README.md). Live probe results:
[`docs/probes.md`](docs/probes.md).
