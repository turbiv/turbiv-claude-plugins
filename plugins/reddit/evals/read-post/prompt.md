---
plugins: ["../.."]
description: >-
  Summarize one known r/buildapc post from its URL. Live: the real MCP server reads Arctic
  Shift (needs --allow-real-servers and the mcp__plugin_reddit_reddit__* grant). Claude must
  read it with get_thread, report the archived comments (22, 9 top-level) rather than the stale
  num_comments of 2, give the date, label the score as a snapshot, and cite the permalink.
tags: [session-3, live, beats-baseline]
max_turns: 12
timeout_seconds: 400
allowed_tools: [Read, Glob, Grep, WebFetch, WebSearch, Bash, ToolSearch, "mcp__plugin_reddit_reddit__*"]
---
Summarize this post: https://www.reddit.com/r/buildapc/comments/wi7uhk/intel_9900k_underclockingpower_limit_experiments/
