---
plugins: ["../.."]
description: >-
  Live, beats baseline. The main use case: count mentions of candidate keyboards over a 3-month
  window in at least 2 keyboard subreddits (count_mentions), then answer with counts, thread
  links and the exact date window. A bounded, possibly sampled scan of the archive.
tags: [session-4, session-5, live, real-server, beats-baseline]
max_turns: 24
timeout_seconds: 720
allowed_tools: [Read, Glob, Grep, WebFetch, WebSearch, Bash, ToolSearch, "mcp__plugin_reddit_reddit__*"]
---
What is the most recommended mechanical keyboard on Reddit in the last 3 months?
