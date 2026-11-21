---
plugins: ["../.."]
description: >-
  Live. A request for a Reddit-wide keyword search. The archive has none: Claude must say so,
  pick fitting subreddits (for example r/framework), and search those.
  Run with --allow-tools "mcp__plugin_reddit_reddit__*".
tags: [session-2, live]
runs: 3
max_turns: 15
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, ToolSearch, "mcp__plugin_reddit_reddit__*"]
---
Search all of Reddit for 'Framework laptop hinge'.
