---
plugins: ["../.."]
description: >-
  Live. Subreddit discovery is by name prefix only (T12). Claude should find r/espresso and
  r/Coffee by name, give subscriber counts and posts per day (subreddit_info), and not claim a
  topic search.
tags: [session-4, live, real-server]
max_turns: 20
timeout_seconds: 480
allowed_tools: [Read, Glob, Grep, WebFetch, WebSearch, Bash, ToolSearch, "mcp__plugin_reddit_reddit__*"]
---
Which subreddits should I follow for home espresso?
