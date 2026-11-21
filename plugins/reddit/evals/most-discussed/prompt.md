---
plugins: ["../.."]
description: >-
  Live. "Most discussed" means a client-side ranking by comment count over a bounded scan of a
  large subreddit's month. The answer must state the window, the number of posts scanned, and
  any truncation or sampling. Run with --allow-tools "mcp__plugin_reddit_reddit__*".
tags: [session-2, live]
runs: 3
max_turns: 15
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, ToolSearch, "mcp__plugin_reddit_reddit__*"]
---
What were the 5 most discussed posts in r/buildapc last month?
